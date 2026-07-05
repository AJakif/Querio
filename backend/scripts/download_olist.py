"""Download the real Olist Brazilian E-Commerce dataset CSV files.

Usage:
    python scripts/download_olist.py

Downloads the full Olist dataset (9 CSV files) from the official Kaggle
repository and places them into a `data/raw/` directory at the project root.

Prerequisites:
    - Kaggle API key set up locally (see https://www.kaggle.com/docs/api)

The downloaded CSVs can then be loaded into the `raw` Postgres schema using
a separate loader script, or they serve as a reference for the real dataset
structure (the `load_raw.py` script generates synthetic data that matches
this schema exactly).

Files downloaded:
    - olist_customers_dataset.csv
    - olist_geolocation_dataset.csv
    - olist_order_items_dataset.csv
    - olist_order_payments_dataset.csv
    - olist_order_reviews_dataset.csv
    - olist_orders_dataset.csv
    - olist_products_dataset.csv
    - olist_sellers_dataset.csv
    - product_category_name_translation.csv
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

DATASET_REF = "olistbr/brazilian-ecommerce"

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "data", "raw")

REQUIRED_FILES = [
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]

RENAMES = {
    "olist_customers_dataset.csv": "customers.csv",
    "olist_geolocation_dataset.csv": "geolocation.csv",
    "olist_order_items_dataset.csv": "order_items.csv",
    "olist_order_payments_dataset.csv": "order_payments.csv",
    "olist_order_reviews_dataset.csv": "order_reviews.csv",
    "olist_orders_dataset.csv": "orders.csv",
    "olist_products_dataset.csv": "products.csv",
    "olist_sellers_dataset.csv": "sellers.csv",
    "product_category_name_translation.csv": "product_category_name_translation.csv",
}


def _check_kaggle_cli() -> bool:
    return shutil.which("kaggle") is not None


def _download_via_kaggle_cli(output: str) -> bool:
    print(f"Downloading {DATASET_REF} via Kaggle CLI...")
    result = subprocess.run(
        ["kaggle", "datasets", "download", DATASET_REF, "--path", output, "--unzip"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Kaggle CLI failed: {result.stderr}")
        return False
    print(result.stdout)
    return True


def _organize_files(temp_dir: str, output_dir: str) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    placed = []
    for fname in REQUIRED_FILES:
        src = os.path.join(temp_dir, fname)
        dst_name = RENAMES.get(fname, fname)
        dst = os.path.join(output_dir, dst_name)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            placed.append(dst_name)
            print(f"  {fname} -> {dst_name}")
        else:
            print(f"  WARNING: {fname} not found in downloaded archive")
    return placed


def download(output_dir: str | None = None) -> list[str]:
    if output_dir is None:
        output_dir = OUTPUT_DIR

    if not _check_kaggle_cli():
        print("Kaggle CLI not found.")
        print()
        print("To install:")
        print("  pip install kaggle")
        print()
        print("Then set up your API key at ~/.kaggle/kaggle.json")
        print("See: https://www.kaggle.com/docs/api")
        print()
        print(f"Expected output directory: {output_dir}")
        print(f"Expected files: {', '.join(REQUIRED_FILES)}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        if not _download_via_kaggle_cli(tmpdir):
            sys.exit(1)

        placed = _organize_files(tmpdir, output_dir)

    print(f"\n{len(placed)}/{len(REQUIRED_FILES)} files placed in {output_dir}")
    return placed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Olist dataset")
    parser.add_argument("--output", default=None, help="Output directory (default: data/raw/)")
    args = parser.parse_args()
    download(args.output)
