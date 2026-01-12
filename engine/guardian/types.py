from enum import Enum, auto

class Decision(Enum):
    ALLOW_INTERNAL_ONLY = auto()
    DENY_SILENT = auto()
    ALLOW_EXECUTE_ONCE = auto()

class Channel(Enum):
    INTERNAL = "internal"
    EMAIL = "email"
    CLOUD = "cloud"
    PUBLIC = "public"
    PRINT = "print"
