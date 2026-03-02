from __future__ import annotations

from enum import Enum


class Capability(str, Enum):
    PASSIVE_CAPTURE = 'PASSIVE_CAPTURE'
    READ_ONLY_DIAG = 'READ_ONLY_DIAG'
    EXPORT_REPORT = 'EXPORT_REPORT'
    ORCHESTRATE_EXTERNAL_TOOL = 'ORCHESTRATE_EXTERNAL_TOOL'
