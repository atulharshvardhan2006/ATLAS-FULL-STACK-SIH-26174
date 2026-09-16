"""
BAS-APG — Deviation Detector

Classifies procedural deviations by comparing observed activity
against the expected procedure state.

Deviation types:
  SKIPPED_STEP:      Expected 1→2→3→4, observed 1→2→4
  WRONG_ORDER:       Expected 3→4→5, observed 3→5→4
  WRONG_OBJECT:      Expected SAMPLE, detected RED_BOX
  INCOMPLETE_ACTION:  Step timeout exceeded without confirmation
"""

from dataclasses import dataclass

@dataclass
class Deviation:
    """A classified deviation event."""

    type: str  
    expected_step: str
    expected_action: str
    expected_object: str
    observed_action: str
    observed_object: str
    details: str
    severity: str  

class DeviationDetector:
    """Analyzes observations and classifies deviation types.

    This is a stateless classifier — it takes inputs and returns
    a Deviation or None. The FSM handles actual state changes.
    """

    @staticmethod
    def classify(
        expected_step_id: str,
        expected_action: str,
        expected_object: str,
        detected_action: str,
        detected_object: str,
        all_steps: list,
        current_idx: int,
    ) -> Deviation | None:
        """Classify a deviation based on expected vs observed activity.

        Args:
            expected_step_id: ID of the step the FSM is waiting for.
            expected_action: The action the astronaut should perform.
            expected_object: The object they should interact with.
            detected_action: What action was actually detected.
            detected_object: What object was actually used.
            all_steps: Full list of procedure step definitions.
            current_idx: Index of the current step in the list.

        Returns:
            Deviation object if a deviation is detected, None otherwise.
        """
        if not detected_action or not detected_object:
            return None

        
        if detected_action == expected_action and detected_object != expected_object:
            return Deviation(
                type="WRONG_OBJECT",
                expected_step=expected_step_id,
                expected_action=expected_action,
                expected_object=expected_object,
                observed_action=detected_action,
                observed_object=detected_object,
                details=(
                    f"Wrong object: {detected_object} was used instead of "
                    f"{expected_object}. Expected action: {expected_action} "
                    f"{expected_object}."
                ),
                severity="error",
            )

        
        for future_idx in range(current_idx + 1, len(all_steps)):
            future = all_steps[future_idx]
            if detected_action == future.action and detected_object == future.object:
                gap = future_idx - current_idx
                skipped = [all_steps[i].step_id for i in range(current_idx, future_idx)]

                dev_type = "SKIPPED_STEP" if gap > 2 else "WRONG_ORDER"
                severity = "critical" if gap > 2 else "warning"

                return Deviation(
                    type=dev_type,
                    expected_step=expected_step_id,
                    expected_action=expected_action,
                    expected_object=expected_object,
                    observed_action=detected_action,
                    observed_object=detected_object,
                    details=(
                        f"Steps {', '.join(skipped)} were not completed. "
                        f"Detected: {detected_action} {detected_object} "
                        f"(matches step {future.step_id})"
                    ),
                    severity=severity,
                )

        return None
