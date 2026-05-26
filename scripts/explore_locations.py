"""Explore OpenAQ — find available monitoring locations.

This script helps you discover what air quality monitors exist in Indonesia
and ASEAN before committing to the full data pull.

Usage:
    1. Get API key from https://explore.openaq.org/
    2. Save it in .env file as OPENAQ_API_KEY=your_key
    3. python scripts/explore_locations.py
"""

import os
import sys
import time
from pathlib import Path

import requests
import pandas as pd
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

console = Console()

# Load environment variables — find .env file in project root regardless of cwd
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)
API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    console.print(f"[red]Error: OPENAQ_API_KEY not found.[/red]")
    console.print(f"Looked in: {ENV_PATH}")
    console.print("Create a .env file with: OPENAQ_API_KEY=your_key_here")
    sys.exit(1)

console.print(f"[dim]API key loaded: {API_KEY[:4]}...{API_KEY[-4:]} (length: {len(API_KEY)})[/dim]")

BASE_URL = "https://api.openaq.org/v3"
HEADERS = {"X-API-Key": API_KEY}

# ASEAN countries to explore
ASEAN_COUNTRIES = [
    "Indonesia", "Singapore", "Malaysia", "Thailand", "Vietnam",
    "Philippines", "Brunei", "Cambodia", "Myanmar", "Laos",
]


# Major ASEAN cities with their bounding boxes (approximate)
# Format: (city_name, lat_min, lat_max, lon_min, lon_max)
CITY_BOUNDS = {
    "Indonesia": [
        ("Jakarta", -6.40, -6.05, 106.65, 107.05),
        ("Bandung", -7.05, -6.80, 107.50, 107.75),
        ("Surabaya", -7.40, -7.15, 112.60, 112.85),
        ("Medan", 3.45, 3.75, 98.55, 98.80),
        ("Makassar", -5.25, -5.05, 119.35, 119.55),
        ("Yogyakarta", -7.95, -7.65, 110.30, 110.55),
        ("Semarang", -7.05, -6.85, 110.30, 110.50),
        ("Palembang", -3.10, -2.85, 104.65, 104.90),
        ("Denpasar", -8.80, -8.55, 115.10, 115.35),
        ("Padang", -1.05, -0.80, 100.30, 100.50),
        ("Pontianak", -0.15, 0.10, 109.25, 109.45),
        ("Banjarmasin", -3.40, -3.20, 114.50, 114.70),
        ("Pekanbaru", 0.40, 0.65, 101.35, 101.55),
        ("Tangerang", -6.30, -6.10, 106.50, 106.75),
        ("Depok", -6.45, -6.30, 106.75, 106.90),
        ("Bekasi", -6.30, -6.15, 106.95, 107.10),
        ("Bogor", -6.65, -6.45, 106.70, 106.85),
        ("Sleman/Yogya", -7.80, -7.60, 110.30, 110.50),
    ],
    "Thailand": [
        ("Bangkok", 13.55, 13.95, 100.40, 100.80),
        ("Chiang Mai", 18.65, 18.85, 98.90, 99.05),
        ("Phuket", 7.85, 8.05, 98.30, 98.45),
        ("Pattaya", 12.85, 12.99, 100.85, 100.95),
        ("Khon Kaen", 16.40, 16.50, 102.80, 102.90),
        ("Hat Yai", 6.95, 7.10, 100.45, 100.55),
        ("Ayutthaya", 14.30, 14.45, 100.50, 100.65),
    ],
    "Vietnam": [
        ("Ho Chi Minh City", 10.65, 10.90, 106.55, 106.85),
        ("Hanoi", 20.95, 21.15, 105.70, 105.95),
        ("Da Nang", 16.00, 16.15, 108.15, 108.30),
        ("Hai Phong", 20.80, 20.95, 106.60, 106.80),
    ],
    "Philippines": [
        ("Manila", 14.50, 14.75, 120.95, 121.10),
        ("Quezon City", 14.60, 14.80, 121.00, 121.15),
        ("Makati", 14.50, 14.60, 121.00, 121.05),
        ("Cebu", 10.25, 10.40, 123.85, 124.00),
        ("Davao", 7.00, 7.20, 125.50, 125.70),
    ],
    "Singapore": [
        ("Singapore", 1.15, 1.50, 103.55, 104.05),
    ],
    "Malaysia": [
        ("Kuala Lumpur", 3.05, 3.25, 101.60, 101.80),
        ("George Town", 5.35, 5.50, 100.20, 100.40),
        ("Johor Bahru", 1.40, 1.55, 103.65, 103.85),
        ("Kota Kinabalu", 5.95, 6.05, 116.05, 116.15),
    ],
    "Cambodia": [
        ("Phnom Penh", 11.50, 11.65, 104.85, 105.00),
        ("Siem Reap", 13.30, 13.45, 103.80, 103.95),
    ],
    "Myanmar": [
        ("Yangon", 16.75, 16.95, 96.05, 96.25),
        ("Mandalay", 21.90, 22.05, 96.05, 96.15),
        ("Naypyidaw", 19.70, 19.85, 96.05, 96.20),
    ],
}


