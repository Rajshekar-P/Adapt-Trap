import streamlit as st
import pandas as pd
from db import get_normalized_logs, get_plugin_states, get_agent_actions
from utils.summarize_logs import get_summary_metrics
from utils.tag_insights import get_tag_insights
from utils.build_charts import build_graphs
from utils.health_check import run_health_checks


st.set_page_config(page_title="ADAPT Trap Dashboard", layout="wide")
st.title("\U0001F6E1 ADAPT Trap Honeypot Dashboard")

# === Load Logs ===
logs_df = get_normalized_logs()

# 🔧 Fix logs_df for Arrow + timezone issues
if "_id" in logs_df.columns:
    logs_df["_id"] = logs_df["_id"].astype(str)
if "timestamp" in logs_df.columns:
    logs_df["timestamp"] = pd.to_datetime(logs_df["timestamp"], errors="coerce", utc=True)
if "port" in logs_df.columns:
    logs_df["port"] = logs_df["port"].astype(str)

summary = get_summary_metrics(logs_df)

# === Top Metrics ===
st.markdown("### \u2728 Top Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("\U0001F4C5 Total Logs", summary['count'])
col2.metric("\U0001F539 Unique IPs", summary['unique_ips'])
col3.metric("\U0001F516 Tagged Logs", summary['tagged'])

# === Health Check ===
st.markdown("### 🩺 System Health Check")
health = run_health_checks()

cols = st.columns(len(health))
for i, (component, (status, color)) in enumerate(health.items()):
    with cols[i]:
        st.markdown(f"**{component}**")
        st.markdown(f":{color}[{status}]")

# === Filters ===
st.markdown("### \U0001F50D Filter Logs")
source_opts = sorted(logs_df['source'].dropna().unique())
proto_opts = sorted(logs_df['protocol'].dropna().unique())
tag_opts = ["brute-force", "ics-probe", "nmap", "upload", "sql-injection"]

col1, col2, col3 = st.columns(3)
source_val = col1.multiselect("Source", source_opts)
proto_val = col2.multiselect("Protocol", proto_opts)
tag_val = col3.multiselect("Tags", tag_opts)

if source_val:
    logs_df = logs_df[logs_df['source'].isin(source_val)]
if proto_val:
    logs_df = logs_df[logs_df['protocol'].isin(proto_val)]
if tag_val:
    logs_df = logs_df[logs_df['tags'].apply(lambda tags: any(t in tags for t in tag_val))]

# === Logs Table ===
st.markdown("### \U0001F4D1 Attack Logs")
st.dataframe(logs_df[["timestamp", "source", "ip", "port", "protocol", "raw_log", "tags"]], use_container_width=True)

# === Plugin States ===
st.markdown("### \u2696 Honeypot Plugin States")
plugin_df = get_plugin_states()

# 🔧 Fix plugin_df if needed
if "_id" in plugin_df.columns:
    plugin_df["_id"] = plugin_df["_id"].astype(str)
if "timestamp" in plugin_df.columns:
    plugin_df["timestamp"] = pd.to_datetime(plugin_df["timestamp"], errors="coerce", utc=True)

st.dataframe(plugin_df, use_container_width=True)

# === RL Agent Actions ===
st.markdown("### \U0001F916 RL Agent Decisions")
rl_df = get_agent_actions()

# 🔧 Fix rl_df if needed
if "_id" in rl_df.columns:
    rl_df["_id"] = rl_df["_id"].astype(str)
if "timestamp" in rl_df.columns:
    rl_df["timestamp"] = pd.to_datetime(rl_df["timestamp"], errors="coerce", utc=True)

st.dataframe(rl_df, use_container_width=True)

# === Charts ===
#st.markdown("### \U0001F4CA Statistics & Visuals")
build_graphs(logs_df)
