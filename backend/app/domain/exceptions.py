from app.core.logging import get_logger


logger = get_logger("domain.exceptions")


class GuardrailViolation(Exception):
    pass


class AmbiguousQuestion(Exception):
    pass
