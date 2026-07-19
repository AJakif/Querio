from app.core.logging import get_logger


logger = get_logger("domain.exceptions")


class GuardrailViolation(Exception):
    pass


class AmbiguousQuestion(Exception):
    pass


class QueryNotFoundError(Exception):
    pass


class SelfVerifyError(ValueError):
    pass


class IdentityRequiredError(Exception):
    pass


class AccountExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class ChatSessionNotFoundError(Exception):
    pass
