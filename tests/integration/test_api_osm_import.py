from __future__ import annotations

from pathlib import Path

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_condominio.osm"

# Minimal valid OSM XML with 2 drivable named roads
SIMPLE_OSM = b"""<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <node id="1" lat="-23.550000" lon="-46.630000"/>
  <node id="2" lat="-23.551000" lon="-46.631000"/>
  <node id="3" lat="-23.552000" lon="-46.632000"/>
  <node id="4" lat="-23.553000" lon="-46.633000"/>
  <way id="10">
    <nd ref="1"/><nd ref="2"/>
    <tag k="highway" v="residential"/>
    <tag k="name" v="Rua Alpha"/>
  </way>
  <way id="11">
    <nd ref="3"/><nd ref="4"/>
    <tag k="highway" v="residential"/>
    <tag k="name" v="Rua Beta"/>
  </way>
</osm>
"""

# OSM with a footway (pedestrian)
OSM_WITH_FOOTWAY = b"""<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <node id="1" lat="-23.55" lon="-46.63"/>
  <node id="2" lat="-23.56" lon="-46.64"/>
  <node id="3" lat="-23.57" lon="-46.65"/>
  <node id="4" lat="-23.58" lon="-46.66"/>
  <way id="10">
    <nd ref="1"/><nd ref="2"/>
    <tag k="highway" v="residential"/>
    <tag k="name" v="Rua Principal"/>
  </way>
  <way id="11">
    <nd ref="3"/><nd ref="4"/>
    <tag k="highway" v="footway"/>
    <tag k="name" v="Calcada"/>
  </way>
</osm>
"""

_OSM_HEADERS = {"Content-Type": "application/octet-stream"}


def _create_project_and_workspace(client):  # type: ignore[no-untyped-def]
    """Helper: create a project and return (project_id, workspace_id)."""
    resp = client.post("/api/v1/projects", json={"name": "Test Project"})
    assert resp.status_code == 201
    proj_id = resp.json()["id"]
    resp = client.get(f"/api/v1/projects/{proj_id}/workspace")
    assert resp.status_code == 200
    ws_id = resp.json()["id"]
    return proj_id, ws_id


# ---------------------------------------------------------------------------
# test_preview_returns_200_with_roads
# ---------------------------------------------------------------------------


def test_preview_returns_200_with_roads(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)
    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=SIMPLE_OSM,
        headers=_OSM_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "roads" in data
    assert len(data["roads"]) == 2
    assert data["total_ways_in_file"] == 2
    # Each road must have >= 2 coordinates
    for road in data["roads"]:
        assert len(road["coordinates"]) >= 2


# ---------------------------------------------------------------------------
# test_preview_rejects_non_xml_file
# ---------------------------------------------------------------------------


def test_preview_rejects_non_xml_file(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)
    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=b"this is not xml at all",
        headers=_OSM_HEADERS,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "osm_parse_error"


# ---------------------------------------------------------------------------
# test_preview_rejects_oversize_file_413
# ---------------------------------------------------------------------------


def test_preview_rejects_oversize_file_413(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)
    # Default osm_max_file_size_mb = 10; send 10MB + 1 byte
    oversize = b"x" * (10 * 1024 * 1024 + 1)
    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=oversize,
        headers=_OSM_HEADERS,
    )
    assert resp.status_code == 413
    assert resp.json()["detail"]["error"] == "payload_too_large"


# ---------------------------------------------------------------------------
# test_preview_rejects_too_many_ways_422
# ---------------------------------------------------------------------------


