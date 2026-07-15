import json
import tempfile
import unittest
from pathlib import Path

from jmag_skill.retrieval import HelpIndex, search_catalog


class RetrievalTests(unittest.TestCase):
    def test_help_search_is_bounded_and_anchor_based(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "classStudy.html"
            source.write_text('<p>UNRELATED ' + ('noise ' * 1000) + '</p><h2 id="run">RunAllCases</h2><p>Runs all active cases.</p>', encoding="utf-8")
            index = root / "help-index.jsonl"
            rows = [
                {"module": "Designer", "class": "Study", "method": "RunAllCases",
                 "summary": "Runs active cases", "source": "classStudy.html", "anchor": "run"}
                for _ in range(5)
            ]
            index.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            hits = HelpIndex(index, root).search("run cases", limit=3)
            self.assertEqual(len(hits), 3)
            sections = HelpIndex(index, root).extract(hits, max_topics=2)
            self.assertEqual(len(sections), 2)
            self.assertIn("Runs all active cases", sections[0]["text"])
            self.assertNotIn("UNRELATED", sections[0]["text"])

    def test_function_catalog_returns_stable_only(self):
        entries = [
            {"id": "stable.one", "status": "stable", "summary": "set parameter"},
            {"id": "candidate.two", "status": "candidate", "summary": "set parameter"},
        ]
        self.assertEqual([x["id"] for x in search_catalog(entries, "parameter")], ["stable.one"])


if __name__ == "__main__": unittest.main()
