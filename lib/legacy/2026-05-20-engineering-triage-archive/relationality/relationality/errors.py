"""Custom exceptions for canonicalization, hashing, and persistence."""


class CanonicalizationError(Exception):
    """Raised when data cannot be canonicalized deterministically."""


class SchemaValidationError(Exception):
    """Raised when a payload fails schema validation."""


class HashMismatchError(Exception):
    """Raised when a computed hash does not match the expected value."""


class IDMismatchError(Exception):
    """Raised when an embedded id does not match its computed value or filename."""


class KindMismatchError(Exception):
    """Raised when a filename kind disagrees with the payload kind."""


class DuplicateObjectError(Exception):
    """Raised when attempting to load two objects with the same (id, kind)."""


class LoaderError(Exception):
    """Generic loader error for unexpected issues while reading files."""
