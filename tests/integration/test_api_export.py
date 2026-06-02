from __future__ import annotations

import json

ROAD_PAYLOAD = {
    "name": "Rua Exportável",
    "coordinates": [{"lat": -20.81, "lng": -49.37}, {"lat": -20.82, "lng": -49.37}],
    "speed_limit_kmh": 30,
    "direction": "two_way",
    "width_meters": 6.0,
}

WAYPOINT_PAYLOAD = {
    "name": "Parada",
    "waypoint_type": "landmark",
    "lat": -20.815,
    "lng": -49.37,
    "road_name": "Rua Exportável",
}


def _setup_published(client):  # type: ignore[no-untyped-def]
    r = client.post("/api/v1/projects", json={"name": "Export Test"})
    project_id = r.json()["id"]
    ws_id = client.get(f"/api/v1/projects/{project_id}/workspace").json()["id"]
    client.post(f"/api/v1/workspaces/{ws_id}/roads", json=ROAD_PAYLOAD)
    client.post(f"/api/v1/workspaces/{ws_id}/waypoints", json=WAYPOINT_PAYLOAD)
    ver_r = client.post(f"/api/v1/workspaces/{ws_id}/publish", json={"version_name": "v1.0"})
    version_id = ver_r.json()["id"]
    return project_id, ws_id, version_id


def test_export_published_version(client) -> None:  # type: ignore[no-untyped-def]
    _, _, version_id = _setup_published(client)
    r = client.post(f"/api/v1/versions/{version_id}/export", json={})
    assert r.status_code == 201
    data = r.json()
    assert data["version_id"] == version_id
    assert data["export_id"] > 0
    assert data["file_size_bytes"] > 0


def test_export_json_valid(client) -> None:  # type: ignore[no-untyped-def]
    _, _, version_id = _setup_published(client)
    export_r = client.post(f"/api/v1/versions/{version_id}/export", json={})
    assert export_r.status_code == 201
    # Download the export
    dl_r = client.get(f"/api/v1/versions/{version_id}/export/download")
    assert dl_r.status_code == 200
    data = json.loads(dl_r.content)
    assert isinstance(data, dict)
    assert "roads" in data
    assert "waypoints" in data
    assert "meta" in data


def test_export_json_passes_format(client) -> None:  # type: ignore[no-untyped-def]
    _, _, version_id = _setup_published(client)
    client.post(f"/api/v1/versions/{version_id}/export", json={})
    dl_r = client.get(f"/api/v1/versions/{version_id}/export/download")
    data = json.loads(dl_r.content)

    assert "meta" in data
    assert data["meta"]["schema_version"] == "1.0"

    if data["waypoints"]:
        wp = data["waypoints"][0]
        assert "type" in wp, "Guardian expects 'type' key, not 'waypoint_type'"
        assert "waypoint_type" not in wp


def test_download_export(client) -> None:  # type: ignore[no-untyped-def]
    _, _, version_id = _setup_published(client)
    client.post(f"/api/v1/versions/{version_id}/export", json={})
    r = client.get(f"/api/v1/versions/{version_id}/export/download")
    assert r.status_code == 200
    assert len(r.content) > 0


def test_export_history_recorded(client) -> None:  # type: ignore[no-untyped-def]
    project_id, _, version_id = _setup_published(client)
    client.post(f"/api/v1/versions/{version_id}/export", json={})
    r = client.get(f"/api/v1/projects/{project_id}/exports")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["version_id"] == version_id
