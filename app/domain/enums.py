from enum import Enum


class ImportStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"