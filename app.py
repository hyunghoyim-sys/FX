import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
import datetime
import numpy as np
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 CSS 디자인 주입 (React 스타일 모방)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="FX-AI Insight Pro", layout="wide", page_icon="📈")

# Streamlit의 기본 스타일을 덮어쓰는 CSS 해킹
st.markdown("""
<style>
    /* 1. 전체 배경색: Dark Slate (#0f172a) */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }

    /* 2. 사이드바 스타일: Lighter Slate (#1e293b) & Border */
    [data-testid="stSidebar"] {
        background-color: #1e293b;
        border-right: 1px solid #334155;
    }

    /* 3. 헤더 그라데이션 텍스트 효과 */
    .gradient-text {
        background: linear-gradient(to right, #fb923c, #fbbf24);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem;
        display: inline-block;
    }
    
    .sub-text {
        color: #94a3b8;
        font-size: 0.9rem;
    }

    /* 4. KPI 카드 스타일 (Metric 위젯 커스텀) */
    [data-testid="stMetric"] {
        background-color: rgba(30, 41, 59, 0.7); /* 반투명 배경 */
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    /* Metric 라벨(제목) 색상 */
    [data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-size: 0.9rem !important;
    }

    /* Metric 값(숫자) 색상 - 오렌지 강조 */
    [data-testid="stMetricValue"] {
        color: #fb923c !important;
        font-size: 2.2rem !important;
        font-weight: 700 !important;
    }

    /* Metric 등락폭(Delta) 색상 */
    [data-testid="stMetricDelta"] {
        color: #94a3b8 !important;
    }

    /* 5. 슬라이더 커스텀 (오렌지 포인트) */
    div.stSlider > div > div > div > div {
        background-color: #f97316 !important;
    }
    
    /* 6. 버튼 커스텀 */
    div.stButton > button {
        background: linear-gradient(90deg, #ea580c, #c2410c);
        color: white;
        border: none;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #f97316, #ea580c);
        box-shadow: 0 4px 12px rgba(234, 88, 12, 0.3);
        border: none;
        color: white;
    }
    
    /* 7. Plotly 차트 배경 투명화 */
    .js-plotly-plot .plotly .main-svg {
        background: rgba(0,0,0,0) !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 데이터 수집 로직 (이중 백업 시스템)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_market_data_robust():
    today = datetime.datetime.now()
    start = today - datetime.timedelta(days=365*2)
    
    df_result = pd.DataFrame()
    source_used = ""
    is_sim = False
    
    # 1. Naver Finance
    try:
        df = fdr.DataReader('USD/KRW', start, today)
        if not df.empty and len(df) > 10:
            df_result = df
            source_used = "Naver Finance"
    except: pass

    # 2. Yahoo Finance
    if df_result.empty:
        try:
            yf_data = yf.download('KRW=X', start=start, end=today, progress=False)
            if not yf_data.empty:
                vals = yf_data['Adj Close'] if 'Adj Close' in yf_data.columns else yf_data.iloc[:, 0]
                if isinstance(vals, pd.DataFrame): vals = vals.iloc[:, 0]
                df_result = pd.DataFrame({'Close': vals})
                source_used = "Yahoo Finance"
        except: pass

    # 3. Simulation
    if df_result.empty:
        dates = pd.date_range(end=today, periods=200)
        base = 1420
        walk = np.cumsum(np.random.normal(0, 4, 200))
        df_result = pd.DataFrame({'Close': base + walk}, index=dates)
        source_used = "Simulation"
        is_sim = True

    if df_result.empty: # Final Fallback
         dates = pd.date_range(end=today, periods=10)
         df_result = pd.DataFrame({'Close': [1400]*10}, index=dates)

    last_price = df_result['Close'].iloc[-1]
    last_date = df_result.index[-1].strftime("%Y-%m-%d")

    return df_result, last_price, last_date, source_used, is_sim

# 데이터 로딩
df_krw, current_price, last_date, source, is_sim = get_market_data_robust()

# -----------------------------------------------------------------------------
# 3. 사이드바 (컨트롤 패널)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Scenario Analysis")
    st.markdown("경제 지표를 조절하여 적정 환율을 예측해보세요.")
    st.markdown("---")
    
    user_seohak = st.slider("🐜 서학개미 매수강도", 0, 100, 75)
    user_us10y = st.slider("🇺🇸 미국채 10년물 (%)", 2.0, 6.0, 4.4)
    user_dxy = st.slider("💵 달러 인덱스 (DXY)", 90.0, 115.0, 106.5)
    user_vix = st.slider("😱 공포지수 (VIX)", 10.0, 40.0, 16.0)
    
    st.markdown("---")
    if st.button("🔄 Reset Variables"):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown(f"""
    <div style='margin-top: 20px; font-size: 0.8rem; color: #64748b;'>
        📡 Data Source: {source}<br>
        📅 Last Sync: {last_date}
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. 모델링 (Fair Value)
# -----------------------------------------------------------------------------
base_constant = 1350 
fair_value = (
    base_constant 
    + (user_us10y - 4.0) * 35 
    + (user_dxy - 103) * 15 
    + (user_vix - 15) * 4 
    + (user_seohak - 50) * 0.8
)
diff = fair_value - current_price

# -----------------------------------------------------------------------------
# 5. 메인 대시보드 (React UI 모방)
# -----------------------------------------------------------------------------

# [Header]
col_logo, col_title = st.columns([1, 10])
with col_title:
    st.markdown('<div class="gradient-text">FX-AI Insight Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-text">Real-time USD/KRW Predictive Model & Risk Analysis</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True) # Spacer

# [KPI Cards]
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("AI 적정 환율 (Fair Value)", f"{fair_value:,.0f} KRW", f"{diff:+.1f} vs Market")

with col2:
    # Regime Logic
    if user_vix > 20: regime = "Risk Off 🔴"
    elif user_seohak > 80: regime = "Strong Buy 🟢"
    else: regime = "Neutral 🟡"
    st.metric("Market Regime", regime, "Sentiment Analysis")

with col3:
    impact = (user_seohak - 50) * 0.8
    st.metric("서학개미 지지 효과", f"{impact:+.1f} KRW", "Buying Power Impact")

st.markdown("<br>", unsafe_allow_html=True) # Spacer

# [Chart Section]
st.markdown("### 📈 Price Simulation & Forecast")

# 차트 데이터 생성
chart_data = df_krw.iloc[-120:].copy()
future_days = 14
dates_future = [pd.Timestamp(last_date) + datetime.timedelta(days=x) for x in range(1, future_days+1)]
prices_future = [current_price + (fair_value - current_price) * (i/future_days) for i in range(1, future_days+1)]

# Plotly 차트 커스텀 (Recharts 스타일 모방)
fig = go.Figure()

# 1. 과거 데이터 (Area)
fig.add_trace(go.Scatter(
    x=chart_data.index, y=chart_data['Close'],
    mode='lines', name='Actual History',
    line=dict(color='#94a3b8', width=2),
    fill='tozeroy', 
    fillcolor='rgba(148, 163, 184, 0.1)' # 은은한 회색 Fill
))

# 2. 미래 예측 (Orange Dotted)
fig.add_trace(go.Scatter(
    x=dates_future, y=prices_future,
    mode='lines+markers', name='AI Forecast',
    line=dict(color='#f97316', width=4, dash='dot'),
    marker=dict(size=6, color='#fb923c')
))

# 레이아웃: 그리드 제거, 배경 투명화
fig.update_layout(
    height=450,
    plot_bgcolor='rgba(0,0,0,0)', 
    paper_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#e2e8f0', family="sans-serif"),
    xaxis=dict(
        showgrid=False, 
        gridcolor='#334155',
        showline=True,
        linecolor='#334155'
    ),
    yaxis=dict(
        showgrid=True, 
        gridcolor='#1e293b', # 아주 어두운 그리드 (거의 안보이게)
        zeroline=False,
        side='right' # 축 오른쪽 배치 (트레이딩뷰 스타일)
    ),
    hovermode="x unified",
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(
        orientation="h", y=1.05, x=0,
        bgcolor='rgba(0,0,0,0)'
    )
)

st.plotly_chart(fig, use_container_width=True)

# [Bottom Insight]
st.info(f"""
**💡 AI Analyst Note:**
현재 **{source}** 데이터를 분석 중입니다. 
서학개미 매수강도가 **{user_seohak}**일 때, 환율 하단을 약 **{impact:.1f}원** 지지하는 효과가 있습니다.
현재 시장가({current_price:,.0f})는 AI 적정가 대비 **{'저평가(Undervalued)' if diff > 0 else '고평가(Overvalued)'}** 구간입니다.
""")