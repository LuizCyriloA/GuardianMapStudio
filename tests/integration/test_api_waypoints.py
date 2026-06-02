from __future__ import annotations

ROAD_PAYLOAD = {
    "name": "Rua A",
    "coordinates": [{"lat": -20.81, "lng": -49.37}, {"lat": -20.82, "lng": -49.37}],
    "speed_limit_kmh": 30,
    "direction": "two_way",
    "width_meters": 6.0,
}


def _setup(client):  # type: ignore[no-untyped-def]
    r = client.post("/api/v1/projects", json={"name": "WP Test"})
    project_id = r.json()["id"]
    ws_id = client.get(f"/api/v1/projects/{project_id}/workspace").json()["id"]
    client.post(f"/api/v1/workspaces/{ws_id}/roads", json=ROAD_PAYLOAD)
    return project_id, ws_id


def test_create_waypoint_returns_201(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    r = client.post(f"/api/v1/workspaces/{ws_id}/waypoints", json={
        "name": "Parada",
        "waypoint_type": "landmark",
        "lat": -20.815,
        "lng": -49.37,
        "road_name": "Rua A",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Parada"
    assert data["id"] > 0


def test_create_waypoint_snap_applied(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    # Place waypoint 0.3m from road endpoint (-20.81, -49.37)
    snap_lat = -20.81 + 2.71e-6
    r = client.post(f"/api/v1/workspaces/{ws_id}/waypoints", json={
        "name": "Snap WP",
        "waypoint_type": "landmark",
        "lat": snap_lat,
        "lng": -49.37,
    })
    assert r.status_code == 201
    data = r.json()
    # Should snap to road endpoint
    assert abs(data["lat"] - (-20.81)) < 1e-5
    assert abs(data["lng"] - (-49.37)) < 1e-8


def test_create_speed_bump_no_height_422(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    r = client.post(f"/api/v1/workspaces/{ws_id}/waypoints", json={
        "name": "Lombada",
        "waypoint_type": "speed_bump",
        "lat": -20.815,
        "lng": -49.37,
        "extra_data": {},
    })
    assert r.status_code == 422


def test_create_gate_invalid_type_422(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    r = client.post(f"/api/v1/workspaces/{ws_id}/waypoints", json={
        "name": "Gate",
        "waypoint_type": "gate",
        "lat": -20.815,
        "lng": -49.37,
        "extra_data": {"gate_type": "invalid"},
    })
    assert r.status_code == 422


def test_list_waypoints_by_type(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    client.post(f"/api/v1/workspaces/{ws_id}/waypoints", json={
        "name": "Stop",
        "waypoint_type": "stop_sign",
        "lat": -20.815,
        "lng": -49.37,
    })
    client.post(f"/api/v1/workspaces/{ws_id}/waypoints", json={
        "name": "Bump",
        "waypoint_type": "speed_bump",
        "lat": -20.816,
        "lng": -49.37,
        "extra_data": {"height_cm": 5},
    })

    all_r = client.get(f"/api/v1/workspaces/{ws_id}/waypoints")
    assert len(all_r.json()) == 2

    filtered = client.get(f"/api/v1/workspaces/{ws_id}/waypoints?type=stop_sign")
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["waypoint_type"] == "stop_sign"
