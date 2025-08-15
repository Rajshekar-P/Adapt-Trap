#!/usr/bin/env python3

import os
import sys
import numpy as np
import gymnasium as gym
import random
import time as time_module
import psutil
import threading
from datetime import datetime, timezone
from pymongo import MongoClient
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from tqdm import tqdm
import torch  # GPU support

# === Path fix for local modules (env is in same folder)
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from adapt_trap_env import AdaptTrapEnv  # type: ignore

# === Reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# === Initialize Environment
env = AdaptTrapEnv()
env.debug = False
env.action_space.seed(SEED)
env.observation_space.seed(SEED)
check_env(env)

# === Reward Tracker
class RewardLoggerWrapper(gym.Wrapper):
    def __init__(self, env):
        super().__init__(env)
        self.episode_rewards = []
        self.episode_reward = 0.0

    def reset(self, **kwargs):
        # start a new episode
        self.episode_reward = 0.0
        return self.env.reset(**kwargs)

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        self.episode_reward += float(reward)
        if terminated or truncated:
            self.episode_rewards.append(self.episode_reward)
            self.episode_reward = 0.0
        return obs, reward, terminated, truncated, info

wrapped_env = RewardLoggerWrapper(env)

# === System Monitor
def monitor_resources(interval=15):
    while True:
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        print(f"[System Resource] CPU: {cpu}%, RAM: {mem}%")
        time_module.sleep(interval)

threading.Thread(target=monitor_resources, daemon=True).start()

# === Model Setup
model_path = "rl_agent/models/ppo_adapttrap_sb3.zip"
os.makedirs("rl_agent/models", exist_ok=True)

if os.path.exists(model_path):
    print(f"📥 Resuming training from: {model_path}")
    model = PPO.load(model_path, env=wrapped_env, device="auto")
else:
    print("🆕 Starting new training")
    model = PPO(
        "MlpPolicy",
        wrapped_env,
        verbose=0,
        tensorboard_log="./ppo_logs",
        seed=SEED,
        device="auto",
        n_steps=512
    )

print("✅ CUDA Available:", torch.cuda.is_available())
print("🚀 Training Device:", model.device)

# === Training Config
MAX_MINUTES = 30
MAX_SECONDS = MAX_MINUTES * 60
TIMESTEP_BATCH = 512
pbar = tqdm(desc="Training PPO")
start_time = time_module.time()
last_status_time = start_time
steps_trained = 0

# === Training Loop
try:
    while True:
        if time_module.time() - start_time >= MAX_SECONDS:
            print("\n⏱️ Time limit reached. Exiting training loop...\n")
            break

        model.learn(total_timesteps=TIMESTEP_BATCH, reset_num_timesteps=False)
        steps_trained += TIMESTEP_BATCH
        pbar.update(TIMESTEP_BATCH)

        if time_module.time() - last_status_time >= 300:
            elapsed = time_module.time() - start_time
            eps = len(wrapped_env.episode_rewards)
            avg_reward = float(np.mean(wrapped_env.episode_rewards[-10:])) if eps else 0.0
            print(f"\n[⏱️ Status @ {elapsed:.1f}s] Steps: {steps_trained}, Episodes: {eps}, Avg Reward (last 10): {avg_reward:.2f}\n")
            last_status_time = time_module.time()

except KeyboardInterrupt:
    print("\n🛑 Training interrupted manually. Saving model...\n")

finally:
    pbar.close()
    model.save(model_path)
    print(f"✅ Model saved to: {model_path}")

    # === Rewards and plotting (guard if empty)
    reward_array = np.array(wrapped_env.episode_rewards, dtype=float)

    if reward_array.size == 0:
        print("⚠️ No completed episodes during this run. Skipping reward stats/plot.")
    else:
        np.save("rl_agent/models/reward_trend.npy", reward_array)
        print("📊 Reward trend saved to: rl_agent/models/reward_trend.npy")

        plt.figure(figsize=(10, 4))
        smoothed = gaussian_filter1d(reward_array, sigma=2)
        plt.plot(smoothed, label="Smoothed Reward")
        plt.xlabel("Episode")
        plt.ylabel("Reward")
        plt.title("Smoothed Training Reward Trend")
        plt.grid(True)
        plt.legend()
        plt.savefig("rl_agent/models/reward_trend.png")
        print("📈 Reward plot saved to: rl_agent/models/reward_trend.png")

    # === MongoDB Logging
    try:
        client = MongoClient("mongodb://192.168.186.135:27017/")
        db = client["adapttrap"]
        actions_db = db["agent_actions"]
        logs_db = db["training_logs"]

        recent_reward = float(reward_array[-1]) if reward_array.size else 0.0
        now = datetime.now(timezone.utc)

        plugin_map = ["ssh", "ftp", "http", "telnet"]
        action_vector = [0, 0, 0, 0]
        if recent_reward > 20:
            action_vector = [1, 1, 1, 1]
        elif recent_reward > 10:
            action_vector = [1, 0, 1, 0]

        for i, val in enumerate(action_vector):
            action_doc = {
                "plugin": plugin_map[i],
                "action": "disable_plugin" if val else "enable_plugin"
            }
            actions_db.insert_one({
                "timestamp": now,
                "selected_action": action_doc,
                "processed": False,
                "created_at": now,
                "reward": float(recent_reward),
                "source": "train_sb3"
            })
            print("✅ Logged action:", action_doc)

        logs_db.insert_one({
            "model_path": model_path,
            "timesteps": steps_trained,
            "final_reward": float(recent_reward),
            "timestamp": now,
            "duration_sec": time_module.time() - start_time,
            "reward_mean": float(np.mean(reward_array)) if reward_array.size else None,
            "reward_std": float(np.std(reward_array)) if reward_array.size else None,
            "seed": SEED
        })
        print("📝 Training metadata logged to MongoDB")

    except Exception as e:
        print("⚠️ MongoDB logging failed:", str(e))

    # === Post-training Evaluation
    print("\n🧪 Sample Evaluation:")
    obs, info = wrapped_env.reset()
    for _ in range(5):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = wrapped_env.step(action)
        print(f"→ Action: {action}, Reward: {reward}")
        if terminated or truncated:
            obs, info = wrapped_env.reset()
