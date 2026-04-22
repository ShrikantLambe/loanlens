"""
generate_platforms.py — Generates platform_metadata.csv (one row per lending platform).

Run directly:  python data_gen/generate_platforms.py
"""

import logging
from datetime import date
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"

PLATFORMS = [
    {
        "platform": "doordash",
        "platform_display_name": "DoorDash",
        "category": "food_delivery",
        "avg_merchant_gmv": 180_000.0,
        "partner_since": date(2021, 6, 1),
    },
    {
        "platform": "amazon",
        "platform_display_name": "Amazon Marketplace",
        "category": "ecommerce",
        "avg_merchant_gmv": 320_000.0,
        "partner_since": date(2021, 9, 15),
    },
    {
        "platform": "mindbody",
        "platform_display_name": "Mindbody",
        "category": "fitness",
        "avg_merchant_gmv": 95_000.0,
        "partner_since": date(2022, 3, 1),
    },
    {
        "platform": "worldpay",
        "platform_display_name": "Worldpay",
        "category": "payments",
        "avg_merchant_gmv": 210_000.0,
        "partner_since": date(2022, 7, 1),
    },
    {
        "platform": "shopify",
        "platform_display_name": "Shopify",
        "category": "ecommerce",
        "avg_merchant_gmv": 145_000.0,
        "partner_since": date(2023, 1, 15),
    },
]


def generate_platforms() -> pd.DataFrame:
    """
    Return static platform metadata DataFrame.

    Returns:
        DataFrame with one row per lending platform.
    """
    return pd.DataFrame(PLATFORMS)


def main() -> None:
    """Write platform_metadata.csv to data_gen/output/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = generate_platforms()
    out_path = OUTPUT_DIR / "platform_metadata.csv"
    df.to_csv(out_path, index=False)
    logger.info("Wrote %s rows to %s", len(df), out_path)


if __name__ == "__main__":
    main()
