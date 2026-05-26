"""Streamlit Dashboard for ASEAN Air Quality Analysis.

Run with:
    python -m streamlit run dashboard/app.py
"""

from pathlib import Path

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px


# --- PAGE CONFIG ---
st.set_page_config(
    page_title="ASEAN Air Quality Analysis 2021-2026",
    page_icon="🌏",
    layout="wide",
)


# --- LOAD DATA ---
@st.cache_data
def load_data():
    """Load the cleaned dataset (parquet preferred, CSV fallback)."""
    base = Path(__file__).parent.parent / "data" / "processed"
    parquet_path = base / "openaq_clean.parquet"
    csv_path = base / "openaq_clean.csv"

    if parquet_path.exists():
        df = pd.read_parquet(parquet_path)
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        st.error(f"Cleaned data not found at {parquet_path} or {csv_path}.")
        st.error("Run notebook 01 first to generate cleaned data.")
        st.stop()

    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data
def load_sensor_counts():
    """Load sensor count info from raw data."""
    base = Path(__file__).parent.parent / "data" / "raw"
    raw_files = sorted(base.glob("openaq_measurements_*.csv"))
    if not raw_files:
        return pd.DataFrame(columns=["country", "city", "sensors"])

    raw_df = pd.read_csv(raw_files[-1])
    locations = pd.read_csv(base / "asean_locations.csv")
    city_lookup = dict(zip(locations["id"], locations["locality"]))
    raw_df["city_clean"] = raw_df["location_id"].map(city_lookup).fillna("Unknown")

    counts = raw_df.groupby(["country", "city_clean"])["location_id"].nunique().reset_index()
    counts.columns = ["country", "city", "sensors"]
    return counts


df = load_data()
sensor_counts = load_sensor_counts()

# --- HEADER ---
st.title("🌏 ASEAN Air Quality Analysis (2021-2026)")
st.markdown(
    """
    Real air quality data from [OpenAQ](https://openaq.org) covering 8 ASEAN countries.
    Use the filters on the left to explore patterns across countries, cities, and time.
    """
)

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filters")

all_countries = sorted(df["country"].unique())
default_countries = all_countries  # Show all by default
selected_countries = st.sidebar.multiselect(
    "Countries",
    options=all_countries,
    default=default_countries,
)

if not selected_countries:
    st.warning("Please select at least one country.")
    st.stop()

year_range = st.sidebar.slider(
    "Year Range",
    min_value=int(df["year"].min()),
    max_value=int(df["year"].max()),
    value=(int(df["year"].min()), int(df["year"].max())),
)

# Reliability filter
show_only_reliable = st.sidebar.checkbox(
    "Show only reliable cities (2+ sensors, 100+ days)",
    value=False,
    help="Filter out cities with limited sensor coverage",
)

filtered = df[
    (df["country"].isin(selected_countries))
    & (df["year"].between(year_range[0], year_range[1]))
]

# --- KEY METRICS ---
st.subheader("📊 Overview")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Records", f"{len(filtered):,}")
col2.metric("Countries", filtered["country"].nunique())
col3.metric("Cities", filtered["city"].nunique())
if "pm25" in filtered.columns:
    col4.metric("Avg PM2.5", f"{filtered['pm25'].mean():.1f} µg/m³")

st.divider()

# --- TABS ---
tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏠 Headline Findings",
    "🏆 City Rankings",
    "🌍 Country Comparison",
    "📈 Trends Over Time",
    "🌡️ Seasonal Patterns",
    "🇮🇩 Indonesia Focus",
    "🔬 Methodology"
])

