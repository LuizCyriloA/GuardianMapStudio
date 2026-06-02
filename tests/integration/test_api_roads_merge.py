from __future__ import annotations


def _setup(client):  # type: ignore[no-untyped-def]
    r = client.post("/api/v1/projects", json={"name": "Merge Test"})
    proj_id = r.json()["id"]
    ws_id = client.get(f"/api/v1/projects/{proj_id}/workspace").json()["id"]
    return proj_id, ws_id


def _make_road(client, ws_id: int, name: str, coords: list | None = None) -> int:  # type: ignore[no-untyped-def]
    if coords is None:
        coords = [{"lat": -20.81, "lng": -49.38}, {"lat": -20.82, "lng": -49.38}]
    r = client.post(f"/api/v1/workspaces/{ws_id}/roads", json={
        "name": name,
        "coordinates": coords,
        "speed_limit_kmh": 20,
        "direction": "two_way",
        "width_meters": 6.0,
    })
    assert r.status_code == 201, f"create_road failed: {r.text}"
    return r.json()["id"]


# ---------------------------------------------------------------------------
# test_list_duplicate_groups_empty_when_unique_names
# ---------------------------------------------------------------------------


def test_list_duplicate_groups_empty_when_unique_names(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    _make_road(client, ws_id, "Rua A")
    _make_road(client, ws_id, "Rua B", [{"lat": -20.83, "lng": -49.38}, {"lat": -20.84, "lng": -49.38}])

    r = client.get(f"/api/v1/workspaces/{ws_id}/roads/duplicate-groups")
    assert r.status_code == 200
    assert r.json()["groups"] == []


# ---------------------------------------------------------------------------
# test_list_duplicate_groups_finds_osm_suffix_pattern
# ---------------------------------------------------------------------------


def test_list_duplicate_groups_finds_osm_suffix_pattern(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    _make_road(client, ws_id, "Rua A")
    _make_road(client, ws_id, "Rua A (2)", [{"lat": -20.82, "lng": -49.38}, {"lat": -20.83, "lng": -49.38}])
    _make_road(client, ws_id, "Rua A (3)", [{"lat": -20.83, "lng": -49.38}, {"lat": -20.84, "lng": -49.38}])

    r = client.get(f"/api/v1/workspaces/{ws_id}/roads/duplicate-groups")
    assert r.status_code == 200
    groups = r.json()["groups"]
    assert len(groups) == 1
    assert groups[0]["base_name"] == "Rua A"
    assert len(groups[0]["road_ids"]) == 3
    assert groups[0]["total_points"] == 6


# ---------------------------------------------------------------------------
# test_list_duplicate_groups_ignores_singletons
# ---------------------------------------------------------------------------


def test_list_duplicate_groups_ignores_singletons(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    _make_road(client, ws_id, "Rua A")
    _make_road(client, ws_id, "Rua B (2)", [{"lat": -20.82, "lng": -49.38}, {"lat": -20.83, "lng": -49.38}])

    r = client.get(f"/api/v1/workspaces/{ws_id}/roads/duplicate-groups")
    assert r.status_code == 200
    # "Rua B (2)" has no "Rua B" → not a duplicate group
    assert r.json()["groups"] == []


# ---------------------------------------------------------------------------
# test_merge_two_roads_returns_200
# ---------------------------------------------------------------------------


def test_merge_two_roads_returns_200(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    id1 = _make_road(client, ws_id, "Rua A")
    id2 = _make_road(client, ws_id, "Rua A (2)", [{"lat": -20.82, "lng": -49.38}, {"lat": -20.83, "lng": -49.38}])

    r = client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [{"target_name": "Rua A", "source_road_ids": [id1, id2]}],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["workspace_id"] == ws_id
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["target_name"] == "Rua A"
    assert result["merged_road_id"] == id1
    assert id2 in result["deleted_road_ids"]


# ---------------------------------------------------------------------------
# test_merge_updates_waypoint_road_name
# ---------------------------------------------------------------------------


def test_merge_updates_waypoint_road_name(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    id1 = _make_road(client, ws_id, "Rua A")
    id2 = _make_road(client, ws_id, "Rua A (2)", [{"lat": -20.82, "lng": -49.38}, {"lat": -20.83, "lng": -49.38}])

    # Waypoint referencing the second road (which will be deleted)
    client.post(f"/api/v1/workspaces/{ws_id}/waypoints", json={
        "name": "WP1", "waypoint_type": "stop_sign",
        "lat": -20.821, "lng": -49.38, "road_name": "Rua A (2)",
    })

    r = client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [{"target_name": "Rua A Merged", "source_road_ids": [id1, id2]}],
    })
    assert r.status_code == 200
    assert r.json()["results"][0]["reassigned_waypoints"] == 1

    # Verify waypoint now references the merged road name
    wps = client.get(f"/api/v1/workspaces/{ws_id}/waypoints").json()
    assert wps[0]["road_name"] == "Rua A Merged"


# ---------------------------------------------------------------------------
# test_merge_updates_crossroad_road_names
# ---------------------------------------------------------------------------


def test_merge_updates_crossroad_road_names(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    id1 = _make_road(client, ws_id, "Rua A")
    id2 = _make_road(client, ws_id, "Rua A (2)", [{"lat": -20.82, "lng": -49.38}, {"lat": -20.83, "lng": -49.38}])
    _make_road(client, ws_id, "Rua B", [{"lat": -20.84, "lng": -49.38}, {"lat": -20.85, "lng": -49.38}])

    client.post(f"/api/v1/workspaces/{ws_id}/crossroads", json={
        "road_a_name": "Rua A (2)", "road_b_name": "Rua B",
        "lat": -20.825, "lng": -49.38,
    })

    r = client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [{"target_name": "Rua A", "source_road_ids": [id1, id2]}],
    })
    assert r.status_code == 200
    assert r.json()["results"][0]["reassigned_crossroads"] == 1

    crs = client.get(f"/api/v1/workspaces/{ws_id}/crossroads").json()
    assert crs[0]["road_a_name"] == "Rua A"


# ---------------------------------------------------------------------------
# test_merge_deletes_source_roads
# ---------------------------------------------------------------------------


def test_merge_deletes_source_roads(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    id1 = _make_road(client, ws_id, "Rua A")
    id2 = _make_road(client, ws_id, "Rua A (2)", [{"lat": -20.82, "lng": -49.38}, {"lat": -20.83, "lng": -49.38}])

    client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [{"target_name": "Rua A", "source_road_ids": [id1, id2]}],
    })

    roads = client.get(f"/api/v1/workspaces/{ws_id}/roads").json()
    road_ids = [r["id"] for r in roads]
    assert id1 in road_ids    # target preserved
    assert id2 not in road_ids  # source deleted


# ---------------------------------------------------------------------------
# test_merge_preserves_target_road_id
# ---------------------------------------------------------------------------


def test_merge_preserves_target_road_id(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    id1 = _make_road(client, ws_id, "Rua A")
    id2 = _make_road(client, ws_id, "Rua A (2)", [{"lat": -20.82, "lng": -49.38}, {"lat": -20.83, "lng": -49.38}])

    r = client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [{"target_name": "Rua A", "source_road_ids": [id1, id2]}],
    })
    # The first source road's id is preserved
    assert r.json()["results"][0]["merged_road_id"] == id1


