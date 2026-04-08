# apps/api/app/core/exceptions.py


class SequenceRuleViolationError(Exception):
    """
    Raised when a proposed exam sequence violates one or more clinical rules.
    Carry the violation list from the rules engine so callers can surface it
    in HTTP responses without coupling to the engine directly.
    """

    code: str = "SEQUENCE_RULE_VIOLATION"

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__(
            f"Sequence violates {len(violations)} clinical rule(s): "
            + "; ".join(violations)
        )
