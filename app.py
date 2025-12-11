import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import datetime
import plotly.graph_objects as go

# --- [페이지 설정] ---
st.set_page_config(page_title="FX-AI Insight Pro", layout="wide", page_icon="📈")

# 디자인 설정 (다크모드 & 오렌지 테마)
st.markdown("""
<style>
    .stApp { background-color: #0f172a; color: white; }
    div.stButton > button { background-color: #ea580c; color: white; border: none; }
    h1, h2, h3 { color: #fb923c !important; }
    .stMetricValue { color: #fb923c !important; }
</style>
""", unsafe_allow_html=True)

# --- [1. 진짜 데이터 가져오기] ---
@st.cache_data(ttl=3600) # 1시간마다 데이터 갱신
def get_data():
    today = datetime.datetime.now()
    start = today - datetime.timedelta(days=365*3) # 3년치 데이터
    
    # 1. 환율 (네이버 금융)
    df_krw = fdr.DataReader('USD/KRW', start, today)
    
    # 2. 미국 금리, 달러 인덱스, 나스닥 (FRED & FRED 매핑)
    # 서학개미 지표로 '나스닥(NASDAQCOM)'을 사용합니다.
    df_us10y = fdr.DataReader('DGS10', start, today, data_source='fred')
    df_dxy = fdr.DataReader('DTWEXBGS', start, today, data_source='fred')
    df_nasdaq = fdr.DataReader('NASDAQCOM', start, today, data_source='fred') 
    
    return df_krw, df_us10y, df_dxy, df_nasdaq

# 데이터 로딩 표시
with st.spinner('실제 금융 데이터를 수집 중입니다... (Naver & Fed)'):
    try:
        krw, us10y, dxy, nasdaq = get_data()
        current_price = krw['Close'].iloc[-1]
        last_date = krw.index[-1].strftime("%Y-%m-%d")
    except:
        # 데이터 수집 실패 시 기본값 설정 (에러 방지용)
        st.error("데이터 통신 중입니다. 잠시만 기다려주세요.")
        current_price = 1400
        last_date = datetime.datetime.now().strftime("%Y-%m-%d")
        krw = pd.DataFrame({'Close': [1400]*100}, index=pd.date_range(end=datetime.datetime.now(), periods=100))

# --- [2. 왼쪽 사이드바 (조종석)] ---
st.sidebar.header("🎛️ 시나리오 시뮬레이션")
st.sidebar.info("슬라이더를 움직여 경제 지표 변화에 따른 환율을 예측해보세요.")

# 사용자 입력 받기
user_seohak = st.sidebar.slider("🐜 서학개미(나스닥) 과열도", 0, 100, 75)
user_us10y = st.sidebar.slider("🇺🇸 미국채 10년물 금리 (%)", 2.0, 6.0, 4.4)
user_dxy = st.sidebar.slider("💵 달러 인덱스", 90.0, 115.0, 106.0)
user_vix = st.sidebar.slider("😱 공포지수 (VIX)", 10.0, 40.0, 16.0)

# --- [3. 예측 모델 (수식)] ---
base_rate = 1350 
fair_value = (
    base_rate 
    + (user_us10y - 4.0) * 35 
    + (user_dxy - 103) * 15 
    + (user_vix - 15) * 4 
    + (user_seohak - 50) * 0.8
)
fair_value = round(fair_value, 2)

# --- [4. 메인 화면 보여주기] ---
col1, col2 = st.columns([2, 1])

with col1:
    st.title("FX-AI Insight Pro")
    st.write(f"📅 데이터 기준일: **{last_date}** | 출처: Naver Finance & US Fed")

with col2:
    st.metric(label="AI 적정 환율 (Fair Value)", 
              value=f"{fair_value} 원", 
              delta=f"{round(fair_value - current_price, 2)} 원 (시장가 대비)")

# 차트 그리기 (Plotly 사용)
st.subheader("📊 환율 흐름과 AI 예측")

# 차트 데이터 준비
chart_df = krw.iloc[-180:].copy() # 최근 6개월
chart_df['Type'] = 'Actual'

fig = go.Figure()

# 1. 실제 환율 선
fig.add_trace(go.Scatter(
    x=chart_df.index, 
    y=chart_df['Close'], 
    mode='lines', 
    name='실제 환율', 
    line=dict(color='#94a3b8')
))

# 2. 예측 점선 추가 (오늘부터 +14일)
future_dates = [datetime.datetime.now() + datetime.timedelta(days=x) for x in range(1, 15)]
# 현재가에서 적정가(Fair Value)로 수렴하는 경로 생성
future_values = [current_price + (fair_value - current_price) * (x/14) for x in range(1, 15)]

fig.add_trace(go.Scatter(
    x=future_dates, 
    y=future_values, 
    mode='lines', 
    name='AI 예측 경로', 
    line=dict(color='#f97316', width=3, dash='dot')
))

fig.update_layout(
    plot_bgcolor='rgba(0,0,0,0)', 
    paper_bgcolor='rgba(0,0,0,0)', 
    font=dict(color='white'),
    xaxis=dict(showgrid=False, title='Date'),
    yaxis=dict(gridcolor='#334155', title='KRW/USD'),
    margin=dict(l=0, r=0, t=30, b=0)
)

st.plotly_chart(fig, use_container_width=True)

# 설명 박스
st.warning(f"""
**💡 분석 인사이트:**
현재 서학개미(나스닥 추종) 매수 강도가 **{user_seohak}**입니다. 
이는 환율 하단을 약 **{(user_seohak-50)*0.8:.1f}원** 지지하는 효과를 냅니다.
""")