# ---------------------------------------------------------------------------
# test_merge_validation_runs_after
# ---------------------------------------------------------------------------


def test_merge_validation_runs_after(client) -> None:  # type: ignore[no-untyped-def]
    proj_id, ws_id = _setup(client)
    id1 = _make_road(client, ws_id, "Rua A")
    id2 = _make_road(client, ws_id, "Rua A (2)", [{"lat": -20.82, "lng": -49.38}, {"lat": -20.83, "lng": -49.38}])

    client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [{"target_name": "Rua A", "source_road_ids": [id1, id2]}],
    })

    ws = client.get(f"/api/v1/projects/{proj_id}/workspace").json()
    assert ws["last_validated_at"] is not None


# ---------------------------------------------------------------------------
# test_merge_rejected_on_published_workspace_409
# ---------------------------------------------------------------------------


def test_merge_rejected_on_published_workspace_409(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    id1 = _make_road(client, ws_id, "Rua A")
    id2 = _make_road(client, ws_id, "Rua A (2)", [{"lat": -20.82, "lng": -49.38}, {"lat": -20.83, "lng": -49.38}])

    client.post(f"/api/v1/workspaces/{ws_id}/publish", json={"version_name": "v1"})

    r = client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [{"target_name": "Rua A", "source_road_ids": [id1, id2]}],
    })
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "workspace_not_draft"


# ---------------------------------------------------------------------------
# test_merge_rejected_with_unknown_road_id_404
# ---------------------------------------------------------------------------


def test_merge_rejected_with_unknown_road_id_404(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    id1 = _make_road(client, ws_id, "Rua A")

    r = client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [{"target_name": "Rua A", "source_road_ids": [id1, 99999]}],
    })
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "not_found"


# ---------------------------------------------------------------------------
# test_merge_rejected_with_road_in_multiple_groups_422
# ---------------------------------------------------------------------------