# --- TAB 0: HEADLINE FINDINGS ---
with tab0:
    st.subheader("🎯 The Story in 30 Seconds")

    st.markdown("""
    **Question:** *How does Indonesia's air quality compare to its ASEAN neighbors?*

    **Answer:** Indonesia is the most polluted country in monitored ASEAN — and uniquely,
    its pollution is chronic (every day is bad) rather than episodic (a few terrible days).
    """)

    st.divider()

    # Headline findings as info cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "🇮🇩 Indonesia's Avg PM2.5",
            "42.1 µg/m³",
            "4.2x WHO safe limit",
            delta_color="inverse",
        )
        st.caption("Highest in monitored ASEAN")

    with col2:
        st.metric(
            "% Indonesian Days With 'Good' Air",
            "4.4%",
            "1 in 23 days",
            delta_color="inverse",
        )
        st.caption("Singapore: 19.8%, Cambodia: 34.2%")

    with col3:
        st.metric(
            "Top Indonesian Hotspots",
            "Jakarta, Yogyakarta, Bandung",
            "All in top 5 ASEAN",
            delta_color="inverse",
        )
        st.caption("Reliable data confirms multi-city issue")

    st.divider()

    # Top findings as expandable cards
    with st.expander("🔴 Finding 1: Indonesia leads ASEAN in chronic air pollution", expanded=True):
        st.markdown("""
        With an average PM2.5 of **42.1 µg/m³** across 7 cities and 2,941 records,
        Indonesia ranks **#1 most polluted** country in monitored ASEAN.

        Critically, Indonesia's mean (42.1) and median (40.3) are nearly identical,
        indicating **chronic, day-after-day pollution** — arguably worse for cumulative
        public health than countries with occasional spikes.
        """)

    with st.expander("🌫️ Finding 2: Only 4.4% of Indonesian days have safe air"):
        st.markdown("""
        Out of every 365 days in Indonesia, only **~16 days** achieve "Good" AQI.
        The other 95.6% are at varying pollution levels:

        - **57.9%** of days are "Unhealthy for Sensitive Groups" or worse
        - For comparison: Singapore has 19.8% Good days, Cambodia 34.2%
        - Indonesia has **4.5x fewer clean days** than Singapore
        """)

    with st.expander("🌳 Finding 3: Yogyakarta is a confirmed pollution hotspot"):
        st.markdown("""
        With **205 days** of statistically validated data, Yogyakarta averages **40.5 µg/m³** —
        nearly identical to Hanoi and just behind Indonesia's worst-polluted cities.

        - Mean (40.5) ≈ Median (40.7) → consistent year-round pollution
        - Likely drivers: high motorbike density, regional agricultural burning,
          surrounding forest fire impact during dry season
        - **Indonesia's pollution problem isn't just Jakarta** — it's nationwide
        """)

    with st.expander("📅 Finding 4: Indonesia has a clear seasonal crisis"):
        st.markdown("""
        June through October consistently shows the worst PM2.5 readings in Indonesia.

        - **August 2023** hit 68 µg/m³ — coinciding with documented El Niño-driven
          forest fires in Sumatra and Kalimantan
        - Wet season (Nov-Mar) provides significant relief
        - Pattern repeats every year, suggesting a **predictable annual public health emergency**
        """)

    with st.expander("🔬 Finding 5: A faulty sensor distorted Vietnam's ranking"):
        st.markdown("""
        Initial analysis showed Vietnam averaging **380 µg/m³** in 2023 — implausibly high.
        Investigation traced the spike to a single sensor at the **US Diplomatic Post in
        Ho Chi Minh City** reporting impossible values (max 985 µg/m³ across 559 days).

        Cross-referencing with [UN data showing Vietnam's true 2023 PM2.5 was 21-52 µg/m³](https://www.unicef.org/vietnam/stories/viet-nams-heavy-air-pollution-needs-stronger-action)
        confirmed sensor malfunction. After filtering, Vietnam's average aligned with
        regional norms (~35 µg/m³).

        **Lesson:** Always validate suspicious findings against authoritative external sources.
        """)

    st.divider()

    # Quick visual summary
    st.subheader("Quick Visual: Country Rankings")

    if "pm25" in df.columns:
        country_summary = df.groupby("country")["pm25"].mean().reset_index().sort_values("pm25", ascending=False)
        fig = px.bar(
            country_summary,
            x="country",
            y="pm25",
            color="pm25",
            color_continuous_scale="YlOrRd",
            title="Average PM2.5 Across ASEAN (2021-2026)",
            labels={"pm25": "PM2.5 (µg/m³)", "country": "Country"},
        )
        fig.add_hline(y=10, line_dash="dash", line_color="green", annotation_text="WHO safe (10)")
        fig.add_hline(y=15, line_dash="dash", line_color="orange", annotation_text="WHO interim (15)")
        st.plotly_chart(fig, use_container_width=True)

    st.info("👈 Use the filters on the left and explore the other tabs to dig into the data yourself.")

