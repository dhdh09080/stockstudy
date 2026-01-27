import streamlit as st
import matplotlib
matplotlib.use('Agg') # [중요] 가장 먼저 실행: 창 띄우기 금지 모드
import matplotlib.pyplot as plt
import mplfinance as mpf
import FinanceDataReader as fdr
import google.generativeai as genai
import io
from PIL import Image
from datetime import datetime, timedelta

# --- 페이지 설정 ---
st.set_page_config(page_title="재미나이 AI 투자 비서 (디버그 모드)", layout="wide")

# --- 사이드바 ---
with st.sidebar:
    st.header("🔑 설정")
    api_key = st.text_input("Google API Key", type="password")
    if api_key:
        genai.configure(api_key=api_key)
        # 무료 모델 강제 설정 (안전한 버전)
        model = genai.GenerativeModel('gemini-2.0-flash-exp') 

# --- 차트 변환 함수 (디버깅 로그 포함) ---
def df_to_image(df, stock_name):
    buf = io.BytesIO()
    # 스타일 지정 없이 기본으로 그려봅니다 (스타일 다운로드 문제 배제)
    mpf.plot(df, type='candle', volume=True, mav=(5, 20),
             title=f"{stock_name}", savefig=buf)
    buf.seek(0)
    image = Image.open(buf)
    return image

# --- 메인 로직 ---
st.title("🛠️ 범인 색출 모드")

stock_code = st.text_input("종목 코드", value="005930")

if st.button("🚀 분석 시작"):
    if not api_key:
        st.error("API 키를 입력해주세요!")
    else:
        st.write("👉 1단계: 데이터 가져오기 시도 중...")
        try:
            end_date = datetime.today()
            start_date = end_date - timedelta(days=100)
            df = fdr.DataReader(stock_code, start_date, end_date)
            if df.empty:
                st.error("데이터가 텅 비었습니다. 종목코드를 확인하세요.")
                st.stop()
            st.success(f"✅ 1단계 성공! 데이터 {len(df)}개 확보")
        except Exception as e:
            st.error(f"❌ 1단계 실패 (데이터): {e}")
            st.stop()

        st.write("👉 2단계: 차트 이미지 그리기 시도 중...")
        try:
            chart_image = df_to_image(df, "Test Stock")
            st.success("✅ 2단계 성공! 차트 이미지 생성 완료")
            st.image(chart_image, caption="AI가 볼 이미지 미리보기") # 화면에 찍어보기
        except Exception as e:
            st.error(f"❌ 2단계 실패 (차트 그리기): {e}")
            st.stop()

        st.write("👉 3단계: 재미나이(AI)에게 전송 중...")
        try:
            prompt = "이 차트의 추세와 매매 전략을 한글로 짧게 3줄 요약해줘."
            response = model.generate_content([prompt, chart_image])
            st.success("✅ 3단계 성공! 분석 완료")
            st.write(response.text)
        except Exception as e:
            st.error(f"❌ 3단계 실패 (AI): {e}")
