import pandas as pd
import streamlit as st

ROW_COLORS = {
    "normal": "#d4edda",
    "abnormal": "#fff3cd",
    "critical": "#f8d7da",
}

BANNER_COLORS = {
    "green": "#d4edda",
    "yellow": "#fff3cd",
    "orange": "#ffe5b4",
    "red": "#f8d7da",
}


def render_metrics(score: int, tier: str, total: int, flagged_count: int):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risk Score", f"{score} / 100")
    c2.metric("Risk Tier", tier)
    c3.metric("Indicators", total)
    c4.metric("Flagged", flagged_count)


def render_banner(tier: str, color: str):
    bg = BANNER_COLORS.get(color, "#f0f0f0")
    st.markdown(
        f"""
        <div style="background:{bg};padding:16px;border-radius:8px;text-align:center;">
            <h2 style="margin:0;">Risk Tier: {tier}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_indicator_table(indicators: list):
    if not indicators:
        st.info("No indicators extracted.")
        return

    df = pd.DataFrame(indicators)
    cols = ["name", "value", "unit", "reference_range", "status", "note"]
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