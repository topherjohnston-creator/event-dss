"""
utils.py â€” Shared utilities for Event DSS
Risk calculation, impact level selection, config loading, conversions.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

# â”€â”€â”€ Paths â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
DOCS_DIR = ROOT / "docs"
DATA_DIR = ROOT / "data"


# â”€â”€â”€ Config loaders â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def load_hazards():
    return json.loads((CONFIG_DIR / "hazards.json").read_text())

def load_locations():
    return json.loads((CONFIG_DIR / "locations.json").read_text())

def load_sources():
    return json.loads((CONFIG_DIR / "data-sources.json").read_text())

def load_risk_matrix():
    return json.loads((CONFIG_DIR / "risk-matrix.json").read_text())

def load_location(location_id: str) -> dict:
    locations = load_locations()
    if location_id not in locations:
        raise ValueError(f"Unknown location: {location_id}. Available: {list(locations.keys())}")
    return locations[location_id]


# â”€â”€â”€ Unit conversions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def k_to_f(kelvin: float) -> float:
    """Kelvin to Fahrenheit."""
    return (kelvin - 273.15) * 9 / 5 + 32

def mps_to_mph(mps: float) -> float:
    """Meters per second to miles per hour."""
    return mps * 2.23694

def m_to_sm(meters: float) -> float:
    """Meters to statute miles."""
    return meters * 0.000621371

def kgm2_to_in(kgm2: float) -> float:
    """kg/mÂ² (liquid equiv.) to inches."""
    return kgm2 * 0.0393701

def convert_value(value: float, hazard_config: dict) -> float:
    """
    Convert a raw GRIB2 value to display units using hazard config.
    Handles special formula-based conversions.
    """
    if value is None:
        return None

    formula = hazard_config.get("conversion_formula")
    if formula:
        # Only safe formulas defined in config
        if "K - 273.15" in formula:
            return k_to_f(value)
        else:
            raise ValueError(f"Unknown conversion formula: {formula}")

    factor = hazard_config.get("conversion", 1.0)
    return value * factor


# â”€â”€â”€ Risk calculation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def probability_to_likelihood(probability: float) -> int:
    """
    Map probability (0-100%) to likelihood level (1-5).

      0-10%  â†’ 1 Unlikely
     10-33%  â†’ 2 Possible
     33-66%  â†’ 3 Likely
     66-90%  â†’ 4 Very Likely
     90-100% â†’ 5 Near Certain
    """
    if probability <= 0:
        return 0
    if probability < 10:
        return 1
    if probability < 33:
        return 2
    if probability < 66:
        return 3
    if probability < 90:
        return 4
    return 5


def select_impact_level(value: float, thresholds: list, inverted: bool = False) -> int:
    """
    Select impact level (1-5) given a value and 4 threshold breakpoints.

    Normal (higher = worse):
      value < t[0]            â†’ level 1
      t[0] <= value < t[1]   â†’ level 2
      t[1] <= value < t[2]   â†’ level 3
      t[2] <= value < t[3]   â†’ level 4
      value >= t[3]           â†’ level 5

    Inverted (lower = worse, e.g. visibility, temperature cold):
      value >= t[0]           â†’ level 1
      t[1] <= value < t[0]   â†’ level 2
      t[2] <= value < t[1]   â†’ level 3
      t[3] <= value < t[2]   â†’ level 4
      value < t[3]            â†’ level 5
    """
    if value is None:
        return 0

    t = thresholds  # 4 thresholds defining 5 levels

    if not inverted:
        if value < t[0]:   return 1
        if value < t[1]:   return 2
        if value < t[2]:   return 3
        if value < t[3]:   return 4
        return 5
    else:
        # Inverted: lower value = higher impact
        if value >= t[0]:  return 1
        if value >= t[1]:  return 2
        if value >= t[2]:  return 3
        if value >= t[3]:  return 4
        return 5


def calculate_risk(probability: float, impact_level: int) -> int:
    """
    Standard probability Ã— impact risk matrix.

    Returns risk level 0-5.
    """
    if probability <= 0 or impact_level <= 0:
        return 0

    rm = load_risk_matrix()
    likelihood = probability_to_likelihood(probability)

    if likelihood == 0:
        return 0

    risk = rm["risk_matrix"][str(likelihood)][str(impact_level)]
    return int(risk)


def risk_to_label(risk: int) -> str:
    rm = load_risk_matrix()
    return rm["risk_labels"].get(str(risk), "UNKNOWN")


def risk_to_color(risk: int) -> str:
    rm = load_risk_matrix()
    return rm["risk_colors"].get(str(risk), "#444444")


# â”€â”€â”€ Flash freeze joint probability â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def flash_freeze_impact_level(
    wet_bulb_f: float,
    surface_is_wet: bool
) -> int:
    """
    Flash freeze impact level based on wet bulb temperature
    and whether surface is wet from precipitation.

    If surface is dry â†’ level 1 (no risk regardless of wet bulb)
    If surface is wet:
      Tw > 36Â°F  â†’ level 1
      Tw <= 36Â°F â†’ level 2
      Tw <= 32Â°F â†’ level 3
      Tw <= 28Â°F â†’ level 4
      Tw <= 25Â°F â†’ level 5
    """
    if not surface_is_wet:
        return 1

    if wet_bulb_f > 36:   return 1
    if wet_bulb_f > 32:   return 2
    if wet_bulb_f > 28:   return 3
    if wet_bulb_f > 25:   return 4
    return 5


def joint_probability_flash_freeze(
    prob_precip: float,
    prob_wet_bulb_below_threshold: float
) -> float:
    """
    Joint probability: surface wet AND wet bulb below threshold.
    Assumes some dependence (weather systems bring both together).
    Uses conditional probability: P(FF) = P(wet) Ã— P(Tw < threshold | wet)
    Conservative estimate: treat as independent.

    Both probabilities 0-100.
    Returns joint probability 0-100.
    """
    p_wet = prob_precip / 100.0
    p_cold = prob_wet_bulb_below_threshold / 100.0
    joint = p_wet * p_cold
    return joint * 100.0


# â”€â”€â”€ Timing utilities â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_latest_refs_cycle(now: datetime = None) -> datetime:
    """
    Get most recent available REFS cycle (00Z, 06Z, 12Z, 18Z).
    REFS typically available ~2 hours after cycle time.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    cycle_hour = (now.hour // 6) * 6
    cycle = now.replace(hour=cycle_hour, minute=0, second=0, microsecond=0)

    # If < 2 hours into current cycle, use previous
    elapsed_minutes = (now.hour % 6) * 60 + now.minute
    if elapsed_minutes < 120:
        cycle = cycle.replace(hour=max(0, cycle_hour - 6) if cycle_hour >= 6
                              else 18)
        if cycle_hour < 6:
            from datetime import timedelta
            cycle = cycle - timedelta(days=1)
            cycle = cycle.replace(hour=18)

    return cycle


def fxx_to_valid_time(cycle: datetime, fxx: int) -> datetime:
    """Convert forecast hour to valid UTC time."""
    from datetime import timedelta
    return cycle + timedelta(hours=fxx)


def block_index_to_fxx(block_idx: int) -> tuple[int, int]:
    """
    Convert block index (0-19) to forecast hour range.
    Block 0  â†’ f001â€“f003
    Block 1  â†’ f004â€“f006
    ...
    Block 19 â†’ f058â€“f060
    """
    start = block_idx * 3 + 1
    end   = (block_idx + 1) * 3
    return start, end


# â”€â”€â”€ Output helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def save_json(path: Path, data: dict, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=indent, default=str))
    log.info(f"âœ“ Saved {path}")


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_disclaimer() -> dict:
    return {
        "status": "EXPERIMENTAL",
        "operational": False,
        "purpose": "Research and event planning only",
        "data_source": "REFS (Regional Ensemble Forecast System) â€” NOAA prototype",
        "aws_bucket": "noaa-rrfs-pds",
        "message": (
            "This system uses experimental, non-operational REFS forecast data "
            "from AWS S3. Not suitable for official operational decisions. "
            "For official forecasts consult weather.gov."
        )
    }
