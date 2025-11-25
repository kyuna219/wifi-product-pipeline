# 🛰️ Wi-Fi Certified Product Data Pipeline

A fully automated data pipeline that fetches, processes, and stores **Wi-Fi Certified™ product data** from [Wi-Fi Alliance](https://www.wi-fi.org/) using **GitHub Actions**, **PostgreSQL**, and **Streamlit** for visualization.

> **Goal:** Provide up-to-date Wi-Fi certification insights every month through automated data collection and visualization.

---

## 📊 Overview

This project automates the process of collecting and updating Wi-Fi Certified™ product information weekly.  
It replaces traditional on-premise schedulers (like Airflow) with **GitHub Actions**, enabling cloud-based automation even when the local machine is off.

### 🔁 Data Flow
Wi-Fi Alliance API → GitHub Actions → PostgreSQL (Neon) → Streamlit (Dashboard)

---

## ⚙️ Key Features

- 🕓 **Weekly Scheduled Data Updates** via GitHub Actions
- 📦 **Manual Monthly Backups** to GitHub Repository and Google Drive
- ☁️ **No Local Server Needed** — runs entirely in the cloud  
- 🧹 **Automated Data Cleaning & Deduplication**  
- 🗄️ **Storage in PostgreSQL** (local or Neon.tech cloud)  
- 📈 **Interactive Streamlit Dashboard** for visualization  
- 💾 **Historical Data Archiving** (GitHub and Google Drive)

---

## 🧩 Tech Stack

| Component | Technology |
|------------|-------------|
| Automation | GitHub Actions (Scheduler) |
| Database | PostgreSQL / Neon.tech |
| Data Processing | Python (requests, pandas, psycopg2) |
| Visualization | Streamlit |
| Version Control | Git + GitHub |

---

## 🚀 Project Structure
```
wifi_certified_data_pipeline/
│
├── .github/workflows/
│ └── weekly_wifi_update.yml # GitHub Actions workflow
│
├── scripts/
│ ├── fetch_and_load.py # Fetch and load Wi-Fi data
│ ├── gdrive_upload.py # Save last month's Excel data to Google Drive
│ ├── dashboard.py # Build visualization for Streamlit
│
├── data/
│ └── YYYY/YYYY-MM.xlsx/csv # Monthly backup files
│
├── README.md
└── requirements.txt
```
---

## 🗓️ How It Works

1. **GitHub Actions** triggers every week (e.g., Sunday 00:00 UTC) for weekly updates and monthly (1st day 09:00 UTC) for backups.
2. Python script (fetch_and_load.py) requests the latest data from Wi-Fi Alliance API.
3. Data is processed and cleaned with `pandas`.
4. Duplicates from previous weeks are checked and removed.
5. Final dataset is upserted (INSERT/UPDATE) into **PostgreSQL** (Neon cloud).
6. Monthly: A dedicated job exports the previous month's data from PostgreSQL into a CSV and XLSX file and archives them on GitHub and Google Drive.
7. **Streamlit** fetches the latest dataset automatically for visualization.

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
# weekly update (saved to DB)
python scripts/fetch_and_load.py scheduled_weekly

# monthly backup (export data into CSV/XLSX)
python scripts/fetch_and_load.py monthly_export
```

## ☁️ Deployment via GitHub Actions
The update_data.yml workflow automates the weekly job.
```
name: Update Wi-Fi Certified Data

on:
  schedule:
    - cron: '0 0 * * 0'   # Every Sunday at 00:00 UTC
    - cron: '0 9 1 * *'    # Every 1st day of the month at 09:00 UTC (Monthly Backup)
  workflow_dispatch:

jobs:
  update:  # Weekly update job
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Weekly Data Update
        run: python scripts/fetch_and_load.py scheduled_weekly
```

## 📈 Streamlit Dashboard

A Streamlit Public dashboard connects directly to your PostgreSQL (Neon) database.
This ensures the dashboard always displays the latest Wi-Fi certification trends.

[Streamlit Dashboard](https://wifi-certified.streamlit.app/) 👉 View Dashboard on Streamlit

## 💾 Historical Archiving

Archived data is structured by year and month.
Older data (past months) can be exported and stored in:

```
data/YYYY/YYYY-MM.xlsx/csv within this repo

or Google Drive 
```

## 🧠 Future Improvements

- Add visualization for certification frequency trends
- Add a monthly data deletion step to the pipeline to keep the database small.

## 📜 License

This project is licensed under the MIT License — feel free to use and adapt it.

## 👩‍💻 Author

Yuna Kim
