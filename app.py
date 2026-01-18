import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
import random
from datetime import datetime

# 페이지 설정
st.set_page_config(layout="wide", page_title="My Stock Study Lab")

# --- 1. 종목 리스트 가져오기 (이름 -> 코드 변환용) ---
@st.cache_data
def get_stock_list():
    # 한국 주식 전체 리스트 (KRX)
    df_krx = fdr.StockListing('KRX')
    # 필요한 컬럼만 남기기 (종목명, 코드, 시장구분)
    df_krx = df_krx[['Name', 'Code', 'Market']]
    
    # 미국 S&P 500 리스트 (주요 종목)
    df_sp500 = fdr.StockListing('S&P500')
    df_sp500 = df_sp500[['Name', 'Symbol']].rename(columns={'Symbol': 'Code'})
    df_sp500['Market'] = 'USA'
    
    # 두 리스트 합치기
    # 편의를 위해 표시할 이름 포맷 만들기: "삼성전자 (005930)"
    df_krx['Display'] = df_krx['Name'] + " (" + df_krx['Code'] + ")"
    df_sp500['Display'] = df_sp500['Name'] + " (" + df_sp500['Code'] + ")"
    
    return pd.concat([df_krx, df_sp500])

# --- 2. yfinance용 티커 변환 함수 ---
def format_ticker(row):
    code = row['Code']
    market = row['Market']
    
    if market == 'KOSPI':
        return f"{code}.KS"
    elif market == 'KOSDAQ':
        return f"{code}.KQ"
    elif market == 'USA':
        return code # 미국은 그대로
    else:
        # 코스피/코스닥 외(KONEX 등)는 일단 .KS로 시도
        return f"{code}.KS"

# --- 3. 데이터 로딩 및 차트 함수 (기존과 동일) ---
@st.cache_data
def get_stock_data(ticker, period="1y"):
    try:
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(period=period)
        if df.empty: return pd.DataFrame()
        df.index = df.index.tz_localize(None)
        return df
    except:
        return pd.DataFrame()

@st.cache_data
def get_current_price(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        data = ticker_obj.history(period='5d')
        if not data.empty:
            return data['Close'].iloc[-1], data['Close'].iloc[-1] - data['Close'].iloc[-2]
        return 0, 0
    except:
        return 0, 0

# === 사이드바: 종목 검색 기능 구현 ===
st.sidebar.title("🔍 종목 검색")

# 주식 리스트 로딩 (앱 켤 때 한 번만 실행됨)
with st.spinner("종목 리스트를 불러오는 중..."):
    df_stocks = get_stock_list()

# 검색창 (Selectbox) - 타이핑으로 검색 가능
# 기본값은 삼성전자로 설정
default_index = df_stocks[df_stocks['Name'] == '삼성전자'].index[0] if not df_stocks.empty else 0

selected_name = st.sidebar.selectbox(
    "이름으로 검색하세요",
    df_stocks['Display'].values,
    index=int(default_index) if not df_stocks.empty else 0
)

# 선택한 이름에서 실제 코드로 변환
if not df_stocks.empty:
    selected_row = df_stocks[df_stocks['Display'] == selected_name].iloc[0]
    final_ticker = format_ticker(selected_row)
else:
    final_ticker = "005930.KS"

st.sidebar.info(f"선택된 코드: **{final_ticker}**")


# === 메인 화면 (나머지는 동일) ===

# 1. 헤더 & 오늘의 공부
study_notes = {
    "PER": "주가 / 주당순이익. 회사가 버는 돈에 비해 주가가 얼마나 비싼가?",
    "PBR": "주가 / 주당순자산. 회사가 망했을 때 건질 수 있는 돈보다 주가가 싼가?",
    "RSI": "상대강도지수. 70 이상이면 과매수(팔 때?), 30 이하면 과매도(살 때?)",
    "MACD": "이동평균 수렴확산지수. 추세의 전환을 파악할 때 유용함.",
    "양봉/음봉": "빨간색(양봉)은 시가보다 종가가 높음, 파란색(음봉)은 시가보다 종가가 낮음."
}
st.title(f"📈 {datetime.now().strftime('%Y-%m-%d')} 주식 공부 노트")
today_topic, today_desc = random.choice(list(study_notes.items()))
st.info(f"**💡 오늘의 지식: {today_topic}** \n\n {today_desc}")

st.markdown("---")

# 2. 시장 현황
st.subheader("🌏 오늘 시장 분위기")
col1, col2, col3 = st.columns(3)
k_p, k_c = get_current_price("^KS11")
kq_p, kq_c = get_current_price("^KQ11")
u_p, u_c = get_current_price("KRW=X")

col1.metric("코스피", f"{k_p:,.2f}", f"{k_c:,.2f}")
col2.metric("코스닥", f"{kq_p:,.2f}", f"{kq_c:,.2f}")
col3.metric("환율(USD)", f"{u_p:,.2f}원", f"{u_c:,.2f}원", delta_color="inverse")

st.markdown("---")

# 3. 차트 분석
st.subheader(f"📊 {selected_name.split('(')[0]} 차트 분석")

df = get_stock_data(final_ticker)

if not df.empty:
    c1, c2, c3 = st.columns(3)
    show_ma = c1.checkbox("이동평균선 (20/60일)", value=True)
    show_bollinger = c2.checkbox("볼린저 밴드")
    show_vol = c3.checkbox("거래량 (하단)")

    # 캔들차트
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='주가'))

    if show_ma:
        ma20 = df['Close'].rolling(window=20).mean()
        ma60 = df['Close'].rolling(window=60).mean()
        fig.add_trace(go.Scatter(x=df.index, y=ma20, line=dict(color='orange', width=1.5), name='20일선'))
        fig.add_trace(go.Scatter(x=df.index, y=ma60, line=dict(color='green', width=1.5), name='60일선'))

    if show_bollinger:
        ma20 = df['Close'].rolling(window=20).mean()
        std = df['Close'].rolling(window=20).std()
        fig.add_trace(go.Scatter(x=df.index, y=ma20+(std*2), line=dict(color='gray', dash='dot', width=1), name='볼린저 상단'))
        fig.add_trace(go.Scatter(x=df.index, y=ma20-(std*2), line=dict(color='gray', dash='dot', width=1), name='볼린저 하단'))
    
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
    
    # 팁: 거래량 그래프는 별도로 그리는 게 깔끔해서 여기서는 생략하거나 추가 가능
else:
    st.error(f"데이터를 가져올 수 없습니다. ({final_ticker})")
