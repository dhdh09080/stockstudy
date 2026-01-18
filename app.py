import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import random
from datetime import datetime

# 페이지 설정 (넓은 화면 사용)
st.set_page_config(layout="wide", page_title="My Stock Study Lab")

# --- 1. 데이터 로딩 함수 (캐싱으로 속도 향상) ---
@st.cache_data
def get_stock_data(ticker, period="1y"):
    df = yf.download(ticker, period=period)
    return df

@st.cache_data
def get_current_price(ticker):
    # 최신 가격 정보 가져오기
    ticker_obj = yf.Ticker(ticker)
    try:
        data = ticker_obj.history(period='1d')
        if not data.empty:
            return data['Close'].iloc[-1], data['Close'].iloc[-1] - data['Open'].iloc[-1]
        return 0, 0
    except:
        return 0, 0

# --- 2. 오늘의 한 줄 공부 (랜덤 명언/용어) ---
study_notes = {
    "PER (주가수익비율)": "기업이 벌어들이는 이익에 비해 주가가 얼마나 높은지 나타내는 지표. 낮을수록 저평가 가능성!",
    "PBR (주가순자산비율)": "1 미만이면 회사를 다 팔아서 주주에게 나눠줘도 돈이 남는다는 뜻 (청산가치보다 저평가).",
    "RSI (상대강도지수)": "70 이상이면 '너무 많이 샀다(과매수)', 30 이하면 '너무 많이 팔았다(과매도)' 신호.",
    "골든크로스": "단기 이동평균선이 장기 이동평균선을 뚫고 올라가는 것. 보통 매수 신호로 해석.",
    "격언": "공포에 사서 환희에 팔아라.",
    "격언": "무릎에 사서 어깨에 팔아라."
}

# 사이드바
st.sidebar.title("🔍 분석 도구")
selected_ticker = st.sidebar.text_input("분석할 종목 코드 (예: 005930.KS)", value="005930.KS") # 삼성전자 기본

# === 메인 화면 구성 ===

# 1. 헤더 & 오늘의 공부
st.title(f"📈 {datetime.now().strftime('%Y-%m-%d')} 주식 공부 노트")
today_topic, today_desc = random.choice(list(study_notes.items()))
st.info(f"**💡 오늘의 지식: {today_topic}** \n\n {today_desc}")

st.markdown("---")

# 2. 시장 현황 (Macro View)
st.subheader("🌏 오늘 시장 분위기")
col1, col2, col3 = st.columns(3)

# 지수 데이터 (코스피, 코스닥, 환율)
kospi_price, kospi_chg = get_current_price("^KS11")
kosdaq_price, kosdaq_chg = get_current_price("^KQ11")
usd_krw_price, usd_krw_chg = get_current_price("KRW=X")

col1.metric("KOSPI", f"{kospi_price:,.2f}", f"{kospi_chg:,.2f}")
col2.metric("KOSDAQ", f"{kosdaq_price:,.2f}", f"{kosdaq_chg:,.2f}")
col3.metric("USD/KRW", f"{usd_krw_price:,.2f} 원", f"{usd_krw_chg:,.2f} 원", delta_color="inverse")

st.markdown("---")

# 3. 차트 분석 실습 (Technical Analysis)
st.subheader(f"📊 차트 뜯어보기: {selected_ticker}")

# 데이터 가져오기
df = get_stock_data(selected_ticker)

if not df.empty:
    # 차트 옵션 선택
    c1, c2, c3 = st.columns(3)
    show_ma = c1.checkbox("이동평균선 (20일/60일)", value=True)
    show_vol = c2.checkbox("거래량 같이 보기", value=True)
    show_bollinger = c3.checkbox("볼린저 밴드 (변동성 확인)")

    # 캔들 차트 생성
    fig = go.Figure()
    
    # 캔들
    fig.add_trace(go.Candlestick(x=df.index,
                    open=df['Open'], high=df['High'],
                    low=df['Low'], close=df['Close'],
                    name='주가'))

    # 이동평균선 계산 및 추가
    if show_ma:
        ma20 = df['Close'].rolling(window=20).mean()
        ma60 = df['Close'].rolling(window=60).mean()
        fig.add_trace(go.Scatter(x=df.index, y=ma20, line=dict(color='orange', width=1.5), name='20일선(생명선)'))
        fig.add_trace(go.Scatter(x=df.index, y=ma60, line=dict(color='green', width=1.5), name='60일선(수급선)'))

    # 볼린저 밴드 (상단, 하단)
    if show_bollinger:
        ma20 = df['Close'].rolling(window=20).mean()
        std = df['Close'].rolling(window=20).std()
        upper = ma20 + (std * 2)
        lower = ma20 - (std * 2)
        fig.add_trace(go.Scatter(x=df.index, y=upper, line=dict(color='gray', dash='dot'), name='볼린저 상단'))
        fig.add_trace(go.Scatter(x=df.index, y=lower, line=dict(color='gray', dash='dot'), name='볼린저 하단'))

    fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # 데이터 해석 가이드 (공부용 팁)
    with st.expander("🧐 차트 보는 법 가이드 (Click)"):
        st.markdown("""
        * **이동평균선:** 주가가 20일선 위에 있으면 단기 상승 추세, 아래에 있으면 하락 추세일 가능성이 큽니다.
        * **볼린저 밴드:** 주가가 밴드 상단을 뚫으면 '과열', 하단을 뚫으면 '반등 가능성'을 의심해보세요.
        * **거래량:** 주가가 오를 때 거래량이 함께 터져야 '진짜 상승'입니다. 거래량 없는 상승은 속임수일 수 있습니다.
        """)

else:
    st.error("데이터를 불러올 수 없습니다. 종목 코드를 확인해주세요. (한국: 005930.KS, 미국: AAPL)")
