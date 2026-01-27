import streamlit as st
import matplotlib
# [핵심] 서버에서 창 띄우기 금지 (무한 로딩 방지)
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import mplfinance as mpf
import FinanceDataReader as fdr
import google.generativeai as genai
import io
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import random # 랜덤 뽑기를 위해 추가
from PIL import Image
from datetime import datetime, timedelta

# --- [설정] 페이지 기본 설정 ---
st.set_page_config(page_title="재미나이 AI 랜덤 발굴기", layout="wide")

# --- [사이드바] ---
with st.sidebar:
    st.header("🔑 설정")
    api_key = st.text_input("Google API Key", type="password")
    if api_key:
        genai.configure(api_key=api_key)
    st.info("모델: gemini-2.5-flash")
    st.markdown("---")
    st.markdown("💡 **Tip:** 실행할 때마다 새로운 종목을 발굴합니다.")

# --- [함수 1] 뉴스 수집기 (구글 뉴스 RSS) ---
def get_market_news():
    # 구글 뉴스 '경제' 섹션 RSS (한국)
    url = "https://news.google.com/rss/topics/CAAqIggKIhxDQkFTRHdvSkwyMHZNR2RtY0hNekVnSnJieWdBUAE?hl=ko&gl=KR&ceid=KR%3Ako"
    try:
        response = requests.get(url)
        root = ET.fromstring(response.content)
        headlines = []
        for item in root.findall('.//item')[:10]: # 상위 10개만
            title = item.find('title').text
            headlines.append(title)
        return headlines
    except:
        return ["뉴스 수집 실패 (네트워크 에러)"]

