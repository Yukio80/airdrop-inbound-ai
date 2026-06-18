import asyncio
import random
import math
from datetime import datetime

class HumanBehaviorSimulator:
    def __init__(self):
        # Configuration for "human-like" patterns
        self.config = {
            'delay_mean': 300, # Average delay 5 minutes
            'delay_std_dev': 60, # Standard deviation 1 minute
            'amount_noise': 0.02, # +/- 2% variation in amounts
            'error_rate': 0.03, # 3% chance of a simulated failure/retry
            'session_range': (600, 3600), # Session length 10min to 1hr
        }

    async def wait_between_actions(self):
        """Simulates the time a human takes to find the next button or read a page."""
        # Use Gaussian distribution for more natural delays
        delay = random.gauss(self.config['delay_mean'], self.config['delay_std_dev'])
        delay = max(30, delay) # Never less than 30 seconds
        
        print(f"😴 Simulating human thought/navigation... waiting {int(delay)}s")
        await asyncio.sleep(delay)

    def randomize_amount(self, amount):
        """Adds a small amount of noise to the transaction value to avoid fixed patterns."""
        if isinstance(amount, (int, float)):
            noise = 1 + random.uniform(-self.config['amount_noise'], self.config['amount_noise'])
            return amount * noise
        return amount

    def should_simulate_error(self):
        """Randomly decide if the bot should 'fail' or pause to mimic human error."""
        return random.random() < self.config['error_rate']

    def get_session_duration(self):
        """Returns a random session length."""
        return random.randint(*self.config['session_range'])
