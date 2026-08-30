# Helper function simulating your friend's cleaner logic
def simple_cleaner(text):
    # Removes extra spaces and turns text into lowercase
    return " ".join(text.split()).lower()

# Test Case 1: Checking space removal
def test_extra_spaces_removal():
    raw_text = "Tylenol   500mg    BID"
    expected_output = "tylenol 500mg bid"
    assert simple_cleaner(raw_text) == expected_output

# Test Case 2: Checking lowercasing
def test_lowercasing():
    raw_text = "AMOXICILLIN 250MG"
    expected_output = "amoxicillin 250mg"
    assert simple_cleaner(raw_text) == expected_output