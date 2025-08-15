import numpy as np
import matplotlib.pyplot as plt
import os

# Load the reward trend file
reward_path = os.path.join(os.path.dirname(__file__), "models", "reward_trend.npy")
if not os.path.exists(reward_path):
    print(f"❌ Reward file not found at {reward_path}")
    exit(1)

rewards = np.load(reward_path)

plt.figure(figsize=(10, 4))
plt.plot(rewards, label="Reward", color="blue")
plt.xlabel("Episode")
plt.ylabel("Total Reward")
plt.title("PPO Training Reward Trend")
plt.legend()
plt.grid(True)
plt.tight_layout()

# Save instead of showing (headless)
output_path = os.path.join(os.path.dirname(__file__), "reward_plot.png")
plt.savefig(output_path)
print(f"✅ Saved plot as {output_path}")
