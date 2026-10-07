from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    score: float
    notes: str


class ResultVerifier:
    """Safe baseline verifier; model/tool-specific verification can extend this."""

    def verify(self, answer: str, *, expected_goal: str) -> VerificationResult:
        if not answer.strip():
            return VerificationResult(False, 0.0, "Empty result")
        return VerificationResult(True, 1.0, "Result contains a non-empty response")
