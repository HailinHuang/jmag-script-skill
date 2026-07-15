import unittest
from pathlib import Path


class SkillContractTests(unittest.TestCase):
    def test_skill_is_small_and_contains_safety_gates(self):
        text = (Path(__file__).parents[2] / "SKILL.md").read_text(encoding="utf-8")
        body = text.split("---", 2)[-1]
        self.assertLessEqual(len(body.split()), 250)
        for phrase in ("stable", "Help", "user approval", "never promote", "REM"):
            self.assertIn(phrase, body)


if __name__ == "__main__": unittest.main()