# --- [함수 2] 시황 분석 (Brain) ---
def analyze_market_trend(headlines):
    model = genai.GenerativeModel('gemini-2.5-flash')
    news_text = "\n".join(headlines)
    
    prompt = f"""
    당신은 30년 경력의 베테랑 펀드매니저입니다.
    아래는 실시간 경제 뉴스 헤드라인입니다.

    [뉴스]
    {news_text}

    위 뉴스를 종합해 **오늘 시장을 관통하는 핵심 테마(섹터) 3가지**를 뽑아주세요.
    그리고 투자자에게 필요한 **한 줄 조언**을 남겨주세요.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "AI 분석 실패 (API 키를 확인하세요)"

# --- [함수 3] 사냥개: 랜덤 발굴 (수정버전) ---
def hunt_candidates():
    # 1. 한국 전체 종목 리스트 가져오기
    try:
        df_krx = fdr.StockListing('KRX')
    except Exception as e:
        st.error(f"데이터 가져오기 실패: {e}")
        return []

    # [🚨 핵심 수정] 데이터 청소 시간! 
    # 글자로 된 숫자(예: "2,000")를 진짜 숫자(2000)로 바꿉니다.
    for col in ['Close', 'Volume', 'ChagesRatio']:
        # 만약 데이터가 숫자가 아니라면(object), 쉼표를 제거하고 숫자로 변환
        if df_krx[col].dtype == 'object':
            df_krx[col] = df_krx[col].astype(str).str.replace(',', '')
        # 숫자로 강제 변환 (에러나는 건 NaN 처리)
        df_krx[col] = pd.to_numeric(df_krx[col], errors='coerce')

    # 변환하다가 깨진 데이터(NaN)는 버림
    df_krx.dropna(subset=['Close', 'Volume', 'ChagesRatio'], inplace=True)

    # 2. [필터링] 잡주 걸러내기 & 활발한 종목 찾기
    active_stocks = df_krx[
        (df_krx['Volume'] > 50000) & 
        (df_krx['Close'] > 2000) &
        (df_krx['ChagesRatio'] > -5)
    ]
    
    # 3. [랜덤 뽑기]
    if len(active_stocks) > 20:
        candidates_pool = active_stocks.sample(n=20)
    else:
        candidates_pool = active_stocks
    
    candidates = []
    
    progress_bar = st.progress(0, text="🐕 사냥개가 숲속(전체 종목)을 뒤지고 있습니다...")
    total = len(candidates_pool)
    
    count = 0
    for i, row in candidates_pool.iterrows():
        count += 1
        progress_bar.progress(count / total)
        
        try:
            code = row['Code']
            name = row['Name']
            
            # 최근 120일 데이터
            df = fdr.DataReader(code, datetime.today() - timedelta(days=120), datetime.today())
            
            if len(df) < 60: continue

            # [기술적 분석 필터]
            ma5 = df['Close'].rolling(5).mean().iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            close = df['Close'].iloc[-1]
            open_p = df['Open'].iloc[-1]
            
            # 정배열 & 양봉 조건
            if ma5 > ma20 and close >= open_p:
                candidates.append({'code': code, 'name': name, 'df': df})
                
        except:
            continue
            
    progress_bar.empty()
    return candidates[:3]

# --- [함수 4] 차트 이미지 생성 ---
def create_chart_image(df, stock_name):
    buf = io.BytesIO()
    # 스타일: 'yahoo', 거래량 포함, 이동평균선(5,20,60)
    mpf.plot(df, type='candle', volume=True, mav=(5, 20, 60),
             title=f"{stock_name}", style='yahoo', savefig=buf)
    buf.seek(0)
    image = Image.open(buf)
    return image

# --- [함수 5] 최종 판결 (AI) ---
def final_judgment(candidates, market_trend):
    results = []
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    for stock in candidates:
        img = create_chart_image(stock['df'], stock['name'])
        
        prompt = f"""
        [현재 시장 트렌드]
        {market_trend}
        
        [종목 차트 분석 요청]
        종목명: {stock['name']}
        
        위 '시장 트렌드'와 이 종목의 '차트(캔들, 거래량, 이평선)'를 연결해서 분석하세요.
        이 종목이 현재 트렌드와 무관하더라도, 차트상 매수 기회라면 추천해주세요.
        
        1. **추세:** 상승 초입인가요?
        2. **전략:** 지금 사도 되나요? (목표가/손절가 제시)
        
        **매수 추천 등급:** (S급 / A급 / B급 / 보류)
        """
        
        try:
            response = model.generate_content([prompt, img])
            results.append(response.text)
        except:
            results.append("분석 실패 (AI 응답 오류)")
            
    return results

# --- [메인 UI] ---
st.title("🦅 대장님의 '랜덤 발굴' 투자 비서")
st.markdown("매번 새로운 종목을 찾아냅니다. 우량주뿐만 아니라 **숨은 급등주**를 노립니다.")

if st.button("🔥 시장 완전 분석 시작 (Click)", type="primary"):
    if not api_key:
        st.error("왼쪽 사이드바에 API Key를 먼저 입력해주세요!")
    else:
        # 1. 뉴스 & 시황
        with st.spinner("📰 1단계: 실시간 뉴스를 읽고 시장 분위기 파악 중..."):
            headlines = get_market_news()
            market_trend = analyze_market_trend(headlines)
        
        st.success("시장 분석 완료!")
        with st.expander("📊 오늘의 핵심 시장 테마 보기 (AI 요약)", expanded=True):
            st.info(market_trend)

        # 2. 랜덤 발굴
        with st.spinner("🐕 2단계: 사냥개가 2,000개 종목 중 랜덤으로 냄새를 맡는 중..."):
            candidates = hunt_candidates()
            
        if not candidates:
            st.warning("아쉽게도 이번 사냥에선 조건에 맞는 종목을 못 찾았습니다. 다시 버튼을 눌러보세요! (랜덤이라 매번 다릅니다)")
        else:
            st.success(f"💎 {len(candidates)}개의 숨은 보석을 발견했습니다! 분석을 시작합니다.")
            
            # 3. AI 심사
            with st.spinner("⚖️ 3단계: 차트 정밀 분석 중..."):
                final_reports = final_judgment(candidates, market_trend)
            
            # 4. 결과 출력
            st.divider()
            st.subheader("🏆 오늘의 발굴 종목")
            
            for i, report in enumerate(final_reports):
                stock_name = candidates[i]['name']
                st.markdown(f"### 📌 발굴 {i+1}: {stock_name}")
                
                c1, c2 = st.columns([1, 1.5])
                with c1:
                    st.markdown(report)
                with c2:
                    st.image(create_chart_image(candidates[i]['df'], stock_name))
                st.divider()
