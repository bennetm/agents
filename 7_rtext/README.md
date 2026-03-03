# Freight Rate Extraction (FCL) – Python

Extract FCL freight rates from tariff PDFs using **OpenAI structured outputs**.  
Output is type-safe **VendorRate** DTOs with regional effective dates.

## Setup

Using **uv** (from project root or from `7_rtext`):

```bash
# From project root (if 7_rtext deps are in root pyproject.toml)
uv sync

# Or from 7_rtext: install from requirements.txt
cd 7_rtext
uv pip install -r requirements.txt
```

Put your OpenAI API key in a `.env` file in the project root (or in `7_rtext`):

```
OPENAI_API_KEY=sk-proj-...
```

## Run

From the **`7_rtext`** folder:

```bash
# Default: read "Nov Tariff.pdf", write "extracted_tariff_rates.json"
python main.py

# Custom PDF and output file
python main.py "path/to/tariff.pdf" --output my_rates.json

# Only print summary, do not write JSON
python main.py --no-export
```

## Project layout

| File | Purpose |
|------|--------|
| `main.py` | Entry point: load PDF, call extractor, print summary, optional JSON export |
| `models.py` | Pydantic DTOs: `RateCharge`, `VendorRate`, `GlobalFee`, `CompleteTariffDocument` (OpenAI strict-schema compatible) |
| `prompts.py` | `EXTRACTION_SYSTEM_PROMPT` (regional dates, table parsing, value rules) |
| `pdf_utils.py` | `read_pdf_as_text()`, `encode_pdf_as_base64()` |
| `extractor.py` | `extract_freight_rates()` – OpenAI API, retries, truncation, gpt-4o-mini by default |
| `requirements.txt` | openai, pydantic, python-dotenv, pdfplumber (use `uv pip install -r requirements.txt`) |
| `Nov Tariff.pdf` | Sample tariff (optional) |

## Behaviour

- Uses **gpt-4o-mini** by default (higher TPM, cheaper). Set `use_mini=False` in `extract_freight_rates()` to use **gpt-4o**.
- With pdfplumber, full tariff text is sent; otherwise truncates to 40k characters to avoid token limits.
- Retries on rate limit with exponential backoff; on token limit can switch to mini or shorten text.
- Regional dates: **S.E.A/China** → Nov 1–30, **India/Middle East/Subcon** → Nov 14–30.

## PDF content

`read_pdf_as_text()` uses **pdfplumber** when available (so the full rate sheet is extracted). Install with `uv pip install -r requirements.txt` in `7_rtext` or `uv sync` from the project root. Without pdfplumber it falls back to raw byte decode (often incomplete for binary PDFs).

## Output

- **Console:** Total routes, global fees count, S.E.A/China vs India/ME counts, and export path.
- **JSON (default):** `extracted_tariff_rates.json` with full `CompleteTariffDocument` (rates, global_fees, notes).

## Optional: use as a module

```python
from dotenv import load_dotenv
load_dotenv()

from pdf_utils import read_pdf_as_text
from extractor import extract_freight_rates
from models import CompleteTariffDocument

pdf_text = read_pdf_as_text("Nov Tariff.pdf")
doc = extract_freight_rates(pdf_text)
for rate in doc.rates:
    print(rate.port_name, rate.region, rate.effective_date_start)
```
