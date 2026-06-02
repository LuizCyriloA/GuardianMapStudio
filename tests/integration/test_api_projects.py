from __future__ import annotations


def test_create_project_returns_201(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post("/api/v1/projects", json={"name": "Project A", "description": "desc"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Project A"
    assert data["id"] > 0


def test_create_project_creates_workspace(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post("/api/v1/projects", json={"name": "Project B"})
    project_id = r.json()["id"]
    ws_r = client.get(f"/api/v1/projects/{project_id}/workspace")
    assert ws_r.status_code == 200
    ws = ws_r.json()
    assert ws["state"] == "draft"
    assert ws["project_id"] == project_id


def test_list_projects_empty(client) -> None:  # type: ignore[no-untyped-def]
    r = client.get("/api/v1/projects")
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_projects_with_data(client) -> None:  # type: ignore[no-untyped-def]
    client.post("/api/v1/projects", json={"name": "P1"})
    client.post("/api/v1/projects", json={"name": "P2"})
    r = client.get("/api/v1/projects")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    names = [p["name"] for p in data["items"]]
    assert "P1" in names
    assert "P2" in names


def test_get_project_by_id(client) -> None:  # type: ignore[no-untyped-def]
    create_r = client.post("/api/v1/projects", json={"name": "Specific"})
    pid = create_r.json()["id"]
    r = client.get(f"/api/v1/projects/{pid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Specific"


def test_get_project_not_found(client) -> None:  # type: ignore[no-untyped-def]
    r = client.get("/api/v1/projects/99999")
    assert r.status_code == 404
