"""Pytest test fixtures and configuration for Biomedical ETL Pipeline test suite."""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure root workspace is available in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from src.pipeline import BiomedicalETLPipeline


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Session-scoped FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def fresh_pipeline() -> BiomedicalETLPipeline:
    """Isolated instance of BiomedicalETLPipeline for unit testing."""
    return BiomedicalETLPipeline(name="Test-Pipeline-Instance")


@pytest.fixture
def sample_clinical_notes():
    """Collection of clinical notes across multiple clinical specialties."""
    return [
        {
            "patient_id": "P-101",
            "raw_note": "pt presented with severe headache... prescribed Tylenol 500mg BID for 5 days.",
            "expected_drugs": ["Tylenol"],
            "expected_dosages": ["500mg"],
        },
        {
            "patient_id": "P-102",
            "raw_note": "Administered Amoxicillin 250 mg daily orally, discontinued past meds. Follow up in 2 wks.",
            "expected_drugs": ["Amoxicillin"],
            "expected_dosages": ["250 mg"],
        },
        {
            "patient_id": "P-103",
            "raw_note": "Metformin 1000mg twice daily with meals. Insulin Glargine 20 units SC at bedtime.",
            "expected_drugs": ["Metformin", "Insulin"],
            "expected_dosages": ["1000mg", "20 units"],
        },
    ]
