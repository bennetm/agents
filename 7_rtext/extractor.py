"""
Freight rate extraction using OpenAI structured outputs.
Includes retry logic, token-limit handling, and strict schema.
"""

import time
from copy import deepcopy
from openai import OpenAI, RateLimitError, APIError

from models import CompleteTariffDocument
from prompts import EXTRACTION_SYSTEM_PROMPT


def _strict_schema(schema: dict) -> dict:
    """Ensure every object has required = all property keys (OpenAI strict mode)."""

    def fix_obj(obj: dict) -> None:
        if not isinstance(obj, dict):
            return
        if obj.get("type") == "object" and "properties" in obj:
            obj["required"] = list(obj["properties"].keys())
        for v in obj.get("properties", {}).values():
            fix_obj(v)
            if isinstance(v, dict) and "items" in v:
                fix_obj(v["items"])
        for ref in obj.get("$defs", obj.get("definitions", {})).values():
            fix_obj(ref)

    out = deepcopy(schema)
    fix_obj(out)
    for defn in out.get("$defs", out.get("definitions", {})).values():
        fix_obj(defn)
    return out

# Truncate only when necessary (e.g. raw PDF decode gave huge string). With pdfplumber, full sheet is usually under 15k chars.
MAX_PDF_CHARS = 40000
FALLBACK_PDF_CHARS = 20000


def extract_freight_rates(
    pdf_text: str,
    *,
    max_retries: int = 3,
    use_mini: bool = True,
    max_chars: int = MAX_PDF_CHARS,
) -> CompleteTariffDocument:
    """
    Extract FCL freight rates from tariff text using OpenAI structured outputs.

    Args:
        pdf_text: Raw text from the tariff PDF (or decoded content).
        max_retries: Number of retries on rate limit or API errors.
        use_mini: If True, use gpt-4o-mini (higher TPM, cheaper).
        max_chars: Truncate input to this many characters to avoid token limits.

    Returns:
        CompleteTariffDocument with rates, global_fees, notes.
    """
    client = OpenAI()
    model = "gpt-4o-mini-2024-07-18" if use_mini else "gpt-4o-2024-08-06"

    if len(pdf_text) > max_chars:
        print(f"PDF text is {len(pdf_text)} chars, truncating to {max_chars}")
        pdf_text = pdf_text[:max_chars]

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"Retry attempt {attempt + 1}/{max_retries}...")

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Extract all FCL freight rates from this tariff document.\n\n"
                            "Return complete VendorRate objects for every port in both "
                            "OUTBOUND and INBOUND sections. Pay special attention to "
                            "regional effective dates.\n\nDocument:\n"
                            + pdf_text
                        ),
                    },
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "freight_rate_extraction",
                        "schema": _strict_schema(CompleteTariffDocument.model_json_schema()),
                        "strict": True,
                    },
                },
                temperature=0,
            )

            result = CompleteTariffDocument.model_validate_json(
                response.choices[0].message.content
            )
            print(f"Extraction successful using {model}")
            return result

        except RateLimitError as e:
            error_msg = str(e)
            print(f"Rate limit error: {error_msg[:200]}...")

            if "tokens per min" in error_msg.lower() or "request too large" in error_msg.lower():
                if not use_mini:
                    print("Switching to gpt-4o-mini (higher limits)...")
                    return extract_freight_rates(
                        pdf_text, max_retries=max_retries, use_mini=True
                    )
                if len(pdf_text) > FALLBACK_PDF_CHARS:
                    print(f"Truncating further to {FALLBACK_PDF_CHARS} chars...")
                    return extract_freight_rates(
                        pdf_text[:FALLBACK_PDF_CHARS],
                        max_retries=max_retries,
                        use_mini=True,
                    )
                print("Text already minimal. Check OpenAI tier/quota.")
                raise

            if attempt < max_retries - 1:
                delay = 2.0 * (2 ** attempt)
                print(f"Waiting {delay:.1f}s before retry...")
                time.sleep(delay)
            else:
                print("Failed after all retries. Check https://platform.openai.com/account/limits")
                raise

        except APIError as e:
            if attempt < max_retries - 1:
                delay = 2.0 * (2 ** attempt)
                print(f"API error. Waiting {delay:.1f}s...")
                time.sleep(delay)
            else:
                raise

    raise RuntimeError("Extraction failed after all retries")
