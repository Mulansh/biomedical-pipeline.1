"""Pydantic data models and schemas for Biomedical ETL Pipeline."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class MedicationEntity(BaseModel):
    """Structured representation of an extracted medication and dosage entity."""

    medication_name: Optional[str] = Field(
        default=None,
        description="Identified pharmaceutical drug or substance name",
        examples=["Aspirin", "Amoxicillin", "Metformin"],
    )
    raw_dosage: str = Field(
        ...,
        description="Exact raw dosage substring extracted from clinical text",
        examples=["500mg", "10 ml", "250 mg", "0.5 mcg", "1/2 tab"],
    )
    dosage_value: Optional[float] = Field(
        default=None,
        description="Parsed normalized numerical dosage value",
        examples=[500.0, 10.0, 250.0, 0.5],
    )
    dosage_unit: Optional[str] = Field(
        default=None,
        description="Normalized unit of measurement (e.g. mg, g, ml, mcg, iu, tab)",
        examples=["mg", "ml", "g", "mcg", "iu", "tab"],
    )
    route: Optional[str] = Field(
        default=None,
        description="Administration route (e.g. oral, IV, IM, SC, sublingual, topical)",
        examples=["oral", "IV", "intravenous", "PO"],
    )
    frequency: Optional[str] = Field(
        default=None,
        description="Administration frequency or sig (e.g. BID, TID, PRN, once daily)",
        examples=["BID", "once daily", "PRN", "every 8 hours"],
    )
    duration: Optional[str] = Field(
        default=None,
        description="Course duration if specified in context",
        examples=["5 days", "2 weeks", "30 days"],
    )
    start_char: Optional[int] = Field(
        default=None,
        description="Character start index within the processed text",
        examples=[12],
    )
    end_char: Optional[int] = Field(
        default=None,
        description="Character end index within the processed text",
        examples=[17],
    )
    confidence: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score between 0.0 and 1.0",
        examples=[0.95],
    )


class CleanTextRequest(BaseModel):
    """Request payload for text cleaning and sanitization endpoint."""

    text: str = Field(
        ...,
        description="Raw unstructured clinical note or biomedical text log",
        examples=["  Pt   administered  500mg  of   Aspirin   orally  BID!! \n\t "],
    )
    lowercase: bool = Field(
        default=True,
        description="Whether to convert output to lowercase",
    )
    strip_punctuation_noise: bool = Field(
        default=True,
        description="Whether to clean redundant non-clinical punctuation noise",
    )


class CleanTextResponse(BaseModel):
    """Response payload for text cleaning endpoint."""

    original_text: str = Field(..., description="Original input string")
    cleaned_text: str = Field(..., description="Normalized and cleaned clinical text")
    original_char_count: int = Field(..., description="Original text character count")
    cleaned_char_count: int = Field(..., description="Cleaned text character count")
    status: str = Field(default="success", description="Status code")


class ExtractDosageRequest(BaseModel):
    """Request payload for medication and dosage extraction endpoint."""

    text: str = Field(
        ...,
        description="Clinical text from which to extract dosages and medications",
        examples=["Patient prescribed Amoxicillin 250mg PO TID for 10 days."],
    )
    clean_first: bool = Field(
        default=True,
        description="Whether to sanitize the text prior to entity extraction",
    )


class ExtractDosageResponse(BaseModel):
    """Response payload for entity extraction endpoint."""

    text: str = Field(..., description="Processed text input")
    dosages: List[str] = Field(
        default_factory=list,
        description="List of extracted raw dosage strings",
        examples=[["250mg", "10ml"]],
    )
    medications: List[MedicationEntity] = Field(
        default_factory=list,
        description="Detailed structured medication entities",
    )
    entity_count: int = Field(..., description="Total number of dosage entities detected")
    status: str = Field(default="success", description="Extraction status")


class PipelineRequest(BaseModel):
    """Request payload for single-record ETL pipeline processing."""

    patient_id: Optional[str] = Field(
        default=None,
        description="Unique patient or encounter identifier",
        examples=["P-101", "ENC-9082"],
    )
    raw_clinical_log: str = Field(
        ...,
        description="Raw uncleaned clinical note or prescription log",
        examples=["pt presented with severe headache... prescribed Tylenol 500mg BID for 5 days."],
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional metadata key-value pairs (e.g. department, clinician)",
    )

    @field_validator("raw_clinical_log")
    @classmethod
    def validate_not_none(cls, v: str) -> str:
        if v is None:
            raise ValueError("raw_clinical_log must not be None")
        return v


class PipelineResponse(BaseModel):
    """Comprehensive response payload for single-record ETL pipeline."""

    patient_id: Optional[str] = Field(
        default=None,
        description="Patient or record identifier",
    )
    raw_clinical_log: str = Field(..., description="Original raw clinical input")
    cleaned_text: str = Field(..., description="Sanitized and normalized text")
    dosage: List[str] = Field(
        default_factory=list,
        description="List of raw dosage strings (backward-compatible)",
    )
    extracted_dosage: List[str] = Field(
        default_factory=list,
        description="List of raw extracted dosages (backward-compatible)",
    )
    medications: List[MedicationEntity] = Field(
        default_factory=list,
        description="Structured medication entity objects",
    )
    entity_count: int = Field(..., description="Total entities extracted")
    processing_time_ms: float = Field(..., description="ETL pipeline duration in milliseconds")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of processing",
    )
    status: str = Field(default="success", description="Pipeline execution status")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class BatchPipelineRequest(BaseModel):
    """Request payload for batch clinical logs ETL processing."""

    records: List[PipelineRequest] = Field(
        ...,
        min_length=1,
        description="List of clinical logs to process in batch",
    )


class BatchSummary(BaseModel):
    """Aggregate statistics for batch ETL processing."""

    total_records: int = Field(..., description="Total logs processed")
    successful_records: int = Field(..., description="Successfully processed count")
    failed_records: int = Field(..., description="Failed record count")
    total_medications_found: int = Field(..., description="Sum of medication entities extracted")
    unique_drugs: List[str] = Field(
        default_factory=list,
        description="List of unique drug names discovered in batch",
    )
    total_processing_time_ms: float = Field(
        ..., description="Total batch duration in milliseconds"
    )
    avg_processing_time_ms: float = Field(
        ..., description="Average processing duration per record"
    )


class BatchPipelineResponse(BaseModel):
    """Response payload for batch ETL pipeline processing."""

    summary: BatchSummary = Field(..., description="Batch execution summary")
    results: List[PipelineResponse] = Field(
        ..., description="List of individual record pipeline results"
    )
    status: str = Field(default="success", description="Overall batch status")


class HealthCheckResponse(BaseModel):
    """System health check and diagnostic information."""

    status: str = Field(default="healthy", description="Service health state")
    version: str = Field(..., description="Application version")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Current server UTC timestamp",
    )
    engine: str = Field(default="Biomedical-NLP-Regex-v2.0", description="Extraction engine identifier")


class PipelineStatsResponse(BaseModel):
    """Live telemetry and execution metrics for API."""

    total_requests: int = Field(..., description="Total requests served")
    total_records_processed: int = Field(..., description="Total clinical notes parsed")
    total_entities_extracted: int = Field(..., description="Total entities found")
    average_latency_ms: float = Field(..., description="Average request latency in ms")
    active_since: str = Field(..., description="Service startup timestamp")


class ClinicalSample(BaseModel):
    """Pre-loaded sample clinical note for testing."""

    id: str
    patient_id: str
    title: str
    category: str
    raw_note: str
