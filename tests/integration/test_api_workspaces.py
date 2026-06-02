from __future__ import annotations

ROAD_PAYLOAD = {
    "name": "Rua Principal",
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
    "road_name": "Rua Principal",
}


def _create_project_and_workspace(client):  # type: ignore[no-untyped-def]
    r = client.post("/api/v1/projects", json={"name": "WS Test"})
    project_id = r.json()["id"]
    ws = client.get(f"/api/v1/projects/{project_id}/workspace").json()
    return project_id, ws["id"]


def test_get_workspace_for_project(client) -> None:  # type: ignore[no-untyped-def]
    project_id, ws_id = _create_project_and_workspace(client)
    r = client.get(f"/api/v1/projects/{project_id}/workspace")
    assert r.status_code == 200
    ws = r.json()
    assert ws["state"] == "draft"
    assert ws["id"] == ws_id


def test_validate_empty_workspace(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)
    r = client.post(f"/api/v1/workspaces/{ws_id}/validate", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["error_count"] > 0
    rule_ids = [res["rule_id"] for res in data["results"]]
    assert "workspace.min_roads" in rule_ids


def test_validate_valid_workspace(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)
    client.post(f"/api/v1/workspaces/{ws_id}/roads", json=ROAD_PAYLOAD)
    client.post(f"/api/v1/workspaces/{ws_id}/waypoints", json=WAYPOINT_PAYLOAD)
    r = client.post(f"/api/v1/workspaces/{ws_id}/validate", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["error_count"] == 0
    assert data["can_publish"] is True


def test_publish_blocked_by_errors(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)
    # Empty workspace has errors
    r = client.post(f"/api/v1/workspaces/{ws_id}/publish", json={"version_name": "v1"})
    assert r.status_code == 422


def test_publish_creates_version(client) -> None:  # type: ignore[no-untyped-def]
    project_id, ws_id = _create_project_and_workspace(client)
    client.post(f"/api/v1/workspaces/{ws_id}/roads", json=ROAD_PAYLOAD)
    client.post(f"/api/v1/workspaces/{ws_id}/waypoints", json=WAYPOINT_PAYLOAD)
    r = client.post(f"/api/v1/workspaces/{ws_id}/publish", json={"version_name": "v1.0"})
    assert r.status_code == 201
    ver = r.json()
    assert ver["version_number"] == 1
    assert ver["name"] == "v1.0"
    assert ver["project_id"] == project_id


def test_publish_creates_new_draft(client) -> None:  # type: ignore[no-untyped-def]
    project_id, ws_id = _create_project_and_workspace(client)
    client.post(f"/api/v1/workspaces/{ws_id}/roads", json=ROAD_PAYLOAD)
    client.post(f"/api/v1/workspaces/{ws_id}/waypoints", json=WAYPOINT_PAYLOAD)
    client.post(f"/api/v1/workspaces/{ws_id}/publish", json={"version_name": "v1"})
    # A new DRAFT workspace must exist
    ws_r = client.get(f"/api/v1/projects/{project_id}/workspace")
    assert ws_r.status_code == 200
    new_ws = ws_r.json()
    assert new_ws["state"] == "draft"
    assert new_ws["id"] != ws_id


def test_get_validation_cached(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _create_project_and_workspace(client)
    client.post(f"/api/v1/workspaces/{ws_id}/validate", json={})
    r = client.get(f"/api/v1/workspaces/{ws_id}/validation")
    assert r.status_code == 200
    data = r.json()
    assert "error_count" in data
    assert "results" in data
