import streamlit as st
import matplotlib
matplotlib.use('Agg') # 무한 로딩 방지
import matplotlib.pyplot as plt
import mplfinance as mpf
import FinanceDataReader as fdr
import google.generativeai as genai
import plotly.graph_objects as go
import io
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from PIL import Image
from datetime import datetime, timedelta

# --- [설정] ---
st.set_page_config(page_title="재미나이 풀오토 주식비서", layout="wide")

# --- [사이드바] ---
with st.sidebar:
    st.header("🔑 설정")
    api_key = st.text_input("Google API Key", type="password")
    if api_key:
        genai.configure(api_key=api_key)
    st.info("모델: gemini-2.5-flash")

# --- [함수 1] 뉴스 수집기 (구글 뉴스 RSS) ---
def get_market_news():
    # 구글 뉴스 '경제' 섹션 RSS (한국)
    url = "https://news.google.com/rss/topics/CAAqIggKIhxDQkFTRHdvSkwyMHZNR2RtY0hNekVnSnJieWdBUAE?hl=ko&gl=KR&ceid=KR%3Ako"
    try:
        response = requests.get(url)
        root = ET.fromstring(response.content)
        
        headlines = []
        # 상위 15개 뉴스 제목만 가져옴
        for item in root.findall('.//item')[:15]:
            title = item.find('title').text
            headlines.append(title)
        return headlines
    except:
        return ["뉴스 수집 실패 (네트워크 에러)"]

# --- [함수 2] 뇌: 시황 분석 및 섹터 선정 ---
def analyze_market_trend(headlines):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    news_text = "\n".join(headlines)
    
    prompt = f"""
    당신은 30년 경력의 펀드매니저입니다.
    아래는 현재 실시간 주요 경제 뉴스 헤드라인입니다.

    [뉴스 헤드라인]
    {news_text}

    위 뉴스를 종합했을 때, **오늘/내일 주식시장에서 가장 주목받을 핵심 테마(섹터) 3가지**는 무엇입니까?
    
    출력 형식:
    1. **테마명**: (선정 이유 1줄)
    2. **테마명**: (선정 이유 1줄)
    3. **테마명**: (선정 이유 1줄)
    
    마지막에 **"투자자들을 위한 한 줄 조언"**도 덧붙여주세요.
    """
    
    response = model.generate_content(prompt)
    return response.text

# --- [함수 3] 사냥개: 차트 우량주 발굴 ---
def hunt_candidates():
    # 코스피/코스닥 시총 상위 40개 (속도 타협)
    kospi = fdr.StockListing('KOSPI')[:30]
    kosdaq = fdr.StockListing('KOSDAQ')[:10]
    stocks = pd.concat([kospi, kosdaq])
    
    candidates = []
    
    # 진행 상황 표시용
    progress_bar = st.progress(0, text="미어캣처럼 시장을 감시 중...")
    total = len(stocks)
    
    for i, row in stocks.iterrows():
        progress_bar.progress((i + 1) / total)
        try:
            code = row['Code']
            name = row['Name']
            df = fdr.DataReader(code, datetime.today() - timedelta(days=120), datetime.today())
            
            if len(df) < 60: continue

            # [조건] 
            # 1. 5일선 > 20일선 (정배열 초기)
            # 2. 거래량: 최근 3일 평균이 전보다 죽지 않음
            ma5 = df['Close'].rolling(5).mean().iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            
            if ma5 > ma20:
                candidates.append({'code': code, 'name': name, 'df': df})
        except:
            continue
            
    progress_bar.empty()
    return candidates[:3] # 상위 3개만 추출

# --- [함수 4] 차트 이미지화 ---
def create_chart_image(df, stock_name):
    buf = io.BytesIO()
    mpf.plot(df, type='candle', volume=True, mav=(5, 20),
             title=f"{stock_name}", style='yahoo', savefig=buf)
    buf.seek(0)
    image = Image.open(buf)
    return image

# --- [함수 5] 최종 판결 (종목+시황 매칭) ---
def final_judgment(candidates, market_trend):
    results = []
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    for stock in candidates:
        img = create_chart_image(stock['df'], stock['name'])
        
        prompt = f"""
        [현재 시장 트렌드]
        {market_trend}
        
        [종목 정보]
        종목명: {stock['name']}
        
        위 '시장 트렌드'와 이 종목의 '차트 흐름'을 연결해서 분석해주세요.
        1. 이 종목이 현재 트렌드(뉴스)와 연관성이 있습니까? (없다면 차트 위주로만 분석)
        2. 지금 매수해도 좋습니까?
        
        **매수 추천 등급:** (S급 / A급 / B급)
        **이유:** (짧고 굵게)
        """
        
        try:
            response = model.generate_content([prompt, img])
            results.append(response.text)
        except:
            results.append("분석 실패")
            
    return results

# --- [메인 UI] ---
st.title("🤖 대장님의 '원클릭' 풀오토 비서")
st.markdown("뉴스 확인부터 종목 추천까지, 버튼 하나로 끝냅니다.")

if st.button("🔥 시장 완전 분석 시작 (Click)", type="primary"):
    if not api_key:
        st.error("API 키를 먼저 입력해주세요!")
    else:
        # 1. 뉴스 & 시황 분석
        with st.spinner("📰 1단계: 실시간 뉴스를 읽고 트렌드를 분석 중..."):
            headlines = get_market_news()
            market_trend = analyze_market_trend(headlines)
        
        st.success("뉴스 분석 완료!")
        with st.expander("📊 오늘의 핵심 트렌드 보기 (AI 요약)", expanded=True):
            st.info(market_trend)

        # 2. 종목 발굴
        with st.spinner("🐕 2단계: 트렌드에 맞는 차트 우량주 발굴 중..."):
            candidates = hunt_candidates()
            
        if not candidates:
            st.warning("조건에 맞는 종목을 못 찾았습니다.")
        else:
            # 3. 최종 매칭
            with st.spinner("⚖️ 3단계: 트렌드와 차트를 매칭하여 최종 점수 산출 중..."):
                final_reports = final_judgment(candidates, market_trend)
            
            st.divider()
            st.subheader("🏆 최종 추천 종목")
            
            for i, report in enumerate(final_reports):
                stock_name = candidates[i]['name']
                with st.container():
                    st.markdown(f"### 📌 추천 {i+1}: {stock_name}")
                    c1, c2 = st.columns([1, 1.5])
                    with c1:
                        st.markdown(report)
                    with c2:
                        st.image(create_chart_image(candidates[i]['df'], stock_name))
                    st.divider()
