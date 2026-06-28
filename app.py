import streamlit as st
from pathlib import Path

from src.pdf_utils import get_patient_files, pdf_to_base64, bytes_to_base64
from src.client import extract_indicators, generate_analysis
from src.risk_scorer import score_report
from src.rag import build_chunks, PatientIndex
from src.ui_components import (
    render_banner,
    render_metrics,
    render_indicator_table,
    render_analysis,
    render_rag_query,
)

st.set_page_config(page_title="Medical Risk Analyzer", layout="wide")
st.title("Medical Risk Analyzer")


def process(pdf_bytes: bytes, key: str):
    if key not in st.session_state:
        with st.spinner("Extracting indicators..."):
            b64 = pdf_to_base64.__wrapped__(pdf_bytes) if hasattr(pdf_to_base64, "__wrapped__") else bytes_to_base64(pdf_bytes)
            extraction = extract_indicators(b64)
        result = score_report(extraction["indicators"])
        result["extraction"] = extraction
        st.session_state[key] = result

    return st.session_state[key]


def _bytes_to_b64(data: bytes) -> str:
    import base64
    return base64.b64encode(data).decode("utf-8")


#  Sidebar 

with st.sidebar:
    st.header("Settings")
    st.caption("Leave blank to use .env key")

    tab_choice = st.radio("Source", ["Sample", "Upload"])

#  Input 

pdf_bytes = None
cache_key = None

if tab_choice == "Sample":
    patients = get_patient_files()
    if not patients:
        st.warning("No PDFs found in Documents/")
        st.stop()
    label = st.selectbox("Select patient", list(patients.keys()))
    path = patients[label]
    pdf_bytes = path.read_bytes()
    cache_key = str(path)

else:
    uploaded = st.file_uploader("Upload a lab report PDF", type="pdf")
    if uploaded:
        pdf_bytes = uploaded.read()
        cache_key = uploaded.name

if not pdf_bytes:
    st.info("Select a sample or upload a PDF to begin.")
    st.stop()

#  Process 

result = process(pdf_bytes, cache_key)
extraction = result["extraction"]

#  Display 

st.subheader(
    f"{extraction.get('patient_name', 'Unknown')} — {extraction.get('report_date', '')}"
)

render_banner(result["tier"], result["color"])
st.divider()
render_metrics(result["score"], result["tier"], result["total"], result["flagged_count"])
st.divider()

st.subheader("Indicators")
render_indicator_table(extraction["indicators"])
st.divider()

#  AI Analysis 

analysis_key = cache_key + "_analysis"
if analysis_key not in st.session_state:
    with st.spinner("Generating clinical analysis..."):
        st.session_state[analysis_key] = generate_analysis(
            result["score"], result["tier"], result["flagged"]
        )

st.subheader("Clinical Analysis")
render_analysis(st.session_state[analysis_key])
st.divider()

#  RAG 

index_key = cache_key + "_index"
if index_key not in st.session_state:
    with st.spinner("Building search index..."):
        try:
            chunks = build_chunks(extraction)
            st.session_state[index_key] = PatientIndex(chunks)
        except Exception as e:
            st.session_state[index_key] = None
            st.warning(f"Search index unavailable: {e}")

if st.session_state.get(index_key):
    render_rag_query(st.session_state[index_key])