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
PAGE_LIMIT = 500

def request_wifi(all_certification_ids, date_from, date_to, start_index, limit):
    headers = {"User-Agent":"Mozilla/5.0","X-Requested-With":"XMLHttpRequest"}
    url = (
        f"https://prf.cert.wi-fi.org/products/view/filtered?"
        f"sort_by=certified&sort_order=desc&"  
        f"certifications={all_certification_ids}&"
        f"date_from={date_from}&"  
        f"date_to={date_to}&"      
        f"start={start_index}&"
        f"items={limit}"
    )
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()

    products_list = data.get("items", [])
    total_count = data.get('total', 0)

    print(f"-> Fetched {len(products_list)} items at start={start_index}. Total expected: {total_count}")

    rows = []
    for p in products_list:
        certs = p.get("certifications", [])

        wifi_n = any(c.get("name")=="Wi-Fi CERTIFIED™ n" and c.get("should_be_displayed_on_details") for c in certs)
        wifi_ac = any(c.get("name")=="Wi-Fi CERTIFIED™ ac" and c.get("should_be_displayed_on_details") for c in certs)
        wifi_6 = any(c.get("name")=="Wi-Fi CERTIFIED 6®" and c.get("should_be_displayed_on_details") for c in certs)
        wifi_7 = any(c.get("name")=="Wi-Fi CERTIFIED 7™" and c.get("should_be_displayed_on_details") for c in certs)
        
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
    return pd.DataFrame(rows), total_count

def update_weekly_data(start_date: str = None):
    today = date.today()
    
    if start_date:
        date_from_str = start_date
    else:
        week_ago = today - timedelta(days=7)
        date_from_str = str(week_ago)

    date_to_str = str(today)

    all_df = pd.DataFrame()
    all_cert_ids_str = ",".join(CERTS) # ⭐ 모든 ID를 통합 ⭐
    start_index = 0
    # for c in CERTS:
    #     try:
    #         df = request_wifi(c, date_from)
    #         all_df = pd.concat([all_df, df], ignore_index=True)
    #     except Exception as e:
    #         print("Error fetching cert", c, e)

    while True:
        try:
            # request_wifi_optimized 함수 호출
            df, total_count = request_wifi_optimized(
                all_cert_ids_str, date_from_str, date_to_str, start_index, PAGE_LIMIT
            )
            
            if df.empty:
                print("-> Reached end of data.")
                break 

            all_df = pd.concat([all_df, df], ignore_index=True)
            
            start_index += PAGE_LIMIT
            
            if total_count > 0 and start_index >= total_count:
                print(f"-> Total count ({total_count}) reached.")
                break
                
            if len(df) < PAGE_LIMIT:
                print(f"-> Fetched less than PAGE_LIMIT ({len(df)} records). Assuming end of data.")
                break

        except requests.exceptions.HTTPError as e:
            print(f"Error fetching data at start={start_index}: {e}")
            break
        except Exception as e:
            print(f"Unexpected Error fetching data at start={start_index}: {e}")
            break
    
    if all_df.empty:
        print("No new data")
        return

    # 중복 제거: cid 기준 최근 날짜 우선
    all_df['date_certified'] = pd.to_datetime(all_df['date_certified'], errors='coerce')
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

def export_monthly_xlsx_csv(target_month: str = None):
    conn = get_db_connection()
    cur = conn.cursor()

    if target_month:
        target_month = target_month
    else:
        # 🔹 자동 실행 시 이전 달 (1일 기준으로 이전 달) 계산
        today = date.today()
        target_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    print(f"🗓 Exporting data for: {target_month}")
    
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
        return target_month, 0

    # 📁 폴더 생성: data/YYYY/
    year = target_month.split("-")[0]
    folder_path = Path(f"data/{year}")
    folder_path.mkdir(parents=True, exist_ok=True)

    # 💾 CSV 파일 저장: data/2025/2025-10.csv
    file_path = folder_path / f"{target_month}.csv"
    df.to_csv(file_path, index=False)
    print(f"📁 Monthly csv backup saved: {file_path}")
    
    # 💾 XLSX 파일 저장 경로 설정
    file_path = folder_path / f"{target_month}.xlsx"

    # Extract necessary columns
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

    # Rename 
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
    print("✅ Monthly export complete")

    return target_month, len(df_excel)

def delete_monthly_data(target_month: str):
    conn = get_db_connection()
    cur = conn.cursor()

    # 🔹 이번 달(1일 기준으로 이전 달)을 백업 대상으로 계산
    # today = date.today()
    # target_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    
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
        print("Error: Missing run mode argument. Use 'weekly', 'monthly_export', or 'monthly_delete'.")
        sys.exit(1)
        
    mode = sys.argv[1]
    
    if mode == 'weekly':
        start_date = sys.argv[2] if len(sys.argv) > 2 else None
        print("🚀 Starting weekly data update...")
        update_weekly_data(start_date)
    elif mode == 'monthly_export':
        print("💾 Starting monthly backup...")
        target_month, count = export_monthly_xlsx_csv()
        # Save target_month to environment variable file
        with open(os.environ.get("GITHUB_ENV"), "a") as env_file:
            env_file.write(f"TARGET_MONTH={target_month}\n")    
    elif mode == 'monthly_delete':
        if len(sys.argv) != 3:
            print("Error: 'monthly_delete' mode requires exactly one target month argument (YYYY-MM).")
            sys.exit(1)
        target_month = sys.argv[2]
        delete_monthly_data(target_month)
    else:
        print(f"Error: Invalid run mode: {mode}")
        sys.exit(1)

if __name__ == "__main__":
    main()