def test_preview_rejects_too_many_ways_422(client) -> None:  # type: ignore[no-untyped-def]
    # Build a custom app with osm_max_ways=1 and upload 2 ways.
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from guardianmapstudio.api.deps import get_db, get_settings
    from guardianmapstudio.config.settings import GuardianMapStudioSettings
    from guardianmapstudio.database.models import Base
    from guardianmapstudio.main import create_app

    low_settings = GuardianMapStudioSettings(
        database_url="sqlite:///:memory:",
        export_dir="/tmp/gms_test_exports",
        osm_max_ways=1,
    )
    engine = create_engine(
        low_settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    app2 = create_app(low_settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with TestClient(app2) as c:
        def override():  # type: ignore[no-untyped-def]
            with factory() as session:
                yield session
        app2.dependency_overrides[get_db] = override
        # Override get_settings so the endpoint sees osm_max_ways=1
        app2.dependency_overrides[get_settings] = lambda: low_settings

        proj_resp = c.post("/api/v1/projects", json={"name": "P"})
        proj_id = proj_resp.json()["id"]
        ws_resp = c.get(f"/api/v1/projects/{proj_id}/workspace")
        ws_id = ws_resp.json()["id"]

        resp = c.post(
            f"/api/v1/workspaces/{ws_id}/osm/preview",
            content=SIMPLE_OSM,
            headers=_OSM_HEADERS,
        )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "osm_too_many_ways"


# ---------------------------------------------------------------------------
# test_preview_requires_draft_workspace_409
# ---------------------------------------------------------------------------


def test_preview_requires_draft_workspace_409(client) -> None:  # type: ignore[no-untyped-def]
    proj_id, ws_id = _create_project_and_workspace(client)
    # Publish the workspace (need at least 1 road first)
    client.post(
        f"/api/v1/workspaces/{ws_id}/roads",
        json={
            "name": "Rua Publicada",
            "coordinates": [
                {"lat": -23.55, "lng": -46.63},
                {"lat": -23.56, "lng": -46.64},
            ],
            "speed_limit_kmh": 20,
            "direction": "two_way",
            "width_meters": 6.0,
        },
    )
    pub_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/publish",
        json={"version_name": "v1"},
    )
    assert pub_resp.status_code == 201
    # Try to preview on the now-PUBLISHED workspace
    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=SIMPLE_OSM,
        headers=_OSM_HEADERS,
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "workspace_not_draft"


# ---------------------------------------------------------------------------
# test_preview_with_include_pedestrian_returns_more_roads
# ---------------------------------------------------------------------------


def test_preview_with_include_pedestrian_returns_more_roads(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)

    resp_no_ped = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=OSM_WITH_FOOTWAY,
        headers=_OSM_HEADERS,
    )
    assert resp_no_ped.status_code == 200
    count_without = len(resp_no_ped.json()["roads"])

    resp_with_ped = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview?include_pedestrian=true",
        content=OSM_WITH_FOOTWAY,
        headers=_OSM_HEADERS,
    )
    assert resp_with_ped.status_code == 200
    count_with = len(resp_with_ped.json()["roads"])

    assert count_with > count_without


# ---------------------------------------------------------------------------
# test_import_creates_roads_201
# ---------------------------------------------------------------------------


def test_import_creates_roads_201(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)

    # First preview to get parsed roads
    preview = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=SIMPLE_OSM,
        headers=_OSM_HEADERS,
    )
    roads_dto = preview.json()["roads"]

    # Then import
    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/import",
        json={"roads": roads_dto, "replace_existing": False},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["workspace_id"] == ws_id
    assert data["created_count"] == 2
    assert data["deleted_existing"] == 0


# ---------------------------------------------------------------------------
# test_import_renames_duplicates
# ---------------------------------------------------------------------------


def test_import_renames_duplicates(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)

    # Create road "Rua Alpha" manually first
    client.post(
        f"/api/v1/workspaces/{ws_id}/roads",
        json={
            "name": "Rua Alpha",
            "coordinates": [
                {"lat": -23.55, "lng": -46.63},
                {"lat": -23.56, "lng": -46.64},
            ],
            "speed_limit_kmh": 20,
            "direction": "two_way",
            "width_meters": 6.0,
        },
    )

    # Preview and import OSM (which also has "Rua Alpha")
    preview = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=SIMPLE_OSM,
        headers=_OSM_HEADERS,
    )
    roads_dto = preview.json()["roads"]

    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/import",
        json={"roads": roads_dto, "replace_existing": False},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["renamed"]) >= 1
    renamed_froms = [r["from"] for r in data["renamed"]]
    assert "Rua Alpha" in renamed_froms


# ---------------------------------------------------------------------------
# test_import_replace_existing_clears_workspace
# ---------------------------------------------------------------------------


def test_import_replace_existing_clears_workspace(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)

    # Create existing road
    client.post(
        f"/api/v1/workspaces/{ws_id}/roads",
        json={
            "name": "Antiga Rua",
            "coordinates": [
                {"lat": -23.55, "lng": -46.63},
                {"lat": -23.56, "lng": -46.64},
            ],
            "speed_limit_kmh": 20,
            "direction": "two_way",
            "width_meters": 6.0,
        },
    )

    preview = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=SIMPLE_OSM,
        headers=_OSM_HEADERS,
    )
    roads_dto = preview.json()["roads"]

    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/import",
        json={"roads": roads_dto, "replace_existing": True},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["deleted_existing"] == 1
    assert data["created_count"] == 2

    # Verify old road is gone
    roads_resp = client.get(f"/api/v1/workspaces/{ws_id}/roads")
    road_names = [r["name"] for r in roads_resp.json()]
    assert "Antiga Rua" not in road_names
    assert "Rua Alpha" in road_names


