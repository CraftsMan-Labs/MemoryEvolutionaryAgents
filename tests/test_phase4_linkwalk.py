from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from memory_evolutionary_agents.phase4.contracts import LinkWalkRequest
from memory_evolutionary_agents.phase4.linkwalk import ObsidianLinkGraphReader


class Phase4LinkWalkTestCase(unittest.TestCase):
    def test_linkwalk_enforces_depth_fanout_and_deduplication(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            (vault / "A.md").write_text("[[B]] [[C]] [[D]]", encoding="utf-8")
            (vault / "B.md").write_text("[[E]]", encoding="utf-8")
            (vault / "C.md").write_text("[[E]]", encoding="utf-8")
            (vault / "D.md").write_text("[[E]]", encoding="utf-8")
            (vault / "E.md").write_text("done", encoding="utf-8")

            reader = ObsidianLinkGraphReader(str(vault))
            response = reader.walk(
                LinkWalkRequest(
                    seed_note_paths=[str(vault / "A.md")],
                    max_depth=2,
                    max_fanout=2,
                )
            )

            names = [
                Path(candidate.note_path).name for candidate in response.candidates
            ]
            self.assertEqual(names[0], "A.md")
            self.assertIn("B.md", names)
            self.assertIn("C.md", names)
            self.assertNotIn("D.md", names)
            self.assertIn("E.md", names)
            self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
