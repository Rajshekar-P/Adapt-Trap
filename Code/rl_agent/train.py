# train.py

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import gym
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from rl_agent.env import AdaptTrapEnv


# PPO Actor-Critic Network
class ActorCritic(nn.Module):
    def __init__(self, input_dim, action_dim):
        super(ActorCritic, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
        )
        self.actor = nn.Linear(128, action_dim)
        self.critic = nn.Linear(128, 1)

    def forward(self, x):
        x = self.fc(x)
        return self.actor(x), self.critic(x)

# PPO Agent
class PPOAgent:
    def __init__(self, env, gamma=0.99, eps_clip=0.2, lr=2.5e-4):
        self.env = env
        self.gamma = gamma
        self.eps_clip = eps_clip

        obs_dim = env.observation_space.shape[0]
        action_dim = env.action_space.shape[0]

        self.policy = ActorCritic(obs_dim, action_dim)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()

    def select_action(self, state):
        state = torch.FloatTensor(state)
        logits, _ = self.policy(state)
        action = torch.sigmoid(logits).round().int().numpy()
        return np.clip(action, 0, 1)

    def train(self, episodes=100):
        print("🚀 Starting PPO training...")
        rewards = []

        for episode in range(episodes):
            state = self.env.reset()
            episode_reward = 0

            for t in range(100):
                action = self.select_action(state)
                next_state, reward, done, _ = self.env.step(action)
                episode_reward += reward
                state = next_state
                if done:
                    break

            rewards.append(episode_reward)
            print(f"🎯 Episode {episode+1}: Total Reward = {episode_reward}")

        # Save model
        os.makedirs("models", exist_ok=True)
        torch.save(self.policy.state_dict(), "models/ppo_adapttrap.pth")
        print("✅ Model saved to models/ppo_adapttrap.pth")

        # Save reward trend
        np.save("models/reward_trend.npy", rewards)
        print("📈 Reward trend saved to models/reward_trend.npy")

# Main entry
if __name__ == "__main__":
    print("🧠 Loading environment...")
    env = AdaptTrapEnv()
    agent = PPOAgent(env)
    agent.train(episodes=100)