# --- TAB 1: CITY RANKINGS ---
with tab1:
    st.subheader("Most Polluted Cities by Average PM2.5")
    st.caption(
        "WHO safe limit: 10 µg/m³ • WHO interim target: 15 µg/m³"
    )

    if "pm25" in filtered.columns:
        city_stats = filtered.groupby(["country", "city"]).agg(
            avg_pm25=("pm25", "mean"),
            median_pm25=("pm25", "median"),
            days=("pm25", "count"),
        ).round(1).reset_index()

        city_stats = city_stats[city_stats["days"] >= 30]

        # Add reliability info
        city_stats = city_stats.merge(sensor_counts, on=["country", "city"], how="left")
        city_stats["sensors"] = city_stats["sensors"].fillna(1).astype(int)
        city_stats["reliable"] = (city_stats["sensors"] >= 2) & (city_stats["days"] >= 100)
        city_stats["reliability"] = city_stats["reliable"].map({
            True: "✅ Reliable",
            False: "⚠️ Limited",
        })

        if show_only_reliable:
            city_stats = city_stats[city_stats["reliable"]]

        city_stats = city_stats.sort_values("avg_pm25", ascending=False).head(20)

        # Display chart
        city_stats["city_country"] = city_stats["city"] + ", " + city_stats["country"]
        city_stats.loc[~city_stats["reliable"], "city_country"] += " *"

        fig = px.bar(
            city_stats,
            x="avg_pm25",
            y="city_country",
            orientation="h",
            color="reliable",
            color_discrete_map={True: "#C73E1D", False: "#E89580"},
            labels={"avg_pm25": "Average PM2.5 (µg/m³)", "city_country": ""},
            title="Top 20 ASEAN Cities by Average PM2.5",
        )
        fig.add_vline(x=10, line_dash="dash", line_color="green",
                      annotation_text="WHO safe (10)")
        fig.add_vline(x=15, line_dash="dash", line_color="orange",
                      annotation_text="WHO interim (15)")
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

        # Display table
        st.dataframe(
            city_stats[["country", "city", "avg_pm25", "median_pm25", "days", "sensors", "reliability"]],
            use_container_width=True,
            hide_index=True,
        )


