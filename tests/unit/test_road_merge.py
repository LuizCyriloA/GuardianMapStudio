from __future__ import annotations

from datetime import UTC, datetime

import pytest

from guardianmapstudio.domain.contracts import GeoPoint, Road, RoadDirection
from guardianmapstudio.geometry.engine import GeometryEngine
from guardianmapstudio.geometry.road_merge import (
    MERGE_JOIN_TOLERANCE_M,
    MergedPolyline,
    RoadMergeService,
)

# Centroid near São Paulo / Damha V for haversine consistency with other unit tests
GEO = GeometryEngine.from_centroid(-20.81, -49.38)

_DT = datetime(2024, 1, 1, tzinfo=UTC)


def _road(
    road_id: int,
    coords: list[tuple[float, float]],
    direction: RoadDirection = RoadDirection.TWO_WAY,
    name: str | None = None,
) -> Road:
    return Road(
        id=road_id,
        workspace_id=1,
        name=name or f"Road {road_id}",
        coordinates=[GeoPoint(latitude=lat, longitude=lng) for lat, lng in coords],
        speed_limit_kmh=20,
        direction=direction,
        width_meters=6.0,
        created_at=_DT,
        updated_at=_DT,
    )


# ---------------------------------------------------------------------------
# test_merge_two_roads_sharing_endpoint
# ---------------------------------------------------------------------------


def test_merge_two_roads_sharing_endpoint() -> None:
    # Road 1 ends exactly where Road 2 begins → dist == 0, no gap, no duplicate
    r1 = _road(1, [(-20.81, -49.38), (-20.82, -49.38)])
    r2 = _road(2, [(-20.82, -49.38), (-20.83, -49.38)])

    result = RoadMergeService(GEO).merge([r1, r2])

    assert isinstance(result, MergedPolyline)
    # Shared endpoint (-20.82) appears once
    assert len(result.coordinates) == 3
    assert result.coordinates[0].latitude == pytest.approx(-20.81)
    assert result.coordinates[1].latitude == pytest.approx(-20.82)
    assert result.coordinates[2].latitude == pytest.approx(-20.83)
    assert result.gaps == []
    assert result.reversed_roads == []
    assert result.chain_order == [1, 2]


# ---------------------------------------------------------------------------
# test_merge_two_roads_with_small_gap_within_tolerance
# ---------------------------------------------------------------------------


def test_merge_two_roads_with_small_gap_within_tolerance() -> None:
    # 0.000008 degrees lat ≈ 0.89 m — within MERGE_JOIN_TOLERANCE_M (1.0m)
    r1 = _road(1, [(-20.81, -49.38), (-20.82, -49.38)])
    r2 = _road(2, [(-20.820008, -49.38), (-20.83, -49.38)])

    result = RoadMergeService(GEO).merge([r1, r2])

    gap = GEO.haversine_distance(
        GeoPoint(-20.82, -49.38), GeoPoint(-20.820008, -49.38)
    )
    assert gap < MERGE_JOIN_TOLERANCE_M, f"Expected gap < 1.0m, got {gap:.3f}m"
    # Gap is bridged but NOT reported since it's within tolerance
    assert result.gaps == []
    # Junction point IS included (dist > 0)
    assert len(result.coordinates) == 4


# ---------------------------------------------------------------------------
# test_merge_two_roads_with_large_gap_returns_warning
# ---------------------------------------------------------------------------


def test_merge_two_roads_with_large_gap_returns_warning() -> None:
    # Roads far apart: gap >> 1.0m
    r1 = _road(1, [(-20.81, -49.38), (-20.82, -49.38)])
    r2 = _road(2, [(-20.84, -49.38), (-20.85, -49.38)])

    result = RoadMergeService(GEO).merge([r1, r2])

    assert len(result.gaps) == 1
    gap_road_id, gap_m = result.gaps[0]
    assert gap_road_id == 2
    assert gap_m > MERGE_JOIN_TOLERANCE_M
    # Merge still succeeds — roads are concatenated
    assert len(result.coordinates) >= 4


# ---------------------------------------------------------------------------
# test_merge_three_roads_in_chain
# ---------------------------------------------------------------------------


def test_merge_three_roads_in_chain() -> None:
    r1 = _road(1, [(-20.81, -49.38), (-20.82, -49.38)])
    r2 = _road(2, [(-20.82, -49.38), (-20.83, -49.38)])
    r3 = _road(3, [(-20.83, -49.38), (-20.84, -49.38)])

    result = RoadMergeService(GEO).merge([r1, r2, r3])

    # All shared endpoints → 4 unique coords (not 6)
    assert len(result.coordinates) == 4
    assert result.coordinates[0].latitude == pytest.approx(-20.81)
    assert result.coordinates[3].latitude == pytest.approx(-20.84)
    assert result.chain_order == [1, 2, 3]
    assert result.gaps == []
    assert result.reversed_roads == []


# ---------------------------------------------------------------------------
# test_merge_reverses_road_when_needed
# ---------------------------------------------------------------------------


