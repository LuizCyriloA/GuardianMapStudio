from __future__ import annotations

import json

import pytest

from guardianmapstudio.database.repository import MapRepository, ProjectRepository
from guardianmapstudio.domain.contracts import GeoPoint, RoadDirection
from guardianmapstudio.osm.importer import ImportSummary, OsmImporter
from guardianmapstudio.osm.parser import ParsedRoad


def _make_parsed_road(
    name: str = "Rua A",
    osm_id: int = 1,
    direction: RoadDirection = RoadDirection.TWO_WAY,
    coords: list[GeoPoint] | None = None,
) -> ParsedRoad:
    if coords is None:
        coords = [
            GeoPoint(latitude=-23.55, longitude=-46.63),
            GeoPoint(latitude=-23.56, longitude=-46.64),
        ]
    return ParsedRoad(
        osm_way_id=osm_id,
        name=name,
        coordinates=coords,
        direction=direction,
        speed_limit_kmh=20,
        width_meters=6.0,
        highway_tag="residential",
        had_name=True,
        osm_warnings=[],
    )


def _create_workspace(db_session):  # type: ignore[no-untyped-def]
    proj = ProjectRepository(db_session).create(name="Test Project")
    from guardianmapstudio.database.repository import WorkspaceRepository
    ws = WorkspaceRepository(db_session).get_active_draft(proj.id)
    assert ws is not None
    return ws


# ---------------------------------------------------------------------------
# test_import_creates_roads_in_workspace
# ---------------------------------------------------------------------------


def test_import_creates_roads_in_workspace(db_session) -> None:  # type: ignore[no-untyped-def]
    ws = _create_workspace(db_session)
    parsed = [_make_parsed_road("Rua A"), _make_parsed_road("Rua B", osm_id=2)]

    summary = OsmImporter(db_session).import_roads(ws.id, parsed)

    assert isinstance(summary, ImportSummary)
    assert summary.created_count == 2
    assert summary.skipped_count == 0
    assert summary.renamed == []
    assert summary.deleted_existing == 0

    roads = MapRepository(db_session).get_roads(ws.id)
    assert len(roads) == 2
    names = {r.name for r in roads}
    assert names == {"Rua A", "Rua B"}


# ---------------------------------------------------------------------------
# test_import_dedupe_appends_suffix
# ---------------------------------------------------------------------------


def test_import_dedupe_appends_suffix(db_session) -> None:  # type: ignore[no-untyped-def]
    ws = _create_workspace(db_session)
    # Pre-create "Rua A" via normal road creation
    coords_json = json.dumps([{"lat": -23.55, "lng": -46.63}, {"lat": -23.56, "lng": -46.64}])
    MapRepository(db_session).create_road(
        workspace_id=ws.id,
        name="Rua A",
        coordinates_json=coords_json,
        speed_limit_kmh=20,
        direction="two_way",
        width_meters=6.0,
    )

    parsed = [_make_parsed_road("Rua A", osm_id=99)]
    summary = OsmImporter(db_session).import_roads(ws.id, parsed)

    assert summary.created_count == 1
    assert len(summary.renamed) == 1
    assert summary.renamed[0] == ("Rua A", "Rua A (2)")

    roads = MapRepository(db_session).get_roads(ws.id)
    names = {r.name for r in roads}
    assert "Rua A" in names
    assert "Rua A (2)" in names


# ---------------------------------------------------------------------------
# test_import_dedupe_handles_multiple_collisions
# ---------------------------------------------------------------------------


def test_import_dedupe_handles_multiple_collisions(db_session) -> None:  # type: ignore[no-untyped-def]
    ws = _create_workspace(db_session)
    # Import three roads with the same name — each should get a unique suffix
    parsed = [
        _make_parsed_road("Rua X", osm_id=1),
        _make_parsed_road("Rua X", osm_id=2),
        _make_parsed_road("Rua X", osm_id=3),
    ]
    summary = OsmImporter(db_session).import_roads(ws.id, parsed)

    assert summary.created_count == 3
    # First one keeps "Rua X", second becomes "Rua X (2)", third "Rua X (3)"
    assert len(summary.renamed) == 2
    renamed_to = {b for (_, b) in summary.renamed}
    assert "Rua X (2)" in renamed_to
    assert "Rua X (3)" in renamed_to

    roads = MapRepository(db_session).get_roads(ws.id)
    names = {r.name for r in roads}
    assert names == {"Rua X", "Rua X (2)", "Rua X (3)"}


# ---------------------------------------------------------------------------
# test_import_replace_existing_deletes_first
# ---------------------------------------------------------------------------


def test_import_replace_existing_deletes_first(db_session) -> None:  # type: ignore[no-untyped-def]
    ws = _create_workspace(db_session)
    coords_json = json.dumps([{"lat": -23.55, "lng": -46.63}, {"lat": -23.56, "lng": -46.64}])
    MapRepository(db_session).create_road(
        workspace_id=ws.id,
        name="Old Road",
        coordinates_json=coords_json,
        speed_limit_kmh=20,
        direction="two_way",
        width_meters=6.0,
    )
    assert len(MapRepository(db_session).get_roads(ws.id)) == 1

    parsed = [_make_parsed_road("New Road", osm_id=10)]
    summary = OsmImporter(db_session).import_roads(ws.id, parsed, replace_existing=True)

    assert summary.deleted_existing == 1
    assert summary.created_count == 1

    roads = MapRepository(db_session).get_roads(ws.id)
    assert len(roads) == 1
    assert roads[0].name == "New Road"


# ---------------------------------------------------------------------------
# test_import_empty_list_creates_nothing
# ---------------------------------------------------------------------------


def test_import_empty_list_creates_nothing(db_session) -> None:  # type: ignore[no-untyped-def]
    ws = _create_workspace(db_session)
    summary = OsmImporter(db_session).import_roads(ws.id, [])

    assert summary.created_count == 0
    assert summary.deleted_existing == 0
    assert MapRepository(db_session).get_roads(ws.id) == []


# ---------------------------------------------------------------------------
# test_import_preserves_coordinate_order
# ---------------------------------------------------------------------------


def test_import_preserves_coordinate_order(db_session) -> None:  # type: ignore[no-untyped-def]
    ws = _create_workspace(db_session)
    coords = [
        GeoPoint(latitude=-23.550, longitude=-46.630),
        GeoPoint(latitude=-23.551, longitude=-46.631),
        GeoPoint(latitude=-23.552, longitude=-46.632),
    ]
    parsed = [_make_parsed_road("Rua Ordenada", coords=coords)]
    OsmImporter(db_session).import_roads(ws.id, parsed)

    roads = MapRepository(db_session).get_roads(ws.id)
    assert len(roads) == 1
    road_coords = roads[0].coordinates
    assert len(road_coords) == 3
    # Verify order preserved
    for i, expected in enumerate(coords):
        assert road_coords[i].latitude == pytest.approx(expected.latitude)
        assert road_coords[i].longitude == pytest.approx(expected.longitude)
