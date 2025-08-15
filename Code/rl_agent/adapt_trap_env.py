import gymnasium as gym
import numpy as np
from pymongo import MongoClient
from gymnasium import spaces


class AdaptTrapEnv(gym.Env):
    """
    Observation: [unique IPs, unique ports, ssh tags, http tags, log count, nmap tags]
    Action: MultiDiscrete([2,2,2,2]) -> [ssh, ftp, http, telnet] (0=enable, 1=disable)
    """
    metadata = {"render.modes": ["human"]}

    def __init__(self):
        super(AdaptTrapEnv, self).__init__()

        # === MongoDB connection
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["adapttrap"]
        self.collection = self.db["normalized_logs"]

        # === Spaces
        self.action_space = spaces.MultiDiscrete([2, 2, 2, 2])
        self.observation_space = spaces.Box(low=0, high=1000, shape=(6,), dtype=np.float32)

        # === Episode control
        self.max_steps = 64        # end an episode after this many steps
        self.step_count = 0

        self.debug = True
        self.last_action = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.step_count = 0
        self.last_action = None
        return self._get_state(), {}

    def step(self, action):
        self.last_action = action
        state = self._get_state()
        reward = self._calculate_reward(action)

        # episode bookkeeping
        self.step_count += 1
        terminated = False
        truncated = self.step_count >= self.max_steps

        decoded = self._decode_action(action)
        info = {"selected_action": decoded}

        if self.debug:
            print("\n[⚙️ STEP DEBUG] --------------------------")
            print(f"Raw Action: {action} → Decoded: {decoded}")
            print(f"Reward: {reward} | step={self.step_count}/{self.max_steps} | truncated={truncated}")
            print("-----------------------------------------\n")

        return state, reward, terminated, truncated, info

    def _decode_action(self, action):
        """Decode numeric action into plugin commands."""
        plugin_map = ["ssh", "ftp", "http", "telnet"]
        return [
            {
                "plugin": plugin_map[i],
                "action": "disable_plugin" if bit == 1 else "enable_plugin"
            }
            for i, bit in enumerate(action)
        ]

    def _get_state(self):
        """Extract observation vector from recent MongoDB logs."""
        recent_logs = list(self.collection.find().sort("timestamp", -1).limit(50))

        ip_set = set()
        ports = set()
        ssh_count, http_count = 0, 0
        nmap_count = 0

        for log in recent_logs:
            ip_set.add(log.get("ip", "unknown"))
            ports.add(log.get("port", "unknown"))
            tags = log.get("tags", [])

            if "ssh" in tags:
                ssh_count += 1
            if "http" in tags:
                http_count += 1
            if "nmap" in tags:
                nmap_count += 1

        return np.array([
            len(ip_set),
            len(ports),
            ssh_count,
            http_count,
            len(recent_logs),
            nmap_count
        ], dtype=np.float32)

    def _calculate_reward(self, action):
        """Reward function based on attacker behavior."""
        logs = list(self.collection.find().sort("timestamp", -1).limit(50))

        ip_counter = {}
        unique_ports = set()
        reward = 0.0
        attack_tag_bonus = 0

        for log in logs:
            ip = log.get("ip", "unknown")
            port = log.get("port", "unknown")
            tags = log.get("tags", [])

            if ip == "unknown":
                continue

            # Unique or repeated IPs
            if ip in ip_counter:
                ip_counter[ip] += 1
            else:
                ip_counter[ip] = 1
                reward += 2.0  # reward for new IP

            if port != "unknown":
                unique_ports.add(port)

            if any(tag in tags for tag in ["nmap", "ssh_brute", "login_attempt"]):
                attack_tag_bonus += 1

        # Port diversity bonus
        reward += 0.5 * len(unique_ports)
        reward += attack_tag_bonus

        # Repeated IP penalty
        repeated_penalty = sum(1 for count in ip_counter.values() if count > 1)
        reward -= float(repeated_penalty)

        # Low activity penalty
        if len(logs) < 5:
            reward -= 0.5

        final_reward = max(reward, 0.0)

        if self.debug:
            print("[🔍 REWARD BREAKDOWN]")
            print(f"Unique IPs: {len(ip_counter)}")
            print(f"Unique Ports: {len(unique_ports)}")
            print(f"Attack Tags Bonus: {attack_tag_bonus}")
            print(f"Repeated IP Penalty: {repeated_penalty}")
            print(f"Final Reward: {final_reward}\n")

        return final_reward

    def render(self, mode='human'):
        print(f"Last action taken: {self.last_action}")
