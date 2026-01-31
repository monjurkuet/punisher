import asyncio
import random
from datetime import datetime, timedelta


class BreakManager:
    """Manages all human-like break logic and configurations."""

    def __init__(self, break_probability=0.15, long_break_min=180, long_break_max=420):
        self.break_probability = break_probability
        self.long_break_min = long_break_min
        self.long_break_max = long_break_max

    def should_take_break(self):
        """Determine if we should take a shorter, random human break."""
        return random.random() < self.break_probability

    def calculate_human_break_time(self):
        """Calculate realistic short break duration (300s to 2 hours) based on weighted random chance."""
        break_types = [
            (300, 900, 0.4),  # 5-15 min (coffee break)
            (900, 1800, 0.3),  # 15-30 min (lunch break)
            (1800, 3600, 0.2),  # 30-60 min (meeting)
            (3600, 7200, 0.1),  # 1-2 hours (long break)
        ]

        # Weighted random selection
        total_weight = sum(weight for _, _, weight in break_types)
        r = random.random() * total_weight

        cumulative = 0
        for min_time, max_time, weight in break_types:
            cumulative += weight
            if r <= cumulative:
                return random.randint(min_time, max_time)

        return random.randint(300, 900)

    async def take_human_break(self, is_long_rotation_break=False):
        """Take a realistic human break."""
        if is_long_rotation_break:
            break_duration = random.randint(self.long_break_min, self.long_break_max)
            reason = "😴 FULL ROTATION COOLDOWN"
        else:
            break_duration = self.calculate_human_break_time()
            break_reasons = [
                "☕ Coffee break",
                "🍽️ Lunch break",
                "📞 Taking a call",
                "💭 Thinking break",
                "🚶 Quick walk",
                "📧 Checking emails",
            ]
            reason = random.choice(break_reasons)

        break_minutes = break_duration / 60
        # print(f"\n[{reason}] Taking break: {break_minutes:.1f} minutes...")

        await asyncio.sleep(break_duration)