# --- TAB 2: COUNTRY COMPARISON ---
with tab2:
    st.subheader("Country-Level Air Quality")

    if "pm25" in filtered.columns:
        country_stats = filtered.groupby("country").agg(
            avg_pm25=("pm25", "mean"),
            median_pm25=("pm25", "median"),
            cities=("city", "nunique"),
            records=("pm25", "count"),
        ).round(1).reset_index().sort_values("avg_pm25", ascending=False)

        if "aqi_pm25" in filtered.columns:
            aqi_stats = filtered.groupby("country")["aqi_pm25"].mean().round(1)
            country_stats["avg_aqi"] = country_stats["country"].map(aqi_stats)

        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                country_stats,
                x="country",
                y="avg_pm25",
                title="Average PM2.5 by Country",
                color="avg_pm25",
                color_continuous_scale="YlOrRd",
            )
            fig.add_hline(y=10, line_dash="dash", line_color="green",
                          annotation_text="WHO safe")
            fig.add_hline(y=15, line_dash="dash", line_color="orange",
                          annotation_text="WHO interim")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Mean vs Median comparison (chronic vs episodic)
            country_stats_melt = country_stats.melt(
                id_vars=["country"],
                value_vars=["avg_pm25", "median_pm25"],
                var_name="metric",
                value_name="value",
            )
            country_stats_melt["metric"] = country_stats_melt["metric"].map({
                "avg_pm25": "Mean",
                "median_pm25": "Median",
            })
            fig = px.bar(
                country_stats_melt,
                x="country",
                y="value",
                color="metric",
                barmode="group",
                title="Mean vs Median PM2.5 (gap = episodic pollution)",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(country_stats, use_container_width=True, hide_index=True)


# --- TAB 3: TRENDS OVER TIME ---
with tab3:
    st.subheader("Yearly PM2.5 Trends")

    if "pm25" in filtered.columns:
        yearly = filtered.groupby(["year", "country"])["pm25"].mean().reset_index()
        fig = px.line(
            yearly,
            x="year",
            y="pm25",
            color="country",
            markers=True,
            title="Average PM2.5 by Year",
        )
        fig.add_hline(y=10, line_dash="dash", line_color="green",
                      annotation_text="WHO safe")
        st.plotly_chart(fig, use_container_width=True)

        # AQI bucket distribution
        st.subheader("Days at Each AQI Level")
        if "aqi_bucket" in filtered.columns:
            bucket_order = [
                "Good", "Moderate", "Unhealthy for Sensitive",
                "Unhealthy", "Very Unhealthy", "Hazardous"
            ]
            colors = {
                "Good": "#2ecc71", "Moderate": "#f1c40f",
                "Unhealthy for Sensitive": "#e67e22", "Unhealthy": "#e74c3c",
                "Very Unhealthy": "#9b59b6", "Hazardous": "#34495e",
            }

            bucket_data = filtered.groupby(["country", "aqi_bucket"]).size().reset_index(name="days")
            total_per_country = filtered.groupby("country").size()
            bucket_data["pct"] = bucket_data.apply(
                lambda r: r["days"] / total_per_country[r["country"]] * 100, axis=1
            )

            fig = px.bar(
                bucket_data,
                x="country",
                y="pct",
                color="aqi_bucket",
                color_discrete_map=colors,
                category_orders={"aqi_bucket": bucket_order},
                title="AQI Bucket Distribution by Country (% of days)",
            )
            st.plotly_chart(fig, use_container_width=True)


# --- TAB 4: SEASONAL PATTERNS ---
with tab4:
    st.subheader("Seasonal Pollution Patterns")

    if "pm25" in filtered.columns:
        monthly = filtered.groupby(["month", "country"])["pm25"].mean().reset_index()
        fig = px.line(
            monthly,
            x="month",
            y="pm25",
            color="country",
            markers=True,
            title="Monthly Average PM2.5 by Country",
            labels={"month": "Month", "pm25": "PM2.5 (µg/m³)"},
        )
        fig.update_xaxes(tickmode="linear", tick0=1, dtick=1)
        st.plotly_chart(fig, use_container_width=True)

        # Heatmap for selected country
        st.subheader("Pollution Heatmap (Year × Month)")
        target = st.selectbox(
            "Select country for heatmap",
            options=selected_countries,
            index=selected_countries.index("Indonesia") if "Indonesia" in selected_countries else 0,
        )

        country_data = filtered[filtered["country"] == target]
        if not country_data.empty:
            pivot = country_data.pivot_table(
                values="pm25", index="month", columns="year", aggfunc="mean"
            ).round(1)

            fig = px.imshow(
                pivot,
                color_continuous_scale="YlOrRd",
                aspect="auto",
                text_auto=".0f",
                labels={"color": "PM2.5"},
                title=f"{target}: PM2.5 by Month and Year",
            )
            st.plotly_chart(fig, use_container_width=True)


# --- TAB 5: INDONESIA FOCUS ---
with tab5:
    st.subheader("🇮🇩 Indonesia Deep Dive")

    indo = df[df["country"] == "Indonesia"]

    if not indo.empty and "pm25" in indo.columns:
        col1, col2, col3 = st.columns(3)
        col1.metric("Avg PM2.5", f"{indo['pm25'].mean():.1f} µg/m³")
        col2.metric("Cities Tracked", indo["city"].nunique())
        col3.metric("Days of Data", f"{len(indo):,}")

        # Indonesia vs Global comparison
        indo_yearly = indo.groupby("year")["pm25"].mean().reset_index()
        indo_yearly["country"] = "Indonesia"
        all_yearly = df.groupby("year")["pm25"].mean().reset_index()
        all_yearly["country"] = "ASEAN Average"
        comparison = pd.concat([indo_yearly, all_yearly])

        fig = px.line(
            comparison,
            x="year",
            y="pm25",
            color="country",
            markers=True,
            title="Indonesia vs ASEAN Average",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Indonesian cities
        st.subheader("Indonesian Cities")
        indo_cities = indo.groupby("city").agg(
            avg_pm25=("pm25", "mean"),
            median_pm25=("pm25", "median"),
            days=("pm25", "count"),
        ).round(1).reset_index().sort_values("avg_pm25", ascending=False)

        indo_cities = indo_cities.merge(sensor_counts, on=["city"], how="left")
        indo_cities = indo_cities.rename(columns={"sensors": "sensor_count"})
        indo_cities["sensor_count"] = indo_cities["sensor_count"].fillna(1).astype(int)
        indo_cities["reliable"] = (indo_cities["sensor_count"] >= 2) & (indo_cities["days"] >= 100)

        st.dataframe(
            indo_cities[indo_cities["days"] >= 30],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("""
        ### Key Insights for Indonesia
        - **Indonesia is #1 most polluted in ASEAN** (avg PM2.5 42.1 µg/m³)
        - **Only 4.4% of days** have "Good" AQI in Indonesia
        - **Yogyakarta** (40.5) is statistically validated as a major pollution hotspot
        - **Jakarta** has the most reliable data (8 sensors, 1,438 days)
        - **Seasonal peak:** June-October (dry season + forest fires)
        """)


# --- TAB 6: METHODOLOGY ---
with tab6:
    st.subheader("How This Analysis Was Built")

    st.markdown("""
    ### Data Pipeline
    1. **Source:** [OpenAQ API](https://openaq.org) — real measurements from government
       and research monitoring stations across ASEAN
    2. **Discovery:** Scanned 916 monitoring locations across all 10 ASEAN countries
    3. **Selection:** Selected 165 locations with strict GPS-based city assignment
    4. **Fetch:** Pulled 5 years of daily measurements per sensor (~69,000 records)
    5. **Cleaning:** Removed invalid values, applied biological plausibility caps,
       re-classified cities by GPS coordinates
    6. **Analysis:** EDA with reliability indicators distinguishing solid findings
       from preliminary signals

    ### Sensor Reliability
    Cities are classified into reliability tiers:
    - **Reliable:** 2+ sensors AND 100+ days of data
    - **Limited:** Single sensor or <100 days

    Findings about limited cities (Bandung, Bogor, Medan) are noted as preliminary.

    ### Data Quality Discovery
    During analysis, Vietnam's 2023 average appeared as 380 µg/m³ — implausibly high.
    Investigation traced this to a single sensor at the US Diplomatic Post in Ho Chi
    Minh City reporting impossible values (max 985 µg/m³). After cross-referencing
    with [UN data confirming Vietnam's true 2023 PM2.5 was 21-52 µg/m³](https://www.unicef.org/vietnam/stories/viet-nams-heavy-air-pollution-needs-stronger-action),
    the malfunctioning data was filtered out by capping PM2.5 readings at 500 µg/m³.

    ### Limitations
    - **Coverage gaps:** Brunei and Laos have no OpenAQ stations.
    - **Sensor density bias:** Larger cities have more sensors than smaller ones.
    - **Time range:** Data starts May 2021, no pre-COVID baseline.
    - **Daily granularity:** Hourly patterns and rush-hour spikes not captured.

    ### Tech Stack
    Python • Pandas • NumPy • Plotly • Streamlit • SQL • Jupyter • OpenAQ API
    """)


# --- FOOTER ---
st.divider()
st.caption(
    f"Data: OpenAQ ASEAN Air Quality 2021-2026 | "
    f"Built with Streamlit, Pandas, Plotly | "
    f"Loaded {len(df):,} city-day records"
)
