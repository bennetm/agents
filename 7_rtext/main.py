"""
Extract FCL freight rates from a tariff PDF using OpenAI structured outputs.

Usage:
    Set OPENAI_API_KEY in .env or environment, then from 7_rtext folder:

        python main.py
        python main.py "path/to/tariff.pdf"
        python main.py "Nov Tariff.pdf" --output rates.json
"""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from pdf_utils import read_pdf_as_text
from extractor import extract_freight_rates

# Load .env from project root or current dir
load_dotenv(override=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract freight rates (FCL) from tariff PDF using OpenAI"
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default="Nov Tariff.pdf",
        help="Path to tariff PDF (default: Nov Tariff.pdf)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="extracted_tariff_rates.json",
        help="Output JSON file (default: extracted_tariff_rates.json)",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Do not write JSON file, only print summary",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}")
        raise SystemExit(1)

    print("Loading PDF...")
    pdf_text = read_pdf_as_text(str(pdf_path))
    print(f"Loaded {len(pdf_text):,} characters")

    print("Extracting freight rates (OpenAI structured outputs)...")
    tariff_data = extract_freight_rates(pdf_text)

    # Compute from extracted rates so total always tallies with regional breakdown
    sea = [r for r in tariff_data.rates if r.region == "sea_china"]
    india_me = [r for r in tariff_data.rates if r.region == "india_middle_east_subcon"]
    total_routes = len(tariff_data.rates)

    print(f"Total routes: {total_routes}")
    print(f"S.E.A/China: {len(sea)} | India/ME/Subcon: {len(india_me)}")
    print(f"Global fees: {len(tariff_data.global_fees)}")

    if not args.no_export:
        # Export with total_routes set from actual count so JSON is self-consistent
        tariff_data.total_routes = total_routes
        out_path = Path(args.output)
        out_path.write_text(
            json.dumps(tariff_data.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        print(f"Exported to {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
