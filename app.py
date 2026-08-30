"""Biomedical NLP & Clinical Text ETL Pipeline - FastAPI Backend Service.

High-performance REST API providing text cleaning, biomedical NER entity extraction,
structured clinical prescription parsing, and batch ETL processing.
"""

import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.__init__ import __version__
from src.cleaner import clean_text
from src.extractor import extract_all_clinical_data, extract_dosage, extract_medication_entities
from src.logger import logger, setup_logger
from src.models import (
    BatchPipelineRequest,
    BatchPipelineResponse,
    CleanTextRequest,
    CleanTextResponse,
    ClinicalSample,
    ExtractDosageRequest,
    ExtractDosageResponse,
    HealthCheckResponse,
    PipelineRequest,
    PipelineResponse,
    PipelineStatsResponse,
)
from src.pipeline import BiomedicalETLPipeline, default_pipeline

# App startup time tracking
START_TIME = time.time()
START_DATETIME = datetime.now(timezone.utc).isoformat()

# Pipeline telemetry counters
TOTAL_REQUESTS = 0
TOTAL_RECORDS = 0
TOTAL_ENTITIES = 0
TOTAL_LATENCY_MS = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info(f"Starting Biomedical ETL Pipeline API v{__version__}")
    yield
    logger.info("Shutting down Biomedical ETL Pipeline API")


