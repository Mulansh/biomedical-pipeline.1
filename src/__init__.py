"""Biomedical NLP & Clinical Text ETL Pipeline.

A high-performance biomedical text cleaning, medication extraction,
and structured ETL processing engine.
"""

__version__ = "2.0.0"
__author__ = "Biomedical Pipeline Engineering Team"

from src.cleaner import clean_text, sanitize_clinical_text
from src.extractor import extract_dosage, extract_medication_entities, extract_all_clinical_data
from src.pipeline import BiomedicalETLPipeline, run_etl_pipeline, run_batch_pipeline

__all__ = [
    "__version__",
    "clean_text",
    "sanitize_clinical_text",
    "extract_dosage",
    "extract_medication_entities",
    "extract_all_clinical_data",
    "BiomedicalETLPipeline",
    "run_etl_pipeline",
    "run_batch_pipeline",
]
