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
import random 
import platform 
from PIL import Image
from datetime import datetime, timedelta

# --- [설정] 페이지 기본 설정 ---
st.set_page_config(page_title="재미나이 AI 급등주 사냥꾼", layout="wide")

# --- [한글 폰트 설정] ---
def configure_korean_font():
    system_name = platform.system()
    if system_name == 'Windows':
        font_family = 'Malgun Gothic'
    elif system_name == 'Darwin':
        font_family = 'AppleGothic'
    else:
        font_family = 'NanumGothic'

    plt.rc('font', family=font_family)
    plt.rc('axes', unicode_minus=False)
    return font_family

korean_font = configure_korean_font()

# --- [사이드바] ---
with st.sidebar:
    st.header("🔑 설정")
    api_key = st.text_input("Google API Key", type="password")
    if api_key:
        genai.configure(api_key=api_key)
    st.info("모델: gemini-2.5-flash")

# --- [함수 1] 뉴스 수집기 ---
def get_market_news():
    url = "https://news.google.com/rss/topics/CAAqIggKIhxDQkFTRHdvSkwyMHZNR2RtY0hNekVnSnJieWdBUAE?hl=ko&gl=KR&ceid=KR%3Ako"
    try:
        response = requests.get(url)
        root = ET.fromstring(response.content)
        headlines = [item.find('title').text for item in root.findall('.//item')[:10]]
        return headlines
    except:
        return ["뉴스 수집 실패"]

# --- [함수 2] 시황 분석 ---
def analyze_market_trend(headlines):
    model = genai.GenerativeModel('gemini-2.5-flash')
    news_text = "\n".join(headlines)
    prompt = f"""
    당신은 펀드매니저입니다. 뉴스 헤드라인을 보고 
    오늘 시장 핵심 테마 3가지와 조언을 '한 줄'로 아주 짧게 요약하세요.
    \n[뉴스]\n{news_text}
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "AI 분석 실패"

# --- [함수 3] 사냥개: 급등주 포착 ---
def hunt_candidates():
    try:
        df_krx = fdr.StockListing('KRX')
    except:
        return []

    # 데이터 청소
    for col in ['Close', 'Volume', 'ChagesRatio']:
        if df_krx[col].dtype == 'object':
            df_krx[col] = df_krx[col].astype(str).str.replace(',', '')
        df_krx[col] = pd.to_numeric(df_krx[col], errors='coerce')
    
    df_krx.dropna(subset=['Close', 'Volume', 'ChagesRatio'], inplace=True)

    # [필터] 거래량 폭발 & 상승세
    active_stocks = df_krx[
        (df_krx['Volume'] > 100000) & 
        (df_krx['Close'] > 2000) &
        (df_krx['ChagesRatio'] > 3) & 
        (df_krx['ChagesRatio'] < 25)
    ]
    
    if len(active_stocks) > 30:
        candidates_pool = active_stocks.sample(n=30)
    else:
        candidates_pool = active_stocks
    
    candidates = []
    progress_bar = st.progress(0, text="🔫 급등주 조준 중...")
    
    for i, row in enumerate(candidates_pool.itertuples()):
        progress_bar.progress((i + 1) / len(candidates_pool))
        try:
            code = row.Code
            name = row.Name
            
            # 80일치 데이터
            df = fdr.DataReader(code, datetime.today() - timedelta(days=80), datetime.today())
            if len(df) < 20: continue

            # [조건] 거래량 2배 급증 + 정배열 + 양봉
            vol_today = df['Volume'].iloc[-1]
            vol_yesterday = df['Volume'].iloc[-2]
            ma5 = df['Close'].rolling(5).mean().iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            
            if (vol_today > vol_yesterday * 2.0) and (ma5 > ma20) and (df['Close'].iloc[-1] >= df['Open'].iloc[-1]):
                candidates.append({'code': code, 'name': name, 'df': df})
            
            if len(candidates) >= 3: break
        except:
            continue
            
    progress_bar.empty()
    return candidates

# --- [함수 4] 차트 이미지 생성 ---
def create_chart_image(df, stock_name):
    buf = io.BytesIO()
    # 한글 폰트 적용 스타일
    korean_style = mpf.make_mpf_style(base_mpf_style='yahoo', rc={'font.family': korean_font})
    mpf.plot(df, type='candle', volume=True, mav=(5, 20),
             title=f"{stock_name}", style=korean_style, savefig=buf)
    buf.seek(0)
    return Image.open(buf)

# --- [함수 5] AI 최종 심사 (요약 버전) ---
def final_judgment(candidates, market_trend):
    results = []
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    for stock in candidates:
        img = create_chart_image(stock['df'], stock['name'])
        
        # [핵심 수정] 프롬프트에 '짧게' 요청 추가
        prompt = f"""
        [시장 트렌드] {market_trend}
        [종목] {stock['name']}
        
        차트를 보고 다음 3가지만 **핵심 위주로 아주 짧게(총 5줄 이내)** 요약하세요.
        오른쪽 차트 이미지 높이와 비슷하게 맞추기 위함입니다.
        
        1. 💥 거래량 의미 (매집/과열)
        2. 🎯 전략 (목표가/손절가)
        3. 🏆 등급 (S/A/B)
        """
        try:
            response = model.generate_content([prompt, img])
            results.append(response.text)
        except:
            results.append("분석 실패")
    return results

# --- [메인 UI] ---
st.title("🦅 대장님의 '급등주' 저격수")

if st.button("🔥 급등주 발굴 시작", type="primary"):
    if not api_key:
        st.error("API 키를 입력하세요!")
    else:
        # 1. 시황
        with st.spinner("📰 뉴스 분석 중..."):
            headlines = get_market_news()
            trend = analyze_market_trend(headlines)
        st.info(f"📊 시황 요약: {trend[:100]}...")

        # 2. 발굴
        with st.spinner("🐕 급등주 사냥 중..."):
            candidates = hunt_candidates()
            
        if not candidates:
            st.warning("조건에 맞는 강력한 놈이 없습니다. 다시 시도해보세요.")
        else:
            # 3. 분석
            with st.spinner("⚖️ AI 정밀 심사 중..."):
                reports = final_judgment(candidates, trend)
            
            st.divider()
            for i, stock in enumerate(candidates):
                # [핵심 수정] 현재가 표시 추가
                current_price = stock['df']['Close'].iloc[-1]
                st.subheader(f"📌 {stock['name']} (현재가: {int(current_price):,}원)")
                
                c1, c2 = st.columns([1, 1.5])
                with c1: st.markdown(reports[i])
                with c2: st.image(create_chart_image(stock['df'], stock['name']))
                st.divider()
