# OpenAI Strict Schema Requirements - Quick Reference

## The Error You Saw

```
BadRequestError: Invalid schema for response_format 'freight_rate_extraction': 
In context=(), 'required' is required to be supplied and to be an array including 
every key in properties. Missing 'applies_to'.
```

## Root Cause

OpenAI's **strict schema mode** (`"strict": True`) has special requirements:

### ❌ What Doesn't Work

```python
class GlobalFee(BaseModel):
    fee_name: str
    amount: float
    applies_to: Optional[str] = Field(None, ...)  # ❌ FAILS in strict mode
```

**Problem:** `Optional[str] = None` is ambiguous in strict mode. OpenAI can't determine if this field is required or optional.

### ✅ What Works

```python
class GlobalFee(BaseModel):
    fee_name: str
    amount: float
    applies_to: str = Field(default="all", ...)  # ✅ Works in strict mode
```

**Solution:** Use explicit default value instead of `None`. This tells OpenAI:
- Field is optional (has default)
- Default value is `"all"`
- Type is `str` (not nullable)

## Rules for OpenAI Strict Schema

### 1. **No Optional with None**

❌ Don't use:
```python
field: Optional[str] = None
field: Optional[str] = Field(None)
field: str | None = None
```

✅ Use instead:
```python
# For strings - use default value
field: str = Field(default="")
field: str = Field(default="unknown")

# For numbers - use default value
field: float = Field(default=0.0)
field: int = Field(default=0)

# For booleans - use default
field: bool = Field(default=False)

# For lists - use factory
field: List[str] = Field(default_factory=list)

# For dicts - use factory
field: dict = Field(default_factory=dict)
```

### 2. **Every Field Must Be Either Required OR Have Default**

```python
class MyModel(BaseModel):
    # Required fields (no default)
    id: str
    name: str
    
    # Optional fields (with defaults)
    description: str = Field(default="")
    tags: List[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    
    class Config:
        extra = "forbid"  # Recommended for strict mode
```

### 3. **Nullable Values Need Special Handling**

If you truly need nullable (field can be `null` in JSON):

```python
# Option 1: Use union with None and explicit default
field: Union[str, None] = Field(default=None)

# Option 2: Use sentinel value
field: str = Field(default="")  # Empty string means "not set"
field: float = Field(default=-1.0)  # -1 means "not set"
```

## Fixed Models for Freight Extraction

### Before (Broken):

```python
class GlobalFee(BaseModel):
    fee_name: str
    amount: float
    currency: Literal["USD", "SGD"]
    unit: str
    applies_to: Optional[str] = Field(None, ...)  # ❌ BREAKS
```

### After (Working):

```python
class GlobalFee(BaseModel):
    fee_name: str
    amount: float
    currency: Literal["USD", "SGD"]
    unit: str
    applies_to: str = Field(
        default="all",  # ✅ WORKS
        description="'all' or specific route/country"
    )
```

## All Fixed Models Summary

```python
class RateCharge(BaseModel):
    charge_type: Literal[...]
    container_type: Literal[...]
    amount: Optional[float] = Field(default=None)  # ✅ Explicit default
    currency: Literal["USD", "SGD"]
    is_included: bool = Field(default=False)  # ✅ Explicit default
    unit: Literal[...] = Field(default="per_container")  # ✅ Explicit default

class VendorRate(BaseModel):
    route_type: Literal[...]
    country: str  # Required
    port_name: str  # Required
    region: Literal[...]
    pol: str
    pod: str
    charges: List[RateCharge]  # Required (not empty list default)
    effective_date_start: str
    effective_date_end: str
    special_notes: List[str] = Field(default_factory=list)  # ✅ Factory

class GlobalFee(BaseModel):
    fee_name: str
    amount: float
    currency: Literal["USD", "SGD"]
    unit: str
    applies_to: str = Field(default="all")  # ✅ Fixed

class CompleteTariffDocument(BaseModel):
    document_name: str = Field(default="November 2025 Tariff")  # ✅
    total_routes: int  # Required
    rates: List[VendorRate]  # Required
    global_fees: List[GlobalFee] = Field(default_factory=list)  # ✅
    notes: List[str] = Field(default_factory=list)  # ✅
```

## Testing Your Schema

Before running extraction, validate your schema:

```python
import json

# Get the schema
schema = CompleteTariffDocument.model_json_schema()

# Check for issues
print(json.dumps(schema, indent=2))

# Look for:
# 1. All properties should either:
#    - Be in "required" array, OR
#    - Have a "default" value
# 2. No "anyOf" with null unless explicitly needed
```

## Common Patterns

### Pattern 1: Optional with Empty Default
```python
# For text that might be missing
description: str = Field(default="")
notes: str = Field(default="N/A")
```

### Pattern 2: Optional with Sentinel Value
```python
# For numbers where 0 is valid
price: float = Field(default=-1.0, description="-1 means not set")
quantity: int = Field(default=-1, description="-1 means not applicable")
```

### Pattern 3: Optional with Collections
```python
# For lists/dicts that might be empty
tags: List[str] = Field(default_factory=list)
metadata: dict = Field(default_factory=dict)
```

### Pattern 4: Truly Nullable (Advanced)
```python
# Only if you need JSON null
from typing import Union

price: Union[float, None] = Field(
    default=None,
    description="Null if not applicable"
)

# In JSON schema, this becomes:
# "price": {"anyOf": [{"type": "number"}, {"type": "null"}]}
```

## Debugging Checklist

When you get schema validation errors:

1. ✅ Check all `Optional[T]` fields have explicit `default=` or `default_factory=`
2. ✅ Don't use `= None` without wrapping in `Field(default=None)`
3. ✅ Use `default_factory=list` for empty lists, not `default=[]`
4. ✅ Use `default_factory=dict` for empty dicts, not `default={}`
5. ✅ Set `extra = "forbid"` in Config for stricter validation
6. ✅ Test schema generation with `.model_json_schema()`

## Quick Fix Command

If you get "Missing 'field_name'" error:

1. Find the field in your model
2. Check if it has `Optional` or no default
3. Add explicit default:

```python
# Before
field: Optional[str] = None

# After
field: str = Field(default="")
```

## When to Use Each Approach

| Scenario | Solution | Example |
|----------|----------|---------|
| Field truly optional, any value OK | `Field(default="")` | `notes: str = Field(default="")` |
| Field represents "not set" state | Sentinel value | `price: float = Field(default=-1)` |
| Field is a collection (empty OK) | `default_factory` | `tags: List[str] = Field(default_factory=list)` |
| Field can be null in JSON | `Union[T, None]` | `optional_id: Union[str, None] = Field(default=None)` |
| Field must always exist | No default | `id: str` |

---

## Summary

**Golden Rule for OpenAI Strict Schema:**

> Every field must either be **required** (no default) or **optional** (explicit default value or factory).

**Never use `Optional[T] = None` without `Field(default=...)`**

This ensures OpenAI can generate valid JSON that matches your schema 100% of the time!
