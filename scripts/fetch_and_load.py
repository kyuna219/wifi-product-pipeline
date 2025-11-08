# API 호출해서 데이터 받아오기

# 데이터프레임 생성 및 중복 제거

# 외부 DB에 저장 또는 CSV로 저장

import os
import requests
import json
import pandas as pd
from datetime import date, timedelta
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
import sys

def get_db_connection():
    """Create and return a PostgreSQL connection using environment variables."""
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD"),
        sslmode=os.environ.get("POSTGRES_SSLMODE", "require") 
    )
    return conn

CERTS = ["276","235","189","1652"]

def request_wifi(certifications, date_from):
    headers = {"User-Agent":"Mozilla/5.0","X-Requested-With":"XMLHttpRequest"}
    url = f"https://www.wi-fi.org/product-finder-api?sort_by=certified&sort_order=desc&certifications={certifications}&date_from={date_from}"
    r = requests.post(url, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    rows = []
    for p in data.get("products", []):
        certs = p.get("certifications", [])

        wifi_n = any(c.get("name")=="Wi-Fi CERTIFIED™ n" and c.get("should_be_displayed_on_details") for c in certs)
        wifi_ac = any(c.get("name")=="Wi-Fi CERTIFIED™ ac" and c.get("should_be_displayed_on_details") for c in certs)
        wifi_6 = any(c.get("name")=="Wi-Fi CERTIFIED 6®" and c.get("should_be_displayed_on_details") for c in certs)
        wifi_7 = any(c.get("name")=="Wi-Fi CERTIFIED 7™" and c.get("should_be_displayed_on_details") for c in certs)
        
        # 지원 기술을 하나의 목록으로 통합 
        supported_list = []
        if wifi_n: supported_list.append("n")
        if wifi_ac: supported_list.append("ac")
        if wifi_6: supported_list.append("6")
        if wifi_7: supported_list.append("7")
            
        wifi_support_list = ", ".join(supported_list) # 예: "n, ac, 6, 7"
        
        d = {
            "cid": p.get("cid"),
            "brand": p.get("companyName"),
            "product": p.get("name"),
            "model_number": p.get("modelNumber"),
            "date_certified": p.get("certified"),
            "category": p.get("productCategory", {}).get("product_consumer_category_class", {}).get("name"),
            "frequency_band": p.get("frequencyBand"),
            "wifi_support_list": wifi_support_list,
            "wifi_n": wifi_n,
            "wifi_ac": wifi_ac,
            "wifi_6": wifi_6,
            "wifi_7": wifi_7,
        }
        rows.append(d)
    return pd.DataFrame(rows)

def update_weekly_data():
    today = date.today()
    week_ago = today - timedelta(days=7)
    date_from = str(week_ago)

    all_df = pd.DataFrame()
    for c in CERTS:
        try:
            df = request_wifi(c, date_from)
            all_df = pd.concat([all_df, df], ignore_index=True)
        except Exception as e:
            print("Error fetching cert", c, e)

    if all_df.empty:
        print("No new data")
        return

    # 중복 제거: cid 기준 최근 날짜 우선
    all_df.sort_values("date_certified", ascending=False, inplace=True)
    all_df = all_df.drop_duplicates(subset=["cid"], keep="first")

    # DB 저장
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS wifi_products (
        cid TEXT PRIMARY KEY,
        brand TEXT,
        product TEXT,
        model_number TEXT,
        date_certified DATE,
        category TEXT,
        frequency_band TEXT,
        wifi_support_list TEXT,
        wifi_n BOOLEAN,
        wifi_ac BOOLEAN,
        wifi_6 BOOLEAN,
        wifi_7 BOOLEAN
    );
    """)
    conn.commit()

    rows = []
    for _, r in all_df.iterrows():
        rows.append((
            r["cid"], r["brand"], r["product"], r["model_number"], r["date_certified"],
            r["category"], r["frequency_band"], r["wifi_support_list"],
            bool(r["wifi_n"]), bool(r["wifi_ac"]), bool(r["wifi_6"]), bool(r["wifi_7"])
        ))

    insert_sql = """
    INSERT INTO wifi_products (
      cid, brand, product, model_number, date_certified,
      category, frequency_band, wifi_support_list, wifi_n, wifi_ac, wifi_6, wifi_7
    ) VALUES %s
    ON CONFLICT (cid) DO UPDATE SET
      brand = EXCLUDED.brand,
      product = EXCLUDED.product,
      model_number = EXCLUDED.model_number,
      date_certified = EXCLUDED.date_certified,
      category = EXCLUDED.category,
      frequency_band = EXCLUDED.frequency_band,
      wifi_support_list = EXCLUDED.wifi_support_list,
      wifi_n = EXCLUDED.wifi_n,
      wifi_ac = EXCLUDED.wifi_ac,
      wifi_6 = EXCLUDED.wifi_6,
      wifi_7 = EXCLUDED.wifi_7;
    """
    execute_values(cur, insert_sql, rows)
    conn.commit()
    cur.close()
    conn.close()
    print("Upsert complete, rows:", len(rows))

def backup_monthly_csv():
    conn = get_db_connection()
    cur = conn.cursor()

    # 🔹 이번 달(1일 기준으로 이전 달)을 백업 대상으로 계산
    today = date.today()
    target_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    print(f"🗓 Backing up data for: {target_month}")

    # 🔹 백업 대상 데이터 가져오기
    query = """
        SELECT * FROM wifi_products
        WHERE TO_CHAR(date_certified, 'YYYY-MM') = %s
        ORDER BY date_certified DESC;
    """
    df = pd.read_sql(query, conn, params=(target_month,))

    if df.empty:
        print("⚠️ No data found for that month.")
        cur.close()
        conn.close()
        return

    # 📁 폴더 생성: data/YYYY/
    year = target_month.split("-")[0]
    folder_path = Path(f"data/{year}")
    folder_path.mkdir(parents=True, exist_ok=True)

    # 💾 CSV 파일 저장: data/2025/2025-10.csv
    # file_path = folder_path / f"{target_month}.csv"
    # df.to_csv(file_path, index=False)
    # print(f"📁 Monthly backup saved: {file_path}")

    # 💾 XLSX 파일 저장 경로 설정
    file_path = folder_path / f"{target_month}.xlsx"

    # extract necessary columns
    df_excel = df.copy()
    final_columns = [
        'cid',
        'brand',
        'product',
        'model_number',
        'date_certified',
        'category',
        'frequency_band',
        'wifi_support_list'  
    ]
    df_excel = df_excel[final_columns]

    # rename 
    df_excel = df_excel.rename(columns={
        'cid': 'CID',
        'brand': 'Brand',
        'product': 'Product',
        'model_number': 'Model Number',
        'date_certified': 'Date Certified',
        'category': 'Category',
        'frequency_band': 'Frequency Band',
        'wifi_support_list': 'Wi-Fi Support List', 
    })
    
    df_excel.to_excel(file_path, index=False) 
    print(f"📁 Monthly XLSX exported: {file_path}")

    cur.close()
    conn.close()
    print("✅ Monthly backup complete")

def deletePrevious():
    conn = get_db_connection()
    cur = conn.cursor()

    # 🔹 이번 달(1일 기준으로 이전 달)을 백업 대상으로 계산
    today = date.today()
    target_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    
    # 🔹 DB에서 해당 월 데이터 삭제
    delete_sql = """
        DELETE FROM wifi_products
        WHERE TO_CHAR(date_certified, 'YYYY-MM') = %s;
    """
    cur.execute(delete_sql, (target_month,))
    conn.commit()
    print(f"🧹 Deleted {target_month} data from DB")

    cur.close()
    conn.close()
    print("✅ Delete complete")
    
def main():
    if len(sys.argv) < 2:
        print("Error: Missing run mode argument. Use 'weekly' or 'monthly'.")
        sys.exit(1)
        
    mode = sys.argv[1]
    
    if mode == 'weekly':
        print("🚀 Starting weekly data update...")
        update_weekly_data()
    elif mode == 'monthly':
        print("💾 Starting monthly backup...")
        backup_monthly_csv()
    else:
        print(f"Error: Invalid run mode: {mode}")
        sys.exit(1)

if __name__ == "__main__":
    main()
