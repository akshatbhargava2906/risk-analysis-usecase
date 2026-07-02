import streamlit as st
from src.pdf_utils import get_patient_names, get_patient_documents, pdf_to_base64, bytes_to_base64, classify_document
from src.client import extract_indicators, generate_analysis
from src.questionnaire import extract_questionnaire, _empty_questionnaire
from src.risk_scorer import score_report
from src.rag import build_chunks, PatientIndex
from src.ui_components import (
    render_patient_details,
    render_banner,
    render_metrics,
    render_indicator_table,
    render_analysis,
    render_rag_query,
)
from pathlib import Path

st.set_page_config(page_title="Medical Risk Analyzer", layout="wide")
st.title("Medical Risk Analyzer")


#  Helpers 

def _tag_indicators(indicators: list, doc_type: str) -> list:
    for ind in indicators:
        ind["doc_type"] = doc_type
    return indicators


def _process(docs: dict, cache_key: str):
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    questionnaire = _empty_questionnaire()
    all_indicators = []

    if docs["questionnaire"]:
        with st.spinner("Reading questionnaire..."):
            b64 = pdf_to_base64(docs["questionnaire"]) if isinstance(docs["questionnaire"], Path) else bytes_to_base64(docs["questionnaire"])
            questionnaire = extract_questionnaire(b64)

    for item in docs["medical"]:
        name = item.name if hasattr(item, "name") else item.stem
        with st.spinner(f"Extracting indicators from {name}..."):
            b64 = bytes_to_base64(item.read()) if hasattr(item, "read") else pdf_to_base64(item)
            extraction = extract_indicators(b64)
            tagged = _tag_indicators(extraction.get("indicators", []), extraction.get("doc_type", "unknown"))
            all_indicators.extend(tagged)

    result = score_report(all_indicators, questionnaire)
    result["questionnaire"] = questionnaire
    result["all_indicators"] = all_indicators

    st.session_state[cache_key] = result
    return result


#  Sidebar 

with st.sidebar:
    st.header("Settings")
    source = st.radio("Source", ["Sample", "Upload"])

#  Input 

docs = None
cache_key = None

if source == "Sample":
    patient_names = get_patient_names()
    if not patient_names:
        st.warning("No patient folders found in Documents/")
        st.stop()
    name = st.selectbox("Select patient", patient_names)
    docs = get_patient_documents(name)
    cache_key = name

else:
    uploaded = st.file_uploader(
        "Upload patient documents (questionnaire + medical reports)",
        type="pdf",
        accept_multiple_files=True,
    )
    if uploaded:
        questionnaire_file = None
        medical_files = []
        for f in uploaded:
            if classify_document(Path(f.name)) == "questionnaire":
                questionnaire_file = f
            else:
                medical_files.append(f)
        docs = {"questionnaire": questionnaire_file, "medical": medical_files}
        cache_key = "_".join(sorted(f.name for f in uploaded))

if not docs or not docs["medical"]:
    st.info("Select a patient or upload at least one medical report PDF to begin.")
    st.stop()

#  Process 

result = _process(docs, cache_key)
questionnaire = result["questionnaire"]
all_indicators = result["all_indicators"]

#  Patient Details 

render_patient_details(questionnaire)
st.divider()

#  Risk Banner + Metrics 

render_banner(result["tier"], result["color"])
st.divider()
render_metrics(
    result["score"],
    result["tier"],
    result["total"],
    result["flagged_count"],
    result["indicator_pts"],
    result["questionnaire_pts"],
)
st.divider()

#  Indicators 

st.subheader("Indicators")
render_indicator_table(all_indicators)
st.divider()

#  Clinical Analysis 

analysis_key = cache_key + "_analysis"
if analysis_key not in st.session_state:
    with st.spinner("Generating clinical analysis..."):
        st.session_state[analysis_key] = generate_analysis(
            result["score"],
            result["tier"],
            result["flagged"],
            questionnaire,
        )

st.subheader("Clinical Analysis")
render_analysis(st.session_state[analysis_key])
st.divider()

#  RAG 

index_key = cache_key + "_index"
if index_key not in st.session_state:
    with st.spinner("Building search index..."):
        try:
            chunks = build_chunks({"indicators": all_indicators, "patient_name": questionnaire.get("patient_name", "")})
            st.session_state[index_key] = PatientIndex(chunks)
        except Exception as e:
            st.session_state[index_key] = None
            st.warning(f"Search index unavailable: {e}")

if st.session_state.get(index_key):
    render_rag_query(st.session_state[index_key])