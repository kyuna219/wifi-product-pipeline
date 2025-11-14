import streamlit as st
import pandas as pd
# psycopg2 모듈은 st.connection이 내부적으로 사용하므로 명시적 import는 필요 없으나,
# Streamlit Cloud에서 psycopg2 드라이버 설치를 확인하는 용도로는 남겨둡니다.
import psycopg2 
import plotly.express as px
import io

# ------------------------------------
# 1. 데이터 로드 및 캐싱 (st.connection 사용)
# ------------------------------------
# @st.cache_data 대신 st.connection().query()를 사용하면 캐싱이 내부적으로 처리됩니다.
# ttl="7d" (7일)을 설정하여 데이터가 7일마다 자동으로 새로 고쳐지도록 합니다.
@st.cache_data(ttl="7d", show_spinner="데이터를 불러오는 중입니다...")
def load_data():
    try:
        # st.connection을 사용하여 PostgreSQL 연결 객체를 생성하고 캐싱합니다.
        # Streamlit은 st.secrets에 있는 모든 POSTGRES_HOST, PORT, USER 등의 정보를 자동으로 사용합니다.
        conn = st.connection("postgresql", type="sql") 
        
        query = "SELECT cid, brand, product, wifi_support_list FROM wifi_products ORDER BY date_certified DESC;"
        
        # conn.query()는 Pandas의 read_sql을 내부적으로 실행하며, 
        # 연결이 끊겼을 경우 재시도 로직까지 포함하여 안정적입니다.
        df = conn.query(query)
        
        return df
        
    except Exception as e:
        st.error(f"데이터 로드 및 연결 오류가 발생했습니다: {e}")
        st.info("Streamlit Secrets에 DB 정보가 정확히 설정되었는지 확인해주세요.")
        return pd.DataFrame()

# ------------------------------------
# 2. Streamlit 앱 레이아웃
# ------------------------------------
def app():
    st.set_page_config(layout="wide")
    st.title("📡 Wi-Fi 인증 제품 현황 대시보드")
    st.markdown("---")

    df = load_data()

    if df.empty:
        st.warning("데이터를 불러올 수 없거나 테이블이 비어 있습니다. DB 연결 상태를 확인해주세요.")
        return

    # ------------------------------------
    # A. 필터링 및 요약
    # ------------------------------------
    st.header("1. 지원 기술 현황 분석")
    
    # df가 비어있지 않은 경우에만 로직 실행
    if not df.empty and 'wifi_support_list' in df.columns:
        # 지원 기술 목록 컬럼을 분할하여 각 표준의 개수를 세기
        # (예: "n, ac, 6" -> 'n', 'ac', '6'으로 분할)
        df_support = df['wifi_support_list'].str.split(', ', expand=True).stack().reset_index(level=1, drop=True).to_frame('Standard')
        
        # 빈 값(None) 및 불필요한 공백 제거
        df_support = df_support[df_support['Standard'].str.strip() != '']
        standard_counts = df_support['Standard'].value_counts().reset_index()
        standard_counts.columns = ['Standard', 'Count']
        
        # 시각화 (막대 그래프)
        fig = px.bar(standard_counts, 
                     x='Standard', 
                     y='Count', 
                     title='표준별 제품 수량 (총 제품 수: %d)' % len(df),
                     color='Standard')
        st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("기술 지원 목록 데이터(wifi_support_list)가 비어있거나 컬럼명이 잘못되었습니다.")


    # ------------------------------------
    # B. 대화형 표 (원본 데이터 목록)
    # ------------------------------------
    st.header("2. 원본 데이터 목록 (필터링 가능)")

    # 💡 사이드바 필터링
    st.sidebar.header("데이터 필터")
    
    top_brands = df['brand'].value_counts().nlargest(10).index.tolist()
    # 'All' 옵션을 추가하여 모든 데이터를 볼 수 있도록 함
    brand_options = ['전체 보기'] + top_brands 
    selected_brand = st.sidebar.selectbox("브랜드 선택", options=brand_options)
    
    if selected_brand != '전체 보기':
        df_filtered = df[df['brand'] == selected_brand]
    else:
        df_filtered = df

    # 대화형 표 표시
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
        """DataFrame을 XLSX 파일 형식으로 변환"""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: 
            df.to_excel(writer, index=False, sheet_name='Latest Data')
        processed_data = output.getvalue()
        return processed_data

    st.sidebar.markdown("---")
    
    # 다운로드할 데이터는 필터링되지 않은 전체 데이터 (df)를 사용
    excel_data = convert_df_to_excel(df) 

    st.sidebar.download_button(
        label="🚀 전체 데이터 XLSX 다운로드",
        data=excel_data,
        file_name="latest_wifi_products.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == '__main__':
    app()
