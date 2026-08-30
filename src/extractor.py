"""Biomedical medication and dosage entity extraction engine."""

import re
from typing import Any, Dict, List, Optional, Tuple
from src.logger import logger
from src.models import MedicationEntity

# Common clinical dosage units regex pattern
DOSAGE_PATTERN = re.compile(
    r"""
    \b
    (
        (?:\d+(?:\.\d+)?|\d+/\d+|\d+\s*-\s*\d+) # Integer, decimal, fraction, or range
        \s*
        (?:
            mg/kg/day|mg/kg/min|mg/kg|mg/day|mg/hr|
            mcg/kg/min|mcg/min|mcg/hr|ml/hr|units?/hr|
            mg|g|grams?|mcg|µg|ug|ml|l|iu|units?|
            meq|mEq|tabs?|tablets?|caps?|capsules?|
            puffs?|drops?|patches?|%
        )
    )
    (?=[\s,.;:!?\)]|$)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Common clinical routes
ROUTE_PATTERN = re.compile(
    r"\b(PO|oral|orally|IV|intravenous|intravenously|IM|intramuscular|SC|subcutaneous|sublingually|sublingual|SL|topical|topically|inhalation|inhaled|PR|rectal|ophthalmic|otic)\b",
    re.IGNORECASE,
)

# Common clinical frequencies & sigs
FREQUENCY_PATTERN = re.compile(
    r"\b(BID|TID|QID|QHS|QD|PRN|Q4H|Q6H|Q8H|Q12H|Q24H|once\s+daily|twice\s+daily|thrice\s+daily|three\s+times\s+daily|four\s+times\s+daily|every\s+\d+\s+hours|every\s+morning|at\s+bedtime|as\s+needed(?:\s+for\s+[a-z]+)?|with\s+meals|daily)\b",
    re.IGNORECASE,
)

# Course durations
DURATION_PATTERN = re.compile(
    r"\b(?:for\s+)?(\d+\s*(?:days?|weeks?|wks?|months?|hrs?|hours?))\b",
    re.IGNORECASE,
)

# Curated knowledge base of common clinical pharmaceutical names for entity resolution
KNOWN_DRUGS = {
    "tylenol", "paracetamol", "acetaminophen", "aspirin", "amoxicillin", "augmentin",
    "metformin", "lisinopril", "atorvastatin", "lipitor", "albuterol", "ventolin",
    "insulin", "glargine", "humalog", "novolog", "ibuprofen", "advil", "motrin",
    "morphine", "fentanyl", "oxycodone", "hydrocodone", "prednisone", "prednisolone",
    "omeprazole", "prilosec", "pantoprazole", "ciprofloxacin", "cipro", "azithromycin",
    "zithromax", "levothyroxine", "synthroid", "hydrochlorothiazide", "hctz",
    "gabapentin", "neurontin", "sertraline", "zoloft", "losartan", "cozaar",
    "furosemide", "lasix", "metoprolol", "lopressor", "toprol", "amlodipine", "norvasc",
    "simvastatin", "zocor", "clopidogrel", "plavix", "escitalopram", "lexapro",
    "fluoxetine", "prozac", "tramadol", "ultram", "warfarin", "coumadin", "eliquis",
    "apixaban", "xarelto", "rivaroxaban", "doxycycline", "cephalexin", "keflex",
    "dexamethasone", "salbutamol", "lorazepam", "ativan", "diazepam", "valium",
    "alprazolam", "xanax", "zolpidem", "ambien", "penicillin", "vancomycin",
    "ceftriaxone", "enoxaparin", "lovenox", "heparin", "digoxin", "spironolactone",
}


def _parse_dosage_value_and_unit(raw_dosage: str) -> Tuple[Optional[float], Optional[str]]:
    """Parse raw dosage string into numerical value and canonical unit."""
    cleaned = raw_dosage.strip().lower()
    # Match number and unit
    m = re.match(r"^([\d\./\s\-]+)\s*([a-z%µ/]+)$", cleaned)
    if not m:
        return None, None

    num_part = m.group(1).strip()
    unit_part = m.group(2).strip()

    # Normalize micro signs
    if unit_part in ("µg", "ug"):
        unit_part = "mcg"
    elif unit_part in ("tablets", "tablet", "tabs"):
        unit_part = "tab"
    elif unit_part in ("capsules", "capsule", "caps"):
        unit_part = "cap"
    elif unit_part in ("puffs", "puff"):
        unit_part = "puff"
    elif unit_part in ("drops", "drop"):
        unit_part = "drop"
    elif unit_part in ("patches", "patch"):
        unit_part = "patch"
    elif unit_part in ("grams", "gram"):
        unit_part = "g"
    elif unit_part == "units":
        unit_part = "unit"

    # Parse numeric part (handling fractions, decimals, ranges)
    val: Optional[float] = None
    try:
        if "/" in num_part and not "-" in num_part:
            numerator, denominator = num_part.split("/", 1)
            val = float(numerator.strip()) / float(denominator.strip())
        elif "-" in num_part:
            start_val, end_val = num_part.split("-", 1)
            val = (float(start_val.strip()) + float(end_val.strip())) / 2.0
        else:
            val = float(num_part)
    except (ValueError, ZeroDivisionError):
        val = None

    return val, unit_part


def _find_surrounding_drug_name(text: str, start_char: int, end_char: int) -> Optional[str]:
    """Identify potential medication name associated with a dosage match."""
    # Look back up to 60 characters before the dosage
    prefix_start = max(0, start_char - 60)
    prefix_text = text[prefix_start:start_char]

    # Look ahead up to 40 characters after the dosage
    suffix_end = min(len(text), end_char + 40)
    suffix_text = text[end_char:suffix_end]

    # Tokenize words in surrounding text
    tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9\-]+\b", prefix_text)

    # 1. Check for known drug matches in prefix (reverse order to find closest)
    for token in reversed(tokens):
        if token.lower() in KNOWN_DRUGS:
            return token.capitalize()

    # 2. Check for known drug matches in suffix
    suffix_tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9\-]+\b", suffix_text)
    for token in suffix_tokens:
        if token.lower() in KNOWN_DRUGS:
            return token.capitalize()

    # 3. Look for capitalized words immediately preceding dosage (e.g. "Prescribed Tylenol 500mg")
    ignore_words = {
        "patient", "pt", "prescribed", "given", "administered", "started", "on",
        "took", "taking", "ordered", "dose", "dosage", "daily", "daily orally",
        "with", "and", "or", "to", "in", "mg", "ml", "tab", "check", "no", "yes",
        "mild", "severe", "follow", "up", "the", "a", "an", "for", "at", "by", "of"
    }
    for token in reversed(tokens):
        if token.lower() not in ignore_words and len(token) > 2:
            return token.capitalize()

    return None


def extract_dosage(text: Optional[str]) -> List[str]:
    """Find and return all dosage substrings from clinical text (backward-compatible API).

    Args:
        text: Clinical note or medical text.

    Returns:
        List of raw dosage strings found in the text.
    """
    if not text or not isinstance(text, str):
        return []

    matches = DOSAGE_PATTERN.finditer(text)
    results = [m.group(1).strip() for m in matches]
    return results


def extract_medication_entities(text: Optional[str]) -> List[MedicationEntity]:
    """Extract structured medication entities including dosage, route, frequency, and duration.

    Args:
        text: Clinical note text string.

    Returns:
        List of MedicationEntity models.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return []

    entities: List[MedicationEntity] = []
    
    # Global route, frequency, and duration candidates for the sentence / text
    route_match = ROUTE_PATTERN.search(text)
    freq_match = FREQUENCY_PATTERN.search(text)
    dur_match = DURATION_PATTERN.search(text)

    default_route = route_match.group(1) if route_match else None
    default_freq = freq_match.group(1) if freq_match else None
    default_dur = dur_match.group(1) if dur_match else None

    for m in DOSAGE_PATTERN.finditer(text):
        raw_dosage = m.group(1).strip()
        start_char, end_char = m.span(1)
        val, unit = _parse_dosage_value_and_unit(raw_dosage)
        drug_name = _find_surrounding_drug_name(text, start_char, end_char)

        # Context-local search for route / frequency within 50 chars of the dosage
        window_start = max(0, start_char - 40)
        window_end = min(len(text), end_char + 50)
        window_text = text[window_start:window_end]

        local_route = ROUTE_PATTERN.search(window_text)
        local_freq = FREQUENCY_PATTERN.search(window_text)
        local_dur = DURATION_PATTERN.search(window_text)

        entity_route = local_route.group(1) if local_route else default_route
        entity_freq = local_freq.group(1) if local_freq else default_freq
        entity_dur = local_dur.group(1) if local_dur else default_dur

        # Calculate confidence score based on contextual completeness
        confidence = 0.85
        if drug_name:
            confidence += 0.08
        if entity_route or entity_freq:
            confidence += 0.05
        confidence = min(0.99, confidence)

        entities.append(
            MedicationEntity(
                medication_name=drug_name,
                raw_dosage=raw_dosage,
                dosage_value=val,
                dosage_unit=unit,
                route=entity_route,
                frequency=entity_freq,
                duration=entity_dur,
                start_char=start_char,
                end_char=end_char,
                confidence=round(confidence, 2),
            )
        )

    return entities


def extract_all_clinical_data(text: Optional[str]) -> Dict[str, Any]:
    """Execute complete entity extraction returning dictionary of extracted attributes."""
    if not text:
        return {"dosages": [], "medications": [], "entity_count": 0}

    dosages = extract_dosage(text)
    medications = extract_medication_entities(text)

    return {
        "dosages": dosages,
        "medications": medications,
        "entity_count": len(dosages),
    }


if __name__ == "__main__":
    test_text = "Patient prescribed Amoxicillin 250mg PO TID for 10 days and 10 ml of cough syrup."
    print("Test Input:", test_text)
    print("Found dosages:", extract_dosage(test_text))
    print("Medication entities:", extract_medication_entities(test_text))