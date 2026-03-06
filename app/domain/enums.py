from enum import Enum


class ImportStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class OperationDirection(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"