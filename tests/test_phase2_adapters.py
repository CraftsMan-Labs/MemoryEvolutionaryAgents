from __future__ import annotations

import unittest

from memory_evolutionary_agents.phase2.adapters import _to_qdrant_point_id


class Phase2AdaptersTestCase(unittest.TestCase):
    def test_non_uuid_string_point_ids_are_hashed_to_positive_int(self) -> None:
        point_id = _to_qdrant_point_id("chunk-integration-1")
        self.assertIsInstance(point_id, int)
        if isinstance(point_id, int):
            self.assertGreater(point_id, 0)

    def test_uuid_point_id_is_preserved(self) -> None:
        raw = "123e4567-e89b-12d3-a456-426614174000"
        self.assertEqual(_to_qdrant_point_id(raw), raw)


if __name__ == "__main__":
    unittest.main()
