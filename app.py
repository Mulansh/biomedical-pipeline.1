import streamlit as st

# 1. Title of the web application
st.title("Biomedical NLP & Clinical Text Parser")
st.write("Paste messy clinical notes below to extract structured medication details.")

# 2. Text input box for user to paste clinical notes
user_input = st.text_area("Raw Clinical Note:", placeholder="e.g., Patient given Aspirin 81mg daily...")

# 3. Action button
if st.button("Extract Data"):
    if user_input:
        st.subheader("Results:")
        # For now, display the raw input back to verify the UI works.
        # Later, we will send this text to your friend's backend parser!
        st.json({
            "status": "Success",
            "original_text": user_input,
            "extracted_medications": [
                {"name": "Sample Medication", "dosage": "Sample Dose"}
            ]
        })
    else:
        st.warning("Please enter some text first!")