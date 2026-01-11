from __future__ import annotations


class AuthorityError(RuntimeError):
    """Base class for authority violations."""


class AlphaRequired(AuthorityError):
    """Raised when an action requires Alpha authority."""


class SignatureRequired(AuthorityError):
    """Raised when a state mutation is attempted without a valid Alpha signature."""


class ImmutableDecisionViolation(AuthorityError):
    """Raised when someone attempts to modify an immutable decision record."""
