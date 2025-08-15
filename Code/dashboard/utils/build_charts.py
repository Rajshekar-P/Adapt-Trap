# utils/build_charts.py
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

def build_graphs(df):
    st.subheader("📊 Statistics & Visuals")

    if df.empty:
        st.info("No data available to visualize.")
        return

    # Force all timestamps to UTC-aware
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.date

    col1, col2 = st.columns(2)

    with col1:
        tag_counts = df.explode("tags")["tags"].value_counts()
        st.bar_chart(tag_counts)

    with col2:
        proto_counts = df["protocol"].value_counts()
        st.bar_chart(proto_counts)

    # Timeline
    st.subheader("📈 Daily Log Volume")
    timeline = df.groupby("date").size()
    st.line_chart(timeline)
