from __future__ import annotations

import unittest

from memory_evolutionary_agents.phase6.contracts import FileStage
from memory_evolutionary_agents.phase6.errors import InvalidStageTransitionError
from memory_evolutionary_agents.phase6.policy import StageTransitionPolicyService


class Phase6PolicyTestCase(unittest.TestCase):
    def test_valid_transitions_pass(self) -> None:
        policy = StageTransitionPolicyService()
        policy.assert_transition(None, FileStage.DISCOVERED)
        policy.assert_transition(FileStage.DISCOVERED, FileStage.WORKFLOW_STARTED)
        policy.assert_transition(
            FileStage.WORKFLOW_STARTED, FileStage.WORKFLOW_COMPLETED
        )
        policy.assert_transition(FileStage.WORKFLOW_COMPLETED, FileStage.COMPLETED)

    def test_invalid_transition_raises(self) -> None:
        policy = StageTransitionPolicyService()
        with self.assertRaises(InvalidStageTransitionError):
            policy.assert_transition(FileStage.DISCOVERED, FileStage.COMPLETED)


if __name__ == "__main__":
    unittest.main()
