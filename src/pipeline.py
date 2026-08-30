"""Biomedical ETL Pipeline Engine for Clinical Notes & Prescription Logs."""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from src.cleaner import clean_text
from src.extractor import extract_dosage, extract_medication_entities
from src.logger import logger
from src.models import (
    BatchPipelineRequest,
    BatchPipelineResponse,
    BatchSummary,
    MedicationEntity,
    PipelineRequest,
    PipelineResponse,
)


class BiomedicalETLPipeline:
    """Enterprise ETL Pipeline for ingestion, cleaning, extraction, and structuring of clinical text."""

    def __init__(self, name: str = "Biomedical-ETL-Core-v2"):
        self.name = name
        self.total_processed: int = 0
        self.total_entities_extracted: int = 0
        self.total_processing_time_ms: float = 0.0
        logger.info(f"Initialized {self.name}")

    def process_record(
        self,
        raw_clinical_log: str,
        patient_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PipelineResponse:
        """Execute single-record ETL pipeline lifecycle."""
        start_time = time.perf_counter()

        if raw_clinical_log is None or not isinstance(raw_clinical_log, str):
            raw_clinical_log = ""

        # Step 1: Clean & Normalize
        cleaned = clean_text(raw_clinical_log)

        # Step 2: Extract Entities & Dosages
        raw_dosages = extract_dosage(cleaned)
        # Also check raw text to guarantee extraction across formats
        if not raw_dosages and raw_clinical_log:
            raw_dosages = extract_dosage(raw_clinical_log)

        medication_entities = extract_medication_entities(raw_clinical_log if raw_clinical_log else cleaned)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

        # Update telemetry
        self.total_processed += 1
        self.total_entities_extracted += len(medication_entities)
        self.total_processing_time_ms += elapsed_ms

        response = PipelineResponse(
            patient_id=patient_id,
            raw_clinical_log=raw_clinical_log,
            cleaned_text=cleaned,
            dosage=raw_dosages,
            extracted_dosage=raw_dosages,
            medications=medication_entities,
            entity_count=len(medication_entities),
            processing_time_ms=elapsed_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="success",
            metadata=metadata or {},
        )
        return response

    def process_batch(
        self,
        batch_request: Union[BatchPipelineRequest, List[PipelineRequest], List[Dict[str, Any]]],
    ) -> BatchPipelineResponse:
        """Execute batch ETL processing across multiple clinical records."""
        start_time = time.perf_counter()
        records: List[PipelineRequest] = []

        if isinstance(batch_request, BatchPipelineRequest):
            records = batch_request.records
        elif isinstance(batch_request, list):
            for item in batch_request:
                if isinstance(item, PipelineRequest):
                    records.append(item)
                elif isinstance(item, dict):
                    records.append(
                        PipelineRequest(
                            patient_id=item.get("patient_id"),
                            raw_clinical_log=item.get("raw_clinical_log") or item.get("raw_note") or "",
                            metadata=item.get("metadata", {}),
                        )
                    )

        results: List[PipelineResponse] = []
        successful = 0
        failed = 0
        total_meds = 0
        unique_drugs_set = set()

        for rec in records:
            try:
                res = self.process_record(
                    raw_clinical_log=rec.raw_clinical_log,
                    patient_id=rec.patient_id,
                    metadata=rec.metadata,
                )
                results.append(res)
                successful += 1
                total_meds += res.entity_count
                for med in res.medications:
                    if med.medication_name:
                        unique_drugs_set.add(med.medication_name)
            except Exception as e:
                logger.error(f"Error processing record patient_id={rec.patient_id}: {e}")
                failed += 1

        total_batch_ms = round((time.perf_counter() - start_time) * 1000, 3)
        avg_ms = round(total_batch_ms / len(records), 3) if records else 0.0

        summary = BatchSummary(
            total_records=len(records),
            successful_records=successful,
            failed_records=failed,
            total_medications_found=total_meds,
            unique_drugs=sorted(list(unique_drugs_set)),
            total_processing_time_ms=total_batch_ms,
            avg_processing_time_ms=avg_ms,
        )

        return BatchPipelineResponse(
            summary=summary,
            results=results,
            status="success" if failed == 0 else "partial_success",
        )


# Global shared pipeline instance
default_pipeline = BiomedicalETLPipeline()


def run_etl_pipeline(raw_clinical_log: Optional[str], patient_id: Optional[str] = None) -> Dict[str, Any]:
    """Execute standard ETL pipeline on raw clinical text (backward-compatible API).

    Args:
        raw_clinical_log: Raw clinical text input.
        patient_id: Optional patient or record identifier.

    Returns:
        Structured dictionary matching pipeline response format.
    """
    if not raw_clinical_log:
        return {}

    response = default_pipeline.process_record(raw_clinical_log, patient_id=patient_id)
    return response.model_dump()


def run_batch_pipeline(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute batch ETL pipeline across a list of raw clinical log dictionaries.

    Args:
        records: List of dictionaries with 'raw_clinical_log' or 'raw_note'.

    Returns:
        Structured batch response dictionary.
    """
    batch_response = default_pipeline.process_batch(records)
    return batch_response.model_dump()


if __name__ == "__main__":
    sample_log = "   PATIENT  was   administered   500mg   of   Paracetamol  and  10 ml   of  Syrup.   "
    result = run_etl_pipeline(sample_log, patient_id="P-001")
    print("--- Structured Pipeline Output ---")
    for key, value in result.items():
        print(f"{key}: {value}")