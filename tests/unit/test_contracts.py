from __future__ import annotations

import pytest

from guardianmapstudio.domain.contracts import (
    GateType,
    GeoPoint,
    RestrictionType,
    RoadDirection,
    ValidationResult,
    ValidationSeverity,
    WaypointType,
    WorkspaceState,
)


def test_geopoint_valid_bounds() -> None:
    pt = GeoPoint(-20.81, -49.37)
    assert pt.latitude == -20.81
    assert pt.longitude == -49.37


def test_geopoint_invalid_latitude() -> None:
    with pytest.raises(ValueError):
        GeoPoint(91.0, 0.0)


def test_geopoint_invalid_longitude() -> None:
    with pytest.raises(ValueError):
        GeoPoint(0.0, -181.0)


def test_geopoint_to_export() -> None:
    pt = GeoPoint(-20.81, -49.37)
    assert pt.to_export() == {"lat": -20.81, "lng": -49.37}


def test_validation_result_is_blocking() -> None:
    result = ValidationResult(
        severity=ValidationSeverity.ERROR,
        rule_id="test.rule",
        message="test",
        affected_entity_type="road",
        affected_entity_id=1,
    )
    assert result.is_blocking is True


def test_validation_result_warning() -> None:
    result = ValidationResult(
        severity=ValidationSeverity.WARNING,
        rule_id="test.rule",
        message="test",
        affected_entity_type="road",
        affected_entity_id=1,
    )
    assert result.is_blocking is False


def test_workspace_state_values() -> None:
    assert WorkspaceState.DRAFT.value == "draft"
    assert WorkspaceState.PUBLISHED.value == "published"


def test_waypoint_type_matches_guardian() -> None:
    assert WaypointType.STOP_SIGN.value == "stop_sign"


def test_gate_type_matches_guardian() -> None:
    assert GateType.ENTRY_EXIT.value == "entry_exit"


def test_restriction_type_matches_guardian() -> None:
    assert RestrictionType.SPEED_LIMIT.value == "speed_limit"


def test_road_direction_matches_guardian() -> None:
    assert RoadDirection.TWO_WAY.value == "two_way"


def test_all_enums_are_strings() -> None:
    all_enums = [
        WorkspaceState,
        ValidationSeverity,
        WaypointType,
        GateType,
        RestrictionType,
        RoadDirection,
    ]
    for enum_cls in all_enums:
        for member in enum_cls:
            msg = f"{enum_cls.__name__}.{member.name} value is not str"
            assert isinstance(member.value, str), msg


def test_frozen_dataclass_immutable() -> None:
    from dataclasses import FrozenInstanceError

    pt = GeoPoint(0.0, 0.0)
    with pytest.raises(FrozenInstanceError):
        pt.latitude = 1.0  # type: ignore[misc]
