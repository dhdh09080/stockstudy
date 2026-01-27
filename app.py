import streamlit as st
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import google.generativeai as genai
import matplotlib.pyplot as plt
import io
from PIL import Image
from datetime import datetime, timedelta

# --- [설정] 페이지 기본 설정 ---
st.set_page_config(page_title="재미나이 AI 투자 비서", layout="wide")

# --- [사이드바] 설정 ---
with st.sidebar:
    st.header("🔑 설정")
    api_key = st.text_input("Google API Key를 입력하세요", type="password")
    

# --- [함수] 데이터 수집 및 차트 이미지 변환 ---
def get_stock_data(code):
    end_date = datetime.today()
    start_date = end_date - timedelta(days=200) # 약 6개월치
    df = fdr.DataReader(code, start_date, end_date)
    return df

def df_to_image(df, stock_name):
    # AI에게 보여줄 '깔끔한 이미지'를 Matplotlib으로 그립니다.
    # (Plotly는 인터랙티브라 AI에게 이미지로 넘기기 까다로워서, 분석용 이미지는 따로 만듭니다)
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 캔들차트 대신 종가선과 거래량을 간단히 그립니다 (AI는 패턴을 잘 봅니다)
    ax.plot(df.index, df['Close'], label='Price', color='black')
    ax.set_title(f"{stock_name} Chart Analysis")
    ax.grid(True)
    
    # 이미지를 메모리(버퍼)에 저장
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image = Image.open(buf)
    plt.close(fig) 
    return image

# --- [함수] 재미나이(Gemini)에게 분석 요청 ---
def analyze_chart_with_gemini(image):
    if not api_key:
        return "API Key가 필요합니다."
    
    # 대장님의 투자 철학이 담긴 '5대 우선순위' 프롬프트
    prompt = """
    당신은 20년 경력의 베테랑 차트 분석가입니다. 
    제공된 주식 차트 이미지를 보고 다음 5가지 기준으로 엄격하게 분석해주세요.

    1. **추세(Trend):** 현재 상승장인가, 하락장인가? (지지/저항 관점)
    2. **거래량(Volume):** 의미 있는 거래량 변화가 있는가?
    3. **이평선(MA):** 정배열인가, 역배열인가?
    4. **과열 여부:** 단기적으로 너무 급등했거나 급락했는가?
    5. **캔들 패턴:** 특이한 반전 신호가 보이는가?

    최종적으로 다음 형식으로 답변하세요:
    - **종합 점수:** (100점 만점 중 몇 점)
    - **매수 의견:** (강력 매수 / 분할 매수 / 관망 / 매도 중 택 1)
    - **매수 추천가:** (구체적 가격)
    - **손절가:** (이 가격 깨지면 도망쳐야 함)
    - **분석 요약:** (3줄 이내로 핵심만)
    """
    
    # Gemini 2.0 Flash 모델 사용
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    with st.spinner('재미나이의 뇌가 풀가동 중입니다... (약 5초 소요)'):
        response = model.generate_content([prompt, image])
        return response.text

# --- [메인 UI] ---
st.title("📈 대장님의 AI 주식 비서")
st.markdown("종목 코드를 입력하면 **재미나이**가 차트를 보고 분석해줍니다.")

col1, col2 = st.columns([1, 3])

with col1:
    stock_code = st.text_input("종목 코드 입력", value="005930") # 기본값: 삼성전자
    stock_name = st.text_input("종목명 (참고용)", value="삼성전자")
    
    if st.button("🚀 AI 분석 시작", type="primary", use_container_width=True):
        if not api_key:
            st.error("왼쪽 사이드바에 API Key를 먼저 입력해주세요!")
        else:
            try:
                # 1. 데이터 가져오기
                df = get_stock_data(stock_code)
                
                # 2. AI에게 보여줄 이미지 생성
                chart_image = df_to_image(df, stock_name)
                
                # 3. AI 분석 요청
                analysis_result = analyze_chart_with_gemini(chart_image)
                
                # 4. 결과 저장 (화면에 뿌리기 위해)
                st.session_state['result'] = analysis_result
                st.session_state['df'] = df
                st.session_state['stock_name'] = stock_name
                
            except Exception as e:
                st.error(f"에러가 발생했습니다: {e}")

# 결과 출력 화면
if 'result' in st.session_state:
    st.divider()
    r_col1, r_col2 = st.columns([1, 1])
    
    with r_col1:
        st.subheader(f"🤖 재미나이 분석 리포트: {st.session_state['stock_name']}")
        st.markdown(st.session_state['result']) # AI의 답변이 여기에 찍힘
        
    with r_col2:
        # 대장님이 보시기 편한 인터랙티브 차트 (Plotly)
        df = st.session_state['df']
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                        open=df['Open'], high=df['High'],
                        low=df['Low'], close=df['Close'])])
        fig.update_layout(title=f"{st.session_state['stock_name']} 상세 차트", height=600)
        st.plotly_chart(fig, use_container_width=True)
