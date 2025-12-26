import unittest
from src.cogs.xp import XPSystem

class MockBot:
    pass

class TestXPLogic(unittest.TestCase):
    def setUp(self):
        self.xp_cog = XPSystem(MockBot())

    def test_level_calculation(self):
        # User Logic:
        # < 100 XP = Level 1
        # 100 XP = Level 2
        # 120 XP = Level 2
        # 200 XP = Level 3

        self.assertEqual(self.xp_cog.calculate_level(0), 1)
        self.assertEqual(self.xp_cog.calculate_level(50), 1)
        self.assertEqual(self.xp_cog.calculate_level(99), 1)

        self.assertEqual(self.xp_cog.calculate_level(100), 2)
        self.assertEqual(self.xp_cog.calculate_level(120), 2)
        self.assertEqual(self.xp_cog.calculate_level(199), 2)

        self.assertEqual(self.xp_cog.calculate_level(200), 3)

if __name__ == '__main__':
    unittest.main()
