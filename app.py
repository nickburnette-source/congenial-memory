import streamlit as st
from multi_agent_db import run_crew

st.title("DB Query Agent Dashboard")

# Tabbed interface for future extensibility
tab1, tab2 = st.tabs(["Query Chat", "Research Ideas (Coming Soon)"])

with tab1:
    user_query = st.text_input("Ask your question about the DB:")
    if st.button("Run Agents"):
        with st.spinner("Agents collaborating..."):
            result = run_crew(user_query)
        st.write(result)  # Add Plotly for viz if needed

with tab2:
    st.write("Future: Input ideas for data defect hunting (e.g., 'Analyze sales for duplicates and suggest fixes'). Agents will research/analyze.")
    # Placeholder: idea_input = st.text_area("Describe research goal:")
    # if st.button("Research"): run_special_crew(idea_input)