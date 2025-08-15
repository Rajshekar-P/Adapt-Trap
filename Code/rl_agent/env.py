# rl_agent/env.py

import gym
from gym import spaces
import numpy as np
from pymongo import MongoClient

class AdaptTrapEnv(gym.Env):
    def __init__(self):
        super(AdaptTrapEnv, self).__init__()

        # Define action space: 4 honeypots (on/off)
        self.action_space = spaces.MultiBinary(4)  # [cowrie, honeypy, honeytrap, conpot]

        # Observation space: normalized attack stats for 4 honeypots
        self.observation_space = spaces.Box(low=0, high=1, shape=(4,), dtype=np.float32)

        # MongoDB connection
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["adapttrap"]
        self.logs = self.db["normalized_logs"]

        # State tracking
        self.state = np.zeros(4, dtype=np.float32)
        self.last_attack_count = 0
        self.step_count = 0
        self.max_steps = 10

    def reset(self):
        self.step_count = 0
        self.last_attack_count = self._get_attack_count()
        self.state = self._compute_state()
        return self.state

    def step(self, action):
        self.step_count += 1

        # Simulate honeypot activation (in real system, send control signal here)
        active_honeypots = [i for i, a in enumerate(action) if a == 1]

        # Wait for attack interval (skipped in test mode)
        # time.sleep(30)  # Placeholder in real deployment

        # Calculate new state
        new_state = self._compute_state()

        # Reward = new attack count - last attack count (i.e., engagement gain)
        new_attacks = self._get_attack_count()
        reward = float(new_attacks - self.last_attack_count)

        self.last_attack_count = new_attacks
        self.state = new_state
        done = self.step_count >= self.max_steps

        return self.state, reward, done, {}

    def _get_attack_count(self):
        # Count attacks in last 5 minutes (simulate step-wise interaction)
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        recent_time = now - timedelta(minutes=5)
        return self.logs.count_documents({"timestamp": {"$gte": recent_time}})

    def _compute_state(self):
        # Normalize log distribution across honeypots in last 5 minutes
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        recent_time = now - timedelta(minutes=5)

        source_list = ['cowrie', 'honeypy', 'honeytrap', 'conpot']
        counts = []
        total = 0

        for src in source_list:
            count = self.logs.count_documents({
                "source": src,
                "timestamp": {"$gte": recent_time}
            })
            counts.append(count)
            total += count

        if total == 0:
            return np.zeros(4, dtype=np.float32)

        norm = np.array(counts) / total
        return norm.astype(np.float32)
