"""Clinical text cleaning and normalization module for Biomedical ETL Pipeline."""

import re
import unicodedata
from typing import Optional
from src.logger import logger


def clean_text(text: Optional[str], lowercase: bool = True, strip_punctuation_noise: bool = False) -> str:
    """Sanitize, normalize, and clean raw clinical text notes.

    Performs whitespace collapsing, newline/tab normalization, unicode canonicalization,
    optional lowercasing, and clinical punctuation preservation.

    Args:
        text: Raw clinical text input.
        lowercase: Whether to convert text to lowercase (default: True).
        strip_punctuation_noise: Whether to strip non-clinical punctuation noise.

    Returns:
        Cleaned, normalized string. Returns empty string if input is None or falsy.
    """
    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    if not text.strip():
        return ""

    # 1. Unicode normalization (NFKC) to resolve special whitespace, micro sign µ, etc.
    normalized = unicodedata.normalize("NFKC", text)

    # 2. Normalize common micro signs (e.g. µg -> mcg for clinical safety)
    normalized = re.sub(r"[µμ]g\b", "mcg", normalized, flags=re.IGNORECASE)

    # 3. Strip HTML/XML tags if clinical notes originate from EHR web exports
    normalized = re.sub(r"<[^>]+>", " ", normalized)

    # 4. Optional removal of repeated non-clinical noise characters (e.g. '!!!!', '???', '***')
    if strip_punctuation_noise:
        normalized = re.sub(r"[!*~`^#]+", " ", normalized)
        normalized = re.sub(r"\.{2,}", " ", normalized)

    # 5. Collapse all consecutive whitespace characters (spaces, tabs, newlines) into a single space
    cleaned = re.sub(r"\s+", " ", normalized).strip()

    # 6. Case normalization
    if lowercase:
        cleaned = cleaned.lower()

    return cleaned


def sanitize_clinical_text(text: Optional[str]) -> str:
    """Convenience alias performing full standard clinical text cleaning."""
    return clean_text(text, lowercase=True, strip_punctuation_noise=True)


if __name__ == "__main__":
    raw_sample = "  Patient   took   500mg  of   Aspirin. \n\t Check dosage daily.   "
    print("Original Text:\n", repr(raw_sample))
    cleaned_result = clean_text(raw_sample)
    print("\nCleaned Text:\n", repr(cleaned_result))
