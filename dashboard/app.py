import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

st.set_page_config(
    page_title="Indian Cyber Incident Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

def fetch_stats():
    try:
        response = requests.get(f"{API_URL}/stats/overview", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch stats: {e}")
        return None

def fetch_trends():
    try:
        response = requests.get(f"{API_URL}/stats/trends", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch trends: {e}")
        return None

def main():
    st.title("🛡️ Cyber Incident Intelligence Dashboard")
    st.markdown("Real-time threat intelligence for the Indian cyberspace.")

    stats = fetch_stats()
    
    if stats:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Incidents", stats.get("total", 0))
        
        severity = stats.get("by_severity", {})
        critical_high = severity.get("critical", 0) + severity.get("high", 0)
        col2.metric("Critical/High Severity", critical_high)
        
        col3.metric("Sectors Affected", len(stats.get("by_sector", {}).keys()))

        st.markdown("---")
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Incidents by Attack Type")
            attack_types = stats.get("by_type", {})
            if attack_types:
                df_types = pd.DataFrame(list(attack_types.items()), columns=["Type", "Count"])
                fig1 = px.pie(df_types, values="Count", names="Type", hole=0.4)
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("No data available.")

        with col_chart2:
            st.subheader("Incidents by Sector")
            sectors = stats.get("by_sector", {})
            if sectors:
                df_sectors = pd.DataFrame(list(sectors.items()), columns=["Sector", "Count"])
                fig2 = px.bar(df_sectors, x="Sector", y="Count", color="Count", color_continuous_scale="Reds")
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No data available.")

    st.markdown("---")
    st.subheader("30-Day Incident Trend")
    trends = fetch_trends()
    if trends and trends.get("daily_counts"):
        df_trends = pd.DataFrame(trends["daily_counts"])
        fig3 = px.line(df_trends, x="date", y="count", markers=True)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No trend data available.")

if __name__ == "__main__":
    main()
