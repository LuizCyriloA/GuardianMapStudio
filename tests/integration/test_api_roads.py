from __future__ import annotations

ROAD_A = {
    "name": "Rua A",
    "coordinates": [{"lat": -20.81, "lng": -49.37}, {"lat": -20.82, "lng": -49.37}],
    "speed_limit_kmh": 30,
    "direction": "two_way",
    "width_meters": 6.0,
}


def _setup(client):  # type: ignore[no-untyped-def]
    r = client.post("/api/v1/projects", json={"name": "Road Test"})
    project_id = r.json()["id"]
    ws_id = client.get(f"/api/v1/projects/{project_id}/workspace").json()["id"]
    return project_id, ws_id


def test_create_road_returns_201(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    r = client.post(f"/api/v1/workspaces/{ws_id}/roads", json=ROAD_A)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Rua A"
    assert data["id"] > 0


def test_create_road_duplicate_name_409(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    client.post(f"/api/v1/workspaces/{ws_id}/roads", json=ROAD_A)
    r = client.post(f"/api/v1/workspaces/{ws_id}/roads", json=ROAD_A)
    assert r.status_code == 409


def test_delete_road_with_waypoints_409(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    road_r = client.post(f"/api/v1/workspaces/{ws_id}/roads", json=ROAD_A)
    road_id = road_r.json()["id"]
    client.post(f"/api/v1/workspaces/{ws_id}/waypoints", json={
        "name": "WP",
        "waypoint_type": "landmark",
        "lat": -20.815,
        "lng": -49.37,
        "road_name": "Rua A",
    })
    r = client.delete(f"/api/v1/workspaces/{ws_id}/roads/{road_id}")
    assert r.status_code == 409


def test_update_road_coordinates(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    road_id = client.post(f"/api/v1/workspaces/{ws_id}/roads", json=ROAD_A).json()["id"]
    new_coords = [{"lat": -20.81, "lng": -49.37}, {"lat": -20.83, "lng": -49.37}, {"lat": -20.85, "lng": -49.37}]
    r = client.patch(f"/api/v1/workspaces/{ws_id}/roads/{road_id}", json={"coordinates": new_coords})
    assert r.status_code == 200
    assert len(r.json()["coordinates"]) == 3


def test_delete_road_204(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    road_id = client.post(f"/api/v1/workspaces/{ws_id}/roads", json=ROAD_A).json()["id"]
    r = client.delete(f"/api/v1/workspaces/{ws_id}/roads/{road_id}")
    assert r.status_code == 204
    # Verify it's gone
    assert client.get(f"/api/v1/workspaces/{ws_id}/roads/{road_id}").status_code == 404


def test_validation_runs_after_create(client) -> None:  # type: ignore[no-untyped-def]
    project_id, ws_id = _setup(client)
    client.post(f"/api/v1/workspaces/{ws_id}/roads", json=ROAD_A)
    ws = client.get(f"/api/v1/projects/{project_id}/workspace").json()
    # After creating one road without waypoints, workspace should reflect updated validation state
    assert "has_validation_errors" in ws
