# 🛡️ ADAPT Trap — Reinforcement Learning-Based Adaptive Honeypot Network
````markdown

## 📖 Overview

**ADAPT Trap** (*Adaptive Deception and Attack Profiling Trap*) is a modern, modular honeypot framework designed to **detect, profile, and adapt** to attacker behaviors in real time.

Unlike traditional honeypots, which are static and easy to fingerprint, ADAPT Trap uses **Reinforcement Learning (PPO)** to dynamically reconfigure services and plugins during an active attack. This ensures attackers remain engaged longer, exposing more of their TTPs (Tactics, Techniques, and Procedures), and helps generate richer Threat Intelligence.

The system operates in a **closed loop**, where honeypot activity continuously influences RL model training, and model outputs directly impact honeypot configurations.

---

## 🎯 Objectives

1. **Deploy** a diverse honeypot infrastructure mimicking real-world services.
2. **Centralize & normalize** honeypot logs in MongoDB.
3. **Implement tagging** to identify attacker techniques (e.g., brute force, scans, uploads).
4. **Train** a PPO RL agent to learn adaptive deception strategies.
5. **Apply actions** in real time via an actuator module.
6. **Visualize** live data and decisions via an interactive dashboard.

---

## 🏗️ System Architecture

### Mermaid Diagram (renders on GitHub)
```mermaid
flowchart LR
    subgraph Honeypots
        A[Cowrie] --> M
        B[HoneyPy] --> M
        C[Honeytrap] --> M
        D[Conpot] --> M
        E[Nodepot-lite] --> M
    end

    M[MongoDB] --> N[Log Normalizer + Tagger]
    N --> R[RL Agent (PPO)]
    R --> P[Predictor Loop (~30s)]
    P --> ACT[Actuator]
    ACT --> Honeypots

    M --> DSH[Dashboard]
````


---

## 📂 Repository Structure

```
ADAPT-Trap/
├── Code/
│   ├── actuator/         # Honeypot plugin control scripts
│   ├── dashboard/        # Streamlit dashboard
│   ├── normalizer/       # Log normalization/tagging
│   ├── rl_agent/         # PPO training + prediction
│   └── utils/            # Helper scripts
├── Honeypots/            # Sanitized honeypot configs
├── Config/
│   ├── samples/          # Example configs (placeholders)
│   └── live_do_not_commit/ # Real configs (ignored)
├── Data/                 # Sample datasets
├── Docs/                 # Report, PPT, diagrams
├── Models/               # RL models (Git LFS tracked)
├── .env.example          # Example env variables
├── requirements.txt      # Dependencies
└── README.md             # This file
```

---

## 🔧 Components

### 1️⃣ Honeypots

* **Cowrie**: SSH/Telnet emulation
* **HoneyPy**: HTTP/FTP/SMTP simulation
* **Honeytrap**: TCP/UDP service emulation
* **Conpot**: ICS/SCADA simulation
* **Nodepot-lite**: HTTP deception + credential/file capture

### 2️⃣ Central Database

* MongoDB storing:

  * Raw logs
  * Normalized/tagged logs
  * RL agent actions
  * Actuator history

### 3️⃣ Log Normalizer

* Cleans & structures logs
* Extracts: source IP, ports, protocols
* Tags: brute force, scanning, uploads, etc.

### 4️⃣ RL Agent (PPO)

* **Observation Space**: `[unique IPs, ports, tag counts, log count]`
* **Action Space**: `MultiDiscrete([2, 2, 2, 2])` (enable/disable plugins)
* Learns from real + simulated attacks

### 5️⃣ Predictor Loop

* Runs \~every 30s
* Checks for new attacker activity
* Inserts action recommendations into MongoDB

### 6️⃣ Actuator

* Reads actions from MongoDB
* Enables/disables honeypot plugins in real time
* Supports SSH/Docker/systemctl control

### 7️⃣ Dashboard

* Live attack log viewer
* Top IPs, ports, and tag distribution charts
* Honeypot health check
* RL decision timeline
* Evidence export

---

## 🚀 Setup & Installation

### 1️⃣ Clone the repository

```bash
git clone git@github.com:Rajshekar-P/Adapt-Trap.git
cd Adapt-Trap
```

### 2️⃣ Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3️⃣ Environment variables

```bash
cp .env.example .env
nano .env   # Set MongoDB URI, honeypot credentials, etc.
```

### 4️⃣ Start MongoDB

```bash
sudo systemctl start mongod
sudo systemctl enable mongod
```

### 5️⃣ Run the dashboard

```bash
cd Code/dashboard
streamlit run app.py
```

### 6️⃣ Start the predictor loop

```bash
cd ../rl_agent
python predictor_loop.py
```

---

## 🧪 Testing

### Simulate attacker logs

```bash
python Code/rl_agent/simulate_test_logs.py
```

### Collect metrics

```bash
python Code/collect_metrics.py --mongo "mongodb://localhost:27017/" --db adapttrap
```

---

## 📊 Workflow

1. Honeypots log all incoming activity.
2. Logs are normalized and tagged in MongoDB.
3. RL agent trains and learns adaptation strategies.
4. Predictor loop decides plugin/service changes.
5. Actuator applies changes in real time.
6. Dashboard displays live data and history.

---

## 📌 Expected Outcomes

* **Dynamic honeypot adaptation** to keep attackers engaged.
* **Higher attacker interaction time** compared to static honeypots.
* **Detailed attacker TTP dataset** for future threat analysis.
* **Operational dashboard** for live monitoring and evidence export.

---

## 🔮 Future Scope

* **Integration with SIEM** for enterprise alerting.
* **Multi-node deployment** with centralized RL control.
* **Expanded honeypot variety** (e.g., Mailoney, ElasticHoney).
* **Federated learning** for cross-organization intelligence sharing.

---

## 📜 Security Notes

* Real credentials are stored **only** in:

  ```
  Config/live_do_not_commit/
  .env
  ```

  and **never** committed to Git.
* `.gitignore` excludes sensitive files by default.

---

## 📄 License

MIT License © 2025 Rajshekar P

---

## 📬 Contact

* **Author:** Rajshekar P
* **Email:** [rajshekar.raju1997@gmail.com](mailto:rajshekar.raju1997@gmail.com)
* **GitHub:** [Rajshekar-P](https://github.com/Rajshekar-P)


