

````markdown
# 🛡️ ADAPT Trap: Reinforcement Learning-Based Adaptive Honeypot Network

## 📌 Overview
ADAPT Trap is a **modern, adaptive honeypot system** designed to dynamically adjust its behavior using **Reinforcement Learning (RL)**.  
Instead of being a static trap, ADAPT Trap **analyzes attacker behavior in real time** and reconfigures services to improve deception, engagement, and threat intelligence gathering.

---

## 📊 Architecture

### High-Level Workflow
1. **Honeypots** (Cowrie, HoneyPy, Honeytrap, Conpot, Nodepot-lite) capture attacker activity.
2. Logs are **centralized in MongoDB**.
3. **Log Normalizer** processes logs into a unified format and tags attacker TTPs.
4. **RL Agent (PPO)** analyzes normalized logs and decides actions (e.g., enable/disable plugins).
5. **Predictor Loop** runs continuously, feeding RL outputs into the **Actuator**.
6. **Actuator** applies changes to honeypots in real-time.
7. **Dashboard** provides visibility into attacks, RL decisions, and honeypot status.

---

## 🌐 VM & IP Mapping

| Honeypot / Service       | VM / Host              | IP Address       | Notes |
|--------------------------|------------------------|------------------|-------|
| **ADAPTTRAPMAIN**        | Central Management VM  | `192.168.186.135` | MongoDB, RL Agent, Dashboard |
| **Cowrie**               | VM                     | `192.168.186.136` | SSH & Telnet honeypot |
| **HoneyPy**              | VM                     | `192.168.186.137` | HTTP(S), FTP, SMTP |
| **Honeytrap** (Docker)   | Docker Host            | `192.168.186.138` | TCP/UDP low-interaction honeypot |
| **Conpot**               | VM                     | `192.168.186.139` | ICS/SCADA honeypot |
| **Nodepot-lite**         | Docker on HoneyPy VM   | `192.168.186.137` | Web admin panel + file uploads |

---

## 🛠️ Setup Instructions

### 1. Clone Repository
```bash
git clone https://github.com/Rajshekar-P/Adapt-Trap.git
cd Adapt-Trap
````

---

### 2. Install Prerequisites

* **MongoDB**
* **Python 3.10+**
* **Docker + Docker Compose**
* **Git LFS**
* **tmux** (for persistent honeypot sessions)

---

### 3. Honeypot Setup

#### 🐍 Cowrie

```bash
ssh user@192.168.186.136
git clone https://github.com/cowrie/cowrie.git
cd cowrie
virtualenv cowrie-env
source cowrie-env/bin/activate
pip install -r requirements.txt
```

Configure `cowrie.cfg` with MongoDB logging → point to `192.168.186.135`.

---

#### 🐝 HoneyPy

```bash
ssh user@192.168.186.137
git clone https://github.com/foospidy/HoneyPy.git honeypy
cd honeypy
pip install -r requirements.txt
```

Enable FTP plugin in `services.cfg` if needed.
Logs forwarded to MongoDB.

---

#### 🪤 Honeytrap (Docker)

```bash
ssh user@192.168.186.138 -p 2222
docker-compose up -d
```

Edit `config.toml` for logging to central MongoDB.

---

#### ⚙️ Conpot

```bash
ssh user@192.168.186.139
git clone https://github.com/mushorg/conpot.git
cd conpot
pip install -r requirements.txt
```

Forward logs to MongoDB.

---

#### 🌐 Nodepot-lite

Runs in Docker alongside HoneyPy VM (`192.168.186.137`).
Supports:

* Credential harvesting
* File uploads (metadata stored in MongoDB)

---

### 4. Log Normalization

Run on **ADAPTTRAPMAIN**:

```bash
python3 Code/normalized_logs.py
```

This will:

* Read from all honeypot Mongo collections
* Normalize into `normalized_logs`
* Tag logs with TTP patterns (e.g., nmap, brute force, SQLi)

---

### 5. Train RL Model

On GPU-enabled host:

```bash
python3 Code/train_sb3.py
```

Uses PPO (`MultiDiscrete([2,2,2,2])` action space for SSH, FTP, HTTP, Telnet control).

---

### 6. Predictor Loop

```bash
python3 Code/predictor_loop.py
```

Runs every 30s, checks for new attacker activity, writes actions to `agent_actions` collection.

---

### 7. Actuator

```bash
python3 Code/actuator/main_actuator.py
```

Reads from MongoDB → Applies plugin enable/disable across honeypots.

---

### 8. Dashboard

```bash
cd Code/adapttrap-dashboard
streamlit run app.py
```

View at:
`http://192.168.186.135:8501`

---

## 📂 Project Structure

```
ADAPT-Trap/
├── Code/
│   ├── actuator/
│   ├── rl_agent/
│   ├── adapttrap-dashboard/
│   ├── normalized_logs.py
│   ├── train_sb3.py
│   └── predictor_loop.py
├── Honeypots/
│   ├── cowrie/
│   ├── honeypy/
│   ├── honeytrap/
│   ├── conpot/
│   └── nodepot-lite/
└── README.md
```

---

## 📈 Expected Outcomes

* Real-time adaptive honeypot behavior.
* Centralized attacker intelligence.
* Scalable deployment model.
* Clear visibility into threats via dashboard.

---

## 📜 License

MIT License – Free to use and modify with attribution.

---

## 🙌 Credits

Developed by **Rajshekar P** as part of **M.Tech Cybersecurity Capstone Project** at **REVA University**.
Special thanks to:

* Cowrie, HoneyPy, Honeytrap, Conpot, Nodepot-lite maintainers
* Stable Baselines3 & MongoDB communities

