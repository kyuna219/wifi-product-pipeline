import streamlit as st
import pandas as pd
import psycopg2
import os
import plotly.express as px

# ------------------------------------
# 1. Neon DB 연결 설정 (Streamlit Cloud 환경에서)
# ------------------------------------
# DB 연결 함수 (GitHub Actions의 fetch_and_load.py에서 사용하던 함수와 유사)
@st.cache_resource # DB 연결 객체는 캐시하여 재사용
def get_neon_connection():
    try:
        conn = psycopg2.connect(
            host=st.secrets["POSTGRES_HOST"],
            port=st.secrets["POSTGRES_PORT"],
            dbname=st.secrets["POSTGRES_DB"],
            user=st.secrets["POSTGRES_USER"],
            password=st.secrets["POSTGRES_PASSWORD"],
            sslmode=st.secrets["POSTGRES_SSLMODE"]
        )
        return conn
    except Exception as e:
        st.error(f"데이터베이스 연결 오류: {e}")
        return None

# ------------------------------------
# 2. 데이터 로드 및 캐싱
# ------------------------------------
@st.cache_data(ttl=600) # 10분마다 데이터 새로고침
def load_data():
    conn = get_neon_connection()
    if conn:
        query = "SELECT brand, product, wifi_support_list FROM wifi_products ORDER BY date_certified DESC;"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

# ------------------------------------
# 3. Streamlit 앱 레이아웃
# ------------------------------------
def app():
    st.set_page_config(layout="wide")
    st.title("📡 Wi-Fi 인증 제품 현황 대시보드")
    st.markdown("---")

    df = load_data()

    if df.empty:
        st.warning("데이터를 불러올 수 없거나 테이블이 비어 있습니다.")
        return

    # ------------------------------------
    # A. 필터링 및 요약
    # ------------------------------------
    st.header("1. 지원 기술 현황 분석")
    
    # 지원 기술 목록 컬럼을 분할하여 각 표준의 개수를 세기
    df_support = df['wifi_support_list'].str.split(', ', expand=True).stack().reset_index(level=1, drop=True).to_frame('Standard')
    standard_counts = df_support['Standard'].value_counts().reset_index()
    standard_counts.columns = ['Standard', 'Count']
    
    # ⭐️ 시각화 (막대 그래프) ⭐️
    fig = px.bar(standard_counts, 
                 x='Standard', 
                 y='Count', 
                 title='표준별 제품 수량 (총 제품 수: %d)' % len(df),
                 color='Standard')
    st.plotly_chart(fig, use_container_width=True)
    

    # ------------------------------------
    # B. 대화형 표 (원본 데이터 목록)
    # ------------------------------------
    st.header("2. 원본 데이터 목록 (필터링 가능)")

    # 사용자가 브랜드로 필터링할 수 있도록 사이드바에 필터 추가
    st.sidebar.header("데이터 필터")
    
    # 상위 10개 브랜드만 필터 옵션으로 제공
    top_brands = df['brand'].value_counts().nlargest(10).index.tolist()
    selected_brands = st.sidebar.multiselect("브랜드 선택 (Top 10)", options=top_brands, default=top_brands[:3])
    
    df_filtered = df[df['brand'].isin(selected_brands)]

    # ⭐️ 대화형 표 표시 ⭐️
    st.dataframe(
        df_filtered, 
        height=400, 
        use_container_width=True,
        hide_index=True
    )
    


    # ------------------------------------
    # C. 데이터 다운로드 버튼
    # ------------------------------------
    @st.cache_data
    def convert_df_to_excel(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: 
            df.to_excel(writer, index=False, sheet_name='Latest Data')
        processed_data = output.getvalue()
        return processed_data

    st.sidebar.markdown("---")
    excel_data = convert_df_to_excel(df)

    st.sidebar.download_button(
        label="🚀 전체 데이터 XLSX 다운로드",
        data=excel_data,
        file_name="latest_wifi_products.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == '__main__':
    import io
    app()