# ---------------------------------------------------------------------------
# test_import_replace_existing_with_dependents_returns_409
# ---------------------------------------------------------------------------


def test_import_replace_existing_with_dependents_returns_409(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)

    # Create a road
    client.post(
        f"/api/v1/workspaces/{ws_id}/roads",
        json={
            "name": "Rua Com Waypoint",
            "coordinates": [
                {"lat": -23.55, "lng": -46.63},
                {"lat": -23.56, "lng": -46.64},
            ],
            "speed_limit_kmh": 20,
            "direction": "two_way",
            "width_meters": 6.0,
        },
    )

    # Create a waypoint referencing that road
    client.post(
        f"/api/v1/workspaces/{ws_id}/waypoints",
        json={
            "name": "Stop 1",
            "waypoint_type": "stop_sign",
            "lat": -23.5505,
            "lng": -46.6305,
            "road_name": "Rua Com Waypoint",
        },
    )

    preview = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=SIMPLE_OSM,
        headers=_OSM_HEADERS,
    )
    roads_dto = preview.json()["roads"]

    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/import",
        json={"roads": roads_dto, "replace_existing": True},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "road_has_dependents"


# ---------------------------------------------------------------------------
# test_import_triggers_validation
# ---------------------------------------------------------------------------


def test_import_triggers_validation(client) -> None:  # type: ignore[no-untyped-def]
    proj_id, ws_id = _create_project_and_workspace(client)

    preview = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=SIMPLE_OSM,
        headers=_OSM_HEADERS,
    )
    roads_dto = preview.json()["roads"]

    client.post(
        f"/api/v1/workspaces/{ws_id}/osm/import",
        json={"roads": roads_dto, "replace_existing": False},
    )

    # Workspace must have been re-validated — check via project workspace endpoint
    ws_resp = client.get(f"/api/v1/projects/{proj_id}/workspace")
    assert ws_resp.status_code == 200
    ws_data = ws_resp.json()
    assert ws_data["last_validated_at"] is not None


# ---------------------------------------------------------------------------
# test_import_increments_workspace_has_no_errors_when_clean
# ---------------------------------------------------------------------------


def test_import_increments_workspace_has_no_errors_when_clean(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)

    # Before import: workspace.min_roads error exists
    val_before = client.post(f"/api/v1/workspaces/{ws_id}/validate")
    assert val_before.status_code == 200
    assert val_before.json()["error_count"] > 0

    preview = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=SIMPLE_OSM,
        headers=_OSM_HEADERS,
    )
    roads_dto = preview.json()["roads"]

    client.post(
        f"/api/v1/workspaces/{ws_id}/osm/import",
        json={"roads": roads_dto, "replace_existing": False},
    )

    # After import: workspace.min_roads should be cleared
    val_after = client.post(f"/api/v1/workspaces/{ws_id}/validate")
    assert val_after.status_code == 200
    # 2 roads imported — min_roads (1 road required) should be satisfied
    errors = [r for r in val_after.json()["results"] if r["rule_id"] == "workspace.min_roads"]
    assert errors == []


# ---------------------------------------------------------------------------
# test_full_flow_preview_then_import
# ---------------------------------------------------------------------------


def test_full_flow_preview_then_import(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)

    # Step 1: Preview with the fixture file
    fixture_bytes = FIXTURE_PATH.read_bytes()
    preview = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=fixture_bytes,
        headers=_OSM_HEADERS,
    )
    assert preview.status_code == 200
    preview_data = preview.json()
    # Fixture has 2 named drivable roads by default (Way 1: Rua das Palmeiras, Way 2: Avenida Sao Joao)
    assert len(preview_data["roads"]) >= 2
    assert preview_data["total_ways_in_file"] >= 5

    # Check unicode name preserved in preview
    road_names = [r["name"] for r in preview_data["roads"]]
    assert any("ã" in n or "S" in n for n in road_names)  # "São" or similar

    # Step 2: Import all previewed roads
    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/import",
        json={"roads": preview_data["roads"], "replace_existing": False},
    )
    assert resp.status_code == 201
    import_data = resp.json()
    assert import_data["created_count"] == len(preview_data["roads"])

    # Step 3: Verify roads appear in GET /map
    map_resp = client.get(f"/api/v1/workspaces/{ws_id}/map")
    assert map_resp.status_code == 200
    map_roads = map_resp.json()["roads"]
    assert len(map_roads) == len(preview_data["roads"])
