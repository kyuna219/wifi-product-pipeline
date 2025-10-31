# 예시파일임! 미완성.

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
        d = {
            "cid": p.get("cid"),
            "brand": p.get("companyName"),
            "product": p.get("name"),
            "model_number": p.get("modelNumber"),
            "date_certified": p.get("certified"),
            "category": p.get("productCategory", {}).get("product_consumer_category_class", {}).get("name"),
            "frequency_band": p.get("frequencyBand"),
            "wifi_n": any(c.get("name")=="Wi-Fi CERTIFIED™ n" and c.get("should_be_displayed_on_details") for c in certs),
            "wifi_ac": any(c.get("name")=="Wi-Fi CERTIFIED™ ac" and c.get("should_be_displayed_on_details") for c in certs),
            "wifi_6": any(c.get("name")=="Wi-Fi CERTIFIED 6®" and c.get("should_be_displayed_on_details") for c in certs),
            "wifi_7": any(c.get("name")=="Wi-Fi CERTIFIED 7™" and c.get("should_be_displayed_on_details") for c in certs),
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
            r["category"], r["frequency_band"],
            bool(r["wifi_n"]), bool(r["wifi_ac"]), bool(r["wifi_6"]), bool(r["wifi_7"])
        ))

    insert_sql = """
    INSERT INTO wifi_products (
      cid, brand, product, model_number, date_certified,
      category, frequency_band, wifi_n, wifi_ac, wifi_6, wifi_7
    ) VALUES %s
    ON CONFLICT (cid) DO UPDATE SET
      brand = EXCLUDED.brand,
      product = EXCLUDED.product,
      model_number = EXCLUDED.model_number,
      date_certified = EXCLUDED.date_certified,
      category = EXCLUDED.category,
      frequency_band = EXCLUDED.frequency_band,
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
    df = pd.read_sql("SELECT * FROM wifi_products ORDER BY date_certified DESC;", conn)
    conn.close()

    if df.empty:
        print("⚠️ No data to back up.")
        return

    # 📁 폴더 경로 생성: data/YYYY/
    year = date.today().year
    month = date.today().strftime("%m")
    folder_path = Path(f"data/{year}")
    folder_path.mkdir(parents=True, exist_ok=True)

    # 💾 파일 경로 예시: data/2025/2025-10.csv
    file_path = folder_path / f"{year}-{month}.csv"
    df.to_csv(file_path, index=False)
    print(f"📁 Monthly backup saved: {file_path}")

    # DELETE로 백업된 데이터 지우고 DB 정리
    cur.execute("""
        DELETE FROM wifi_products
        WHERE TO_CHAR(date_certified, 'YYYY-MM') = %s
    """, (target_month,))
    conn.commit()
    print(f"🧹 Deleted data for {target_month} from DB")

def main():
    update_weekly_data()

    # 🔸 매달 1일이면 백업 실행
    today = date.today()
    if today.day == 1:
        print("🗓 Running monthly backup...")
        backup_monthly_csv()

if __name__ == "__main__":
    main()
