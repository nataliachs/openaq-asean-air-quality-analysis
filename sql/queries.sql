-- ============================================================
-- ASEAN Air Quality Analysis (OpenAQ) — SQL Queries
-- ============================================================
-- Analytical queries answering business questions about the cleaned
-- ASEAN air quality dataset (2021-2026). Compatible with SQLite,
-- PostgreSQL, MySQL, and BigQuery.
--
-- To load data into SQLite:
--   sqlite3 air_quality.db
--   .mode csv
--   .headers on
--   .import data/processed/openaq_clean.csv air_quality
--
-- Sections:
--   1. Basic exploration
--   2. Country comparison
--   3. AQI bucket distribution
--   4. Time-series analysis
--   5. Window functions (ranks, rolling averages, YoY)
--   6. Indonesia deep dive
--   7. WHO compliance analysis
--   8. Data quality checks
-- ============================================================


-- ============================================================
-- 1. BASIC EXPLORATION
-- ============================================================

-- Q1.1 Records summary by country
SELECT country,
       COUNT(*) AS records,
       COUNT(DISTINCT city) AS cities,
       MIN(date) AS first_date,
       MAX(date) AS last_date
FROM air_quality
GROUP BY country
ORDER BY records DESC;

-- Q1.2 Worst PM2.5 readings ever recorded
SELECT country, city, date, pm25, aqi_pm25, aqi_bucket
FROM air_quality
WHERE pm25 IS NOT NULL
ORDER BY pm25 DESC
LIMIT 20;

-- Q1.3 Best (cleanest) PM2.5 days
SELECT country, city, date, pm25, aqi_bucket
FROM air_quality
WHERE pm25 IS NOT NULL
ORDER BY pm25 ASC
LIMIT 20;


-- ============================================================
-- 2. AGGREGATIONS — Country Comparison
-- ============================================================

-- Q2.1 Average PM2.5 by country (the main ranking)
SELECT country,
       ROUND(AVG(pm25), 1) AS avg_pm25,
       ROUND(AVG(pm10), 1) AS avg_pm10,
       ROUND(AVG(aqi_pm25), 1) AS avg_aqi,
       COUNT(DISTINCT city) AS cities,
       COUNT(*) AS records
FROM air_quality
WHERE pm25 IS NOT NULL
GROUP BY country
ORDER BY avg_pm25 DESC;

-- Q2.2 Mean vs Median (chronic vs episodic pollution)
-- Note: SQLite doesn't have a built-in median function; this uses
-- a workaround. PostgreSQL: use PERCENTILE_CONT(0.5) WITHIN GROUP
SELECT
    country,
    ROUND(AVG(pm25), 1) AS mean_pm25,
    ROUND((SELECT pm25
           FROM air_quality AS sub
           WHERE sub.country = aq.country AND sub.pm25 IS NOT NULL
           ORDER BY sub.pm25
           LIMIT 1
           OFFSET (SELECT COUNT(*) / 2
                   FROM air_quality AS sub2
                   WHERE sub2.country = aq.country AND sub2.pm25 IS NOT NULL)), 1)
        AS median_pm25,
    ROUND(AVG(pm25) - (SELECT pm25
                       FROM air_quality AS sub
                       WHERE sub.country = aq.country AND sub.pm25 IS NOT NULL
                       ORDER BY sub.pm25
                       LIMIT 1
                       OFFSET (SELECT COUNT(*) / 2
                               FROM air_quality AS sub2
                               WHERE sub2.country = aq.country AND sub2.pm25 IS NOT NULL)), 1)
        AS skew
FROM air_quality AS aq
WHERE pm25 IS NOT NULL
GROUP BY country
ORDER BY skew DESC;


-- ============================================================
-- 3. AQI BUCKET DISTRIBUTION
-- ============================================================

