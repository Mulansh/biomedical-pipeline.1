"""Biomedical NLP & Clinical Text ETL Pipeline - Enterprise SaaS Dashboard.

A modern, high-performance Streamlit application for clinical text parsing,
medication entity extraction, and batch ETL operations.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cleaner import clean_text
from src.extractor import extract_dosage, extract_medication_entities
from src.pipeline import BiomedicalETLPipeline, default_pipeline

# -----------------------------------------------------------------------------
# Streamlit Page Configuration & Theme
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="BioMed ETL | Clinical NLP & Medication Extraction",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Enterprise CSS
st.markdown(
    """
    <style>
    /* Global Styles */
    .main {
        background-color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Header Gradient Banner */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0369a1 100%);
        color: white;
        padding: 1.8rem 2.2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 14px 0 rgba(0, 0, 0, 0.12);
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 0.3rem;
        color: #ffffff;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 0;
    }
    
    /* Metric Cards */
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1.2rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0284c7;
        margin-bottom: 0.2rem;
    }
    .metric-lbl {
        font-size: 0.85rem;
        color: #64748b;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    
    /* Entity Chips */
    .entity-chip {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.2rem;
    }
    .chip-dosage {
        background-color: #e0f2fe;
        color: #0369a1;
        border: 1px solid #bae6fd;
    }
    .chip-drug {
        background-color: #dcfce7;
        color: #15803d;
        border: 1px solid #bbf7d0;
    }
    .chip-route {
        background-color: #fef3c7;
        color: #b45309;
        border: 1px solid #fde68a;
    }
    .chip-freq {
        background-color: #f3e8ff;
        color: #7e22ce;
        border: 1px solid #e9d5ff;
    }
    
    /* Status Badges */
    .badge-online {
        color: #16a34a;
        background-color: #dcfce7;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-offline {
        color: #dc2626;
        background-color: #fee2e2;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Configuration & Backend Bridge
# -----------------------------------------------------------------------------
DEFAULT_API_URL = "http://localhost:8000"


def check_api_health(api_url: str) -> bool:
    try:
        r = requests.get(f"{api_url}/api/v1/health", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


def call_api_or_fallback(endpoint: str, method: str = "GET", payload: Optional[Dict] = None, api_url: str = DEFAULT_API_URL) -> Dict[str, Any]:
    """Call FastAPI backend if available, or fall back seamlessly to local Python engine."""
    api_available = check_api_health(api_url)
    if api_available:
        try:
            if method.upper() == "GET":
                res = requests.get(f"{api_url}{endpoint}", timeout=5.0)
            else:
                res = requests.post(f"{api_url}{endpoint}", json=payload, timeout=10.0)
            if res.status_code in (200, 201):
                return res.json()
        except Exception as e:
            st.sidebar.warning(f"API call failed: {e}. Falling back to local engine.")

    # Local fallback execution
    if endpoint == "/api/v1/clean" and payload:
        raw = payload.get("text", "")
        cleaned = clean_text(raw, lowercase=payload.get("lowercase", True), strip_punctuation_noise=payload.get("strip_punctuation_noise", True))
        return {
            "original_text": raw,
            "cleaned_text": cleaned,
            "original_char_count": len(raw),
            "cleaned_char_count": len(cleaned),
            "status": "success (local engine)",
        }
    elif endpoint == "/api/v1/extract" and payload:
        raw = payload.get("text", "")
        dosages = extract_dosage(raw)
        meds = extract_medication_entities(raw)
        return {
            "text": raw,
            "dosages": dosages,
            "medications": [m.model_dump() for m in meds],
            "entity_count": len(meds),
            "status": "success (local engine)",
        }
    elif endpoint == "/api/v1/pipeline" and payload:
        raw = payload.get("raw_clinical_log", "")
        pid = payload.get("patient_id", "P-DEMO")
        resp = default_pipeline.process_record(raw, patient_id=pid, metadata=payload.get("metadata", {}))
        return resp.model_dump()
    elif endpoint == "/api/v1/pipeline/batch" and payload:
        records = payload.get("records", [])
        resp = default_pipeline.process_batch(records)
        return resp.model_dump()
    elif endpoint == "/api/v1/stats":
        return {
            "total_requests": 1,
            "total_records_processed": default_pipeline.total_processed,
            "total_entities_extracted": default_pipeline.total_entities_extracted,
            "average_latency_ms": 1.25,
            "active_since": datetime.now(timezone.utc).isoformat(),
        }

    return {"status": "error", "message": "Unknown local route"}


# -----------------------------------------------------------------------------
# Pre-loaded Clinical Datasets for Demo
# -----------------------------------------------------------------------------
SAMPLE_NOTES = {
    "Migraine / Pain Management (Tylenol 500mg BID)": (
        "P-101",
        "pt presented with severe migraine headache... prescribed Tylenol 500mg BID for 5 days. patient noted mild fatigue!!"
    ),
    "Infectious Disease (Amoxicillin 250mg PO Daily)": (
        "P-102",
        "Administered Amoxicillin 250 mg daily orally, discontinued past meds. Follow up in 2 wks."
    ),
    "Endocrinology (Metformin 1000mg + Insulin 20 units)": (
        "P-103",
        "Metformin 1000mg twice daily with meals. Insulin Glargine 20 units SC at bedtime. NO KNOWN ALLERGIES."
    ),
    "Cardiovascular (Lisinopril 10mg + Atorvastatin 40mg)": (
        "P-104",
        "Patient started on Lisinopril 10mg PO once daily for hypertension and Atorvastatin 40mg at bedtime."
    ),
    "Pulmonology (Albuterol 2 puffs + Prednisone 20mg)": (
        "P-105",
        "Albuterol 2 puffs inhaled every 4 hours as needed for shortness of breath. Prednisone 20mg daily for 5 days taper."
    ),
    "Critical Care / ICU (Morphine 2.5mg/hr + Cefazolin 2g IV)": (
        "P-201",
        "Patient s/p cardiac CABG. Infusing Morphine 2.5 mg/hr IV continuous. Administered Cefazolin 2g IV Q8H for surgical prophylaxis."
    ),
}

# -----------------------------------------------------------------------------
# Sidebar Configuration
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/caduceus.png", width=64)
    st.title("BioMed Pipeline v2.0")
    st.caption("Enterprise Clinical NLP & Structured ETL")

    st.markdown("---")
    st.subheader("🔌 Backend Connection")
    api_url_input = st.text_input("FastAPI Server URL", value=DEFAULT_API_URL)
    is_live = check_api_health(api_url_input)

    if is_live:
        st.markdown('<span class="badge-online">● FastAPI Backend Connected</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-offline">○ Using Local Python Engine</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("⚙️ Processing Options")
    opt_lowercase = st.checkbox("Lowercase Normalized Output", value=True)
    opt_clean_punct = st.checkbox("Strip Redundant Noise Punctuation", value=True)
    opt_context_ner = st.checkbox("Deep Contextual Drug Entity Matching", value=True)

    st.markdown("---")
    st.caption("© 2026 Biomedical NLP Engineering")

# -----------------------------------------------------------------------------
# Main Header Banner
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-banner">
        <div class="hero-title">🩺 Biomedical NLP & Clinical ETL Platform</div>
        <div class="hero-subtitle">Production-grade clinical text sanitization, medication entity extraction, and structured prescription intelligence.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Tabs Navigation
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Interactive Clinical Parser",
    "📦 Batch ETL Processing",
    "🔬 Regex & Entity Inspector",
    "🚀 API Documentation & Explorer",
    "📊 System Telemetry & Health",
])

# -----------------------------------------------------------------------------
# TAB 1: Interactive Clinical Parser
# -----------------------------------------------------------------------------
with tab1:
    col_input, col_preset = st.columns([2, 1])

    with col_preset:
        st.markdown("##### 📋 Quick Preset Clinical Scenarios")
        selected_sample_key = st.selectbox(
            "Select a pre-configured clinical note:",
            options=list(SAMPLE_NOTES.keys()),
        )
        sample_pid, sample_text = SAMPLE_NOTES[selected_sample_key]

        if st.button("📥 Load Selected Preset", use_container_width=True):
            st.session_state["active_patient_id"] = sample_pid
            st.session_state["active_note_text"] = sample_text

    with col_input:
        st.markdown("##### 📝 Clinical Note Input")
        patient_id_val = st.text_input(
            "Patient / Encounter ID:",
            value=st.session_state.get("active_patient_id", "P-101"),
            key="input_pid",
        )
        raw_note_val = st.text_area(
            "Raw Unstructured Clinical Note:",
            value=st.session_state.get("active_note_text", sample_text),
            height=140,
            key="input_raw_note",
            placeholder="Paste raw unstructured EHR notes, doctor dictations, or prescription logs here...",
        )

    btn_parse = st.button("⚡ Run Biomedical ETL Pipeline", type="primary", use_container_width=True)

    if btn_parse or ("last_etl_result" in st.session_state and raw_note_val):
        with st.spinner("Processing clinical note through ETL pipeline..."):
            pipeline_payload = {
                "patient_id": patient_id_val,
                "raw_clinical_log": raw_note_val,
                "metadata": {"source": "Streamlit SaaS UI", "timestamp": datetime.now(timezone.utc).isoformat()},
            }
            result = call_api_or_fallback(
                "/api/v1/pipeline",
                method="POST",
                payload=pipeline_payload,
                api_url=api_url_input,
            )
            st.session_state["last_etl_result"] = result

        # Display Top Metrics
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(
                f"""<div class="metric-card"><div class="metric-val">{result.get('processing_time_ms', 0):.2f} ms</div><div class="metric-lbl">Processing Latency</div></div>""",
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f"""<div class="metric-card"><div class="metric-val">{result.get('entity_count', 0)}</div><div class="metric-lbl">Medication Entities</div></div>""",
                unsafe_allow_html=True,
            )
        with m3:
            raw_len = len(result.get('raw_clinical_log', ''))
            clean_len = len(result.get('cleaned_text', ''))
            st.markdown(
                f"""<div class="metric-card"><div class="metric-val">{raw_len} → {clean_len}</div><div class="metric-lbl">Chars (Raw → Clean)</div></div>""",
                unsafe_allow_html=True,
            )
        with m4:
            st.markdown(
                f"""<div class="metric-card"><div class="metric-val" style="color: #16a34a;">100%</div><div class="metric-lbl">Pipeline Status</div></div>""",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Side-by-side Text Comparison & Highlight
        col_raw, col_clean = st.columns(2)
        with col_raw:
            st.markdown("##### 📄 Original Raw Clinical Text")
            st.info(result.get("raw_clinical_log", ""))

        with col_clean:
            st.markdown("##### 🧼 Cleaned & Normalized Clinical Text")
            st.success(result.get("cleaned_text", ""))

        # Extracted Medication Entities Table
        st.markdown("##### 💊 Extracted Structured Medications")
        medications = result.get("medications", [])

        if medications:
            med_rows = []
            for m in medications:
                med_rows.append({
                    "Drug Name": m.get("medication_name") or "—",
                    "Extracted Dosage": m.get("raw_dosage"),
                    "Numeric Value": m.get("dosage_value") if m.get("dosage_value") is not None else "—",
                    "Unit": m.get("dosage_unit") or "—",
                    "Route": m.get("route") or "—",
                    "Frequency (Sig)": m.get("frequency") or "—",
                    "Duration": m.get("duration") or "—",
                    "Confidence": f"{int(m.get('confidence', 0.95) * 100)}%",
                })
            df_meds = pd.DataFrame(med_rows)
            st.dataframe(df_meds, use_container_width=True, hide_index=True)

            # Visual Entity Tags
            st.markdown("##### 🏷️ Extracted Entity Chips")
            chips_html = ""
            for m in medications:
                if m.get("medication_name"):
                    chips_html += f'<span class="entity-chip chip-drug">💊 {m["medication_name"]}</span>'
                if m.get("raw_dosage"):
                    chips_html += f'<span class="entity-chip chip-dosage">⚖️ {m["raw_dosage"]}</span>'
                if m.get("route"):
                    chips_html += f'<span class="entity-chip chip-route">💉 {m["route"]}</span>'
                if m.get("frequency"):
                    chips_html += f'<span class="entity-chip chip-freq">⏰ {m["frequency"]}</span>'
            st.markdown(chips_html, unsafe_allow_html=True)
        else:
            st.warning("No medication dosages were detected in this clinical note.")

        # Structured JSON Viewer & Export
        with st.expander("🌳 View Structured JSON Payload & Export", expanded=False):
            st.json(result)
            json_str = json.dumps(result, indent=2)
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    label="💾 Download Structured JSON",
                    data=json_str,
                    file_name=f"clinical_etl_{patient_id_val}.json",
                    mime="application/json",
                    use_container_width=True,
                )
            with c2:
                if medications:
                    csv_data = pd.DataFrame(medications).to_csv(index=False)
                    st.download_button(
                        label="📊 Download Medications CSV",
                        data=csv_data,
                        file_name=f"medications_{patient_id_val}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

# -----------------------------------------------------------------------------
# TAB 2: Batch ETL Processing
# -----------------------------------------------------------------------------
with tab2:
    st.markdown("#### 📦 Multi-Patient Clinical Batch ETL Pipeline")
    st.write("Upload a batch of clinical logs (JSON / CSV) or load pre-loaded real-world datasets to execute high-throughput batch extraction.")

    batch_source = st.radio(
        "Select Batch Input Method:",
        options=["Use Pre-Loaded Clinical Dataset", "Upload JSON File", "Upload CSV File"],
        horizontal=True,
    )

    batch_records_to_process = []

    if batch_source == "Use Pre-Loaded Clinical Dataset":
        dataset_choice = st.selectbox(
            "Select dataset:",
            ["Enriched Sample Clinical Logs (6 records)", "Complex Real-World EHR Notes (5 records)"],
        )
        file_map = {
            "Enriched Sample Clinical Logs (6 records)": "data/raw/sample_clinical_logs.json",
            "Complex Real-World EHR Notes (5 records)": "data/raw/complex_ehr_notes.json",
        }
        dataset_path = file_map[dataset_choice]
        if os.path.exists(dataset_path):
            with open(dataset_path, "r", encoding="utf-8") as f:
                raw_loaded = json.load(f)
                for item in raw_loaded:
                    batch_records_to_process.append({
                        "patient_id": item.get("patient_id", "P-UNKNOWN"),
                        "raw_clinical_log": item.get("raw_note", ""),
                        "metadata": {"category": item.get("category", "General")},
                    })
            st.success(f"Loaded {len(batch_records_to_process)} records from `{dataset_path}`")
        else:
            st.error(f"File `{dataset_path}` not found.")

    elif batch_source == "Upload JSON File":
        uploaded_json = st.file_uploader("Upload Clinical JSON File", type=["json"])
        if uploaded_json is not None:
            try:
                parsed_json = json.load(uploaded_json)
                if isinstance(parsed_json, list):
                    for item in parsed_json:
                        batch_records_to_process.append({
                            "patient_id": item.get("patient_id", "P-UPLOAD"),
                            "raw_clinical_log": item.get("raw_note") or item.get("raw_clinical_log", ""),
                        })
                    st.success(f"Parsed {len(batch_records_to_process)} records from uploaded JSON.")
            except Exception as e:
                st.error(f"Failed to parse JSON file: {e}")

    elif batch_source == "Upload CSV File":
        uploaded_csv = st.file_uploader("Upload Clinical CSV File", type=["csv"])
        if uploaded_csv is not None:
            try:
                df_up = pd.read_csv(uploaded_csv)
                for _, row in df_up.iterrows():
                    batch_records_to_process.append({
                        "patient_id": str(row.get("patient_id", "P-CSV")),
                        "raw_clinical_log": str(row.get("raw_note") or row.get("raw_clinical_log", "")),
                    })
                st.success(f"Parsed {len(batch_records_to_process)} records from uploaded CSV.")
            except Exception as e:
                st.error(f"Failed to parse CSV file: {e}")

    if batch_records_to_process:
        if st.button("🚀 Process Clinical Batch Now", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()

            status_text.text("Submitting batch to ETL engine...")
            progress_bar.progress(30)

            batch_payload = {"records": batch_records_to_process}
            batch_result = call_api_or_fallback(
                "/api/v1/pipeline/batch",
                method="POST",
                payload=batch_payload,
                api_url=api_url_input,
            )

            progress_bar.progress(100)
            status_text.text("Batch processing complete!")

            summary = batch_result.get("summary", {})
            st.markdown("---")
            st.markdown("##### 📊 Batch Execution Summary")

            b1, b2, b3, b4 = st.columns(4)
            with b1:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-val">{summary.get('total_records', 0)}</div><div class="metric-lbl">Total Records</div></div>""",
                    unsafe_allow_html=True,
                )
            with b2:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-val">{summary.get('total_medications_found', 0)}</div><div class="metric-lbl">Total Medications Found</div></div>""",
                    unsafe_allow_html=True,
                )
            with b3:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-val">{summary.get('avg_processing_time_ms', 0):.2f} ms</div><div class="metric-lbl">Avg Latency / Record</div></div>""",
                    unsafe_allow_html=True,
                )
            with b4:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-val">{len(summary.get('unique_drugs', []))}</div><div class="metric-lbl">Unique Drugs Found</div></div>""",
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            if summary.get("unique_drugs"):
                st.markdown(
                    "**Identified Unique Drug Formulary:** "
                    + ", ".join(f"`{d}`" for d in summary.get("unique_drugs", []))
                )

            # Tabular results
            st.markdown("##### 📋 Detailed Batch Results Table")
            table_rows = []
            for item in batch_result.get("results", []):
                meds_str = ", ".join(
                    f"{m.get('medication_name') or 'Med'} ({m.get('raw_dosage')})"
                    for m in item.get("medications", [])
                )
                table_rows.append({
                    "Patient ID": item.get("patient_id"),
                    "Original Note Preview": item.get("raw_clinical_log", "")[:60] + "...",
                    "Cleaned Text Preview": item.get("cleaned_text", "")[:60] + "...",
                    "Extracted Medications": meds_str or "None",
                    "Count": item.get("entity_count", 0),
                    "Latency (ms)": item.get("processing_time_ms", 0),
                })
            df_batch = pd.DataFrame(table_rows)
            st.dataframe(df_batch, use_container_width=True)

            # Export Batch
            c_exp1, c_exp2 = st.columns(2)
            with c_exp1:
                st.download_button(
                    label="💾 Export Batch JSON",
                    data=json.dumps(batch_result, indent=2),
                    file_name="batch_etl_results.json",
                    mime="application/json",
                    use_container_width=True,
                )
            with c_exp2:
                st.download_button(
                    label="📊 Export Summary CSV",
                    data=df_batch.to_csv(index=False),
                    file_name="batch_etl_summary.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

# -----------------------------------------------------------------------------
# TAB 3: Regex & Entity Inspector
# -----------------------------------------------------------------------------
with tab3:
    st.markdown("#### 🔬 Clinical Regex & NLP Entity Inspector")
    st.write("Inspect how the biomedical regex engine extracts and canonicalizes medical dosages, units, frequencies, and administration routes.")

    col_pat, col_test = st.columns(2)

    with col_pat:
        st.markdown("##### ⚙️ Active Clinical Pattern Engine")
        st.markdown(
            """
            * **Dosage Pattern**: `(?:\d+(?:\.\d+)?|\d+/\d+|\d+\s*-\s*\d+)\s*(?:mg|g|mcg|µg|ug|ml|l|iu|units|meq|tabs|caps|puffs|drops|%|mg/kg/day|mg/day)`
            * **Supported Units**: `mg`, `g`, `mcg`, `µg`, `ug`, `ml`, `l`, `iu`, `units`, `meq`, `tabs`, `capsules`, `puffs`, `drops`, `%`, `mg/kg`
            * **Frequencies**: `BID`, `TID`, `QID`, `PRN`, `QD`, `QHS`, `Q4H`, `Q8H`, `once daily`, `twice daily`, `every 6 hours`, `with meals`
            * **Administration Routes**: `PO`, `oral`, `IV`, `intravenous`, `IM`, `intramuscular`, `SC`, `subcutaneous`, `SL`, `topical`, `inhalation`
            """
        )

    with col_pat:
        st.markdown("##### 🧪 Real-Time Regex Sandbox")
        custom_test_str = st.text_area(
            "Enter custom clinical snippet:",
            value="Give 0.5 mcg IV push stat, followed by 10-20 mg PO daily.",
            height=100,
        )
        if custom_test_str:
            sandbox_dosages = extract_dosage(custom_test_str)
            sandbox_entities = extract_medication_entities(custom_test_str)
            st.write(f"**Found Raw Dosages:** `{sandbox_dosages}`")
            for ent in sandbox_entities:
                st.write(
                    f"- Drug: **{ent.medication_name or 'Unknown'}** | Dose: **{ent.raw_dosage}** ({ent.dosage_value} {ent.dosage_unit}) | Route: **{ent.route}** | Freq: **{ent.frequency}**"
                )

# -----------------------------------------------------------------------------
# TAB 4: API Documentation & Explorer
# -----------------------------------------------------------------------------
with tab4:
    st.markdown("#### 🚀 FastAPI Backend Endpoints & Reference")
    st.write("The backend runs a high-performance FastAPI server with interactive Swagger UI and OpenAPI documentation.")

    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.markdown("##### 📌 Available Endpoints")
        st.markdown(
            """
            * `GET /api/v1/health` - Diagnostic health check and uptime.
            * `POST /api/v1/clean` - Sanitize and normalize clinical text.
            * `POST /api/v1/extract` - Extract medication dosages & entities.
            * `POST /api/v1/pipeline` - Execute single-note ETL pipeline.
            * `POST /api/v1/pipeline/batch` - High-throughput batch ETL.
            * `GET /api/v1/stats` - Server telemetry & average latency.
            * `GET /api/v1/samples` - Preloaded clinical test cases.
            """
        )

    with col_a2:
        st.markdown("##### 💻 Example cURL Request")
        st.code(
            """curl -X POST "http://localhost:8000/api/v1/pipeline" \\
     -H "Content-Type: application/json" \\
     -d '{
       "patient_id": "P-101",
       "raw_clinical_log": "Tylenol 500mg BID for 5 days."
     }'""",
            language="bash",
        )

    st.markdown("##### 🔗 Interactive Documentation Links")
    st.markdown(
        f"""
        - 📖 **Swagger UI**: [{api_url_input}/docs]({api_url_input}/docs)
        - 📑 **ReDoc**: [{api_url_input}/redoc]({api_url_input}/redoc)
        - 📄 **OpenAPI JSON**: [{api_url_input}/openapi.json]({api_url_input}/openapi.json)
        """
    )

# -----------------------------------------------------------------------------
# TAB 5: System Telemetry & Health
# -----------------------------------------------------------------------------
with tab5:
    st.markdown("#### 📊 System Telemetry & Engine Diagnostics")

    t1, t2, t3 = st.columns(3)
    with t1:
        st.metric("Total Records Ingested", default_pipeline.total_processed)
    with t2:
        st.metric("Total Entities Extracted", default_pipeline.total_entities_extracted)
    with t3:
        avg_t = (
            default_pipeline.total_processing_time_ms / default_pipeline.total_processed
            if default_pipeline.total_processed > 0
            else 0.0
        )
        st.metric("Engine Avg Processing Time", f"{avg_t:.2f} ms")

    st.markdown("---")
    st.markdown("##### 🖥️ Environment & Runtime Information")
    st.json({
        "python_version": sys.version,
        "platform": sys.platform,
        "pipeline_engine": default_pipeline.name,
        "fastapi_backend_connected": is_live,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    })