def test_merge_reverses_road_when_needed() -> None:
    # Road 2's END matches Road 1's END — needs a reverse to chain correctly
    r1 = _road(1, [(-20.81, -49.38), (-20.82, -49.38)])
    r2 = _road(2, [(-20.83, -49.38), (-20.82, -49.38)])

    result = RoadMergeService(GEO).merge([r1, r2])

    assert 2 in result.reversed_roads
    assert result.gaps == []
    # After reverse: r2 becomes [(-20.82,-49.38), (-20.83,-49.38)]
    # Shared endpoint → chain = [(-20.81,-49.38), (-20.82,-49.38), (-20.83,-49.38)]
    assert len(result.coordinates) == 3
    assert result.coordinates[2].latitude == pytest.approx(-20.83)


# ---------------------------------------------------------------------------
# test_merge_prepends_when_chain_start_is_nearest
# ---------------------------------------------------------------------------


def test_merge_prepends_when_chain_start_is_nearest() -> None:
    # Road 2's END matches Road 1's START exactly → prepend_forward wins
    r1 = _road(1, [(-20.82, -49.38), (-20.83, -49.38)])
    r2 = _road(2, [(-20.80, -49.38), (-20.82, -49.38)])

    result = RoadMergeService(GEO).merge([r1, r2])

    # prepend_forward: dist(r1[0]=(-20.82), r2[-1]=(-20.82)) = 0
    assert 2 not in result.reversed_roads  # no reverse needed
    assert result.gaps == []
    # Chain: [(-20.80), (-20.82), (-20.83)]
    assert len(result.coordinates) == 3
    assert result.coordinates[0].latitude == pytest.approx(-20.80)
    assert result.coordinates[1].latitude == pytest.approx(-20.82)
    assert result.coordinates[2].latitude == pytest.approx(-20.83)


# ---------------------------------------------------------------------------
# test_merge_preserves_coordinate_order_within_road
# ---------------------------------------------------------------------------


def test_merge_preserves_coordinate_order_within_road() -> None:
    # Multi-point roads — verify intermediate vertices are not dropped
    r1 = _road(1, [
        (-20.81, -49.38),
        (-20.815, -49.38),
        (-20.82, -49.38),
    ])
    r2 = _road(2, [
        (-20.82, -49.38),   # shared endpoint
        (-20.825, -49.38),
        (-20.83, -49.38),
    ])

    result = RoadMergeService(GEO).merge([r1, r2])

    # dist == 0 at junction → no insert, extend with r2[1:]
    # Expected: 3 + 2 = 5 coords
    assert len(result.coordinates) == 5
    lats = [c.latitude for c in result.coordinates]
    assert lats == pytest.approx([-20.81, -20.815, -20.82, -20.825, -20.83])


# ---------------------------------------------------------------------------
# test_merge_one_road_raises_value_error
# ---------------------------------------------------------------------------


def test_merge_one_road_raises_value_error() -> None:
    r1 = _road(1, [(-20.81, -49.38), (-20.82, -49.38)])

    with pytest.raises(ValueError, match="at least 2 roads"):
        RoadMergeService(GEO).merge([r1])


# ---------------------------------------------------------------------------
# test_merge_road_with_one_point_raises_value_error
# ---------------------------------------------------------------------------


def test_merge_road_with_one_point_raises_value_error() -> None:
    r1 = _road(1, [(-20.81, -49.38)])  # only 1 coordinate
    r2 = _road(2, [(-20.82, -49.38), (-20.83, -49.38)])

    with pytest.raises(ValueError, match="fewer than 2 points"):
        RoadMergeService(GEO).merge([r1, r2])


# ---------------------------------------------------------------------------
# test_merge_chain_order_reflects_greedy_selection
# ---------------------------------------------------------------------------


def test_merge_chain_order_reflects_greedy_selection() -> None:
    # A connects to C (not B); C connects to B.
    # Input order is [A, B, C] but greedy should produce A → C → B.
    road_a = _road(10, [(-20.81, -49.38), (-20.82, -49.38)])
    road_b = _road(20, [(-20.84, -49.38), (-20.85, -49.38)])   # far from A's end
    road_c = _road(30, [(-20.82, -49.38), (-20.84, -49.38)])   # connects A to B

    result = RoadMergeService(GEO).merge([road_a, road_b, road_c])

    # Greedy: start=A, next=C (dist=0, closest), next=B (dist=0)
    assert result.chain_order == [10, 30, 20]
    assert len(result.coordinates) == 4  # 4 unique endpoints
    assert result.gaps == []


# ---------------------------------------------------------------------------
# test_merge_handles_unicode_coordinates  (São Paulo / negative lat)
# ---------------------------------------------------------------------------


def test_merge_handles_unicode_coordinates() -> None:
    # Real-world-like São Paulo area coordinates with accented road name
    r1 = _road(1, [
        (-20.8100, -49.3400),
        (-20.8120, -49.3380),
        (-20.8140, -49.3360),
    ], name="Avenida São João")
    r2 = _road(2, [
        (-20.8140, -49.3360),   # exact shared endpoint
        (-20.8160, -49.3340),
    ], name="Avenida São João (2)")

    result = RoadMergeService(GEO).merge([r1, r2])

    assert result.gaps == []
    assert result.reversed_roads == []
    # 3 + 2 - 1 shared = 4 coords
    assert len(result.coordinates) == 4
    assert result.coordinates[0].latitude == pytest.approx(-20.8100)
    assert result.coordinates[3].latitude == pytest.approx(-20.8160)


