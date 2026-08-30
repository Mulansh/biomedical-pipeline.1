"""Unit tests for Clinical Text Cleaning and Normalization module."""

import pytest
from src.cleaner import clean_text, sanitize_clinical_text


# Test Case 1: Checking extra whitespace removal
def test_extra_spaces_removal():
    raw_text = "Tylenol   500mg    BID"
    expected_output = "tylenol 500mg bid"
    assert clean_text(raw_text) == expected_output


# Test Case 2: Checking lowercasing
def test_lowercasing():
    raw_text = "AMOXICILLIN 250MG"
    expected_output = "amoxicillin 250mg"
    assert clean_text(raw_text) == expected_output


# Test Case 3: Empty string handling
def test_empty_string():
    assert clean_text("") == ""
    assert clean_text("   ") == ""


# Test Case 4: None input handling
def test_none_input():
    assert clean_text(None) == ""


# Test Case 5: Multiline string with mixed tabs, newlines, and carriage returns
def test_multiline_whitespace_collapse():
    raw_text = "Patient given \n\n Aspirin 81mg \t daily. \r\n Check vitals."
    expected = "patient given aspirin 81mg daily. check vitals."
    assert clean_text(raw_text) == expected


# Test Case 6: Preserving case when lowercase=False
def test_preserve_case_option():
    raw_text = "  Patient given Lisinopril 10mg PO Daily  "
    expected = "Patient given Lisinopril 10mg PO Daily"
    assert clean_text(raw_text, lowercase=False) == expected


# Test Case 7: Stripping redundant punctuation noise
def test_strip_punctuation_noise():
    raw_text = "Patient taking Tylenol 500mg BID... Urgent check needed!!!! ***"
    expected = "patient taking tylenol 500mg bid urgent check needed"
    assert clean_text(raw_text, strip_punctuation_noise=True) == expected


# Test Case 8: Preserving medical decimals and percentages
def test_preserve_decimals_and_percentages():
    raw_text = "Administered 0.5mg Ativan and 0.9% Normal Saline."
    expected = "administered 0.5mg ativan and 0.9% normal saline."
    assert clean_text(raw_text) == expected


# Test Case 9: Microgram symbol normalization (µg / ug -> mcg)
def test_microgram_symbol_normalization():
    raw_text = "Levothyroxine 50µg daily and Fentanyl 25μg patch"
    cleaned = clean_text(raw_text)
    assert "50mcg" in cleaned
    assert "25mcg" in cleaned


# Test Case 10: HTML / XML tag removal from EHR web exports
def test_html_tag_removal():
    raw_text = "<p>Patient prescribed <b>Amoxicillin 500mg</b> TID.</p><br/>"
    expected = "patient prescribed amoxicillin 500mg tid."
    assert clean_text(raw_text) == expected


# Test Case 11: Idempotency (cleaning already cleaned text returns identical string)
def test_cleaner_idempotency():
    raw_text = "metformin 1000mg twice daily with meals."
    cleaned_once = clean_text(raw_text)
    cleaned_twice = clean_text(cleaned_once)
    assert cleaned_once == cleaned_twice


# Test Case 12: Non-string data type coercion
def test_non_string_input_coercion():
    assert clean_text(12345) == "12345"


# Test Case 13: Sanitize clinical text convenience alias
def test_sanitize_clinical_text_alias():
    raw_text = "   Metformin   500mg   BID!! ... No allergies.  "
    res = sanitize_clinical_text(raw_text)
    assert "metformin 500mg bid" in res
    assert "no allergies." in res


# Test Case 14: Complex clinical prescription note with slashes and dashes
def test_complex_clinical_punctuations():
    raw_text = "Patient s/p CABG, start ASA 81mg/day + Plavix 75mg q.d."
    cleaned = clean_text(raw_text)
    assert "81mg/day" in cleaned
    assert "75mg" in cleaned


# Test Case 15: Leading and trailing spaces only
def test_extreme_whitespace_padding():
    raw_text = "\t\t\n   Morphine 2mg IV   \n\t  "
    assert clean_text(raw_text) == "morphine 2mg iv"