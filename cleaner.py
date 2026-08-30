import re
def clean_text(text):
     if not text:
         return ''
     text = re.sub(r'\s+', ' ', text.strip().lower())
     return text


if __name__ == "__main__":
    # Let's test a messy medical string
    raw_sample = "  Patient   took   500mg  of   Aspirin. \n\t Check dosage daily.   "

    print("Original Text:")
    print(repr(raw_sample))

    cleaned_result = clean_text(raw_sample)
    print("\nCleaned Text:")
    print(repr(cleaned_result))
