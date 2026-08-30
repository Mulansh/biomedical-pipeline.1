"""Unit and edge-case tests for Biomedical Medication and Dosage Entity Extraction."""

import pytest
from src.extractor import (
    extract_all_clinical_data,
    extract_dosage,
    extract_medication_entities,
)


# 1. Standard mg dosage
def test_extract_mg_dosage():
    text = "Patient given Aspirin 500mg daily."
    dosages = extract_dosage(text)
    assert "500mg" in dosages


# 2. Spaced mg dosage (e.g. '500 mg')
def test_extract_spaced_mg_dosage():
    text = "Administered Amoxicillin 250 mg daily."
    dosages = extract_dosage(text)
    assert "250 mg" in dosages


# 3. Grams (g) unit
def test_extract_gram_dosage():
    text = "Infusing Cefazolin 2g IV Q8H."
    dosages = extract_dosage(text)
    assert "2g" in dosages


# 4. Milliliters (ml / mL) unit
def test_extract_ml_dosage():
    text = "Prescribed 10 ml of cough syrup and 500ml saline."
    dosages = extract_dosage(text)
    assert "10 ml" in dosages
    assert "500ml" in dosages


# 5. Micrograms (mcg / µg / ug) unit
def test_extract_mcg_dosage():
    text = "Fentanyl 25 mcg IV and Levothyroxine 100 ug PO."
    dosages = extract_dosage(text)
    assert "25 mcg" in dosages
    assert "100 ug" in dosages


# 6. International Units (IU / units)
def test_extract_iu_and_units():
    text = "Administer Insulin Glargine 20 units SC and Vitamin D 50000 IU weekly."
    dosages = extract_dosage(text)
    assert "20 units" in dosages
    assert "50000 IU" in dosages


# 7. Tablet and capsule counts
def test_extract_tablets_and_capsules():
    text = "Take 2 tablets by mouth with breakfast and 1 cap at bedtime."
    dosages = extract_dosage(text)
    assert "2 tablets" in dosages
    assert "1 cap" in dosages


# 8. Inhalation puffs and topical drops
def test_extract_puffs_and_drops():
    text = "Albuterol 2 puffs inhaled Q4H PRN. Tobramycin 3 drops right eye BID."
    dosages = extract_dosage(text)
    assert "2 puffs" in dosages
    assert "3 drops" in dosages


# 9. Decimal dosage values (e.g. 0.5mg, 2.5ml)
def test_extract_decimal_dosage():
    text = "Ativan 0.5mg SL and Morphine 2.5 mg IV."
    dosages = extract_dosage(text)
    assert "0.5mg" in dosages
    assert "2.5 mg" in dosages


# 10. Fraction dosage values (e.g. 1/2 tab)
def test_extract_fraction_dosage():
    text = "Take 1/2 tab of Metoprolol Tartrate 25mg daily."
    dosages = extract_dosage(text)
    assert "1/2 tab" in dosages
    assert "25mg" in dosages


# 11. Dosage ranges (e.g. 10-20 mg)
def test_extract_range_dosage():
    text = "Prednisone 10-20 mg daily based on symptoms."
    dosages = extract_dosage(text)
    assert "10-20 mg" in dosages


# 12. Rate dosages (e.g. mg/kg/day, ml/hr, mg/day)
def test_extract_rate_dosages():
    text = "Morphine 2.5 mg/hr continuous infusion and Amoxicillin 45 mg/kg/day."
    dosages = extract_dosage(text)
    assert "2.5 mg/hr" in dosages
    assert "45 mg/kg/day" in dosages


# 13. Case insensitivity (MG, Mg, mg, ML, iu)
def test_case_insensitivity():
    text = "TYLENOL 500MG, AMPICILLIN 1G, COUGH SYRUP 10ML."
    dosages = extract_dosage(text)
    assert "500MG" in dosages
    assert "1G" in dosages
    assert "10ML" in dosages


# 14. Multiple distinct dosages in a single clinical note
def test_multiple_dosages_in_note():
    text = "Patient prescribed Metformin 1000mg twice daily, Lisinopril 10mg once daily, and Atorvastatin 40mg at bedtime."
    dosages = extract_dosage(text)
    assert len(dosages) == 3
    assert "1000mg" in dosages
    assert "10mg" in dosages
    assert "40mg" in dosages


# 15. Medication entity drug name resolution
def test_medication_entity_drug_name_resolution():
    text = "Patient was prescribed Tylenol 500mg BID."
    entities = extract_medication_entities(text)
    assert len(entities) == 1
    assert entities[0].medication_name == "Tylenol"
    assert entities[0].raw_dosage == "500mg"
    assert entities[0].dosage_value == 500.0
    assert entities[0].dosage_unit == "mg"


# 16. Frequency (sig) extraction
def test_frequency_extraction():
    text = "Administer Amoxicillin 250mg PO TID for 10 days."
    entities = extract_medication_entities(text)
    assert len(entities) == 1
    assert entities[0].frequency.upper() == "TID"


# 17. Administration route extraction
def test_route_extraction():
    text = "Infuse Morphine 4mg IV push stat."
    entities = extract_medication_entities(text)
    assert len(entities) == 1
    assert entities[0].route.upper() == "IV"


# 18. Duration extraction
def test_duration_extraction():
    text = "Prescribe Prednisone 20mg daily for 5 days."
    entities = extract_medication_entities(text)
    assert len(entities) == 1
    assert "5 days" in entities[0].duration.lower()


# 19. Character offsets (start_char, end_char)
def test_entity_character_offsets():
    text = "Aspirin 81mg daily"
    entities = extract_medication_entities(text)
    assert len(entities) == 1
    assert entities[0].start_char == 8
    assert entities[0].end_char == 12
    assert text[entities[0].start_char:entities[0].end_char] == "81mg"


# 20. Confidence score calculation
def test_confidence_score():
    text = "Patient prescribed Amoxicillin 500mg PO TID for 7 days."
    entities = extract_medication_entities(text)
    assert len(entities) == 1
    assert entities[0].confidence >= 0.90


# 21. Rejection of non-dosage numbers (e.g. year, room number, telephone)
def test_false_positive_rejection():
    text = "Patient seen on 2026-08-30 in room 402 with phone 5551234. No meds given."
    dosages = extract_dosage(text)
    assert len(dosages) == 0


# 22. Empty, whitespace, and None text handling
def test_extractor_empty_inputs():
    assert extract_dosage("") == []
    assert extract_dosage(None) == []
    assert extract_dosage("   ") == []
    assert extract_medication_entities("") == []
    assert extract_medication_entities(None) == []


# 23. Helper function extract_all_clinical_data
def test_extract_all_clinical_data():
    text = "Patient given Lisinopril 20mg daily."
    data = extract_all_clinical_data(text)
    assert data["entity_count"] == 1
    assert len(data["dosages"]) == 1
    assert len(data["medications"]) == 1


# 24. Complex ICU note multi-drug extraction
def test_complex_icu_note_extraction():
    text = "Patient in ICU: Infusing Norepinephrine 4mcg/min and Vancomycin 1g IV Q12H."
    entities = extract_medication_entities(text)
    assert len(entities) >= 2
    raws = [e.raw_dosage for e in entities]
    assert any("4mcg/min" in r or "4 mcg/min" in r for r in raws)
    assert any("1g" in r for r in raws)


# 25. Percentages in clinical infusions
def test_percentage_infusion():
    text = "Administer 1000ml of 0.9% Normal Saline and Dextrose 5% IV."
    dosages = extract_dosage(text)
    assert "1000ml" in dosages
    assert "0.9%" in dosages
    assert "5%" in dosages
