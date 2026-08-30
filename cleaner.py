"""Root re-export and CLI helper for Biomedical Clinical Text Cleaner.

Provides backward-compatible entry points for legacy scripts and test harnesses.
"""

import sys
import os

# Add root directory to sys.path if not present
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cleaner import clean_text, sanitize_clinical_text

__all__ = ["clean_text", "sanitize_clinical_text"]

if __name__ == "__main__":
    raw_sample = "  Patient   took   500mg  of   Aspirin. \n\t Check dosage daily.   "
    print("Original Text:")
    print(repr(raw_sample))

    cleaned_result = clean_text(raw_sample)
    print("\nCleaned Text:")
    print(repr(cleaned_result))
