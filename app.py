import streamlit as st
import matplotlib
# [핵심 1] 무한 로딩 방지: 백그라운드에서만 그림 그리기
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import mplfinance as mpf
import FinanceDataReader as fdr
import google.generativeai as genai
import plotly.graph_objects as go
import io
from PIL import Image
from datetime import datetime, timedelta

# --- [설정] 페이지 기본 설정 ---
st.set_page_config(page_title="재미나이 AI 투자 비서", layout="wide")

# --- [사이드바] API 키 입력 ---
with st.sidebar:
    st.header("🔑 설정")
    api_key = st.text_input("Google API Key를 입력하세요", type="password")
    if api_key:
        genai.configure(api_key=api_key)
    st.info("성공한 모델: gemini-2.5-flash")

# --- [함수 1] 데이터 가져오기 ---
def get_stock_data(code):
    end_date = datetime.today()
    start_date = end_date - timedelta(days=200) # 6개월치
    df = fdr.DataReader(code, start_date, end_date)
    return df

# --- [함수 2] AI에게 보여줄 '전문가용 차트' 만들기 (mplfinance) ---
def create_chart_for_ai(df, stock_name):
    buf = io.BytesIO()
    # [핵심 2] 캔들(candle) + 이동평균선(mav) + 거래량(volume) 모두 포함
    # 스타일: 'yahoo'가 AI 인식률이 좋습니다.
    mpf.plot(df, type='candle', volume=True, mav=(5, 20, 60),
             title=f"{stock_name} (Daily)", style='yahoo',
             savefig=buf)
    buf.seek(0)
    image = Image.open(buf)
    return image

# --- [함수 3] 재미나이(Gemini)에게 분석 요청 ---
def analyze_chart_with_gemini(image):
    if not api_key:
        return "API Key가 필요합니다."
    
    # 대장님의 5대 투자 원칙 프롬프트
    prompt = """
    당신은 20년 경력의 베테랑 기술적 분석가입니다. 
    제공된 주식 차트(캔들, 이동평균선, 거래량 포함)를 보고 다음 5가지 기준으로 엄격하게 분석해주세요.

    1. **추세(Trend):** 현재 주가가 상승 추세인가, 하락 추세인가? (이평선 정배열 여부 확인)
    2. **거래량(Volume):** 의미 있는 대량 거래가 발생했는가? (매수세 유입 확인)
    3. **지지/저항:** 현재 주가가 주요 지지선 근처인가, 저항선 근처인가?
    4. **캔들 패턴:** 바닥권 시그널(망치형 등)이나 고점 시그널이 보이는가?
    5. **전략 수립:** 지금 사야 하는가?

    최종적으로 다음 형식으로 답변하세요:
    - **📊 종합 점수:** (100점 만점 중 몇 점)
    - **💡 투자 의견:** (강력 매수 / 분할 매수 / 관망 / 매도 중 택 1)
    - **🎯 매수 목표가:** (현재가 기준 진입 구간)
    - **🛡️ 손절가:** (이 가격 이탈 시 매도)
    - **📝 3줄 요약:** (분석 핵심 내용)
    """
    
    # [핵심 3] 대장님 계정에서 성공한 모델!
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    with st.spinner('재미나이가 차트를 뚫어지게 보는 중입니다... (약 5초)'):
        response = model.generate_content([prompt, image])
        return response.text

# --- [메인 UI] ---
st.title("📈 대장님의 AI 주식 비서 (Final)")
st.markdown("종목 코드를 입력하면 **캔들, 거래량, 이평선**을 모두 분석해 매매 전략을 짭니다.")

col1, col2 = st.columns([1, 3])

with col1:
    stock_code = st.text_input("종목 코드 입력", value="005930") # 삼성전자
    stock_name = st.text_input("종목명 (참고용)", value="삼성전자")
    
    if st.button("🚀 AI 분석 시작", type="primary", use_container_width=True):
        if not api_key:
            st.error("왼쪽 사이드바에 API Key를 먼저 입력해주세요!")
        else:
            try:
                # 1. 데이터 확보
                df = get_stock_data(stock_code)
                if df.empty:
                    st.error("데이터가 없습니다. 종목 코드를 확인해주세요.")
                else:
                    # 2. AI용 이미지 생성 (백그라운드)
                    ai_image = create_chart_for_ai(df, stock_name)
                    
                    # 3. AI 분석 요청
                    result = analyze_chart_with_gemini(ai_image)
                    
                    # 4. 결과 저장
                    st.session_state['result'] = result
                    st.session_state['df'] = df
                    st.session_state['stock_name'] = stock_name
                
            except Exception as e:
                st.error(f"에러 발생: {e}")

# --- 결과 출력 화면 ---
if 'result' in st.session_state:
    st.divider()
    r_col1, r_col2 = st.columns([1, 1.2]) # 비율 조절
    
    with r_col1:
        st.subheader("🤖 재미나이 분석 리포트")
        st.info(st.session_state['result']) # AI 답변 출력
        
    with r_col2:
        st.subheader(f"📉 {st.session_state['stock_name']} 인터랙티브 차트")
        # 사용자가 보기 편한 '반응형 차트' (마우스로 확대/축소 가능)
        df = st.session_state['df']
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                        open=df['Open'], high=df['High'],
                        low=df['Low'], close=df['Close'],
                        name='주가')])
        fig.update_layout(height=600, title=f"{st.session_state['stock_name']} 상세 보기")
        st.plotly_chart(fig, use_container_width=True)
