"""Integration tests for Biomedical ETL Pipeline Engine."""

import pytest
from src.models import BatchPipelineRequest, PipelineRequest, PipelineResponse
from src.pipeline import BiomedicalETLPipeline, run_batch_pipeline, run_etl_pipeline


# 1. Single record ETL pipeline execution
def test_single_record_pipeline(fresh_pipeline):
    raw_log = "   PATIENT  was   administered   500mg   of   Paracetamol  and  10 ml   of  Syrup.   "
    response = fresh_pipeline.process_record(raw_log, patient_id="P-101")

    assert isinstance(response, PipelineResponse)
    assert response.patient_id == "P-101"
    assert response.status == "success"
    assert "paracetamol" in response.cleaned_text
    assert len(response.dosage) >= 2
    assert response.processing_time_ms > 0
    assert response.timestamp is not None


# 2. Backward compatibility of run_etl_pipeline functional API
def test_run_etl_pipeline_backward_compatibility():
    raw_log = "Patient given Aspirin 81mg daily."
    result = run_etl_pipeline(raw_log, patient_id="P-LEGACY")

    assert isinstance(result, dict)
    assert result["patient_id"] == "P-LEGACY"
    assert result["status"] == "success"
    assert "dosage" in result
    assert "extracted_dosage" in result
    assert "cleaned_text" in result
    assert "medications" in result


# 3. Empty input handling
def test_pipeline_empty_input(fresh_pipeline):
    res_empty_func = run_etl_pipeline("")
    assert res_empty_func == {}

    res_none_func = run_etl_pipeline(None)
    assert res_none_func == {}

    res_empty_obj = fresh_pipeline.process_record("")
    assert res_empty_obj.entity_count == 0
    assert res_empty_obj.cleaned_text == ""


# 4. Metadata preservation
def test_pipeline_metadata_preservation(fresh_pipeline):
    metadata = {"hospital": "General Hospital", "doctor": "Dr. Smith", "ward": "ICU-3"}
    res = fresh_pipeline.process_record("Tylenol 500mg BID", patient_id="P-META", metadata=metadata)
    assert res.metadata["hospital"] == "General Hospital"
    assert res.metadata["doctor"] == "Dr. Smith"
    assert res.metadata["ward"] == "ICU-3"


# 5. Batch pipeline execution with Pydantic request
def test_batch_pipeline_pydantic_request(fresh_pipeline):
    records = [
        PipelineRequest(patient_id="P-01", raw_clinical_log="Tylenol 500mg PO BID"),
        PipelineRequest(patient_id="P-02", raw_clinical_log="Amoxicillin 250mg TID"),
        PipelineRequest(patient_id="P-03", raw_clinical_log="Metformin 1000mg daily"),
    ]
    batch_req = BatchPipelineRequest(records=records)
    batch_resp = fresh_pipeline.process_batch(batch_req)

    assert batch_resp.status == "success"
    assert batch_resp.summary.total_records == 3
    assert batch_resp.summary.successful_records == 3
    assert batch_resp.summary.failed_records == 0
    assert batch_resp.summary.total_medications_found == 3
    assert len(batch_resp.results) == 3


# 6. Batch pipeline execution with raw dict list
def test_batch_pipeline_dict_input(fresh_pipeline):
    dict_records = [
        {"patient_id": "P-D1", "raw_clinical_log": "Aspirin 81mg PO daily"},
        {"patient_id": "P-D2", "raw_note": "Lisinopril 10mg daily"},
    ]
    batch_resp = fresh_pipeline.process_batch(dict_records)
    assert batch_resp.summary.total_records == 2
    assert batch_resp.summary.successful_records == 2


# 7. Functional run_batch_pipeline helper
def test_run_batch_pipeline_helper():
    dict_records = [
        {"patient_id": "P-H1", "raw_clinical_log": "Morphine 2mg IV"},
        {"patient_id": "P-H2", "raw_clinical_log": "Atorvastatin 20mg PO"},
    ]
    res_dict = run_batch_pipeline(dict_records)
    assert isinstance(res_dict, dict)
    assert res_dict["summary"]["total_records"] == 2
    assert res_dict["status"] == "success"


# 8. Unique drug aggregation in batch summary
def test_batch_unique_drug_aggregation(fresh_pipeline):
    records = [
        PipelineRequest(patient_id="P-U1", raw_clinical_log="Tylenol 500mg BID"),
        PipelineRequest(patient_id="P-U2", raw_clinical_log="Tylenol 1000mg BID"),
        PipelineRequest(patient_id="P-U3", raw_clinical_log="Aspirin 81mg daily"),
    ]
    batch_resp = fresh_pipeline.process_batch(BatchPipelineRequest(records=records))
    unique_drugs = batch_resp.summary.unique_drugs
    assert "Tylenol" in unique_drugs
    assert "Aspirin" in unique_drugs
    # Verify deduplication
    assert len(unique_drugs) == 2


# 9. Pipeline instance internal telemetry tracking
def test_pipeline_telemetry_counters(fresh_pipeline):
    initial_processed = fresh_pipeline.total_processed
    fresh_pipeline.process_record("Tylenol 500mg BID")
    fresh_pipeline.process_record("Amoxicillin 250mg PO")

    assert fresh_pipeline.total_processed == initial_processed + 2
    assert fresh_pipeline.total_entities_extracted >= 2
    assert fresh_pipeline.total_processing_time_ms > 0


# 10. Large multiline clinical note pipeline execution
def test_pipeline_large_clinical_note(fresh_pipeline):
    large_note = """
    CHIEF COMPLAINT: Follow up for chronic hypertension and diabetes mellitus type 2.
    HISTORY OF PRESENT ILLNESS: Patient is a 58-year-old male presenting for routine check.
    CURRENT MEDICATIONS:
    1. Metformin 1000mg PO twice daily with meals.
    2. Lisinopril 20mg PO once daily in the morning.
    3. Atorvastatin 40mg PO at bedtime.
    4. Aspirin 81mg PO daily.
    ASSESSMENT & PLAN: Blood pressure controlled. Continue current medication regimen.
    """
    res = fresh_pipeline.process_record(large_note, patient_id="P-LARGE")
    assert res.entity_count >= 4
    assert res.status == "success"


# 11. Structured MedicationEntity values validation
def test_medication_entity_values_accuracy(fresh_pipeline):
    res = fresh_pipeline.process_record("Administered Albuterol 2.5mg inhalation Q4H PRN.")
    assert len(res.medications) >= 1
    med = res.medications[0]
    assert med.raw_dosage == "2.5mg"
    assert med.dosage_value == 2.5
    assert med.dosage_unit == "mg"
    assert med.medication_name == "Albuterol"


# 12. Pydantic model serialization idempotency
def test_pydantic_serialization(fresh_pipeline):
    res = fresh_pipeline.process_record("Prednisone 20mg daily for 5 days.", patient_id="P-SER")
    dumped = res.model_dump()
    reconstructed = PipelineResponse(**dumped)
    assert reconstructed.patient_id == res.patient_id
    assert reconstructed.entity_count == res.entity_count
    assert len(reconstructed.medications) == len(res.medications)