# Initialize FastAPI Application with metadata
app = FastAPI(
    title="Biomedical NLP & Clinical Text ETL Pipeline",
    description="""
    An enterprise-grade biomedical natural language processing (NLP) and ETL engine.
    
    ### Key Capabilities:
    * **Clinical Text Cleaning**: Sanitizes noisy EHR notes, normalizes whitespace, standardizes medical units.
    * **Medication & Dosage Extraction**: Extracts pharmaceutical drug names, dosages, units (mg, ml, mcg, IU, etc.), routes, and frequencies.
    * **ETL Pipeline**: End-to-end ingestion, transformation, and structured JSON generation with full provenance and latency metrics.
    * **High-Throughput Batch Processing**: Process multi-patient clinical batches with summary telemetry.
    """,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Timing & Telemetry Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    global TOTAL_REQUESTS, TOTAL_LATENCY_MS
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time_ms = (time.perf_counter() - start_time) * 1000
    TOTAL_REQUESTS += 1
    TOTAL_LATENCY_MS += process_time_ms
    response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
    return response


# Custom Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format validation errors into clean, structured JSON."""
    errors = []
    for err in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg"),
            "type": err.get("type"),
        })
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "error_type": "ValidationError",
            "message": "Input validation failed. Please inspect the request payload.",
            "details": errors,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Format HTTP exceptions into standard error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error_type": "HTTPException",
            "message": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all unexpected error handler."""
    logger.exception(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error_type": "InternalServerError",
            "message": "An unexpected error occurred while processing the clinical record.",
        },
    )


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------


@app.get(
    "/",
    tags=["General"],
    summary="API Root & Overview",
    description="Returns welcome message, API version, and documentation links.",
)
async def root():
    return {
        "title": "Biomedical NLP & Clinical Text ETL Pipeline",
        "version": __version__,
        "status": "operational",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json",
        },
        "endpoints": {
            "health": "GET /api/v1/health",
            "clean_text": "POST /api/v1/clean",
            "extract_entities": "POST /api/v1/extract",
            "run_pipeline": "POST /api/v1/pipeline",
            "batch_pipeline": "POST /api/v1/pipeline/batch",
            "stats": "GET /api/v1/stats",
            "samples": "GET /api/v1/samples",
        },
    }


@app.get(
    "/api/v1/health",
    response_model=HealthCheckResponse,
    tags=["System"],
    summary="Health & Readiness Check",
    description="Verifies the operational status, server uptime, and engine version.",
)
async def health_check():
    uptime = time.time() - START_TIME
    return HealthCheckResponse(
        status="healthy",
        version=__version__,
        uptime_seconds=round(uptime, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
        engine="Biomedical-NLP-Regex-v2.0",
    )


@app.get(
    "/api/v1/stats",
    response_model=PipelineStatsResponse,
    tags=["System"],
    summary="Pipeline Telemetry & Statistics",
    description="Returns live counters for requests, processed records, and latency.",
)
async def get_stats():
    avg_latency = (
        round(TOTAL_LATENCY_MS / TOTAL_REQUESTS, 2) if TOTAL_REQUESTS > 0 else 0.0
    )
    return PipelineStatsResponse(
        total_requests=TOTAL_REQUESTS,
        total_records_processed=default_pipeline.total_processed,
        total_entities_extracted=default_pipeline.total_entities_extracted,
        average_latency_ms=avg_latency,
        active_since=START_DATETIME,
    )


@app.post(
    "/api/v1/clean",
    response_model=CleanTextResponse,
    tags=["NLP Processing"],
    summary="Clean and Normalize Clinical Text",
    description="Sanitizes raw clinical text by collapsing whitespace, normalizing characters, and removing noise.",
)
async def clean_clinical_text(payload: CleanTextRequest):
    if not payload.text:
        return CleanTextResponse(
            original_text="",
            cleaned_text="",
            original_char_count=0,
            cleaned_char_count=0,
            status="success",
        )

    cleaned = clean_text(
        payload.text,
        lowercase=payload.lowercase,
        strip_punctuation_noise=payload.strip_punctuation_noise,
    )
    return CleanTextResponse(
        original_text=payload.text,
        cleaned_text=cleaned,
        original_char_count=len(payload.text),
        cleaned_char_count=len(cleaned),
        status="success",
    )


@app.post(
    "/api/v1/extract",
    response_model=ExtractDosageResponse,
    tags=["NLP Processing"],
    summary="Extract Medication and Dosage Entities",
    description="Identifies pharmaceutical drug names, dosages, units, routes, and frequencies from clinical text.",
)
async def extract_clinical_entities(payload: ExtractDosageRequest):
    input_text = payload.text
    if payload.clean_first:
        input_text = clean_text(input_text, lowercase=False)

    dosages = extract_dosage(input_text)
    medications = extract_medication_entities(input_text)

    return ExtractDosageResponse(
        text=payload.text,
        dosages=dosages,
        medications=medications,
        entity_count=len(medications),
        status="success",
    )


@app.post(
    "/api/v1/pipeline",
    response_model=PipelineResponse,
    tags=["ETL Pipeline"],
    summary="Execute Full Single-Note ETL Pipeline",
    description="Ingests a raw clinical record, executes full cleaning and entity extraction, and outputs structured JSON.",
)
async def run_single_pipeline(payload: PipelineRequest):
    global TOTAL_RECORDS, TOTAL_ENTITIES
    response = default_pipeline.process_record(
        raw_clinical_log=payload.raw_clinical_log,
        patient_id=payload.patient_id,
        metadata=payload.metadata,
    )
    TOTAL_RECORDS += 1
    TOTAL_ENTITIES += response.entity_count
    return response


@app.post(
    "/api/v1/pipeline/batch",
    response_model=BatchPipelineResponse,
    tags=["ETL Pipeline"],
    summary="Execute Batch ETL Pipeline",
    description="Processes multiple clinical notes concurrently and generates aggregate metrics and structured outputs.",
)
async def run_batch_etl_pipeline(payload: BatchPipelineRequest):
    global TOTAL_RECORDS, TOTAL_ENTITIES
    batch_response = default_pipeline.process_batch(payload)
    TOTAL_RECORDS += batch_response.summary.total_records
    TOTAL_ENTITIES += batch_response.summary.total_medications_found
    return batch_response


@app.get(
    "/api/v1/samples",
    response_model=List[ClinicalSample],
    tags=["Testing & Samples"],
    summary="Get Pre-loaded Clinical Test Samples",
    description="Returns pre-configured clinical note samples across departments for quick UI testing.",
)
async def get_clinical_samples():
    return [
        ClinicalSample(
            id="SMPL-001",
            patient_id="P-101",
            title="Acute Migraine / Headache",
            category="Neurology",
            raw_note="pt presented with severe migraine headache... prescribed Tylenol 500mg BID for 5 days. patient noted mild fatigue!!",
        ),
        ClinicalSample(
            id="SMPL-002",
            patient_id="P-102",
            title="Bacterial Respiratory Infection",
            category="Infectious Disease",
            raw_note="Administered Amoxicillin 250 mg daily orally, discontinued past meds. Follow up in 2 wks.",
        ),
        ClinicalSample(
            id="SMPL-003",
            patient_id="P-103",
            title="Type 2 Diabetes Mellitus",
            category="Endocrinology",
            raw_note="Metformin 1000mg twice daily with meals. Insulin Glargine 20 units SC at bedtime. NO KNOWN ALLERGIES.",
        ),
        ClinicalSample(
            id="SMPL-004",
            patient_id="P-104",
            title="Cardiovascular Disease & Hypertension",
            category="Cardiology",
            raw_note="Patient started on Lisinopril 10mg PO once daily for hypertension and Atorvastatin 40mg at bedtime.",
        ),
        ClinicalSample(
            id="SMPL-005",
            patient_id="P-105",
            title="Asthma & COPD Exacerbation",
            category="Pulmonology",
            raw_note="Albuterol 2 puffs inhaled every 4 hours as needed for shortness of breath. Prednisone 20mg daily for 5 days taper.",
        ),
        ClinicalSample(
            id="SMPL-006",
            patient_id="P-106",
            title="ICU Sedation Protocol",
            category="Critical Care",
            raw_note="Patient s/p cardiac CABG. Infusing Morphine 2.5 mg/hr IV continuous. Administered Cefazolin 2g IV Q8H for surgical prophylaxis.",
        ),
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)