-- Q3.1 % of days at each AQI level by country
SELECT country,
       ROUND(SUM(CASE WHEN aqi_bucket = 'Good' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_good,
       ROUND(SUM(CASE WHEN aqi_bucket = 'Moderate' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_moderate,
       ROUND(SUM(CASE WHEN aqi_bucket = 'Unhealthy for Sensitive' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_unhealthy_sensitive,
       ROUND(SUM(CASE WHEN aqi_bucket = 'Unhealthy' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_unhealthy,
       ROUND(SUM(CASE WHEN aqi_bucket IN ('Very Unhealthy', 'Hazardous') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_very_bad
FROM air_quality
WHERE aqi_bucket IS NOT NULL
GROUP BY country
ORDER BY pct_good DESC;


-- ============================================================
-- 4. TIME-SERIES ANALYSIS
-- ============================================================

-- Q4.1 Yearly trend by country
SELECT year,
       country,
       ROUND(AVG(pm25), 1) AS avg_pm25,
       ROUND(AVG(aqi_pm25), 1) AS avg_aqi,
       COUNT(*) AS records
FROM air_quality
WHERE pm25 IS NOT NULL
GROUP BY year, country
ORDER BY country, year;

-- Q4.2 Monthly seasonality across all countries
SELECT month,
       ROUND(AVG(pm25), 1) AS avg_pm25_global,
       COUNT(*) AS records
FROM air_quality
WHERE pm25 IS NOT NULL
GROUP BY month
ORDER BY month;

-- Q4.3 Worst pollution months in Indonesia (dry season pattern)
SELECT year, month,
       ROUND(AVG(pm25), 1) AS avg_pm25,
       ROUND(MAX(pm25), 1) AS max_pm25,
       COUNT(*) AS records
FROM air_quality
WHERE country = 'Indonesia' AND pm25 IS NOT NULL
GROUP BY year, month
ORDER BY avg_pm25 DESC
LIMIT 20;


-- ============================================================
-- 5. WINDOW FUNCTIONS — Advanced SQL
-- ============================================================

-- Q5.1 Rank cities within each country by avg PM2.5
WITH city_avg AS (
    SELECT country, city,
           AVG(pm25) AS avg_pm25,
           COUNT(*) AS days
    FROM air_quality
    WHERE pm25 IS NOT NULL
    GROUP BY country, city
    HAVING COUNT(*) >= 30
)
SELECT country, city,
       ROUND(avg_pm25, 1) AS avg_pm25,
       days,
       RANK() OVER (PARTITION BY country ORDER BY avg_pm25 DESC) AS rank_in_country,
       RANK() OVER (ORDER BY avg_pm25 DESC) AS rank_global
FROM city_avg
ORDER BY country, rank_in_country;

-- Q5.2 Year-over-year change per country
WITH yearly AS (
    SELECT country, year, AVG(pm25) AS avg_pm25
    FROM air_quality
    WHERE pm25 IS NOT NULL
    GROUP BY country, year
)
SELECT country, year,
       ROUND(avg_pm25, 1) AS avg_pm25,
       ROUND(LAG(avg_pm25) OVER (PARTITION BY country ORDER BY year), 1) AS prev_year_pm25,
       ROUND(avg_pm25 - LAG(avg_pm25) OVER (PARTITION BY country ORDER BY year), 1) AS yoy_change,
       ROUND((avg_pm25 - LAG(avg_pm25) OVER (PARTITION BY country ORDER BY year)) /
             LAG(avg_pm25) OVER (PARTITION BY country ORDER BY year) * 100, 1) AS yoy_pct_change
FROM yearly
ORDER BY country, year;

-- Q5.3 Rolling 7-day average PM2.5 per city (recent data)
SELECT city, country, date, pm25,
       ROUND(AVG(pm25) OVER (
           PARTITION BY city
           ORDER BY date
           ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
       ), 1) AS rolling_7day_avg
FROM air_quality
WHERE pm25 IS NOT NULL AND country = 'Indonesia'
ORDER BY city, date DESC
LIMIT 50;


-- ============================================================
-- 6. INDONESIA DEEP DIVE
-- ============================================================

-- Q6.1 Indonesian cities ranked
SELECT city,
       ROUND(AVG(pm25), 1) AS avg_pm25,
       ROUND(AVG(aqi_pm25), 1) AS avg_aqi,
       COUNT(*) AS days,
       ROUND(MIN(pm25), 1) AS min_pm25,
       ROUND(MAX(pm25), 1) AS max_pm25
FROM air_quality
WHERE country = 'Indonesia' AND pm25 IS NOT NULL
GROUP BY city
HAVING COUNT(*) >= 30
ORDER BY avg_pm25 DESC;

-- Q6.2 Indonesia vs ASEAN neighbors yearly
SELECT country, year,
       ROUND(AVG(pm25), 1) AS avg_pm25,
       ROUND(AVG(aqi_pm25), 1) AS avg_aqi
FROM air_quality
WHERE country IN ('Indonesia', 'Singapore', 'Malaysia', 'Thailand',
                   'Vietnam', 'Philippines', 'Cambodia', 'Myanmar')
  AND pm25 IS NOT NULL
GROUP BY country, year
ORDER BY country, year;

-- Q6.3 Indonesia's seasonal forest fire pattern (June-October peaks)
SELECT
    CASE
        WHEN month BETWEEN 6 AND 10 THEN 'Dry/Fire Season (Jun-Oct)'
        ELSE 'Wet Season (Nov-May)'
    END AS season,
    ROUND(AVG(pm25), 1) AS avg_pm25,
    ROUND(MAX(pm25), 1) AS max_pm25,
    COUNT(*) AS days
FROM air_quality
WHERE country = 'Indonesia' AND pm25 IS NOT NULL
GROUP BY season;


-- ============================================================
-- 7. WHO COMPLIANCE ANALYSIS
-- ============================================================

-- Q7.1 % of days exceeding WHO safe limit (10 µg/m³)
SELECT country,
       COUNT(*) AS total_days,
       SUM(CASE WHEN pm25 > 10 THEN 1 ELSE 0 END) AS above_who_safe,
       ROUND(SUM(CASE WHEN pm25 > 10 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_above_who_safe,
       SUM(CASE WHEN pm25 > 15 THEN 1 ELSE 0 END) AS above_who_interim,
       ROUND(SUM(CASE WHEN pm25 > 15 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_above_who_interim
FROM air_quality
WHERE pm25 IS NOT NULL
GROUP BY country
ORDER BY pct_above_who_safe DESC;


-- ============================================================
-- 8. DATA QUALITY CHECKS (METHODOLOGY)
-- ============================================================

-- Q8.1 Reliability tiers — cities with 100+ days of data
SELECT country, city, COUNT(*) AS days,
       CASE WHEN COUNT(*) >= 100 THEN 'Reliable' ELSE 'Limited' END AS reliability
FROM air_quality
WHERE pm25 IS NOT NULL
GROUP BY country, city
ORDER BY country, days DESC;

-- Q8.2 Detect potential sensor anomalies (extreme outliers per city)
SELECT country, city,
       ROUND(AVG(pm25), 1) AS avg_pm25,
       ROUND(MAX(pm25), 1) AS max_pm25,
       ROUND(MAX(pm25) / NULLIF(AVG(pm25), 0), 2) AS max_to_avg_ratio,
       COUNT(*) AS days
FROM air_quality
WHERE pm25 IS NOT NULL
GROUP BY country, city
HAVING MAX(pm25) > 5 * AVG(pm25) AND COUNT(*) > 30
ORDER BY max_to_avg_ratio DESC;
