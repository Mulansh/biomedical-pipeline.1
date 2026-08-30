"""FastAPI API endpoint tests using TestClient."""

import pytest
from fastapi.testclient import TestClient


# 1. Test root endpoint
def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "version" in data
    assert "documentation" in data
    assert "endpoints" in data


# 2. Test health check endpoint
def test_health_check_endpoint(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "version" in data
    assert data["engine"] == "Biomedical-NLP-Regex-v2.0"


# 3. Test stats telemetry endpoint
def test_stats_endpoint(client: TestClient):
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "total_records_processed" in data
    assert "average_latency_ms" in data
    assert "active_since" in data


# 4. Test pre-loaded samples endpoint
def test_samples_endpoint(client: TestClient):
    response = client.get("/api/v1/samples")
    assert response.status_code == 200
    samples = response.json()
    assert isinstance(samples, list)
    assert len(samples) >= 4
    first = samples[0]
    assert "id" in first
    assert "patient_id" in first
    assert "raw_note" in first


# 5. Test text cleaning endpoint
def test_clean_endpoint(client: TestClient):
    payload = {
        "text": "   Patient   taking   Tylenol  500mg   BID!!  ",
        "lowercase": True,
        "strip_punctuation_noise": True,
    }
    response = client.post("/api/v1/clean", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["cleaned_text"] == "patient taking tylenol 500mg bid"
    assert data["original_char_count"] > data["cleaned_char_count"]


# 6. Test text cleaning endpoint with empty input
def test_clean_endpoint_empty(client: TestClient):
    response = client.post("/api/v1/clean", json={"text": ""})
    assert response.status_code == 200
    data = response.json()
    assert data["cleaned_text"] == ""


# 7. Test entity extraction endpoint
def test_extract_endpoint(client: TestClient):
    payload = {
        "text": "Administered Amoxicillin 250mg PO TID for 10 days.",
        "clean_first": True,
    }
    response = client.post("/api/v1/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["entity_count"] == 1
    assert len(data["dosages"]) == 1
    assert "250mg" in data["dosages"]
    assert len(data["medications"]) == 1
    assert data["medications"][0]["medication_name"] == "Amoxicillin"


# 8. Test single pipeline endpoint
def test_pipeline_endpoint(client: TestClient):
    payload = {
        "patient_id": "P-201",
        "raw_clinical_log": "pt prescribed Tylenol 500mg BID for 5 days.",
        "metadata": {"dept": "Neurology"},
    }
    response = client.post("/api/v1/pipeline", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "P-201"
    assert data["status"] == "success"
    assert data["entity_count"] == 1
    assert data["processing_time_ms"] > 0
    assert data["metadata"]["dept"] == "Neurology"


# 9. Test batch pipeline endpoint
def test_batch_pipeline_endpoint(client: TestClient):
    payload = {
        "records": [
            {"patient_id": "P-B1", "raw_clinical_log": "Aspirin 81mg daily"},
            {"patient_id": "P-B2", "raw_clinical_log": "Metformin 500mg BID"},
            {"patient_id": "P-B3", "raw_clinical_log": "Lisinopril 10mg daily"},
        ]
    }
    response = client.post("/api/v1/pipeline/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["summary"]["total_records"] == 3
    assert data["summary"]["successful_records"] == 3
    assert data["summary"]["total_medications_found"] == 3
    assert len(data["results"]) == 3


# 10. Test validation error handling on malformed payload (422)
def test_validation_error_handling(client: TestClient):
    # Missing required 'raw_clinical_log' in PipelineRequest
    response = client.post("/api/v1/pipeline", json={"patient_id": "P-INVALID"})
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"
    assert data["error_type"] == "ValidationError"
    assert "details" in data


# 11. Test batch pipeline with empty list triggers validation error (422)
def test_batch_empty_records_validation(client: TestClient):
    response = client.post("/api/v1/pipeline/batch", json={"records": []})
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"


# 12. Test custom response header X-Process-Time-Ms
def test_process_time_header_present(client: TestClient):
    response = client.get("/api/v1/health")
    assert "x-process-time-ms" in response.headers
    val = float(response.headers["x-process-time-ms"])
    assert val >= 0.0


# 13. Test CORS headers presence
def test_cors_headers_present(client: TestClient):
    response = client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:8501", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in ("*", "http://localhost:8501")


# 14. Test OpenAPI JSON schema accessibility
def test_openapi_schema_endpoint(client: TestClient):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "Biomedical NLP & Clinical Text ETL Pipeline"
    assert "/api/v1/pipeline" in data["paths"]


# 15. Test extract endpoint with complex multi-drug text
def test_extract_endpoint_multi_drug(client: TestClient):
    payload = {
        "text": "Pt ordered Metformin 1000mg twice daily and Glipizide 5mg every morning.",
        "clean_first": True,
    }
    response = client.post("/api/v1/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["entity_count"] == 2
    assert len(data["medications"]) == 2
