import streamlit as st
import requests
import pandas as pd
import os

st.set_page_config(page_title="Incidents List", page_icon="📋", layout="wide")

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

st.title("📋 Incident Database")

def fetch_incidents(page=1, page_size=50):
    try:
        response = requests.get(
            f"{API_URL}/incidents", 
            params={"page": page, "page_size": page_size},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch incidents: {e}")
        return None

data = fetch_incidents()

if data and data.get("incidents"):
    incidents = data["incidents"]
    st.write(f"Showing {len(incidents)} of {data['total']} total incidents.")
    
    df = pd.DataFrame(incidents)
    
    display_df = df[['title', 'attack_type', 'severity', 'confidence_score', 'india_relevance_score', 'published_at']].copy()
    display_df['published_at'] = pd.to_datetime(display_df['published_at']).dt.strftime('%Y-%m-%d %H:%M')
    
    display_df['confidence_score'] = (display_df['confidence_score'] * 100).round(1).astype(str) + '%'
    display_df['india_relevance_score'] = (display_df['india_relevance_score'] * 100).round(1).astype(str) + '%'
    
    st.dataframe(
        display_df,
        column_config={
            "title": st.column_config.TextColumn("Title", width="large"),
            "attack_type": st.column_config.TextColumn("Type"),
            "severity": st.column_config.TextColumn("Severity"),
            "confidence_score": st.column_config.TextColumn("Confidence"),
            "india_relevance_score": st.column_config.TextColumn("Relevance"),
            "published_at": st.column_config.TextColumn("Date"),
        },
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("No incidents found in the database.")
