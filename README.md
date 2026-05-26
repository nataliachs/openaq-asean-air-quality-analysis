# ASEAN Air Quality Analysis (2021-2026)

Analysis of 5 years of air quality data from 8 ASEAN countries, sourced from [OpenAQ](https://openaq.org) — an open API providing measurements from government and research monitoring stations across the region.

## 🎯 Business Question

**"How does Indonesia's air quality compare to its ASEAN neighbors, and what does the data reveal about the region's pollution patterns?"**

Specifically:
- Which ASEAN cities have the worst air quality?
- How does Indonesia rank regionally?
- Are there seasonal patterns?
- What share of days are actually safe to breathe?

## 📊 Key Findings

### 1. Indonesia leads ASEAN in chronic air pollution
With an average PM2.5 of 42.1 µg/m³ across 7 cities and 2,941 records, Indonesia ranks #1 most polluted country in monitored ASEAN. Critically, Indonesia's **mean (42.1) and median (40.3) are nearly identical**, indicating chronic, day-after-day pollution — arguably worse for cumulative public health than countries with occasional spikes.

### 2. Among reliable city-level data, Indonesia has 2 of the top 3 worst cities
Filtering to cities with 2+ sensors and 100+ days of data:
- **Hanoi, Vietnam:** 41.3 µg/m³
- **Yogyakarta, Indonesia:** 40.5 µg/m³ (statistically validated as healthy data)
- **Jakarta, Indonesia:** 36.7 µg/m³ (8 sensors, most reliable Indonesian estimate)

### 3. Indonesia's air quality crisis is seasonal
The June-October period (Indonesia's dry season) consistently shows the worst PM2.5 readings. August 2023 hit 68 µg/m³ — coinciding with documented El Niño-driven forest fires in Sumatra and Kalimantan. Wet season (November-March) brings significant relief.

### 4. Only 4.4% of days in Indonesia have "Good" air quality
Out of every 365 days, only ~16 have AQI in the "Good" range. The other 95.6% are at varying levels of pollution, with **57.9% reaching "Unhealthy for Sensitive Groups" or worse**. This is 4.5x worse than Singapore's 19.8% Good days.

### 5. Even Singapore can't escape regional pollution
Despite having the strictest environmental policies in ASEAN, Singapore averages 19.8 µg/m³ — nearly 2x the WHO safe limit (10) and 32% above the WHO interim target (15). Regional smoke and emissions impose a floor that no single country can drop below alone.

### 6. ASEAN splits into a clear two-tier pollution landscape
- **Tier 1 (AQI 95-112):** Indonesia, Vietnam — Unhealthy for Sensitive Groups on average
- **Tier 2 (AQI 63-75):** Myanmar, Thailand, Malaysia, Philippines, Singapore, Cambodia — Moderate

The 18-point AQI gap between Indonesia and Vietnam (#2) shows Indonesia faces uniquely severe air quality challenges.

## 🔬 Methodology Highlights

### Data Quality Discovery
Initial analysis showed Vietnam averaging 380 µg/m³ in 2023 — implausibly high. Investigation traced the spike to a single sensor at the **US Diplomatic Post in Ho Chi Minh City** reporting impossible values (max 985 µg/m³ across 559 days). Cross-referencing with [UN data showing Vietnam's true 2023 PM2.5 averages were 21-52 µg/m³](https://www.unicef.org/vietnam/stories/viet-nams-heavy-air-pollution-needs-stronger-action) confirmed sensor malfunction. After filtering out values above 500 µg/m³, Vietnam's average aligned with regional norms.

### Sensor Reliability Tiers
Cities are categorized by sensor coverage:
- **Reliable:** 2+ sensors AND 100+ days of data
- **Limited:** Single sensor or fewer than 100 days

Findings about limited-data cities (Bandung, Bogor, Medan, Palembang) are noted as preliminary indicators rather than confirmed citywide measurements.

### GPS-Based City Re-classification
OpenAQ's `locality` field is often empty or inaccurate. Sensors were re-assigned to cities using strict GPS bounding boxes, separating Jakarta from neighboring Depok, Tangerang, Bekasi, and Bogor. This revealed that some sensors initially labeled "Jakarta" were actually in Depok or, in one case, 1,000 km away in Sumatra.

## 🛠 Tech Stack

| Component | Tool |
|-----------|------|
| Data Source | OpenAQ API (real-time air quality measurements) |
| Data Processing | Pandas, NumPy |
| Visualization | Matplotlib, Seaborn, Plotly |
| Statistics | SciPy |
| Dashboard | Streamlit |
| Database | SQL (SQLite, PostgreSQL compatible) |
| Notebooks | Jupyter |
| External Validation | UN/WHO/UNICEF reports |

## 📁 Project Structure

```
openaq-air-quality-analysis/
├── README.md                          # You are here
├── requirements.txt                   # Dependencies
├── .env.example                       # API key template
├── data/
│   ├── raw/                           # Scraped data
│   └── processed/                     # Cleaned data
├── scripts/
│   ├── explore_locations.py           # Discover monitoring stations
│   └── fetch_measurements.py          # Pull historical data
├── notebooks/
│   ├── 01_data_cleaning.ipynb         # Clean, validate, GPS reclassify
│   └── 02_eda.ipynb                   # Analysis with reliability checks
├── sql/
│   └── queries.sql                    # Demonstrations of SQL skills
└── dashboard/
    └── app.py                         # Streamlit interactive dashboard
```

## 🚀 How to Run

### 1. Setup

```bash
pip install -r requirements.txt
```

### 2. Get API Key

Sign up at [explore.openaq.org/register](https://explore.openaq.org/register) (free).

Create a `.env` file in the project root:
```
OPENAQ_API_KEY=your_actual_key_here
```

### 3. Pull Data

```bash
# Discover available monitoring stations
python scripts/explore_locations.py

# Fetch historical measurements (~30-60 minutes)
python scripts/fetch_measurements.py
```

### 4. Run Analysis

```bash
python -m jupyter notebook notebooks/
```

Run notebooks in order:
1. `01_data_cleaning.ipynb` — produces cleaned dataset
2. `02_eda.ipynb` — exploratory analysis with reliability checks

### 5. Launch Dashboard

```bash
python -m streamlit run dashboard/app.py
```

### 6. Run SQL Queries

```bash
sqlite3 air_quality.db < sql/queries.sql
```

## ⚠️ Data Limitations

- **Coverage gaps:** Brunei and Laos have no monitoring stations in OpenAQ. Myanmar has only 3.
- **Sensor density bias:** Jakarta has 8 sensors while smaller Indonesian cities have only 1-2 each, limiting cross-city comparisons.
- **Time range:** Data starts in May 2021, so a true pre-COVID baseline isn't available.
- **Source:** OpenAQ aggregates data from various government and research stations — not all sensors are equivalently calibrated or maintained.
- **Granularity:** Daily aggregates (not hourly) are used for analysis.

## 🛠 Tools & Techniques

- **OpenAQ API** for real-time air quality measurements
- **Python ETL pipeline** with rate limiting, retries, and incremental saves
- **GPS-based geocoding** to assign sensors to cities by coordinates
- **Outlier detection** with biological plausibility caps and external validation
- **Statistical analysis** including mean-vs-median distribution comparison
- **Multi-source cross-referencing** with UN, WHO, and UNICEF reports
- **Pandas + NumPy** for data wrangling
- **Plotly + Matplotlib + Seaborn** for visualization
- **SQL** with window functions, CTEs, and time-series queries
- **Streamlit** for the interactive dashboard

## 🌏 What This Means for Indonesia

Air quality in Indonesia is not a Jakarta-centric problem. Yogyakarta, Depok, and Bandung all show pollution levels comparable to or exceeding Jakarta. With only 4.4% of days providing genuinely clean air, this represents a chronic public health condition affecting 270+ million people year-round, with documented seasonal worsening from regional forest fires.

Solving Indonesia's air quality crisis requires:
1. **Regional coordination** — Forest fires are transboundary
2. **Year-round emission controls** — Not just dry-season responses
3. **City-specific monitoring expansion** — Many Indonesian cities lack adequate sensor coverage
4. **Public health planning** — Sensitive populations need year-round protection

## 💼 Business Decisions This Analysis Supports

### Public Sector
- **Health budgets:** Allocate respiratory care resources year-round, not just during fire season — Indonesia's chronic pollution pattern means cumulative health impact is constant
- **School policies:** Issue mask mandates or remote learning days during Jun-Oct peaks
- **Hospital readiness:** Pre-stock respiratory medications before dry season starts
- **Forest fire prevention:** Pre-deploy resources to Sumatra and Kalimantan in May
- **Sensor infrastructure:** Most Indonesian cities have only 1-2 sensors — a national air quality monitoring expansion is overdue

### Private Sector
- **Air purifier market:** 270M+ Indonesians are exposed to chronic pollution year-round, not just seasonally — a sustained-demand market larger than typical seasonal estimates
- **Real estate:** Buildings with air purification systems can command premium pricing; cleaner cities like Bogor may appreciate as awareness grows
- **Insurance:** Pricing models can incorporate city-level air quality as a health risk factor
- **HR & talent:** Air quality is a real factor in relocation decisions and family planning for skilled workers

### Tourism
- **Seasonal positioning:** Wet season (Nov-Mar) marketing should emphasize cleaner air as a value proposition
- **Destination diversification:** Promote Bogor and other cleaner Indonesian cities as alternatives to traditional Jakarta-focused tourism

### Cross-Border Cooperation
- **ASEAN haze policy:** Indonesia's pollution affects Singapore and Malaysia — multilateral funding agreements are economically rational for all parties
- **Climate aid allocation:** International climate funding focused on Indonesia would have outsized regional health impact

## 📝 License

MIT License — free for educational and portfolio use.

## 🙏 Acknowledgments

- [OpenAQ](https://openaq.org) for providing free, open-access air quality data
- WHO, UN, UNICEF, and Vietnamese news outlets for context and validation data

Findings reflect public data accessible through OpenAQ as of May 2026.
