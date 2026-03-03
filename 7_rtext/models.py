"""
Pydantic models for freight rate extraction (VendorRate DTO and related).
Compatible with OpenAI structured outputs (strict schema mode).
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class RateCharge(BaseModel):
    """Individual charge component (ocean freight, surcharge, BAF, AMS)."""

    charge_type: Literal[
        "ocean_freight", "dg3_surcharge", "dg2_surcharge", "baf_lss", "ams"
    ]
    container_type: Literal["20'GP", "40'GP", "40'HC"]
    amount: Optional[float] = Field(
        default=None,
        description="Null if INCL. or - in PDF",
    )
    currency: Literal["USD", "SGD"]
    is_included: bool = Field(
        default=False,
        description="True only if PDF shows INCL.",
    )
    unit: Literal["per_container", "per_set", "per_teu"] = Field(
        default="per_container"
    )

    class Config:
        extra = "forbid"


class VendorRate(BaseModel):
    """Complete freight rate for a specific port/route."""

    route_type: Literal["outbound", "inbound"]
    country: str = Field(description="Country name e.g. BRUNEI PHILIPPINES")
    port_name: str = Field(
        description="Port name may include notes like MUARA SGD or CHATTOGRAM CY/CY"
    )
    region: Literal["sea_china", "india_middle_east_subcon"] = Field(
        description="Region determines effective date range"
    )
    pol: str = Field(description="Port of Loading")
    pod: str = Field(description="Port of Destination")
    charges: List[RateCharge] = Field(
        description="All charges for this route"
    )
    effective_date_start: str = Field(
        description="ISO date 2025-11-01 for sea_china 2025-11-14 for india_middle_east_subcon"
    )
    effective_date_end: str = Field(
        description="ISO date 2025-11-30 for both regions"
    )
    special_notes: List[str] = Field(
        default_factory=list,
        description="Any special conditions for this route",
    )

    class Config:
        extra = "forbid"


class GlobalFee(BaseModel):
    """Document-wide fees (BL Fee, Seal Fee, etc.)."""

    fee_name: str
    amount: float
    currency: Literal["USD", "SGD"]
    unit: str = Field(description="per_set per_container etc")
    # Required (no default) so OpenAI strict schema includes it in "required" array
    applies_to: str = Field(
        description="Use 'all' for global fees, or specific route/country if applicable"
    )

    class Config:
        extra = "forbid"


class CompleteTariffDocument(BaseModel):
    """Complete tariff document extraction result."""

    document_name: str = Field(default="November 2025 Tariff")
    total_routes: int = Field(description="Total number of port routes extracted")
    rates: List[VendorRate] = Field(
        description="All freight rates with regional dates"
    )
    global_fees: List[GlobalFee] = Field(
        default_factory=list,
        description="Document-wide fees like BL Fee SGD200/SET",
    )
    notes: List[str] = Field(
        default_factory=list,
        description="Any additional notes from document footer",
    )

    class Config:
        extra = "forbid"