def _city_from_coords(country: str, lat: float, lon: float, fallback_name: str = "") -> str:
    """Match GPS coordinates to a known city.

    Args:
        country: Country name.
        lat: Latitude.
        lon: Longitude.
        fallback_name: Sensor name to use if no city matches.

    Returns:
        City name (best match) or 'Other' if no match.
    """
    bounds = CITY_BOUNDS.get(country, [])
    for city, lat_min, lat_max, lon_min, lon_max in bounds:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return city
    # Fallback: use raw name if available
    return fallback_name or "Other"


def get_country_id(country_name: str) -> int | None:
    """Find OpenAQ country ID for a given country name."""
    url = f"{BASE_URL}/countries"
    params = {"limit": 200}

    response = requests.get(url, params=params, headers=HEADERS, timeout=15)
    response.raise_for_status()

    countries = response.json().get("results", [])
    for country in countries:
        if country.get("name", "").lower() == country_name.lower():
            return country.get("id")
    return None


def get_locations_for_country(country_id: int, country_name: str) -> list[dict]:
    """Get all monitoring locations for a country."""
    locations = []
    page = 1

    while True:
        url = f"{BASE_URL}/locations"
        params = {
            "countries_id": country_id,
            "limit": 100,
            "page": page,
        }

        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if response.status_code == 429:
                console.print(f"  [yellow]Rate limited, waiting 5s...[/yellow]")
                time.sleep(5)
                continue
            response.raise_for_status()
        except requests.RequestException as e:
            console.print(f"  [red]Error: {e}[/red]")
            break

        results = response.json().get("results", [])
        if not results:
            break

        for loc in results:
            sensors = loc.get("sensors", [])
            parameters = [s.get("parameter", {}).get("name") for s in sensors]

            locality = loc.get("locality")
            name = loc.get("name", "")
            lat = loc.get("coordinates", {}).get("latitude")
            lon = loc.get("coordinates", {}).get("longitude")

            # Assign city based on GPS coordinates if locality is missing
            if not locality and lat and lon:
                locality = _city_from_coords(country_name, lat, lon, name)

            locations.append({
                "country": country_name,
                "id": loc.get("id"),
                "name": name,
                "locality": locality,
                "lat": lat,
                "lon": lon,
                "is_active": loc.get("isMobile") is not True,
                "parameters": ", ".join(filter(None, parameters)) if parameters else "",
                "sensor_count": len(sensors),
                "first_data": loc.get("datetimeFirst", {}).get("local") if loc.get("datetimeFirst") else None,
                "last_data": loc.get("datetimeLast", {}).get("local") if loc.get("datetimeLast") else None,
            })

        if len(results) < 100:
            break

        page += 1
        time.sleep(1)  # Be polite to the API

    return locations


def main():
    console.print("[bold cyan]OpenAQ Location Explorer[/bold cyan]")
    console.print("=" * 50)
    console.print()

    all_locations = []

    for country_name in ASEAN_COUNTRIES:
        console.print(f"  Checking {country_name}...")

        country_id = get_country_id(country_name)
        if not country_id:
            console.print(f"    [yellow]Not found in OpenAQ[/yellow]")
            continue

        console.print(f"    Country ID: {country_id}")

        locations = get_locations_for_country(country_id, country_name)
        console.print(f"    Found {len(locations)} locations")
        all_locations.extend(locations)

        time.sleep(1)

    if not all_locations:
        console.print("[red]No locations found.[/red]")
        return

    df = pd.DataFrame(all_locations)

    # Save raw locations
    output_path = Path("data/raw/asean_locations.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    console.print(f"\n[green]Saved {len(df)} locations to {output_path}[/green]")

    # Summary by country
    console.print("\n[bold]Summary by Country:[/bold]")
    table = Table()
    table.add_column("Country", style="cyan")
    table.add_column("Total Locations", justify="center")
    table.add_column("Active Locations", justify="center")
    table.add_column("With PM2.5", justify="center")

    for country in df["country"].unique():
        country_data = df[df["country"] == country]
        active = country_data[country_data["is_active"]]
        with_pm25 = country_data[country_data["parameters"].str.contains("pm25", case=False, na=False)]
        table.add_row(
            country,
            str(len(country_data)),
            str(len(active)),
            str(len(with_pm25)),
        )

    console.print(table)

    # Indonesia detail
    indonesia = df[df["country"] == "Indonesia"]
    if not indonesia.empty:
        console.print(f"\n[bold]Indonesia Details ({len(indonesia)} locations):[/bold]")
        cities = indonesia["locality"].value_counts().head(15)
        table2 = Table()
        table2.add_column("City/Locality", style="green")
        table2.add_column("Locations", justify="center")
        for city, count in cities.items():
            table2.add_row(str(city), str(count))
        console.print(table2)


if __name__ == "__main__":
    main()
