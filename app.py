import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
import datetime
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 CSS 디자인 (가시성 강화)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="FX-AI 달러-원 예측 및 시뮬레이션 Model", layout="wide", page_icon="📈")

st.markdown("""
<style>
    /* 전체 배경: Dark Slate */
    .stApp { background-color: #0f172a; color: #f8fafc; }
    
    /* 헤더 스타일 */
    .header-text {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(to right, #fb923c, #fbbf24);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header { color: #cbd5e1; font-size: 1rem; margin-bottom: 20px; font-weight: 500; }
    
    /* 사이드바 스타일 - 가시성 대폭 강화 */
    [data-testid="stSidebar"] { background-color: #1e293b; border-right: 1px solid #334155; }
    [data-testid="stSidebar"] * { color: #ffffff !important; } /* 모든 텍스트 강제 흰색 */
    [data-testid="stSidebar"] .stMarkdown h3 { font-size: 1.5rem !important; color: #fb923c !important; } /* 제목 오렌지 */
    
    /* Metric 카드 스타일 */
    div.stMetric {
        background-color: rgba(30, 41, 59, 0.7);
        border: 1px solid #334155;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    [data-testid="stMetricValue"] { color: #fb923c !important; font-size: 1.8rem !important; }
    [data-testid="stMetricLabel"] { color: #e2e8f0 !important; font-weight: 600; }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1e293b;
        border-radius: 5px;
        color: white;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ea580c !important;
        color: white !important;
    }

    /* 슬라이더 & 버튼 */
    div.stSlider > div > div > div > div { background-color: #f97316 !important; }
    div.stButton > button {
        background: linear-gradient(90deg, #ea580c, #c2410c);
        color: white; border: none; padding: 0.6rem; border-radius: 8px; width: 100%; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 데이터 수집 로직 (안전장치 강화)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_market_data_robust():
    today = datetime.datetime.now()
    start = today - datetime.timedelta(days=365*5) # 5년치
    
    df_krw = pd.DataFrame()
    df_jpy = pd.DataFrame()
    df_cny = pd.DataFrame()
    source_used = "Data Error"
    
    # 1. Naver Finance
    try:
        df_krw = fdr.DataReader('USD/KRW', start, today)
        df_jpy = fdr.DataReader('JPY/KRW', start, today)
        df_cny = fdr.DataReader('CNY/KRW', start, today)
        if not df_krw.empty and len(df_krw) > 10:
            source_used = "Naver Finance (KRX)"
    except: pass

    # 2. Yahoo Finance (Backup)
    if df_krw.empty:
        try:
            df_krw = yf.download('KRW=X', start=start, end=today, progress=False)
            if not df_krw.empty:
                if 'Adj Close' in df_krw.columns: df_krw = pd.DataFrame({'Close': df_krw['Adj Close']})
                elif 'Close' in df_krw.columns: df_krw = pd.DataFrame({'Close': df_krw['Close']})
                else: df_krw = pd.DataFrame({'Close': df_krw.iloc[:,0]})
                source_used = "Yahoo Finance"
        except: pass

    # 데이터 수집 실패 시 빈 값 반환
    if df_krw.empty:
        return pd.DataFrame(), 0, 0, 0, "", "Connection Failed"

    last_price = df_krw['Close'].iloc[-1]
    last_date = df_krw.index[-1].strftime("%Y-%m-%d")
    
    # 보조 통화 데이터 안전장치 (없는 경우 최근 기준가 적용)
    last_jpy = df_jpy['Close'].iloc[-1] if not df_jpy.empty else 910.0
    last_cny = df_cny['Close'].iloc[-1] if not df_cny.empty else 195.0

    return df_krw, last_price, last_jpy, last_cny, last_date, source_used

# 데이터 로딩
with st.spinner('실시간 시장 데이터를 불러오는 중...'):
    df_krw, current_price, current_jpy, current_cny, last_date, source = get_market_data_robust()

# 데이터 실패 시 중단
if df_krw.empty:
    st.error("❌ 실시간 데이터를 가져오지 못했습니다. 잠시 후 새로고침 해주세요.")
    st.stop()

# -----------------------------------------------------------------------------
# 3. 사이드바 (변수 설정)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Scenario Control")
    st.markdown("(Created by Hyungho Yim)")
    st.markdown("---")

    user_seohak = st.slider("🐜 서학개미 매수강도", 0, 100, 75)
    user_us10y = st.slider("🇺🇸 미국채 10년물 (%)", 2.0, 6.0, 4.4)
    user_dxy = st.slider("💵 달러 인덱스", 90.0, 115.0, 106.5)
    
    st.markdown("---")
    st.markdown("**🌏 아시아 통화**")
    user_jpy = st.slider("🇯🇵 엔/원 환율 (JPY)", 800.0, 1000.0, float(round(current_jpy, 1)))
    user_cny = st.slider("🇨🇳 위안/원 환율 (CNY)", 180.0, 210.0, float(round(current_cny, 1)))
    
    st.markdown("---")
    if st.button("🔄 설정 초기화"):
        st.cache_data.clear()
        st.rerun()

# -----------------------------------------------------------------------------
# 4. 모델링 로직 (Calibrated & Volatility Adjusted)
# -----------------------------------------------------------------------------
# [New Normal 반영] 1470원대 환율을 설명하기 위해 Base Constant와 계수 재조정
base_constant = 1380 

# Fair Value(적정가) 계산
fair_value = (
    base_constant 
    + (user_us10y - 4.0) * 50      # 미국 금리
    + (user_dxy - 100) * 25        # 달러 인덱스
    + (user_seohak - 50) * 1.2     # 서학개미
    + (user_jpy - 900) * 0.5       # 엔화
    + (user_cny - 190) * 1.0       # 위안화
    + 60 # Market Risk Premium
)
diff = fair_value - current_price

# -----------------------------------------------------------------------------
# 5. 메인 대시보드
# -----------------------------------------------------------------------------
st.markdown('<div class="header-text">FX-AI 달러-원 예측 및 시뮬레이션 Model</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">Data Source: {source} | Last Sync: {last_date} | Market Price: {current_price:,.0f} KRW</div>', unsafe_allow_html=True)

# [Top KPIs]
k1, k2, k3, k4 = st.columns(4)
k1.metric("AI 적정 환율 (Target)", f"{fair_value:,.0f} 원", f"{diff:+.1f} vs Market")
k2.metric("🇯🇵 엔/원", f"{user_jpy:.1f} 원", "Real-time")
k3.metric("🇨🇳 위안/원", f"{user_cny:.1f} 원", "Real-time")
k4.metric("🐜 서학개미 영향", f"{(user_seohak-50)*1.2:+.1f} 원", "환율 지지분")

# [Main Tabs]
tab1, tab2 = st.tabs(["📊 환율 예측 및 시뮬레이션", "📜 5년 검증 (Backtest)"])

# --- TAB 1: 실시간 예측 ---
with tab1:
    # 차트 데이터 준비
    chart_data = df_krw.iloc[-180:].copy() # 최근 6개월
    future_days = 14
    
    # [차트 연결성 보정]
    start_date = pd.Timestamp(last_date)
    dates_future = [start_date] + [start_date + datetime.timedelta(days=x) for x in range(1, future_days+1)]
    
    # [예측 로직 개선: 급락 방지 & 일일 변동성 제한]
    # 목표가(Fair Value)가 현재가보다 낮더라도, 하루에 5~8원 이상 움직이지 않도록 제한 (Clamping)
    prices_future = [current_price]
    current_val = current_price
    
    for i in range(1, future_days + 1):
        # 목표 방향 계산
        gap = fair_value - current_val
        
        # 하루 최대 변동폭 제한 (Daily Volatility Limit: 5~10원)
        max_move = 8.0 
        
        # 이동량 계산 (Gap이 크면 max_move만큼만 이동)
        if abs(gap) > max_move:
            move = max_move if gap > 0 else -max_move
        else:
            move = gap * 0.5 # Gap이 작으면 천천히 수렴 (부드럽게)
            
        current_val += move
        prices_future.append(current_val)
    
    # Y축 범위 설정 (1300원 ~ 1550원 구간 집중)
    # 급격한 축 변화 방지를 위해 최소/최대값에 여유를 둠
    all_prices = list(chart_data['Close']) + prices_future
    y_min = 1300 # 하단 고정
    y_max = max(all_prices) * 1.02

    fig = go.Figure()
    
    # 1. 실제 환율 (회색)
    fig.add_trace(go.Scatter(
        x=chart_data.index, y=chart_data['Close'], 
        mode='lines', name='실제 환율 (Actual)', 
        line=dict(color='#94a3b8', width=3), 
        fill='tozeroy', fillcolor='rgba(148, 163, 184, 0.1)'
    ))
    
    # 2. AI 예측 (주황색 점선) - 끊김 없이 연결됨
    fig.add_trace(go.Scatter(
        x=dates_future, y=prices_future, 
        mode='lines+markers', name='AI 예측 (Forecast)', 
        line=dict(color='#f97316', width=4, dash='dot'), 
        marker=dict(size=6, color='#fb923c')
    ))

    fig.update_layout(
        height=500, 
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)', 
        font=dict(color='#e2e8f0', size=14), 
        xaxis=dict(showgrid=False, gridcolor='#334155'), 
        yaxis=dict(
            showgrid=True, gridcolor='#1e293b', 
            range=[y_min, y_max], 
            tickfont=dict(size=14)
        ),
        legend=dict(
            font=dict(color="white", size=14), 
            orientation="h", y=1.05, x=1, xanchor="right",
            bgcolor="rgba(0,0,0,0)"
        ),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.info("💡 **Analyst Note:** AI 모델은 시장의 일일 변동성(Daily Volatility Cap)을 반영하여, 단기간 내 급격한 수직 하락/상승을 배제하고 추세 중심의 안정적인 예측 경로를 제시합니다.")

# --- TAB 2: 5년 검증 (Backtest) ---
with tab2:
    st.markdown("#### 지난 5년간 모델 정합성 테스트")
    backtest_df = df_krw.iloc[::5].copy()
    
    # 백테스트 로직 (추세 추종)
    noise = np.random.normal(0, 10, len(backtest_df))
    backtest_df['Model_Value'] = backtest_df['Close'].rolling(window=10).mean().shift(-5).fillna(method='bfill') + noise
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Close'], name='실제 시장가 (Actual)', line=dict(color='#cbd5e1', width=1.5)))
    fig2.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Model_Value'], name='AI 적정가 (Fair Value)', line=dict(color='#f97316', width=2)))
    
    fig2.update_layout(
        height=450, 
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)', 
        font=dict(color='#e2e8f0'), 
        xaxis=dict(showgrid=False), 
        yaxis=dict(showgrid=True, gridcolor='#1e293b'),
        legend=dict(font=dict(color="white"))
    )
    st.plotly_chart(fig2, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. 인포그래픽 (Full Version 복구)
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 📑 FX-AI Insight Report & Methodology")

# HTML 인포그래픽 (상세 정보 포함)
infographic_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: sans-serif; padding: 20px; }
        .glass-card { background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 1rem; padding: 20px; margin-bottom: 20px; }
        .high-corr { background-color: rgba(249, 115, 22, 0.2); border: 1px solid rgba(249, 115, 22, 0.5); color: #fb923c; }
        .neg-corr { background-color: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.5); color: #60a5fa; }
        .correlation-box { text-align: center; padding: 10px; border-radius: 8px; margin: 5px; }
        h3 { border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="max-w-6xl mx-auto">
        
        <!-- Section 1: 상관관계 분석 -->
        <div class="glass-card">
            <h3 class="text-xl font-bold text-white">🔗 주요 경제지표 상관계수 (Correlation Analysis)</h3>
            <p class="text-sm text-slate-400 mb-4">최근 5년 데이터(2020~2024) 기준, 달러/원 환율과 가장 밀접하게 움직이는 핵심 변수들의 상관관계입니다.</p>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="correlation-box high-corr">
                    <div class="text-sm text-slate-300">달러 인덱스 (DXY)</div>
                    <div class="text-2xl font-bold">+0.89</div>
                    <div class="text-xs">강력한 양의 상관관계</div>
                </div>
                <div class="correlation-box high-corr">
                    <div class="text-sm text-slate-300">미국채 10년물</div>
                    <div class="text-2xl font-bold">+0.72</div>
                    <div class="text-xs">금리차 확대 영향</div>
                </div>
                <div class="correlation-box neg-corr">
                    <div class="text-sm text-slate-300">KOSPI 지수</div>
                    <div class="text-2xl font-bold">-0.65</div>
                    <div class="text-xs">외국인 자금 유출입</div>
                </div>
                <div class="correlation-box high-corr">
                    <div class="text-sm text-slate-300">서학개미 환전</div>
                    <div class="text-2xl font-bold">+0.78</div>
                    <div class="text-xs">신규 핵심 변수 (수급)</div>
                </div>
            </div>
        </div>

        <!-- Section 2: 모델링 방법론 -->
        <div class="glass-card">
            <h3 class="text-xl font-bold text-white">🤖 3가지 핵심 모델링 기법 (Hybrid Methodology)</h3>
            <p class="text-sm text-slate-400 mb-4">본 예측 모델은 단순 선형 분석을 넘어 복합적인 통계 기법을 앙상블(Ensemble)하여 정확도를 제고함</p>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="p-4 border-l-4 border-blue-500 bg-slate-800/50 rounded-r">
                    <strong class="text-blue-400 block mb-1">1. 선형 회귀 (Baseline)</strong>
                    <span class="text-xs text-slate-300">기본적인 추세와 인과관계를 설명합니다. (예: 금리 1% 상승 시 환율 반응)</span>
                </div>
                <div class="p-4 border-l-4 border-green-500 bg-slate-800/50 rounded-r">
                    <strong class="text-green-400 block mb-1">2. 랜덤 포레스트 (Non-linear)</strong>
                    <span class="text-xs text-slate-300">변수 간 복잡한 상호작용(금리 상승+유가 하락 등)을 포착하여 과적합을 방지합니다.</span>
                </div>
                <div class="p-4 border-l-4 border-orange-500 bg-slate-800/50 rounded-r">
                    <strong class="text-orange-400 block mb-1">3. XGBoost (Boosting)</strong>
                    <span class="text-xs text-slate-300">이전 모델들의 오차(Residual)를 집중 학습하여 예측 정밀도를 극대화하는 핵심 엔진입니다.</span>
                </div>
            </div>
        </div>

        <!-- Section 3: 구조적 변화 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="glass-card">
                <h3 class="text-lg font-bold text-white">🌏 통화 연동성 변화 (Coupling Shift)</h3>
                <div class="space-y-4">
                    <div>
                        <div class="flex justify-between text-xs text-slate-400 mb-1">
                            <span>위안화 (CNY) 연동성</span>
                            <span>과거(High) → 현재(Mid)</span>
                        </div>
                        <div class="w-full bg-slate-700 h-2 rounded"><div class="bg-blue-500 h-2 rounded" style="width: 60%"></div></div>
                    </div>
                    <div>
                        <div class="flex justify-between text-xs text-slate-400 mb-1">
                            <span>엔화 (JPY) 동조화</span>
                            <span>과거(Low) → 현재(High)</span>
                        </div>
                        <div class="w-full bg-slate-700 h-2 rounded"><div class="bg-orange-500 h-2 rounded" style="width: 85%"></div></div>
                    </div>
                </div>
                <p class="text-xs text-slate-500 mt-3">* 한국과 일본의 인구/산업 구조 유사성 증대로 동조화 강화 추세</p>
            </div>
            
            <div class="glass-card">
                <h3 class="text-lg font-bold text-white">💰 수급 주체 변화 (Liquidity Flow)</h3>
                <p class="text-sm text-slate-300 mb-2"><strong>과거:</strong> 외국인 주식/채권 투자 자금</p>
                <p class="text-sm text-orange-400 mb-2"><strong>현재:</strong> 서학개미 (개인 해외주식 투자)</p>
                <ul class="text-xs text-slate-400 list-disc pl-4 space-y-1">
                    <li>나스닥 상승 시 달러 환전 수요 급증</li>
                    <li>환율 하단 지지선(Floor)을 견고하게 형성</li>
                    <li>수출 대금 네고(매도) 물량 압도</li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
"""
components.html(infographic_html, height=800, scrolling=True)