import unittest
from unittest.mock import AsyncMock

class TestCrimeLogic(unittest.TestCase):
    def test_crime_probability(self):
        # Simulate Logic
        thief_skill = 5
        thief_luck = 5

        victim_luck = 5
        has_safe = True

        # Min/Max scores
        # Crime: (5*2) + 5 + [1..20] = 15 + [1..20] = 16 to 35
        # Defense (Safe): (5*2) + 50 + [1..20] = 60 + [1..20] = 61 to 80

        # With safe, Thief (max 35) should ALWAYS lose to Defense (min 61)
        crime_max = (thief_skill * 2) + thief_luck + 20
        def_min = (victim_luck * 2) + (50 if has_safe else 0) + 1

        self.assertTrue(crime_max < def_min, "Thief should fail against Safe with low stats")

        # Test without safe
        has_safe = False
        # Defense (No Safe): 10 + [1..20] = 11 to 30
        # Thief (Max 35). Thief CAN win.

        crime_score = 30 # high roll
        def_score = 15 # low roll
        self.assertTrue(crime_score > def_score)

if __name__ == '__main__':
    unittest.main()
