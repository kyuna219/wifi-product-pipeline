# 🛰️ Wi-Fi Certified Product Data Pipeline

A fully automated data pipeline that fetches, processes, and stores **Wi-Fi Certified™ product data** from [Wi-Fi Alliance](https://www.wi-fi.org/) using **GitHub Actions**, **PostgreSQL**, and **Tableau** for visualization.

> **Goal:** Provide up-to-date Wi-Fi certification insights every week through automated data collection and visualization.

---

## 📊 Overview

This project automates the process of collecting and updating Wi-Fi Certified™ product information weekly.  
It replaces traditional on-premise schedulers (like Airflow) with **GitHub Actions**, enabling cloud-based automation even when the local machine is off.

### 🔁 Data Flow
Wi-Fi Alliance API → GitHub Actions → PostgreSQL (Neon/Supabase or local) → Tableau (Dashboard)

---

## ⚙️ Key Features

- 🕓 **Weekly Scheduled Data Updates** via GitHub Actions  
- ☁️ **No Local Server Needed** — runs entirely in the cloud  
- 🧹 **Automated Data Cleaning & Deduplication**  
- 🗄️ **Storage in PostgreSQL** (local or Neon.tech cloud or Supabase)  
- 📈 **Interactive Tableau Dashboard** for visualization  
- 💾 **Historical Data Archiving** (optional: GitHub or Google Drive)

---

## 🧩 Tech Stack

| Component | Technology |
|------------|-------------|
| Automation | GitHub Actions |
| Database | PostgreSQL / Neon.tech / Supabase |
| Data Processing | Python (requests, pandas, psycopg2) |
| Visualization | Tableau Public |
| Version Control | Git + GitHub |

---

## 🚀 Project Structure
```
wifi_certified_data_pipeline/
│
├── .github/workflows/
│ └── update_data.yml # GitHub Actions workflow
│
├── scripts/
│ ├── fetch_wifi_data.py # Fetch and clean Wi-Fi data
│ └── upload_to_postgres.py # Insert data into PostgreSQL
│
├── data/
│ └── (optional) archived_data.csv
│
├── README.md
└── requirements.txt
```
---

## 🗓️ How It Works

1. **GitHub Actions** triggers every week (e.g., Sunday 00:00 UTC).
2. Python scripts request the latest data from Wi-Fi Alliance API.
3. Data is processed and cleaned with `pandas`.
4. Duplicates from previous weeks are checked and removed.
5. Final dataset is stored in **PostgreSQL** (local or Neon cloud or Supabase).
6. **Tableau** fetches the latest dataset automatically for visualization.

---

## 🔄 Setup (for local testing)

### 1️⃣ Create a `.env` file:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

### 2️⃣ Install dependencies:
```bash
pip install -r requirements.txt
```

### 3️⃣ Run manually:
```bash
python scripts/fetch_wifi_data.py
python scripts/upload_to_postgres.py
```
