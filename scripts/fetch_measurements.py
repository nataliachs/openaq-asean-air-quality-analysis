"""Fetch air quality measurements from OpenAQ.

This script downloads historical measurements for selected locations.
Run explore_locations.py first to discover available locations.

Usage:
    python scripts/fetch_measurements.py
    python scripts/fetch_measurements.py --countries Indonesia,Singapore
    python scripts/fetch_measurements.py --years 5  # last 5 years
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta

import requests
import pandas as pd
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress

console = Console()

load_dotenv()
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)
API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    console.print(f"[red]Error: OPENAQ_API_KEY not found in {ENV_PATH}[/red]")
    sys.exit(1)

BASE_URL = "https://api.openaq.org/v3"
HEADERS = {"X-API-Key": API_KEY}


def fetch_sensor_measurements(
    sensor_id: int,
    start_date: str,
    end_date: str,
    sensor_info: dict,
) -> list[dict]:
    """Fetch hourly measurements for a single sensor.

    Args:
        sensor_id: OpenAQ sensor ID.
        start_date: ISO date string (YYYY-MM-DD).
        end_date: ISO date string (YYYY-MM-DD).
        sensor_info: Metadata about the sensor (location, parameter, etc).

    Returns:
        List of measurement dictionaries.
    """
    measurements = []
    page = 1

    while True:
        url = f"{BASE_URL}/sensors/{sensor_id}/measurements/daily"
        params = {
            "datetime_from": f"{start_date}T00:00:00Z",
            "datetime_to": f"{end_date}T00:00:00Z",
            "limit": 1000,
            "page": page,
        }

        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if response.status_code == 429:
                time.sleep(5)
                continue
            if response.status_code != 200:
                break
        except requests.RequestException:
            break

        results = response.json().get("results", [])
        if not results:
            break

        for r in results:
            measurements.append({
                **sensor_info,
                "datetime": r.get("period", {}).get("datetimeFrom", {}).get("local"),
                "value": r.get("value"),
            })

        if len(results) < 1000:
            break

        page += 1
        time.sleep(0.5)

    return measurements


def fetch_for_locations(
    locations_df: pd.DataFrame,
    start_date: str,
    end_date: str,
    pollutants: list[str] = None,
    save_path: Path = None,
    save_every: int = 10,
) -> pd.DataFrame:
    """Fetch measurements for all sensors in the given locations.

    Args:
        locations_df: DataFrame from explore_locations.py output.
        start_date: ISO date string.
        end_date: ISO date string.
        pollutants: Filter to these pollutants only (e.g., ['pm25', 'pm10', 'no2']).
        save_path: If provided, save progress every `save_every` locations.
        save_every: Save partial results after this many locations processed.

    Returns:
        DataFrame of measurements.
    """
    if pollutants is None:
        pollutants = ["pm25", "pm10", "no2", "so2", "o3", "co"]

    all_measurements = []

    with Progress() as progress:
        task = progress.add_task("Fetching measurements...", total=len(locations_df))

        for idx, (_, loc) in enumerate(locations_df.iterrows()):
            location_id = loc["id"]

            # Get sensors for this location
            try:
                sensor_url = f"{BASE_URL}/locations/{location_id}/sensors"
                resp = requests.get(sensor_url, headers=HEADERS, timeout=15)
                if resp.status_code != 200:
                    progress.update(task, advance=1)
                    continue

                sensors = resp.json().get("results", [])
            except requests.RequestException:
                progress.update(task, advance=1)
                continue

            for sensor in sensors:
                param_name = sensor.get("parameter", {}).get("name", "").lower()
                if pollutants and param_name not in pollutants:
                    continue

                sensor_info = {
                    "country": loc["country"],
                    "city": loc.get("locality") or "Unknown",
                    "location_name": loc.get("name"),
                    "location_id": location_id,
                    "sensor_id": sensor.get("id"),
                    "parameter": param_name,
                    "units": sensor.get("parameter", {}).get("units"),
                    "lat": loc.get("lat"),
                    "lon": loc.get("lon"),
                }

                measurements = fetch_sensor_measurements(
                    sensor.get("id"),
                    start_date,
                    end_date,
                    sensor_info,
                )
                all_measurements.extend(measurements)

                time.sleep(0.5)

            progress.update(task, advance=1)

            # Save incrementally so we don't lose progress on crash
            if save_path and (idx + 1) % save_every == 0 and all_measurements:
                temp_df = pd.DataFrame(all_measurements)
                temp_df.to_csv(save_path, index=False, encoding="utf-8-sig")

            time.sleep(0.3)

    return pd.DataFrame(all_measurements)


@click.command()
@click.option(
    "--countries", "-c",
    default="Indonesia,Singapore,Malaysia,Thailand,Vietnam,Philippines,Brunei,Cambodia,Myanmar,Laos",
    help="Comma-separated list of countries to fetch.",
)
@click.option("--years", "-y", default=5, type=int, help="Years back to fetch. Default: 5")
@click.option("--max-locations", "-m", default=30, type=int, help="Max locations per non-focus country.")
@click.option("--output", "-o", default=None, help="Output CSV filename.")
def main(countries, years, max_locations, output):
    """Fetch OpenAQ measurements for specified countries."""
    console.print("[bold cyan]OpenAQ Measurement Fetcher[/bold cyan]")
    console.print(f"  Countries: {countries}")
    console.print(f"  Years: {years}")
    console.print(f"  Max locations per country: {max_locations}")
    console.print()

    # Load locations from explore_locations.py output (always relative to project root)
    locations_path = PROJECT_ROOT / "data" / "raw" / "asean_locations.csv"
    if not locations_path.exists():
        console.print(f"[red]Error: {locations_path} not found.[/red]")
        console.print("Run scripts/explore_locations.py first.")
        sys.exit(1)

    all_locations = pd.read_csv(locations_path)

    # Filter
    country_list = [c.strip() for c in countries.split(",")]
    filtered = all_locations[all_locations["country"].isin(country_list)]

    # Take only active locations
    filtered = filtered[filtered["is_active"] == True]

    # SMART SELECTION STRATEGY for diverse, balanced data:
    # - Indonesia (focus country): take ALL locations
    # - Small countries (<=20 locations): take ALL
    # - Larger countries: cap at max_locations with city diversification

    selected_parts = []
    for country in country_list:
        country_data = filtered[filtered["country"] == country]
        if len(country_data) == 0:
            continue

        if country == "Indonesia":
            # All Indonesia locations (focus country)
            selected_parts.append(country_data)
        elif len(country_data) <= max_locations:
            # Small enough — take all
            selected_parts.append(country_data)
        else:
            # Diversify by city, then cap
            sensors_per_city = max(2, max_locations // 5)
            diversified = country_data.sort_values(
                ["locality", "last_data"], ascending=[True, False]
            )
            diversified = diversified.groupby("locality").head(sensors_per_city)
            # Then top N most recently active
            top_n = diversified.sort_values("last_data", ascending=False).head(max_locations)
            selected_parts.append(top_n)

    selected = pd.concat(selected_parts, ignore_index=True)

    console.print(f"  Selected {len(selected)} total locations:")
    console.print()
    console.print("  Distribution by country:")
    for country in selected["country"].unique():
        country_sel = selected[selected["country"] == country]
        total_in_country = len(filtered[filtered["country"] == country])
        marker = " (ALL)" if len(country_sel) == total_in_country else f" (of {total_in_country})"
        cities = country_sel["locality"].nunique()
        console.print(f"    {country}: {len(country_sel)} locations{marker} across {cities} cities")
    console.print()

    # Date range
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
    console.print(f"  Date range: {start_date} to {end_date}")
    console.print()

    # Determine output path
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d")
        output_path = PROJECT_ROOT / "data" / "raw" / f"openaq_measurements_{timestamp}.csv"
    else:
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    console.print(f"  Output will save to: {output_path}")
    console.print(f"  Progress saves every 10 locations (in case of crash)")
    console.print()

    # Fetch with incremental saves
    df = fetch_for_locations(selected, start_date, end_date, save_path=output_path)

    if df.empty:
        console.print("[red]No measurements retrieved.[/red]")
        sys.exit(1)

    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    console.print(f"\n[bold green]Saved {len(df):,} measurements to {output_path}[/bold green]")
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Date range: {df['datetime'].min()} to {df['datetime'].max()}")
    console.print(f"  Countries: {df['country'].nunique()}")
    console.print(f"  Cities: {df['city'].nunique()}")
    console.print(f"  Pollutants: {df['parameter'].unique().tolist()}")


if __name__ == "__main__":
    main()
