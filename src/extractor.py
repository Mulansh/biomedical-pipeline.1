import re
def extract_dosage(text):
    """"find dosage in text"""
    if not text:
        return []
    dosage_pattern = r'(\d+\s*(?:mg|g|ml|mcg))'
    matches = re.findall(dosage_pattern, text,re.IGNORECASE)
    return matches
if __name__ == "__main__":
    test_text = "patient took 500mg of aspirin and 10 ml of cough syrup."
    print("Found dosages:", extract_dosage(test_text))