from __future__ import annotations


def _setup(client):  # type: ignore[no-untyped-def]
    r = client.post("/api/v1/projects", json={"name": "Crossroad Detect Test"})
    proj_id = r.json()["id"]
    ws_id = client.get(f"/api/v1/projects/{proj_id}/workspace").json()["id"]
    return proj_id, ws_id


def _make_road(client, ws_id: int, name: str, coords: list) -> int:  # type: ignore[no-untyped-def]
    r = client.post(f"/api/v1/workspaces/{ws_id}/roads", json={
        "name": name,
        "coordinates": coords,
        "speed_limit_kmh": 20,
        "direction": "two_way",
        "width_meters": 6.0,
    })
    assert r.status_code == 201, f"create_road failed: {r.text}"
    return r.json()["id"]


def test_detect_crossroads_creates_intersection(client) -> None:  # type: ignore[no-untyped-def]
    """POST /crossroads/detect must run the geometry engine and create the
    crossroad where two roads cross. Regression for the bug where the endpoint
    built GeometryEngine() with no epsg argument and 500'd."""
    _, ws_id = _setup(client)
    # Two roads that cross near (-20.81, -49.38): one N-S, one E-W.
    _make_road(client, ws_id, "Rua Norte-Sul",
               [{"lat": -20.815, "lng": -49.380}, {"lat": -20.805, "lng": -49.380}])
    _make_road(client, ws_id, "Rua Leste-Oeste",
               [{"lat": -20.810, "lng": -49.385}, {"lat": -20.810, "lng": -49.375}])

    r = client.post(f"/api/v1/workspaces/{ws_id}/crossroads/detect")
    assert r.status_code == 200, r.text
    created = r.json()
    assert len(created) == 1
    names = {created[0]["road_a_name"], created[0]["road_b_name"]}
    assert names == {"Rua Norte-Sul", "Rua Leste-Oeste"}
    # Intersection near the crossing point.
    assert abs(created[0]["lat"] - (-20.810)) < 1e-3
    assert abs(created[0]["lng"] - (-49.380)) < 1e-3


def test_detect_crossroads_is_idempotent(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    _make_road(client, ws_id, "Rua Norte-Sul",
               [{"lat": -20.815, "lng": -49.380}, {"lat": -20.805, "lng": -49.380}])
    _make_road(client, ws_id, "Rua Leste-Oeste",
               [{"lat": -20.810, "lng": -49.385}, {"lat": -20.810, "lng": -49.375}])

    first = client.post(f"/api/v1/workspaces/{ws_id}/crossroads/detect")
    assert len(first.json()) == 1
    # Second run creates nothing new (pair already has a crossroad).
    second = client.post(f"/api/v1/workspaces/{ws_id}/crossroads/detect")
    assert second.status_code == 200
    assert second.json() == []
    # Still exactly one crossroad recorded.
    listed = client.get(f"/api/v1/workspaces/{ws_id}/crossroads")
    assert len(listed.json()) == 1


def test_detect_crossroads_no_roads_returns_empty(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    r = client.post(f"/api/v1/workspaces/{ws_id}/crossroads/detect")
    assert r.status_code == 200
    assert r.json() == []
