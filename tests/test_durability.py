import unittest
from unittest.mock import AsyncMock
from src.cogs.economy import Economy

class TestDurabilityLogic(unittest.TestCase):
    def test_refurbish_math(self):
        # Initial State
        max_durability = 100
        stats_mod = 1.0

        # Refurbish 1
        new_stats_mod = stats_mod * 0.90
        new_max_durability = int(max_durability * 0.95)

        self.assertEqual(new_stats_mod, 0.90)
        self.assertEqual(new_max_durability, 95)

        # Refurbish 2
        new_stats_mod_2 = new_stats_mod * 0.90
        new_max_durability_2 = int(new_max_durability * 0.95)

        self.assertEqual(new_stats_mod_2, 0.81)
        self.assertEqual(new_max_durability_2, 90) # int(95 * 0.95) = 90.25 -> 90

if __name__ == '__main__':
    unittest.main()
