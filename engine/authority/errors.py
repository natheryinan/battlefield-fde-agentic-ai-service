from __future__ import annotations


class AuthorityError(RuntimeError):
    """Base class for authority violations."""


class AlphaRequired(AuthorityError):
    """Raised when an action requires Alpha authority."""


class SignatureRequired(AuthorityError):
    """Raised when a state mutation is attempted without a valid Alpha signature."""


class NotAuthorized(Exception):
    """Raised when an action is not permitted by policy (default deny)."""
    pass

