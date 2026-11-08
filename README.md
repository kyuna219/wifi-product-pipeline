# Wi-Fi Certified Product Data Pipeline

An automated data pipeline that collects Wi-Fi Certified™ product information from the [Wi-Fi Alliance](https://www.wi-fi.org/), transforms the records, stores them in PostgreSQL, and makes the data explorable through a Streamlit dashboard.

## Architecture

```text
Wi-Fi Alliance product data endpoint
              |
              v
      GitHub Actions
       (scheduled jobs)
              | 
              v
    Python ETL (Requests
       + Pandas)
              |
              v
 PostgreSQL database (Neon)
              |
              v
   Streamlit + Plotly dashboard
```

GitHub Actions orchestrates scheduled ingestion and monthly backup workflows.

## Key Features

- Retrieves product certification records from the Wi-Fi Alliance product endpoint.
- Uses pagination to retrieve larger result sets.
- Extracts product ID, brand, product name, model number, certification date, category, frequency band, and supported Wi-Fi standards.
- Sorts by certification date and deduplicates by certification ID (`cid`).
- Uses PostgreSQL `ON CONFLICT (cid) DO UPDATE` to insert new products and refresh existing records.
- Runs weekly ETL updates through GitHub Actions.
- Exports the previous month's records to CSV and XLSX.
- Commits monthly exports to GitHub and uploads the XLSX backup to Google Drive through the configured workflow.
- Provides a Streamlit dashboard with Plotly charts, brand filtering, and XLSX download.

## Tech Stack

| Component | Technology |
|---|---|
| Data source | Wi-Fi Alliance product data endpoint |
| Ingestion | Python, Requests |
| Transformation | Pandas |
| Database | PostgreSQL, Neon |
| Database driver | psycopg2 |
| Orchestration | GitHub Actions |
| Dashboard | Streamlit, Plotly |
| Export | CSV, XLSX, openpyxl |
| Archive | Google Drive |

## Data Model

The ETL creates a `wifi_products` table with `cid` as the primary key.

| Field | Description |
|---|---|
| `cid` | Product certification ID; primary key |
| `brand` | Company or brand name |
| `product` | Product name |
| `model_number` | Product model number |
| `date_certified` | Certification date |
| `category` | Product category |
| `frequency_band` | Supported frequency band |
| `wifi_support_list` | Comma-separated supported Wi-Fi standards |
| `wifi_n`, `wifi_ac`, `wifi_6`, `wifi_7` | Boolean support flags |

The current extraction logic checks certification IDs `276`, `235`, `189`, and `1652`, and identifies Wi-Fi n, ac, 6, and 7 support from returned certification metadata.

## Automation

Workflow definition: `.github/workflows/weekly_wifi_update.yml`.

| Workflow | Schedule | Purpose |
|---|---|---|
| Weekly update | Monday at 09:00 UTC | Fetch preceding seven days and upsert records |
| Monthly export | 1st day of each month at 09:00 UTC | Export previous month's records and archive the backup |
| Manual weekly update | On demand | Update from a supplied start date |
| Manual deletion | On demand | Delete records for a specified month |

The workflow uses Python 3.11 and repository Actions secrets for database and Google Drive credentials.

Manual workflow modes available through **Actions → Run workflow**:

- `scheduled_weekly`: default seven-day update.
- `manual_weekly`: update from a supplied `YYYY-MM-DD` start date.
- `monthly_export`: export the previous month's data.
- `manual_delete`: delete data for a supplied month.

## Dashboard

The Streamlit app connects to PostgreSQL using Streamlit's SQL connection interface.

Features:

- Bar chart of product counts by supported Wi-Fi standard.
- Sidebar filter for the top 10 brands.
- Interactive product table.
- XLSX download of the full dataset.
- Cached query results with a seven-day time-to-live.

[Open the live Streamlit dashboard](https://wifi-certified.streamlit.app/).

## Local Setup

### 1. Clone

```bash
git clone https://github.com/kyuna219/wifi-product-pipeline.git
cd wifi-product-pipeline
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure PostgreSQL environment variables

Set these variables in your local environment. Do not commit credentials or a populated `.env` file.

```text
POSTGRES_HOST=your-host
POSTGRES_PORT=5432
POSTGRES_DB=your-database
POSTGRES_USER=your-username
POSTGRES_PASSWORD=your-password
POSTGRES_SSLMODE=require
```

### 5. Run the ETL

Update the last seven days:

```bash
python scripts/fetch_and_load.py weekly
```

Update from a specific start date:

```bash
python scripts/fetch_and_load.py weekly 2025-01-01
```

Export the previous month's records:

```bash
python scripts/fetch_and_load.py monthly_export
```

Delete records for a specific month (use with care):

```bash
python scripts/fetch_and_load.py monthly_delete 2025-01
```

### 6. Run the dashboard

Configure the PostgreSQL connection in Streamlit secrets, then run:

```bash
streamlit run scripts/dashboard.py
```

## GitHub Actions Configuration

Configure these repository secrets before enabling automated workflows:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_SSLMODE`
- `GDRIVE_SERVICE_ACCOUNT_CREDENTIALS`

The Streamlit app also requires PostgreSQL connection values in its app secrets.

Never put database passwords, service-account JSON, or other credentials in source code or commit them to Git.

## Repository Structure

```text
wifi-product-pipeline/
├── .github/
│   └── workflows/
│       └── weekly_wifi_update.yml
├── scripts/
│   ├── fetch_and_load.py
│   ├── dashboard.py
│   └── gdrive_upload.py
├── data/
│   └── YYYY/
│       ├── WiFi_Products_YYYY-MM.csv
│       └── WiFi_Products_YYYY-MM.xlsx
├── requirements.txt
└── README.md
```

## Future Improvements

- Add automated data-quality checks and structured logging.
- Add retry and alerting behavior for failed ingestion runs.
- Expand dashboard trends by certification date, category, and frequency band.
- Add tests for API parsing, deduplication, and database upsert behavior.
- Review historical retention and backup policies as the dataset grows.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Author

**Yuna Kim**

- [GitHub](https://github.com/kyuna219)
- [LinkedIn](https://www.linkedin.com/in/yuna-kim-/)