def test_merge_rejected_with_road_in_multiple_groups_422(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    id1 = _make_road(client, ws_id, "Rua A")
    id2 = _make_road(client, ws_id, "Rua A (2)", [{"lat": -20.82, "lng": -49.38}, {"lat": -20.83, "lng": -49.38}])
    id3 = _make_road(client, ws_id, "Rua B", [{"lat": -20.84, "lng": -49.38}, {"lat": -20.85, "lng": -49.38}])

    r = client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [
            {"target_name": "Rua A", "source_road_ids": [id1, id2]},
            {"target_name": "Rua B", "source_road_ids": [id2, id3]},  # id2 duplicated
        ],
    })
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "merge_duplicate_source"


# ---------------------------------------------------------------------------
# test_merge_rejected_with_single_road_in_group_422
# ---------------------------------------------------------------------------


def test_merge_rejected_with_single_road_in_group_422(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    id1 = _make_road(client, ws_id, "Rua A")

    r = client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [{"target_name": "Rua A", "source_road_ids": [id1]}],
    })
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "merge_insufficient_roads"


# ---------------------------------------------------------------------------
# test_merge_gaps_reported_in_response
# ---------------------------------------------------------------------------


def test_merge_gaps_reported_in_response(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    # Roads far apart — gap >> 1.0m
    id1 = _make_road(client, ws_id, "Rua A",
                     [{"lat": -20.81, "lng": -49.38}, {"lat": -20.82, "lng": -49.38}])
    id2 = _make_road(client, ws_id, "Rua A (2)",
                     [{"lat": -20.85, "lng": -49.38}, {"lat": -20.86, "lng": -49.38}])

    r = client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [{"target_name": "Rua A", "source_road_ids": [id1, id2]}],
    })
    assert r.status_code == 200
    result = r.json()["results"][0]
    assert len(result["gaps_meters"]) == 1
    assert result["gaps_meters"][0] > 1.0


# ---------------------------------------------------------------------------
# test_merge_two_groups_in_one_request
# ---------------------------------------------------------------------------


def test_merge_two_groups_in_one_request(client) -> None:  # type: ignore[no-untyped-def]
    _, ws_id = _setup(client)
    a1 = _make_road(client, ws_id, "Rua A")
    a2 = _make_road(client, ws_id, "Rua A (2)", [{"lat": -20.82, "lng": -49.38}, {"lat": -20.83, "lng": -49.38}])
    b1 = _make_road(client, ws_id, "Rua B", [{"lat": -20.84, "lng": -49.38}, {"lat": -20.85, "lng": -49.38}])
    b2 = _make_road(client, ws_id, "Rua B (2)", [{"lat": -20.85, "lng": -49.38}, {"lat": -20.86, "lng": -49.38}])

    r = client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [
            {"target_name": "Rua A", "source_road_ids": [a1, a2]},
            {"target_name": "Rua B", "source_road_ids": [b1, b2]},
        ],
    })
    assert r.status_code == 200
    assert len(r.json()["results"]) == 2

    roads = client.get(f"/api/v1/workspaces/{ws_id}/roads").json()
    road_names = {r["name"] for r in roads}
    assert "Rua A" in road_names
    assert "Rua B" in road_names
    assert "Rua A (2)" not in road_names
    assert "Rua B (2)" not in road_names


# ---------------------------------------------------------------------------
# test_full_flow_osm_import_then_detect_then_merge
# ---------------------------------------------------------------------------


def test_full_flow_osm_import_then_detect_then_merge(client) -> None:  # type: ignore[no-untyped-def]
    from pathlib import Path

    _, ws_id = _setup(client)

    fixture = Path(__file__).parent.parent / "fixtures" / "sample_condominio.osm"
    osm_bytes = fixture.read_bytes()

    # Preview and import all OSM roads
    preview = client.post(
        f"/api/v1/workspaces/{ws_id}/osm/preview",
        content=osm_bytes,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert preview.status_code == 200
    roads_dto = preview.json()["roads"]

    imp = client.post(f"/api/v1/workspaces/{ws_id}/osm/import",
                      json={"roads": roads_dto, "replace_existing": False})
    assert imp.status_code == 201
    assert imp.json()["created_count"] > 0

    # Detect duplicate groups (OSM import creates suffixed duplicates)
    dup = client.get(f"/api/v1/workspaces/{ws_id}/roads/duplicate-groups")
    assert dup.status_code == 200
    groups = dup.json()["groups"]
    # sample_condominio.osm has "Rua das Palmeiras" + "Rua das Palmeiras" → one group
    assert len(groups) >= 1

    # Merge the first group
    first_group = groups[0]
    merge_r = client.post(f"/api/v1/workspaces/{ws_id}/roads/merge", json={
        "groups": [{
            "target_name": first_group["base_name"],
            "source_road_ids": first_group["road_ids"],
        }],
    })
    assert merge_r.status_code == 200
    result = merge_r.json()["results"][0]
    assert result["target_name"] == first_group["base_name"]
    # All source roads minus 1 were deleted
    assert len(result["deleted_road_ids"]) == len(first_group["road_ids"]) - 1
