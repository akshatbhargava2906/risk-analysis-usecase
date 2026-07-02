import pandas as pd
import streamlit as st

ROW_COLORS = {
    "normal": "#d4edda",
    "abnormal": "#fff3cd",
    "critical": "#f8d7da",
}

BANNER_COLORS = {
    "green": "#d4edda",
    "orange": "#ffe5b4",
    "red": "#f8d7da",
}


def render_patient_details(q: dict):
    st.subheader("Patient Details")
    ins = q.get("insurance", {})
    smoking = q.get("smoking", {})
    family = q.get("family_history", [])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Name", q.get("patient_name") or "—")
    c2.metric("Age", q.get("age") or "—")
    c3.metric("Gender", q.get("gender") or "—")
    c4.metric("Location", q.get("location") or "—")

    st.divider()

    d1, d2, d3 = st.columns(3)
    with d1:
        st.markdown("**Insurance**")
        st.markdown(f"Coverage: {ins.get('current_coverage') or '—'}")
        st.markdown(f"Amount: {ins.get('coverage_amount') or '—'}")
        st.markdown(f"Previous Claims: {ins.get('previous_claims') or 'None'}")

    with d2:
        st.markdown("**Lifestyle**")
        st.markdown(f"Smoking: {smoking.get('status', '—').capitalize()}")
        st.markdown(f"Pack Years: {smoking.get('pack_years') or '—'}")

    with d3:
        st.markdown("**Family History**")
        if family:
            for condition in family:
                st.markdown(f"- {condition}")
        else:
            st.markdown("None reported")


def render_banner(tier: str, color: str):
    bg = BANNER_COLORS.get(color, "#f0f0f0")
    st.markdown(
        f"""
        <div style="background:{bg};padding:16px;border-radius:8px;text-align:center;">
            <h2 style="margin:0;color:#1a1a1a;">Risk Tier: {tier}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(score: int, tier: str, total: int, flagged_count: int,
                   indicator_pts: int = 0, questionnaire_pts: int = 0):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risk Score", f"{score} / 100")
    c2.metric("Risk Tier", tier)
    c3.metric("Indicators", total)
    c4.metric("Flagged", flagged_count)

    if questionnaire_pts > 0:
        st.caption(
            f"Score breakdown: {indicator_pts} from clinical indicators "
            f"+ {questionnaire_pts} from lifestyle / history = {score}"
        )


def render_indicator_table(indicators: list):
    if not indicators:
        st.info("No indicators extracted.")
        return

    df = pd.DataFrame(indicators)

    if "doc_type" in df.columns:
        df = df.rename(columns={"doc_type": "source"})

    cols = ["source", "name", "value", "unit", "reference_range", "status", "note"]
    df = df[[c for c in cols if c in df.columns]]

    def color_row(row):
        bg = ROW_COLORS.get(row.get("status", ""), "")
        if bg:
            return [f"background-color:{bg};color:#1a1a1a" for _ in row]
        return ["" for _ in row]

    st.dataframe(
        df.style.apply(color_row, axis=1),
        use_container_width=True,
    )


def render_analysis(text: str):
    sections = {"SUMMARY": "", "FLAGGED INDICATORS": "", "RECOMMENDATIONS": ""}
    current = None

    for line in text.splitlines():
        clean = line.strip().upper()
        for ch in ("#", "*", "_", ":"):
            clean = clean.replace(ch, "")
        clean = clean.strip()

        matched = next((key for key in sections if clean == key or clean.startswith(key)), None)
        if matched:
            current = matched
        elif current:
            sections[current] += line + "\n"

    for title, body in sections.items():
        with st.expander(title, expanded=True):
            st.markdown(body.strip() if body.strip() else "_Not provided._")


def render_rag_query(index):
    st.subheader("Ask the Report")
    query = st.text_input("Query", placeholder="e.g. Which indicators are critical?")

    if st.button("Search") and query.strip():
        with st.spinner("Searching..."):
            results = index.search(query.strip(), k=5)

        st.markdown("**Top matches from the report:**")
        for i, chunk in enumerate(results, 1):
            st.markdown(f"`{i}.` {chunk}")