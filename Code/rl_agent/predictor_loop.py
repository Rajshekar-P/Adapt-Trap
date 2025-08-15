import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import time
import numpy as np
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone

from stable_baselines3 import PPO
from rl_agent.adapt_trap_env import AdaptTrapEnv

# =========================
# DEMO MODE TOGGLE
# =========================
DEMO_MODE = True  # ✅ Set to False for normal operation

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["adapttrap"]
logs_collection = db["normalized_logs"]
actions_collection = db["agent_actions"]
state_collection = db["plugin_states"]  # 🔁 NEW: tracks current state

# Load model
model_path = os.path.abspath("rl_agent/models/ppo_adapttrap_sb3.zip")
model = PPO.load(model_path)
print("✅ RL model loaded from:", model_path)

# Environment setup
env = AdaptTrapEnv()

# Track last check time (shorter for demo)
LOOKBACK_SECONDS = 10 if DEMO_MODE else 30
last_check_time = datetime.now(timezone.utc) - timedelta(seconds=LOOKBACK_SECONDS)

# Define tags that should trigger prediction
TRIGGER_TAGS = {
    "brute_force", "nmap", "upload", "rce",
    "sqli", "dir_traversal", "netcat", "login_attempt"
}

def check_for_attacker_activity(since_time):
    recent_logs = list(logs_collection.find(
        {"timestamp": {"$gte": since_time}},
        sort=[("timestamp", -1)]
    ))

    if DEMO_MODE:
        # In demo mode: trigger if ANY log has at least one tag or valid external IP
        for log in recent_logs:
            tags = set(log.get("tags", []))
            ip = log.get("ip", "unknown")
            protocol = log.get("protocol", "unknown")
            if tags or (protocol in {"ftp", "http", "ssh", "telnet"} and ip != "unknown"):
                return True, len(recent_logs)
        return False, len(recent_logs)
    else:
        # Normal mode: stricter logic
        trigger_count = 0
        for log in recent_logs:
            tags = set(log.get("tags", []))
            ip = log.get("ip", "unknown")
            protocol = log.get("protocol", "unknown")

            # Known attack tags
            if tags & TRIGGER_TAGS:
                trigger_count += 1
            # Fallback for external IPs
            elif protocol in {"ftp", "http", "ssh", "telnet"} and ip != "unknown" and not ip.startswith("192.168.186."):
                trigger_count += 1

        return trigger_count > 0, len(recent_logs)

def get_current_plugin_state(plugin):
    entry = state_collection.find_one({"plugin": plugin})
    return entry["status"] if entry else "enabled"  # default: enabled

def update_plugin_state(plugin, action):
    new_state = "enabled" if action == "enable_plugin" else "disabled"
    state_collection.update_one(
        {"plugin": plugin},
        {"$set": {"status": new_state, "last_updated": datetime.now(timezone.utc)}},
        upsert=True
    )

def run_predictor_loop():
    global last_check_time
    print(f"{'[DEMO] ' if DEMO_MODE else ''}Predictor loop started. Lookback window = {LOOKBACK_SECONDS}s\n")

    while True:
        now = datetime.now(timezone.utc)

        should_predict, log_count = check_for_attacker_activity(last_check_time)
        print(f"[+] {now.isoformat()} → Checked {log_count} new logs")

        if not should_predict:
            print("[=] No significant attacker activity. Skipping prediction.\n")
        else:
            print(f"{'[DEMO] ' if DEMO_MODE else ''}[!] Attack detected! Making prediction...")

            obs, _ = env.reset()
            action, _ = model.predict(obs, deterministic=True if DEMO_MODE else False)
            print(f"[DEBUG] Full action vector from agent: {action}")

            _, reward_value, _, _, info = env.step(action)
            selected_actions = info.get("selected_action", [])

            changes_logged = 0
            for selected_action in selected_actions:
                plugin = selected_action.get("plugin")
                action_type = selected_action.get("action")

                current_state = get_current_plugin_state(plugin)
                desired_state = "enabled" if action_type == "enable_plugin" else "disabled"

                if current_state != desired_state:
                    actions_collection.insert_one({
                        "timestamp": now,
                        "selected_action": selected_action,
                        "processed": False,
                        "created_at": now,
                        "reward": reward_value
                    })
                    update_plugin_state(plugin, action_type)
                    changes_logged += 1
                    print(f"[✓] Action logged: {selected_action} (reward: {reward_value})")
                else:
                    print(f"[=] Skipping {plugin} ({action_type}) — already in desired state.")

            if changes_logged == 0:
                print("[-] No action needed. Agent decision matches current plugin states.")

        last_check_time = now
        time.sleep(LOOKBACK_SECONDS)

if __name__ == "__main__":
    run_predictor_loop()
