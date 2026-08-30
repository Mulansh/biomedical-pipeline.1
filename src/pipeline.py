from cleaner import clean_text
from src.extractor import extract_dosage
def run_etl_pipeline(raw_clinical_log):
    if not raw_clinical_log:
        return{}
    cleaned_text = clean_text(raw_clinical_log)
    dosage = extract_dosage(cleaned_text)
    structured_output = {
        "raw_clinical_log": raw_clinical_log,
        "dosage": dosage,
        "extracted_dosage": extract_dosage(raw_clinical_log),
        "status": "success"
    }
    return structured_output


if __name__ == "__main__":
    sample_log = "   PATIENT  was   administered   500mg   of   Paracetamol  and  10 ml   of  Syrup.   "

    result = run_etl_pipeline(sample_log)
    print("--- Structured Pipeline Output ---")
    for key, value in result.items():
        print(f"{key}: {value}")