# GuardianMapStudio — Editor UX Improvements v1 (Complementary Spec — Doc 16)

> **Status**: Complementary specification, applied on top of MVP01 + Doc 15 (OSM Import).
> **Type**: 10 distinct UX improvements + 1 new backend feature (road merge).
> **Author intent**: After using the editor with real OSM imports, the operator
> identified friction points and a few missing affordances. This doc resolves
> all of them while preserving every prior invariant.

---

## 1. Purpose & Scope

This document collects 10 distinct improvements requested after the
post-Doc-15 acceptance run. Each is small in isolation; together they make
the editor production-ready for the operator's day-to-day flow.

| # | Request | Type | Backend? | Frontend? |
|---|---|---|---|---|
| 1 | Unify duplicate roads after OSM import | New feature | Yes (1 endpoint) | Yes (modal) |
| 2 | Remove "Estrada" toolbar button | UI cleanup | No | Yes |
| 3 | On workspace load, re-center map on entities | UX | No | Yes |
| 4 | Show N/S/E/W cardinal points on the map | UX | No | Yes |
| 5 | Ensure Waypoint form opens reliably + reorder fields | Bug fix + UX | No | Yes |
| 6 | Click-to-select road: highlight whole polyline | UX | No | Yes |
| 7 | DELETE key on selected road → confirmation modal | UX | No | Yes |
| 8 | Rectangle selection: multi-select roads, bulk delete | New feature | No | Yes |
| 9 | Undo accidental deletion | Scoped feature | No | Yes |
| 10 | (Implicit, from #1) Detect duplicate groups for merge | New endpoint | Yes (1 endpoint) | Yes |

### 1.1 Relationship to other documents

| Doc | Relationship |
|---|---|
| 02 (Roadmap) | Full undo/redo stays MVP02. This doc adds a **scoped undo for delete only** — a strict subset. The MVP02 plan in §MVP02 is unaffected. |
| 04 (MVP01 Spec) | Adds WF-06 (merge), WF-07 (rectangle delete), WF-08 (undo). Existing WF-01..WF-05 unchanged. Adds NFR for keyboard shortcuts. |
| 08 (Domain Model) | **No change.** No new aggregate or enum. |
| 09 (API Spec) | Adds 2 new endpoints (`POST .../roads/merge`, `GET .../roads/duplicate-groups`). |
| 11 (Frontend Spec) | Adds 3 new components (CompassControl, ConfirmModal, MergeRoadsModal), modifies MapEditor, EntityForm, MapStore. |
| 13 (Implementation Blueprint) | Add as new "Stage 7 — Editor UX". Stages 1–6 unchanged. |
| 15 (OSM Import) | The merge feature in this doc is the natural complement: OSM imports tend to produce duplicates; merge fixes them in one click. |

### 1.2 What this is NOT

- Not the full undo/redo stack from MVP02 (that handles every operation:
  create, update, move, delete). This doc adds **only delete undo**.
- Not multi-entity rectangle selection across types. Rectangle select
  is **roads only** for MVP. Waypoints, crossroads, areas remain
  click-to-select.
- Not a polyline editor (vertex drag, vertex insert) — those stay MVP02.

---

## 2. Impact Analysis — What Stays, What Changes

### 2.1 What stays exactly the same

| Component | Status |
|---|---|
| All 11 database tables | **Unchanged** (no new table) |
| All SQLAlchemy models | **Unchanged** |
| Domain contracts and enums | **Unchanged** |
| Geometry engines (Geometry, Snap, Crossroad, Validation) | **Unchanged** |
| GuardianExporter & export format | **Unchanged** |
| All 35 existing API endpoints (33 original + 2 from Doc 15) | **Unchanged** |
| OSM Import endpoints from Doc 15 | **Unchanged** |
| Validation rules | **Unchanged** |
| Publish & Export workflows | **Unchanged** |
| Test coverage threshold (80%) | **Unchanged** |
| Restricted areas backend (still hidden in UI, intact in code) | **Unchanged** |
| Manual road drawing backend (POST/PATCH/DELETE /roads) | **Unchanged** (only UI button hidden) |

### 2.2 What changes

| Area | Change | Files touched |
|---|---|---|
| Backend dependencies | None added | — |
| Backend service | New `RoadMergeService` | `src/guardianmapstudio/geometry/road_merge.py` (new) |
| Backend schemas | Append merge DTOs | `api/schemas.py` (additive) |
| Backend router (roads) | 2 new endpoints | `api/routers/roads.py` (additive) |
| Frontend toolbar | Remove "Estrada", add "Mesclar" button | `MapEditor.vue` or toolbar component |
| Frontend components (new) | `CompassControl.vue`, `ConfirmModal.vue`, `MergeRoadsModal.vue`, `RectangleSelector.vue` (Leaflet handler) | `components/map/`, `components/common/` |
| Frontend components (modify) | `MapEditor.vue` (map init, selection, rectangle handler, DELETE key, undo button), `EntityForm.vue` (field reorder, reliability) | existing files |
| Frontend stores | New `useUndoStack` composable; `mapStore` getters | `stores/undo.ts` (new), `stores/map.ts` (additive) |
| Tests | New unit tests for merge service, new integration tests for merge endpoints | `tests/unit/test_road_merge.py`, `tests/integration/test_api_roads_merge.py` |

### 2.3 Why all changes are safe

- **No new tables, no migrations** — 11-tables invariant preserved.
- **No existing endpoint changes** — all additive.
- **Merge endpoint reuses existing repository methods** (`update_road`,
  `delete_road`, `get_waypoints`, `update_waypoint`, etc.) — no new
  database access patterns.
- **Undo is in-memory frontend only** — survives no refresh, no
  backend persistence, no risk of corrupted state.
- **Removing the "Estrada" button follows the same pattern as Doc 15
  removing "Área"**: backend stays intact, only the toolbar entry is
  hidden. Roads can still be created via OSM import or merge or
  direct API call.

---

## 3. Architecture Decisions

### ADR-16-01 — Merge is a backend transaction, not a frontend choreography

**Decision**: Road merging happens in a single `POST /workspaces/{id}/roads/merge`
endpoint that performs the entire operation atomically: concatenate polylines,
reassign waypoint road references, reassign crossroad road references, delete
source roads, create or update the merged road, all in one transaction.

**Rationale**:
- Doing this from the frontend requires 4+ sequential API calls. If any
  intermediate call fails, the workspace ends in a half-merged state
  with broken `road_name` references on waypoints/crossroads.
- A single transaction guarantees all-or-nothing semantics.
- Centralizes the polyline concatenation logic in one tested place.

**Trade-off**: The merge endpoint is the first endpoint that modifies
multiple entity types in one call. We accept this as a special case;
no other endpoint follows this pattern.

### ADR-16-02 — Polyline concatenation: greedy nearest-endpoint chain

**Decision**: To merge N polylines into one, repeatedly connect the
polyline whose endpoint is closest (in projected meters) to either
end of the current chain. If the closest gap exceeds 2× snap tolerance
(1.0 m), the polylines are concatenated **with a gap** and a WARNING
is included in the merge response so the operator knows the geometry
may be discontinuous.

**Rationale**:
- OSM-imported duplicates almost always share an endpoint within snap
  tolerance — they're segments of the same physical road that OSM
  split at a node. Greedy chaining handles this 95% case correctly.
- The 1.0 m threshold matches the existing `INTERSECTION_PROXIMITY_M`
  used by CrossroadEngine, keeping geometric thresholds consistent.
- For the rare case of true gaps, returning a warning instead of
  refusing keeps the operator in control.

**Alternative considered**: refuse to merge if gap > tolerance. Rejected
because it forces the operator into a manual workaround (delete + redraw)
that loses waypoint associations.

### ADR-16-03 — Undo is frontend-only, memory-only, delete-only

**Decision**: The undo stack lives in a Pinia store on the frontend.
It is cleared on workspace switch, on publish, and on page refresh.
It tracks **only delete operations**. Create, update, and move
operations are not undoable in this MVP.

**Rationale**:
- The user's explicit pain point is "I accidentally deleted a road
  and want it back." A 50-line composable solves exactly that.
- Full undo/redo is already scheduled for MVP02 (Roadmap §MVP02).
  Building a half-implementation now would conflict with the MVP02
  plan and create migration debt.
- Memory-only is fine: nobody expects undo to survive a browser
  refresh. The operator's mental model is "the back button works
  for a few seconds, then the action is permanent."
- Backend-stored undo would need a new table → violates the 11-tables
  invariant for a feature that's about to be redone properly in MVP02.

**Trade-off**: The operator cannot undo a deletion after refreshing
the page. Mitigation: the confirmation modal (§5.6) makes accidental
deletion much rarer.

### ADR-16-04 — Rectangle selection is roads-only for MVP

**Decision**: The rectangle drag selects only `Road` entities. Waypoints,
crossroads, and restricted areas inside the rectangle are NOT selected.

**Rationale**:
- The user's request explicitly mentions roads only.
- Mixed-type bulk operations raise UX questions (what does "delete all
  selected" mean when waypoints depend on selected roads?) that need
  a wider design pass.
- Roads-only keeps the implementation tight and the semantics clear.

**Future**: A later iteration can extend selection to waypoints and
crossroads; the selection store will be the natural extension point.

### ADR-16-05 — Cardinal compass is a custom Leaflet control, no plugin

**Decision**: Render the N/S/E/W compass as a custom `L.Control` with
inline SVG, positioned `topright`. No new npm dependency.

**Rationale**:
- A static compass (north is always up in EPSG:4326 Web Mercator tiles)
  is just an SVG icon. No rotation, no interactivity needed.
- Plugins like `leaflet-compass` add bundle weight and another
  dependency to maintain — for a static glyph that's 50 lines of SVG.

**Note**: If a future iteration adds map rotation (MVP04+ simulation
view), this decision should be revisited.

---

## 4. Backend Changes

### 4.1 New module: `geometry/road_merge.py`

Pure service module. Receives roads, returns the merged polyline
plus an audit of what was joined and what wasn't.

**File**: `src/guardianmapstudio/geometry/road_merge.py`

```python
from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from guardianmapstudio.domain.contracts import GeoPoint, Road, RoadDirection
from guardianmapstudio.geometry.engine import GeometryEngine

# Two endpoints within this distance (projected meters) are considered
# the same point during merge. Matches CrossroadEngine.INTERSECTION_PROXIMITY_M
# for consistency.
MERGE_JOIN_TOLERANCE_M = 1.0


@dataclass(frozen=True, slots=True)
class MergedPolyline:
    """Output of the merge geometry algorithm.

    coordinates: concatenated polyline in chain order.
    chain_order: ids of input roads in the order they were joined.
    gaps: list of (after_road_id, gap_meters) pairs for joins that
          exceeded MERGE_JOIN_TOLERANCE_M.
    reversed_roads: ids of roads whose coordinate order was reversed
                    to fit the chain (operator may want to verify
                    direction afterwards).
    """
    coordinates: list[GeoPoint]
    chain_order: list[int]
    gaps: list[tuple[int, float]]
    reversed_roads: list[int]


class RoadMergeService:
    """Concatenates multiple Road polylines into a single polyline.

    Uses a greedy nearest-endpoint chain:
      1. Start with the first road's coordinates as the chain.
      2. Repeatedly pick the unjoined road whose endpoint is closest
         to either end of the current chain.
      3. Reverse that road's coordinates if needed so its near endpoint
         touches the chain end.
      4. Append (or prepend) its remaining coordinates to the chain.
      5. If the gap at join time exceeds MERGE_JOIN_TOLERANCE_M, record
         a warning but proceed (avoids leaving operator with a half-merge).
    """

    def __init__(self, geo: GeometryEngine) -> None:
        self._geo = geo

    def merge(self, roads: list[Road]) -> MergedPolyline:
        """Merge the given roads into a single polyline.

        Roads are merged in greedy nearest-endpoint order, regardless
        of the input list order.

        Raises:
            ValueError: if `roads` has fewer than 2 entries or any
                        road has fewer than 2 points.
        """
        if len(roads) < 2:
            raise ValueError("merge() requires at least 2 roads")
        for r in roads:
            if len(r.coordinates) < 2:
                raise ValueError(
                    f"Road {r.id} has fewer than 2 points; cannot merge"
                )

        # Start with the first road
        first = roads[0]
        chain: list[GeoPoint] = list(first.coordinates)
        chain_order: list[int] = [first.id]
        reversed_ids: list[int] = []
        gaps: list[tuple[int, float]] = []

        remaining: dict[int, Road] = {r.id: r for r in roads[1:]}

        while remaining:
            best_id, best_op, best_dist = self._find_best_join(chain, remaining)
            road = remaining.pop(best_id)
            coords = list(road.coordinates)

            if best_op == "append_forward":
                # road.coordinates[0] is near chain[-1]
                if best_dist > 0:
                    chain.append(coords[0])  # join with snap to road start
                chain.extend(coords[1:])
            elif best_op == "append_reverse":
                # road.coordinates[-1] is near chain[-1]; reverse and append
                coords.reverse()
                reversed_ids.append(road.id)
                if best_dist > 0:
                    chain.append(coords[0])
                chain.extend(coords[1:])
            elif best_op == "prepend_forward":
                # road.coordinates[-1] is near chain[0]
                if best_dist > 0:
                    chain.insert(0, coords[-1])
                chain = coords[:-1] + chain
            elif best_op == "prepend_reverse":
                # road.coordinates[0] is near chain[0]; reverse and prepend
                coords.reverse()
                reversed_ids.append(road.id)
                if best_dist > 0:
                    chain.insert(0, coords[-1])
                chain = coords[:-1] + chain

            chain_order.append(road.id)

            if best_dist > MERGE_JOIN_TOLERANCE_M:
                gaps.append((road.id, best_dist))
                logger.warning(
                    "Road merge: joined road {} with gap of {:.2f}m",
                    road.id, best_dist,
                )

        return MergedPolyline(
            coordinates=chain,
            chain_order=chain_order,
            gaps=gaps,
            reversed_roads=reversed_ids,
        )

    def _find_best_join(
        self,
        chain: list[GeoPoint],
        remaining: dict[int, Road],
    ) -> tuple[int, str, float]:
        """Return (road_id, operation, distance_meters) for the best next join.

        Considers four operations per candidate road:
          - append_forward:  chain[-1] ↔ road.coords[0]
          - append_reverse:  chain[-1] ↔ road.coords[-1]
          - prepend_forward: chain[0]  ↔ road.coords[-1]
          - prepend_reverse: chain[0]  ↔ road.coords[0]
        """
        chain_start = chain[0]
        chain_end = chain[-1]
        best: tuple[int, str, float] | None = None

        for rid, road in remaining.items():
            r_start = road.coordinates[0]
            r_end = road.coordinates[-1]
            candidates = [
                (rid, "append_forward",  self._geo.haversine_distance(chain_end, r_start)),
                (rid, "append_reverse",  self._geo.haversine_distance(chain_end, r_end)),
                (rid, "prepend_forward", self._geo.haversine_distance(chain_start, r_end)),
                (rid, "prepend_reverse", self._geo.haversine_distance(chain_start, r_start)),
            ]
            for cand in candidates:
                if best is None or cand[2] < best[2]:
                    best = cand

        assert best is not None  # remaining is non-empty
        return best
```

### 4.2 Schema additions (`api/schemas.py`)

Append to the existing `schemas.py` — additive only.

```python
# --- Road Merge (appended) ---

class DuplicateGroupResponse(BaseModel):
    """One group of roads that appear to be duplicates of each other.

    Detected by stripping the OSM-suffix pattern from road names:
    "Rua A", "Rua A (2)", "Rua A (3)" → group with base_name "Rua A".
    """
    base_name: str
    road_ids: list[int]
    road_names: list[str]
    total_points: int       # sum of all coordinates across the group


class DuplicateGroupsResponse(BaseModel):
    groups: list[DuplicateGroupResponse]


class RoadMergeGroup(BaseModel):
    """One merge instruction: combine these source_road_ids into a new
    road named target_name. The first id in the list determines which
    road's attributes (direction, speed_limit, width) are kept."""
    target_name: str
    source_road_ids: list[int]


class RoadMergeRequest(BaseModel):
    groups: list[RoadMergeGroup]


class RoadMergeResultItem(BaseModel):
    target_name: str
    merged_road_id: int          # id of the resulting merged road
    source_road_ids: list[int]   # original ids that were combined
    deleted_road_ids: list[int]  # ids that no longer exist after merge
    total_coordinates: int       # length of the merged polyline
    reversed_road_ids: list[int] # source roads whose direction was flipped
    gaps_meters: list[float]     # gap sizes > 1.0m (warnings)
    reassigned_waypoints: int    # count of waypoints whose road_name was updated
    reassigned_crossroads: int   # count of crossroads with road_a/road_b updates


class RoadMergeResponse(BaseModel):
    workspace_id: int
    results: list[RoadMergeResultItem]
```

### 4.3 New router endpoints (`api/routers/roads.py`)

Append to the existing `roads.py` router — do not modify any existing
endpoint.

```python
# --- Duplicate detection & merge (appended) ---

import re
from collections import defaultdict

# Matches the OSM importer's suffix pattern: "Foo (2)", "Foo (3)", ...
_SUFFIX_RE = re.compile(r"^(.*) \((\d+)\)$")


def _strip_suffix(name: str) -> str:
    """Return the base name without the OSM dedup suffix.

    >>> _strip_suffix("Rua A")
    'Rua A'
    >>> _strip_suffix("Rua A (2)")
    'Rua A'
    >>> _strip_suffix("Rua A (10)")
    'Rua A'
    """
    m = _SUFFIX_RE.match(name)
    return m.group(1) if m else name


@router.get(
    "/{workspace_id}/roads/duplicate-groups",
    response_model=DuplicateGroupsResponse,
)
def list_duplicate_groups(
    workspace_id: int,
    db: DbSession,
) -> DuplicateGroupsResponse:
    """Detect groups of roads that share a base name.

    Used by the 'Mesclar ruas duplicadas' modal to suggest merge candidates.
    """
    repo = MapRepository(db)
    roads = repo.get_roads(workspace_id)

    by_base: dict[str, list[Road]] = defaultdict(list)
    for r in roads:
        by_base[_strip_suffix(r.name)].append(r)

    groups: list[DuplicateGroupResponse] = []
    for base_name, group_roads in by_base.items():
        if len(group_roads) < 2:
            continue
        groups.append(DuplicateGroupResponse(
            base_name=base_name,
            road_ids=[r.id for r in group_roads],
            road_names=[r.name for r in group_roads],
            total_points=sum(len(r.coordinates) for r in group_roads),
        ))
    return DuplicateGroupsResponse(groups=groups)


@router.post(
    "/{workspace_id}/roads/merge",
    response_model=RoadMergeResponse,
    status_code=status.HTTP_200_OK,
)
def merge_roads(
    workspace_id: int,
    payload: RoadMergeRequest,
    db: DbSession,
) -> RoadMergeResponse:
    """Merge groups of roads into single roads.

    For each group:
      1. Load all source roads.
      2. Concatenate polylines via RoadMergeService (greedy chain).
      3. Update the FIRST source road in place with the merged polyline
         and target_name (preserves id; cleaner audit trail).
      4. Reassign waypoints (road_name = old → target_name) for the
         remaining source roads.
      5. Reassign crossroads (road_a_name / road_b_name) for the
         remaining source roads.
      6. Delete the remaining source roads.

    All steps for all groups run in a single transaction. Validation
    runs once at the end.
    """
    _require_draft(workspace_id, db)

    map_repo = MapRepository(db)
    all_roads = {r.id: r for r in map_repo.get_roads(workspace_id)}

    # Validate the request before any write
    seen_ids: set[int] = set()
    for grp in payload.groups:
        if len(grp.source_road_ids) < 2:
            raise HTTPException(status_code=422, detail={
                "error": ErrorCode.MERGE_INSUFFICIENT_ROADS.value,
                "message": f"Group '{grp.target_name}' has fewer than 2 source roads",
                "detail": {"target_name": grp.target_name},
            })
        for rid in grp.source_road_ids:
            if rid not in all_roads:
                raise HTTPException(status_code=404, detail={
                    "error": ErrorCode.NOT_FOUND.value,
                    "message": f"Road id {rid} not found in workspace",
                    "detail": {"road_id": rid},
                })
            if rid in seen_ids:
                raise HTTPException(status_code=422, detail={
                    "error": ErrorCode.MERGE_DUPLICATE_SOURCE.value,
                    "message": f"Road id {rid} appears in multiple merge groups",
                    "detail": {"road_id": rid},
                })
            seen_ids.add(rid)

    # Build a GeometryEngine for the merge service
    all_points = [p for r in all_roads.values() for p in r.coordinates]
    avg_lat = sum(p.latitude for p in all_points) / len(all_points)
    avg_lng = sum(p.longitude for p in all_points) / len(all_points)
    geo = GeometryEngine.from_centroid(avg_lat, avg_lng)
    merge_service = RoadMergeService(geo)

    results: list[RoadMergeResultItem] = []
    try:
        for grp in payload.groups:
            roads_to_merge = [all_roads[rid] for rid in grp.source_road_ids]
            merged = merge_service.merge(roads_to_merge)

            # Update the first source road in place
            target_road = roads_to_merge[0]
            map_repo.update_road(
                road_id=target_road.id,
                name=grp.target_name,
                coordinates=merged.coordinates,
                # preserve direction/speed/width from the first road
            )

            # Reassign waypoints from the OTHER source roads to target_name
            old_names = [r.name for r in roads_to_merge[1:]]
            wp_count = 0
            for wp in map_repo.get_waypoints(workspace_id):
                if wp.road_name in old_names or wp.road_name == target_road.name:
                    if wp.road_name != grp.target_name:
                        map_repo.update_waypoint(
                            waypoint_id=wp.id, road_name=grp.target_name,
                        )
                        wp_count += 1

            # Reassign crossroads
            cr_count = 0
            for cr in map_repo.get_crossroads(workspace_id):
                changed = False
                new_a = cr.road_a_name
                new_b = cr.road_b_name
                if cr.road_a_name in old_names or cr.road_a_name == target_road.name:
                    if cr.road_a_name != grp.target_name:
                        new_a = grp.target_name
                        changed = True
                if cr.road_b_name in old_names or cr.road_b_name == target_road.name:
                    if cr.road_b_name != grp.target_name:
                        new_b = grp.target_name
                        changed = True
                if changed:
                    map_repo.update_crossroad(
                        crossroad_id=cr.id,
                        road_a_name=new_a, road_b_name=new_b,
                    )
                    cr_count += 1

            # Delete the other source roads
            deleted_ids: list[int] = []
            for r in roads_to_merge[1:]:
                map_repo.delete_road(r.id)
                deleted_ids.append(r.id)

            results.append(RoadMergeResultItem(
                target_name=grp.target_name,
                merged_road_id=target_road.id,
                source_road_ids=list(grp.source_road_ids),
                deleted_road_ids=deleted_ids,
                total_coordinates=len(merged.coordinates),
                reversed_road_ids=list(merged.reversed_roads),
                gaps_meters=[g[1] for g in merged.gaps],
                reassigned_waypoints=wp_count,
                reassigned_crossroads=cr_count,
            ))
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail={
            "error": ErrorCode.MERGE_FAILED.value,
            "message": str(e),
            "detail": {},
        }) from e
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail={
            "error": ErrorCode.DATABASE_ERROR.value,
            "message": "Database error during merge",
            "detail": {},
        }) from e

    _run_validation_after_write(workspace_id, db)
    db.commit()

    return RoadMergeResponse(workspace_id=workspace_id, results=results)
```

> **Note on `update_crossroad`**: the existing `MapRepository` may not
> have an `update_crossroad` method (the crossroad router only exposes
> POST/DELETE per Doc 09 §6). If absent, ADD it as part of Stage 7.B,
> following the same `_to_domain` pattern as `update_waypoint`. This
> is the only repository extension required.

### 4.4 ErrorCode additions (`api/errors.py`)

Append (only what is missing):

```python
class ErrorCode(str, Enum):
    # ... existing values ...
    MERGE_INSUFFICIENT_ROADS = "merge_insufficient_roads"
    MERGE_DUPLICATE_SOURCE = "merge_duplicate_source"
    MERGE_FAILED = "merge_failed"
```

### 4.5 Tests

#### `tests/unit/test_road_merge.py`

```
test_merge_two_roads_sharing_endpoint
test_merge_two_roads_with_small_gap_within_tolerance
test_merge_two_roads_with_large_gap_returns_warning
test_merge_three_roads_in_chain
test_merge_reverses_road_when_needed
test_merge_prepends_when_chain_start_is_nearest
test_merge_preserves_coordinate_order_within_road
test_merge_one_road_raises_value_error
test_merge_road_with_one_point_raises_value_error
test_merge_chain_order_reflects_greedy_selection
test_merge_handles_unicode_coordinates  # São Paulo / negative lat
```

#### `tests/integration/test_api_roads_merge.py`

```
test_list_duplicate_groups_empty_when_unique_names
test_list_duplicate_groups_finds_osm_suffix_pattern
test_list_duplicate_groups_ignores_singletons
test_merge_two_roads_returns_200
test_merge_updates_waypoint_road_name
test_merge_updates_crossroad_road_names
test_merge_deletes_source_roads
test_merge_preserves_target_road_id
test_merge_validation_runs_after
test_merge_rejected_on_published_workspace_409
test_merge_rejected_with_unknown_road_id_404
test_merge_rejected_with_road_in_multiple_groups_422
test_merge_rejected_with_single_road_in_group_422
test_merge_gaps_reported_in_response
test_merge_two_groups_in_one_request
test_full_flow_osm_import_then_detect_then_merge
```

Coverage target: `geometry/road_merge.py` ≥ 95%, merge endpoints ≥ 85%.
Overall project coverage stays ≥ 80%.

---

## 5. Frontend Changes

Each subsection is independent — they can be implemented in any order
within Stage 7.C, except where noted.

### 5.1 Remove the "Estrada" toolbar button

Same pattern as Doc 15's removal of the "Área" button.

**Delete only the toolbar button** bound to `drawingMode === 'road'`.

**Keep**:
- The `'road'` value in any `DrawingMode` TypeScript union
- The `setMode('road')` method
- The road-drawing handler `onMapClickRoadMode()` (or equivalent)
- The `roadsLayer` and all road rendering code
- `mapStore.createRoad`, `mapStore.updateRoad`, `mapStore.deleteRoad`
- `RoadForm.vue` (still used when clicking a road to edit it)

Roads are still creatable via OSM import (Doc 15) and the merge endpoint
(§4 above). Manual drawing is just no longer exposed in the UI.

### 5.2 Auto-center map on workspace load

In `MapEditor.vue`, after `this.fetchMap(workspace.id)` completes
successfully and entities are added to the Leaflet layers, call:

```typescript
methods: {
  recenterOnEntities() {
    const bounds = L.latLngBounds([])
    // Roads
    for (const road of this.mapStore.roads) {
      for (const pt of road.coordinates) bounds.extend([pt.lat, pt.lng])
    }
    // Waypoints
    for (const wp of this.mapStore.waypoints) {
      bounds.extend([wp.lat, wp.lng])
    }
    // Crossroads
    for (const cr of this.mapStore.crossroads) {
      bounds.extend([cr.lat, cr.lng])
    }
    // Restricted areas (still render even though no draw button)
    for (const area of this.mapStore.restrictedAreas) {
      for (const pt of area.polygon) bounds.extend([pt.lat, pt.lng])
    }

    if (bounds.isValid()) {
      this.map.fitBounds(bounds, {
        padding: [40, 40],   // 40px padding around the entities
        maxZoom: 19,         // do not zoom in farther than this
      })
    } else {
      // Empty workspace: center on Brazil (or a configured default)
      this.map.setView([-15.78, -47.93], 5)
    }
  },
},

async mounted() {
  this.$nextTick(async () => {
    this.initMap()
    await this.mapStore.fetchMap(this.workspace.id)
    this.renderAllEntities()
    this.recenterOnEntities()
  })
},
```

**Trigger conditions** (call `recenterOnEntities()`):
- After initial workspace load
- After a successful OSM import (the imported roads may be outside the
  current viewport)
- After a successful merge (the merged road may extend the bounding box)
- Add a small "🎯 Centralizar mapa" toolbar button so the operator can
  trigger it manually any time

**Do NOT** auto-center after every entity create/delete — that would be
disorienting during normal editing.

### 5.3 Cardinal points overlay (compass)

**New file**: `frontend/src/components/map/CompassControl.ts`

```typescript
import L from 'leaflet'

/**
 * Static compass rose displayed in the top-right corner of the map.
 *
 * No rotation, no interactivity. Maps in EPSG:4326 Web Mercator
 * always have North up.
 */
export const CompassControl = L.Control.extend({
  options: { position: 'topright' },

  onAdd(): HTMLElement {
    const div = L.DomUtil.create('div', 'gms-compass')
    div.innerHTML = `
      <svg viewBox="0 0 60 60" width="60" height="60" aria-label="Bússola N S L O">
        <circle cx="30" cy="30" r="28" fill="white" stroke="#222" stroke-width="1.2" opacity="0.92"/>
        <!-- N pointer -->
        <polygon points="30,6 26,30 30,26 34,30" fill="#E24B4A"/>
        <!-- S pointer -->
        <polygon points="30,54 26,30 30,34 34,30" fill="#222"/>
        <!-- E/O ticks -->
        <line x1="54" y1="30" x2="48" y2="30" stroke="#222" stroke-width="1.5"/>
        <line x1="6"  y1="30" x2="12" y2="30" stroke="#222" stroke-width="1.5"/>
        <!-- Labels -->
        <text x="30" y="14" text-anchor="middle" font-family="sans-serif" font-size="10" font-weight="700" fill="#222">N</text>
        <text x="30" y="52" text-anchor="middle" font-family="sans-serif" font-size="9"  fill="#222">S</text>
        <text x="51" y="33" text-anchor="middle" font-family="sans-serif" font-size="9"  fill="#222">L</text>
        <text x="9"  y="33" text-anchor="middle" font-family="sans-serif" font-size="9"  fill="#222">O</text>
      </svg>
    `
    // Prevent map drag when interacting with the compass
    L.DomEvent.disableClickPropagation(div)
    return div
  },
})
```

Add to the map init in `MapEditor.vue`:

```typescript
import { CompassControl } from './CompassControl'

initMap() {
  this.map = L.map(this.$refs.mapContainer, {
    zoom: 18,
    // ... existing options
  })
  // ... existing tile layer etc.
  new CompassControl().addTo(this.map)
}
```

**Labels**: N (Norte), S (Sul), L (Leste), O (Oeste). Brazilian Portuguese
convention uses "L" for Leste (East) and "O" for Oeste (West), not the
English "E" and "W".

### 5.4 Waypoint form: reliability + field reorder

**Two changes** to `EntityForm.vue` (or wherever the waypoint create form lives):

#### 5.4.1 Ensure the form always opens after a map click in waypoint mode

Today the form may fail to open intermittently (race condition between
the Leaflet click handler and the Vue reactivity). The fix:

```typescript
// In MapEditor.vue, the click handler for waypoint mode:
onMapClickWaypointMode(e: L.LeafletMouseEvent) {
  // Always reset first to force re-render even if form was already open
  this.entityFormOpen = false
  this.$nextTick(() => {
    this.entityFormType = 'waypoint'
    this.entityFormData = {
      lat: e.latlng.lat,
      lng: e.latlng.lng,
      waypoint_type: '',   // empty so the Type select is the action
      name: '',
      road_name: this.guessNearestRoadName(e.latlng) || null,
      extra_data: {},
    }
    this.entityFormOpen = true
  })
},
```

Two guarantees this gives:
- The form is reset and re-opened cleanly on every click.
- The `Tipo` select is the first action — the form starts with an empty
  type, forcing the operator to choose.

#### 5.4.2 Field order: Tipo first, Nome second

In the form template, reorder:

```vue
<form @submit.prevent="onSave">
  <!-- 1. TIPO (was below) -->
  <label>
    Tipo
    <select v-model="formData.waypoint_type" ref="typeSelect" required>
      <option value="" disabled>Selecione um tipo</option>
      <option value="stop_sign">Placa de PARE</option>
      <option value="speed_bump">Lombada</option>
      <option value="gate">Portaria</option>
      <option value="landmark">Ponto de referência</option>
      <option value="curve">Curva</option>
      <option value="crossroad">Marcador de cruzamento</option>
      <option value="stop_zone">Zona de parada</option>
    </select>
  </label>

  <!-- 2. NOME (was above) -->
  <label>
    Nome
    <input v-model="formData.name" type="text" required />
  </label>

  <!-- 3. Conditional fields (height_cm, gate_type, heading_degrees) -->
  <!-- ...unchanged... -->

  <!-- 4. Road association -->
  <label>
    Rua
    <select v-model="formData.road_name">
      <option :value="null">— Nenhuma —</option>
      <option v-for="r in mapStore.roads" :key="r.id" :value="r.name">
        {{ r.name }}
      </option>
    </select>
  </label>

  <!-- 5. Lat/lng read-only -->
  <div class="coord-display">
    Posição: {{ formData.lat.toFixed(6) }}, {{ formData.lng.toFixed(6) }}
  </div>
</form>
```

Auto-focus the Tipo select on open:

```typescript
watch: {
  open(newVal: boolean) {
    if (newVal) {
      this.$nextTick(() => (this.$refs.typeSelect as HTMLSelectElement)?.focus())
    }
  },
},
```

### 5.5 Click-to-select road: highlight whole polyline

Add to `mapStore`:

```typescript
state: () => ({
  // ... existing state
  selectedRoadIds: [] as number[],   // NEW
}),

actions: {
  selectRoad(roadId: number) {
    this.selectedRoadIds = [roadId]
  },
  selectRoads(roadIds: number[]) {
    this.selectedRoadIds = [...roadIds]
  },
  clearSelection() {
    this.selectedRoadIds = []
  },
},

getters: {
  isRoadSelected: (state) => (id: number) => state.selectedRoadIds.includes(id),
},
```

In `MapEditor.vue`, when rendering roads:

```typescript
const SELECTED_ROAD_COLOR = '#FFB400'   // amber yellow — high contrast
const SELECTED_ROAD_WEIGHT = 6          // thicker than default 4

renderRoad(road: RoadResponse) {
  const selected = this.mapStore.isRoadSelected(road.id)
  const color = selected ? SELECTED_ROAD_COLOR :
                (road.direction === 'one_way' ? '#ff7800' : '#378ADD')
  const weight = selected ? SELECTED_ROAD_WEIGHT : 4

  const line = L.polyline(
    road.coordinates.map(p => [p.lat, p.lng]),
    { color, weight, opacity: 0.9 },
  )
  line.on('click', (e) => {
    L.DomEvent.stopPropagation(e)
    this.onRoadClick(road)
  })
  this.roadsLayer.addLayer(line)
  this.roadLayerIndex[road.id] = line
},

onRoadClick(road: RoadResponse) {
  if (this.drawingMode !== 'select') return
  this.mapStore.selectRoad(road.id)
  this.refreshRoadStyles()
  // Show the road's data in the side panel (existing behavior)
  this.entityFormOpen = true
  this.entityFormType = 'road'
  this.entityFormData = { ...road }
},

refreshRoadStyles() {
  // Re-render every road with the new selection state.
  // (For performance with 500+ roads, only restyle the ones that changed.)
  for (const [id, layer] of Object.entries(this.roadLayerIndex)) {
    const selected = this.mapStore.isRoadSelected(Number(id))
    const road = this.mapStore.roads.find(r => r.id === Number(id))!
    layer.setStyle({
      color: selected ? SELECTED_ROAD_COLOR :
             (road.direction === 'one_way' ? '#ff7800' : '#378ADD'),
      weight: selected ? SELECTED_ROAD_WEIGHT : 4,
    })
  }
},
```

**Clicking on empty map** (no road) in select mode clears the selection:

```typescript
this.map.on('click', () => {
  if (this.drawingMode === 'select' && this.mapStore.selectedRoadIds.length > 0) {
    this.mapStore.clearSelection()
    this.refreshRoadStyles()
    this.entityFormOpen = false
  }
})
```

### 5.6 ConfirmModal component

**New file**: `frontend/src/components/common/ConfirmModal.vue`

A reusable confirmation modal used by §5.7 (single delete), §5.8 (bulk
delete), and any future destructive action.

```vue
<template>
  <div v-if="visible" class="modal-backdrop" @click.self="onCancel">
    <div class="modal" role="dialog" aria-modal="true">
      <h2>{{ title }}</h2>
      <p>{{ message }}</p>
      <ul v-if="items && items.length" class="modal-items">
        <li v-for="(item, idx) in items.slice(0, 10)" :key="idx">{{ item }}</li>
        <li v-if="items.length > 10">… e mais {{ items.length - 10 }} item(ns)</li>
      </ul>
      <div class="modal-actions">
        <button class="btn-secondary" ref="cancelBtn" @click="onCancel">
          {{ cancelLabel }}
        </button>
        <button class="btn-danger" @click="onConfirm">
          {{ confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'ConfirmModal',
  props: {
    visible: { type: Boolean, required: true },
    title: { type: String, required: true },
    message: { type: String, required: true },
    items: { type: Array as () => string[], default: () => [] },
    confirmLabel: { type: String, default: 'Sim, excluir' },
    cancelLabel: { type: String, default: 'Cancelar' },
  },
  emits: ['confirm', 'cancel'],
  watch: {
    visible(v: boolean) {
      if (v) {
        // Cancel is the default focused action — protects against
        // accidental Enter-key confirmations.
        this.$nextTick(() => (this.$refs.cancelBtn as HTMLButtonElement)?.focus())
      }
    },
  },
  methods: {
    onConfirm() { this.$emit('confirm') },
    onCancel() { this.$emit('cancel') },
  },
  mounted() {
    document.addEventListener('keydown', this.onKey)
  },
  beforeUnmount() {
    document.removeEventListener('keydown', this.onKey)
  },
  // Defined separately so addEventListener/removeEventListener match
  methods_internal: {} as any,
})
</script>
```

(The `onKey` for Escape-to-cancel is implementation detail — add it
inside the component.)

### 5.7 DELETE key on selected road → confirmation

In `MapEditor.vue`:

```typescript
mounted() {
  // ... existing init
  document.addEventListener('keydown', this.onKeyDown)
},

beforeUnmount() {
  document.removeEventListener('keydown', this.onKeyDown)
},

methods: {
  onKeyDown(e: KeyboardEvent) {
    // Ignore if the user is typing in an input/textarea
    const tag = (e.target as HTMLElement).tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return

    if (e.key === 'Delete' || e.key === 'Backspace') {
      if (this.mapStore.selectedRoadIds.length > 0) {
        this.openDeleteConfirm()
      }
    }
    // Undo (§5.9):
    if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
      this.undoStore.undoLast()
    }
  },

  openDeleteConfirm() {
    const ids = this.mapStore.selectedRoadIds
    const names = ids
      .map(id => this.mapStore.roads.find(r => r.id === id)?.name)
      .filter(Boolean) as string[]

    this.confirmModal = {
      visible: true,
      title: ids.length === 1 ? 'Excluir rua?' : `Excluir ${ids.length} ruas?`,
      message: ids.length === 1
        ? `Esta ação removerá a rua selecionada do rascunho.`
        : `Esta ação removerá ${ids.length} ruas do rascunho.`,
      items: names,
      onConfirm: () => this.performDelete(ids),
    }
  },

  async performDelete(ids: number[]) {
    this.confirmModal.visible = false
    const restoreEntries: RoadResponse[] = []
    for (const id of ids) {
      const road = this.mapStore.roads.find(r => r.id === id)
      if (road) restoreEntries.push(road)
    }
    try {
      for (const id of ids) {
        await this.mapStore.deleteRoad(id)
      }
      // Push to undo stack as a single grouped operation
      this.undoStore.push({
        type: 'delete_roads',
        roads: restoreEntries,
        timestamp: Date.now(),
      })
      this.mapStore.clearSelection()
    } catch (e: any) {
      this.showError(e.message || 'Falha ao excluir')
    }
  },
}
```

### 5.8 Rectangle selection mode

The "Selecionar" toolbar button enters select mode. In this mode:

- **Click on a road**: selects that road (clears previous selection)
  — as specified in §5.5
- **Click + drag on empty map**: draws a translucent rectangle.
  On mouseup, all roads whose bounding box intersects the rectangle
  become selected.
- **Shift+Click on a road**: adds/removes that road from the selection
  (additive). *(Optional polish — implement only if straightforward.)*

**New helper file**: `frontend/src/components/map/RectangleSelector.ts`

```typescript
import L from 'leaflet'

export interface RectangleSelectorOptions {
  /** Called with the geographic bounds of the drawn rectangle. */
  onSelect: (bounds: L.LatLngBounds) => void
  /** Visual style for the in-progress rectangle. */
  style?: L.PathOptions
}

const DEFAULT_STYLE: L.PathOptions = {
  color: '#FFB400',
  weight: 1.5,
  fillColor: '#FFB400',
  fillOpacity: 0.18,
  dashArray: '4 4',
}

/**
 * Attaches a click-drag rectangle selection handler to a Leaflet map.
 * Returns a teardown function that removes all handlers.
 *
 * Only active while attached — call teardown() when leaving select mode.
 */
export function attachRectangleSelector(
  map: L.Map,
  opts: RectangleSelectorOptions,
): () => void {
  const style = { ...DEFAULT_STYLE, ...(opts.style ?? {}) }
  let startLatLng: L.LatLng | null = null
  let rectLayer: L.Rectangle | null = null

  const onMouseDown = (e: L.LeafletMouseEvent) => {
    // Only start when the user holds Shift, or always — design choice.
    // We use "always start in select mode" for simplicity.
    if ((e.originalEvent.target as HTMLElement)?.closest('.leaflet-marker-icon')) {
      return // don't start a rectangle on a marker
    }
    startLatLng = e.latlng
    map.dragging.disable()
    map.getContainer().style.cursor = 'crosshair'
  }

  const onMouseMove = (e: L.LeafletMouseEvent) => {
    if (!startLatLng) return
    const bounds = L.latLngBounds(startLatLng, e.latlng)
    if (!rectLayer) {
      rectLayer = L.rectangle(bounds, style).addTo(map)
    } else {
      rectLayer.setBounds(bounds)
    }
  }

  const onMouseUp = (e: L.LeafletMouseEvent) => {
    if (!startLatLng) return
    const bounds = L.latLngBounds(startLatLng, e.latlng)
    const moved = startLatLng.distanceTo(e.latlng)
    // Ignore tiny drags — treat as a click (which is handled elsewhere).
    if (moved > 5) {
      opts.onSelect(bounds)
    }
    if (rectLayer) {
      map.removeLayer(rectLayer)
      rectLayer = null
    }
    startLatLng = null
    map.dragging.enable()
    map.getContainer().style.cursor = ''
  }

  map.on('mousedown', onMouseDown)
  map.on('mousemove', onMouseMove)
  map.on('mouseup', onMouseUp)

  return () => {
    map.off('mousedown', onMouseDown)
    map.off('mousemove', onMouseMove)
    map.off('mouseup', onMouseUp)
    if (rectLayer) map.removeLayer(rectLayer)
    map.dragging.enable()
  }
}
```

In `MapEditor.vue`:

```typescript
data() {
  return {
    // ...
    rectangleTeardown: null as (() => void) | null,
  }
},

watch: {
  drawingMode(newMode: string, oldMode: string) {
    if (oldMode === 'select' && this.rectangleTeardown) {
      this.rectangleTeardown()
      this.rectangleTeardown = null
    }
    if (newMode === 'select') {
      this.rectangleTeardown = attachRectangleSelector(this.map, {
        onSelect: (bounds) => this.selectRoadsInBounds(bounds),
      })
    }
  },
},

methods: {
  selectRoadsInBounds(bounds: L.LatLngBounds) {
    const selectedIds: number[] = []
    for (const road of this.mapStore.roads) {
      // Road is selected if ANY of its vertices is inside the rectangle.
      // (Fast and matches the operator's mental model.)
      const hit = road.coordinates.some(p =>
        bounds.contains([p.lat, p.lng] as L.LatLngExpression),
      )
      if (hit) selectedIds.push(road.id)
    }
    this.mapStore.selectRoads(selectedIds)
    this.refreshRoadStyles()

    // Per the user's requirement: when multiple roads are selected,
    // do NOT show the data form. Show a small status bar instead.
    this.entityFormOpen = false
    if (selectedIds.length > 1) {
      this.bulkStatus = `${selectedIds.length} ruas selecionadas. Pressione Delete para excluir todas.`
    } else if (selectedIds.length === 1) {
      // Single selection by rectangle: open the form (same as click)
      const road = this.mapStore.roads.find(r => r.id === selectedIds[0])!
      this.entityFormType = 'road'
      this.entityFormData = { ...road }
      this.entityFormOpen = true
    }
  },
},
```

**Performance note**: the "any vertex inside bounds" check is O(N×M)
where N is roads and M is mean vertices per road. For the MVP01 target
of ≤500 entities, this runs in <5 ms. Optimization (STRtree on the
frontend) is unnecessary.

### 5.9 Undo stack (delete only)

**New file**: `frontend/src/stores/undo.ts`

```typescript
import { defineStore } from 'pinia'
import type { RoadResponse, WaypointResponse, CrossroadResponse } from '../api/types'
import { api } from '../api/client'

type UndoEntry =
  | { type: 'delete_roads'; roads: RoadResponse[]; timestamp: number }
  | { type: 'delete_waypoint'; waypoint: WaypointResponse; timestamp: number }
  | { type: 'delete_crossroad'; crossroad: CrossroadResponse; timestamp: number }

const STACK_LIMIT = 20

export const useUndoStore = defineStore('undo', {
  state: () => ({
    stack: [] as UndoEntry[],
    busy: false,
  }),

  getters: {
    canUndo: (state) => state.stack.length > 0 && !state.busy,
    lastActionLabel(state): string {
      const top = state.stack[state.stack.length - 1]
      if (!top) return ''
      switch (top.type) {
        case 'delete_roads':
          return top.roads.length === 1
            ? `Desfazer exclusão de rua "${top.roads[0].name}"`
            : `Desfazer exclusão de ${top.roads.length} ruas`
        case 'delete_waypoint':
          return `Desfazer exclusão de waypoint "${top.waypoint.name}"`
        case 'delete_crossroad':
          return `Desfazer exclusão de cruzamento`
      }
    },
  },

  actions: {
    push(entry: UndoEntry) {
      this.stack.push(entry)
      while (this.stack.length > STACK_LIMIT) this.stack.shift()
    },

    clear() {
      this.stack = []
    },

    async undoLast() {
      if (!this.canUndo) return
      const entry = this.stack.pop()!
      this.busy = true
      try {
        // Workspace id from the workspace store
        const wsId = (window as any).guardianApp.$pinia.state.value.workspace.workspace?.id
        if (!wsId) throw new Error('No active workspace')

        switch (entry.type) {
          case 'delete_roads':
            for (const road of entry.roads) {
              await api.createRoad(wsId, {
                name: road.name,
                coordinates: road.coordinates,
                speed_limit_kmh: road.speed_limit_kmh,
                direction: road.direction,
                width_meters: road.width_meters,
              })
            }
            break
          case 'delete_waypoint':
            await api.createWaypoint(wsId, {
              name: entry.waypoint.name,
              waypoint_type: entry.waypoint.waypoint_type,
              lat: entry.waypoint.lat,
              lng: entry.waypoint.lng,
              road_name: entry.waypoint.road_name,
              heading_degrees: entry.waypoint.heading_degrees,
              extra_data: entry.waypoint.extra_data,
              active: entry.waypoint.active,
            })
            break
          case 'delete_crossroad':
            await api.createCrossroad(wsId, {
              road_a_name: entry.crossroad.road_a_name,
              road_b_name: entry.crossroad.road_b_name,
              lat: entry.crossroad.lat,
              lng: entry.crossroad.lng,
            })
            break
        }
        // Reload map and validation to reflect the restoration
        const mapStore = (await import('./map')).useMapStore()
        const wsStore = (await import('./workspace')).useWorkspaceStore()
        await mapStore.fetchMap(wsId)
        await wsStore.runValidation()
      } catch (e) {
        // Push back on failure so the operator can try again
        this.stack.push(entry)
        throw e
      } finally {
        this.busy = false
      }
    },
  },
})
```

**Toolbar UI**:

```vue
<button
  class="btn-undo"
  :disabled="!undoStore.canUndo"
  :title="undoStore.canUndo ? undoStore.lastActionLabel : 'Nada para desfazer'"
  @click="undoStore.undoLast()"
>
  ⟲ Desfazer
</button>
```

Keyboard shortcut: `Ctrl+Z` (or `Cmd+Z`) — already wired in §5.7.

**Clear the stack** on:
- Workspace switch (in `workspaceStore.fetchWorkspace`, call `undoStore.clear()`)
- After publish (publish flow already reloads the workspace, so this is automatic)
- Page refresh (handled by Pinia — store is in-memory)

**Important caveat to display to operator** (tooltip on the undo button
when the stack is empty AFTER a refresh):

> "O histórico de desfazer é mantido apenas durante a sessão atual."

### 5.10 Merge duplicates UI

**New file**: `frontend/src/components/map/MergeRoadsModal.vue`

A modal triggered by a "Mesclar ruas duplicadas" toolbar button.

```
States:
  loading  → "Buscando grupos duplicados..."
  empty    → "Nenhuma rua duplicada encontrada."
  preview  → list of groups, each with:
              - base name as group title
              - checkbox per group (default: checked)
              - editable target name (defaults to base name)
              - list of source roads with point counts
  merging  → "Mesclando..."
  done     → summary: total groups merged, total roads removed, gaps detected
  error    → error message
```

On open: GET `/api/v1/workspaces/{id}/roads/duplicate-groups`.
On confirm: POST `/api/v1/workspaces/{id}/roads/merge` with the selected
groups. After success, call `mapStore.fetchMap()` + `workspaceStore.runValidation()`
+ `recenterOnEntities()` and clear the undo stack (merge is not undoable
in this MVP — make this clear in the modal).

API client additions (`api/client.ts`):

```typescript
export const api = {
  // ... existing ...

  getDuplicateGroups: (wsId: number) =>
    request<{ groups: Array<{
      base_name: string
      road_ids: number[]
      road_names: string[]
      total_points: number
    }> }>('GET', `/api/v1/workspaces/${wsId}/roads/duplicate-groups`),

  mergeRoads: (wsId: number, groups: Array<{
    target_name: string
    source_road_ids: number[]
  }>) =>
    request<{ workspace_id: number; results: any[] }>(
      'POST', `/api/v1/workspaces/${wsId}/roads/merge`, { groups },
    ),
}
```

---

## 6. New Workflows

### WF-06 — Mesclar ruas duplicadas após import OSM

```
1. Operator imports an OSM file via WF-05.
2. Notices that several roads are split: "Rua A", "Rua A (2)", "Rua A (3)".
3. Clicks the "Mesclar ruas duplicadas" toolbar button.
4. Modal opens (state: loading) → fetches duplicate groups.
5. Preview state: each group shows base name + member roads + edit name field.
6. Operator unchecks any group they don't want merged. Optionally edits target name.
7. Clicks "Mesclar selecionados" (state: merging).
8. Backend runs the merge transactionally.
9. Modal shows summary: "X groups merged, Y roads removed, 0 gaps detected".
10. Map editor reloads — duplicate roads are now single polylines.
11. Validation runs automatically.
```

### WF-07 — Excluir várias ruas com seleção em retângulo

```
1. Operator activates "Selecionar" mode.
2. Click + drag a rectangle around several roads.
3. Selected roads highlight in amber. Status bar shows "N ruas selecionadas".
4. Operator presses Delete.
5. Confirmation modal opens with the list of road names.
6. Operator clicks "Sim, excluir".
7. Roads are deleted (one API call each, single undo entry created).
8. "Desfazer" button becomes enabled.
9. Operator realizes one was deleted by mistake → clicks Desfazer.
10. ALL roads from that batch are restored. (To recover only one,
    delete the others again — this is the limitation of grouped undo.)
```

### WF-08 — Desfazer exclusão acidental

```
1. Operator clicks a road, presses Delete, confirms.
2. Road disappears from map. Undo button shows label "Desfazer exclusão de rua 'Rua X'".
3. Operator clicks Desfazer (or presses Ctrl+Z).
4. The road is re-created via POST /roads. Map reloads. Validation re-runs.
5. The road now has a NEW database id but the same name and geometry.
6. Any waypoints that had been associated by name still display correctly.
```

---

## 7. Implementation Sequence

Single Stage 7, four sub-stages.

### Stage 7.A — Backend merge service + tests

1. Create `src/guardianmapstudio/geometry/road_merge.py` per §4.1.
2. Write `tests/unit/test_road_merge.py` per §4.5.
3. If `MapRepository.update_crossroad` does not exist, add it
   following the existing `update_waypoint` pattern.

**Quality gate**:

```bash
uv run ruff check src/guardianmapstudio/geometry/ tests/unit/test_road_merge.py
uv run mypy src/guardianmapstudio/geometry/
uv run pytest tests/unit/test_road_merge.py -v \
    --cov=guardianmapstudio.geometry.road_merge --cov-report=term-missing
uv run pytest tests/ -v   # full regression
```

`road_merge.py` coverage ≥ 95%. Commit when green.

### Stage 7.B — Backend merge endpoints + schemas + errors

1. Append to `api/schemas.py` per §4.2.
2. Append to `api/errors.py` per §4.4.
3. Append the two endpoints to `api/routers/roads.py` per §4.3.
4. Write `tests/integration/test_api_roads_merge.py` per §4.5.

**Quality gate**:

```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/ -v --cov=guardianmapstudio --cov-fail-under=80

# 11-tables invariant:
python3 -c "
from sqlalchemy import create_engine, inspect
from guardianmapstudio.database.connection import create_tables
engine = create_engine('sqlite:///:memory:')
create_tables(engine)
tables = sorted(inspect(engine).get_table_names())
assert len(tables) == 11, f'Expected 11, got {len(tables)}: {tables}'
print('OK: 11 tables')
"
```

All pre-existing tests must still pass.

### Stage 7.C — Frontend (all 10 UI changes)

Implement in this order — each is independent except where a section
note says otherwise.

1. §5.1 Remove "Estrada" toolbar button (1 line change)
2. §5.3 CompassControl (new file, 1 line in initMap)
3. §5.2 `recenterOnEntities()` + auto-call after fetchMap (~20 lines)
4. §5.6 ConfirmModal component (new file)
5. §5.5 Road selection highlight + click handler (modifies render path)
6. §5.7 DELETE key + ConfirmModal wiring (depends on §5.5, §5.6)
7. §5.8 RectangleSelector helper + selectRoadsInBounds (depends on §5.5)
8. §5.9 Undo store + toolbar button + Ctrl+Z (depends on §5.7)
9. §5.4 Waypoint form reliability + field reorder
10. §5.10 MergeRoadsModal + API client methods (depends on §7.B endpoints)

**Quality gate**:

```bash
cd frontend
npm run build           # zero TS errors
cd ..

uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/ -v --cov=guardianmapstudio --cov-fail-under=80

uv run guardianmapstudio
```

Manual checks per §8 acceptance criteria.

### Stage 7.D — End-to-end smoke

Run WF-01, WF-05, WF-06, WF-07, WF-08 in sequence on a single
clean workspace. Confirm:

- Existing workflows from prior stages still work
- Export JSON still passes `guardian-seed-map --from-json`
- `restricted_areas: []` key still present in export
- Coverage still ≥ 80%

---

## 8. Acceptance Criteria

### Backend — Merge

- [ ] `GET /workspaces/{id}/roads/duplicate-groups` returns groups when names match suffix pattern
- [ ] Returns empty `groups` when no duplicates
- [ ] `POST /workspaces/{id}/roads/merge` returns 200 with results
- [ ] After merge, source roads (except target) are deleted
- [ ] After merge, target road has the concatenated polyline
- [ ] After merge, waypoints' `road_name` is updated to target_name
- [ ] After merge, crossroads' `road_a_name` / `road_b_name` updated
- [ ] Merge with gap > 1.0m reports gap in response (does not refuse)
- [ ] Merge on PUBLISHED workspace → 409
- [ ] Merge with single road in group → 422
- [ ] Merge with same road in two groups → 422
- [ ] Merge with unknown road id → 404
- [ ] Validation runs after merge (workspace.has_validation_errors updated)
- [ ] Transaction is atomic: any failure rolls back all groups

### Frontend — Toolbar & Map

- [ ] "Estrada" button no longer appears in the editor toolbar
- [ ] Map auto-centers on existing entities when workspace loads
- [ ] Empty workspace centers on a sensible default (Brazil)
- [ ] N/S/L/O compass appears in top-right of the map
- [ ] Compass is non-interactive (clicks pass through)
- [ ] "🎯 Centralizar mapa" button manually re-fits bounds

### Frontend — Waypoint form

- [ ] Form reliably opens after every click in waypoint mode (no missed clicks)
- [ ] Field order: Tipo, Nome, Conditional, Rua, Posição
- [ ] Tipo select is auto-focused on form open
- [ ] All existing validation (height_cm > 0, gate_type required) still works

### Frontend — Road selection

- [ ] Clicking a road in Select mode highlights the whole polyline (amber, thicker)
- [ ] Side panel shows the road's data
- [ ] Clicking empty map clears the selection and closes the panel
- [ ] Pressing Delete with one road selected opens confirmation modal
- [ ] Confirming the modal deletes the road
- [ ] Cancelling the modal keeps the road
- [ ] Escape key cancels the modal (default focus on Cancel button)

### Frontend — Rectangle selection

- [ ] In Select mode, click + drag draws a translucent rectangle
- [ ] Rectangle disappears on mouseup
- [ ] All roads with at least one vertex inside the rectangle become selected
- [ ] Multi-selection shows status bar (not the data form)
- [ ] Pressing Delete with N>1 roads selected opens bulk confirmation modal
- [ ] Bulk modal lists all road names (truncated after 10)
- [ ] Confirming bulk modal deletes all selected roads
- [ ] All bulk-deleted roads become a single undo entry

### Frontend — Undo

- [ ] "Desfazer" button appears in the toolbar
- [ ] Button is disabled when stack is empty
- [ ] Button is enabled after deleting a road
- [ ] Clicking Desfazer re-creates the deleted road
- [ ] Re-created road has the same name, coordinates, attributes
- [ ] Re-created road has a NEW database id (expected)
- [ ] Ctrl+Z triggers the same action as the button
- [ ] Undo button label shows what will be undone (tooltip)
- [ ] Workspace switch clears the undo stack
- [ ] Publish clears the undo stack
- [ ] Page refresh clears the undo stack (memory only)
- [ ] Bulk delete of N roads is a single undo entry

### Frontend — Merge UI

- [ ] "Mesclar ruas duplicadas" toolbar button is visible
- [ ] Button is disabled when workspace is not DRAFT
- [ ] Clicking opens modal in loading state
- [ ] Modal shows "Nenhuma rua duplicada" when no groups exist
- [ ] Each detected group is editable (checkbox + target name)
- [ ] Clicking "Mesclar selecionados" runs the merge
- [ ] After success, map reloads with merged geometry
- [ ] Modal summary shows count of merged groups and gap warnings

### Regression — Nothing else broken

- [ ] All Stage 1–6 tests pass with no modification
- [ ] Database still has exactly 11 tables
- [ ] Overall test coverage ≥ 80%
- [ ] `ruff check` zero warnings
- [ ] `mypy --strict` zero errors
- [ ] WF-01 (manual drawing) — N/A now that "Estrada" button is hidden;
      replaced by WF-05/WF-06 (OSM import + merge)
- [ ] WF-05 (OSM import) completes end-to-end
- [ ] Exported JSON still passes `guardian-seed-map --from-json`
- [ ] Existing restricted areas (from prior versions) still render
- [ ] Export JSON still includes `"restricted_areas": []` key

---

## 9. Out of Scope (Future Work)

| Feature | Status | Why deferred |
|---|---|---|
| Full undo/redo (create, update, move) | MVP02 (already in Roadmap) | This doc adds only delete undo as scoped MVP |
| Vertex-level edit (drag a single vertex of a road) | MVP02 | Requires polyline editor library and per-vertex hit testing |
| Rectangle selection for waypoints / crossroads / areas | MVP02 | Mixed-type selection raises UX questions; roads-only is clear |
| Merge undo (undo a road merge) | MVP02 | Merge is multi-entity; undo would need to restore deleted source roads and reverse waypoint/crossroad rename — fits naturally into the MVP02 full undo |
| Custom merge geometry (operator chooses join order) | MVP02 | Greedy auto-chain handles 95% of cases |
| Shift+Click to add/remove from selection | Optional polish | Implement if straightforward during Stage 7.C |
| Visualize gap warnings on the map after merge | MVP02 | Validation panel mentions them; visual marker is extra |
| Rotate map / measure tool / scale bar | MVP04+ | Not requested |

---

## 10. Notes for Reviewers

1. **Why we don't refuse merges with gaps**: refusing forces the operator
   into a manual delete-and-redraw that loses waypoint associations.
   Reporting the gap in the response lets the operator decide
   case-by-case, with full information.

2. **Why the merge endpoint reassigns by NAME, not by ID**: waypoints and
   crossroads reference roads by NAME (per Doc 08 §3.5). After the merge,
   the target road keeps its id but takes the target_name. Any waypoint
   that referenced any of the source road names must be updated to the
   target_name. We do not touch waypoints that already had the target_name.

3. **Why undo re-creates instead of restoring the id**: restoring a deleted
   id would require either preventing autoincrement reuse (SQLite makes no
   guarantee) or a soft-delete column (new schema). A new id with the same
   data is functionally equivalent because waypoint→road and crossroad→road
   references are by NAME, not by id.

4. **Why the compass uses L/O (not E/W)**: the operator base is Brazilian
   Portuguese (per the project's UI language throughout: "Publicar",
   "Validar", "Versões", "Cancelar"). Brazilian convention is N/S/L/O
   (Norte/Sul/Leste/Oeste).

5. **Why removing "Estrada" is safe even though manual road drawing was
   the original workflow**: OSM Import (Doc 15) covers the bulk creation
   case. Merge (this doc) covers the cleanup case. Direct manual drawing
   was used for the initial WF-01 demo but is no longer the primary
   workflow. The backend stays intact for any future programmatic creation.
