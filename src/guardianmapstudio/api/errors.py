from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    NOT_FOUND = "not_found"
    WORKSPACE_NOT_DRAFT = "workspace_not_draft"
    VALIDATION_ERRORS_BLOCKING = "validation_errors_blocking"
    ROAD_NAME_DUPLICATE = "road_name_duplicate"
    ROAD_HAS_DEPENDENTS = "road_has_dependents"
    INVALID_ENUM_VALUE = "invalid_enum_value"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    EXPORT_WRITE_ERROR = "export_write_error"
    DATABASE_ERROR = "database_error"
    OSM_PARSE_ERROR = "osm_parse_error"
    OSM_TOO_MANY_WAYS = "osm_too_many_ways"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    MERGE_INSUFFICIENT_ROADS = "merge_insufficient_roads"
    MERGE_DUPLICATE_SOURCE = "merge_duplicate_source"
    MERGE_FAILED = "merge_failed"