# ---------------------------------------------------------------------------
# test_merge_append_reverse_with_gap
# (covers append_reverse branch with best_dist > 0)
# ---------------------------------------------------------------------------


def test_merge_append_reverse_with_gap() -> None:
    # Road 2's END is near Chain's END but not exact — triggers append_reverse + gap
    # Chain: [(-20.81), (-20.82)], Road2: [(-20.84), (-20.821)]
    # append_reverse wins: dist(chain_end=(-20.82), road2_end=(-20.821)) ≈ 11m
    r1 = _road(1, [(-20.81, -49.38), (-20.82, -49.38)])
    r2 = _road(2, [(-20.84, -49.38), (-20.821, -49.38)])

    result = RoadMergeService(GEO).merge([r1, r2])

    # Road 2 was reversed AND joined with a gap
    assert 2 in result.reversed_roads
    assert len(result.gaps) == 1  # gap > 1.0m
    assert result.gaps[0][0] == 2
    # After reverse r2 = [(-20.821), (-20.84)]; dist > 0 → junction point inserted
    # Chain: [(-20.81), (-20.82), (-20.821), (-20.84)]
    assert len(result.coordinates) == 4


# ---------------------------------------------------------------------------
# test_merge_prepend_forward_with_gap
# (covers prepend_forward branch with best_dist > 0)
# ---------------------------------------------------------------------------


def test_merge_prepend_forward_with_gap() -> None:
    # Road 2's END is near Chain's START but not exact → prepend_forward + gap
    # Chain: [(-20.82), (-20.83)], Road2: [(-20.80), (-20.821)]
    # prepend_forward wins: dist(chain_start=(-20.82), road2_end=(-20.821)) ≈ 11m
    r1 = _road(1, [(-20.82, -49.38), (-20.83, -49.38)])
    r2 = _road(2, [(-20.80, -49.38), (-20.821, -49.38)])

    result = RoadMergeService(GEO).merge([r1, r2])

    # Not reversed (prepend_forward keeps road order)
    assert 2 not in result.reversed_roads
    # gap > 1.0m
    assert len(result.gaps) == 1
    assert result.gaps[0][0] == 2
    # Junction point inserted at chain[0], then r2[:-1] prepended
    # Chain: [(-20.80), (-20.821), (-20.82), (-20.83)]
    assert len(result.coordinates) == 4
    assert result.coordinates[0].latitude == pytest.approx(-20.80)


# ---------------------------------------------------------------------------
# test_merge_prepend_reverse_exact
# (covers prepend_reverse branch with best_dist == 0)
# ---------------------------------------------------------------------------


def test_merge_prepend_reverse_exact() -> None:
    # Road 2's START matches Chain's START → prepend_reverse (road is reversed)
    # Chain: [(-20.82), (-20.83)], Road2: [(-20.82), (-20.80)]
    # prepend_reverse wins: dist(chain_start=(-20.82), road2_start=(-20.82)) = 0
    r1 = _road(1, [(-20.82, -49.38), (-20.83, -49.38)])
    r2 = _road(2, [(-20.82, -49.38), (-20.80, -49.38)])

    result = RoadMergeService(GEO).merge([r1, r2])

    # Road 2 reversed to [(-20.80), (-20.82)]; dist == 0, no insert
    # chain = [(-20.80)] + [(-20.82), (-20.83)]
    assert 2 in result.reversed_roads
    assert result.gaps == []
    assert len(result.coordinates) == 3
    assert result.coordinates[0].latitude == pytest.approx(-20.80)
    assert result.coordinates[1].latitude == pytest.approx(-20.82)
    assert result.coordinates[2].latitude == pytest.approx(-20.83)


# ---------------------------------------------------------------------------
# test_merge_prepend_reverse_with_gap
# (covers prepend_reverse branch with best_dist > 0 — last missing line)
# ---------------------------------------------------------------------------


def test_merge_prepend_reverse_with_gap() -> None:
    # Road 2's START is near Chain's START but not exact → prepend_reverse + gap
    # Chain: [(-20.82), (-20.83)], Road2: [(-20.821), (-20.80)]
    # prepend_reverse wins: dist(chain_start=(-20.82), road2_start=(-20.821)) ≈ 11m
    r1 = _road(1, [(-20.82, -49.38), (-20.83, -49.38)])
    r2 = _road(2, [(-20.821, -49.38), (-20.80, -49.38)])

    result = RoadMergeService(GEO).merge([r1, r2])

    # Road 2 reversed to [(-20.80), (-20.821)]; dist > 0 → junction inserted
    assert 2 in result.reversed_roads
    assert len(result.gaps) == 1
    assert result.gaps[0][0] == 2
    # Junction point + prepend + chain: [(-20.80), (-20.821), (-20.82), (-20.83)]
    assert len(result.coordinates) == 4
    assert result.coordinates[0].latitude == pytest.approx(-20.80)
