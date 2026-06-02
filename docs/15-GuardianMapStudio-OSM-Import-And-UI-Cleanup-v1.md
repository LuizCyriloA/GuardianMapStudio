# GuardianMapStudio — OSM Import & UI Cleanup v1 (Complementary Spec — Doc 15)

> **Status**: Complementary specification for MVP01 (already shipped).
> **Type**: Additive feature + cosmetic UI cleanup. **Non-breaking**.
> **Author intent**: Speed up road authoring by importing the road network
> from an OpenStreetMap `.osm` XML file. The operator then adds waypoints,
> stop signs, etc. manually.

---

## 1. Purpose & Context

Authoring an entire condominium road network by clicking each vertex on the
Leaflet map is the slowest step of WF-01 (doc 04). OpenStreetMap already
contains the road geometry of most Brazilian condominiums with reasonable
precision, exported as a standard XML file from `openstreetmap.org → Exportar`.

This document specifies:

1. A new **OSM Import** feature that ingests a `.osm` XML file and creates
   `Road` entities in the active DRAFT Workspace.
2. **Removal of the "Area" button** from the editor toolbar (restricted area
   drawing is no longer accessible from the UI).

Both changes are scoped to a single new module on the backend, a single new
component on the frontend, and a one-line change in the editor toolbar.
**No existing endpoint, database table, domain contract, or export rule is
modified.**

### 1.1 Relationship to other documents

| Doc | Relationship |
|---|---|
| 02 (Roadmap) | Roadmap lists "OSM import" as MVP02. This spec implements a **basic** version (manual confirm, no auto-snap, no auto-crossroad). The "smart" version (auto-snap, road merging, intersection detection) **remains scheduled for MVP02**. |
| 04 (MVP01 Spec) | Adds new workflow WF-05; removes one toolbar button mentioned in §4. Existing acceptance criteria remain valid. |
| 08 (Domain Model) | **No change.** No new aggregate, value object, or enum. |
| 09 (API Spec) | Adds 2 new endpoints. Does not modify any existing endpoint. |
| 11 (Frontend Spec) | Adds 1 new component (`OsmImportModal.vue`) and removes 1 toolbar button. |
| 13 (Implementation Blueprint) | Add as new section "Stage 6 — OSM Import". Stages 1–5 unchanged. |

### 1.2 What this is NOT

This is **not** the full MVP02 OSM feature. Explicitly out of scope here
(see §9 for the complete list):

- No automatic endpoint snapping between OSM roads
- No automatic crossroad detection at intersections
- No road segment merging (each OSM `<way>` becomes one separate `Road`)
- No POI / waypoint import from OSM (only roads)
- No restricted area import from OSM polygons
- No PBF format support — XML only
- No geocoding or address lookup
- No direct download from the OSM API (operator exports the file manually)

---

## 2. Impact Analysis — What Stays, What Changes

### 2.1 What stays exactly the same

| Component | Status |
|---|---|
| All 11 database tables | **Unchanged** |
| All SQLAlchemy models | **Unchanged** |
| Domain contracts (`Road`, `Waypoint`, etc.) | **Unchanged** |
| Domain events | **Unchanged** |
| Geometry engines (Geometry, Snap, Crossroad, Validation) | **Unchanged** |
| GuardianExporter | **Unchanged** |
| All existing 33 API endpoints | **Unchanged** |
| Restricted Areas backend (router, repository, model, tests) | **Unchanged** (only UI button is hidden) |
| Validation rules | **Unchanged** |
| Snap behavior on manual placement | **Unchanged** |
| Publish & Export workflows | **Unchanged** |
| Test coverage threshold (80%) | **Unchanged** |

### 2.2 What changes

| Area | Change | Files touched |
|---|---|---|
| Backend dependencies | None added | — |
| Backend modules | New `osm/` package (2 files) | `src/guardianmapstudio/osm/parser.py`, `osm/importer.py` |
| Backend schemas | New DTOs appended | `api/schemas.py` (additive only) |
| Backend routers | New router (2 endpoints) | `api/routers/osm_import.py` |
| Backend main | One `include_router` line | `main.py` |
| Backend settings | 2 optional fields | `config/settings.py` |
| Frontend toolbar | Remove "Area" button | `MapEditor.vue` (or toolbar component) |
| Frontend toolbar | Add "Importar OSM" button | `MapEditor.vue` |
| Frontend components | New modal component | `components/map/OsmImportModal.vue` |
| Frontend API client | 2 new functions | `api/client.ts` (additive) |
| Frontend map store | 1 new action | `stores/map.ts` (additive) |
| Tests | New test files | `tests/unit/test_osm_parser.py`, `tests/integration/test_api_osm_import.py` |

### 2.3 Why these changes are safe

- **No removal of public API**: every existing endpoint and response shape stays identical. Integration with Guardian (export JSON) is untouched.
- **No new dependencies**: parser uses `xml.etree.ElementTree` from the standard library.
- **No DB migration**: the `candidate_entities` table from doc 12 is **not** introduced. The MVP01 invariant "exactly 11 tables" continues to hold and the existing `test_create_tables_count == 11` assertion still passes.
- **Restricted Areas remain operational on the backend**: hiding the button does not delete data, does not deprecate the endpoints, and does not remove tests. If a future UI re-introduces the button, no code revival is needed.
- **Import operation is gated by DRAFT state**: same guard as every other write — a PUBLISHED workspace cannot be imported into.
- **Validation runs after import**: the existing `_run_validation_after_write()` helper is called at the end of the import handler, keeping `has_validation_errors` consistent.

---

## 3. Architecture Decisions

### ADR-15-01 — OSM parsing via stdlib `xml.etree.ElementTree`

**Decision**: Parse OSM XML using Python's standard library `xml.etree.ElementTree`. Do **not** add `osmium`, `osmread`, or `pyrosm` to dependencies.

**Rationale**:
- The expected input is the file produced by `openstreetmap.org → Exportar`, which is XML — never PBF.
- Typical condominium exports are under 2 MB and contain fewer than 200 ways. `ElementTree` parses such files in well under 1 second.
- `osmium` requires a native C++ extension (`libosmium`), complicating the install on the Guardian machine.
- Adding a dependency for one feature violates the MVP01 minimalism in pyproject.toml.

**Trade-off**: If we ever support PBF or files > 50 MB, the parser will need to be replaced or upgraded. Not relevant for the target environment.

**Security**: `ElementTree` is vulnerable to XML attacks (billion laughs, entity expansion). Mitigation: enforce a file size limit (`STUDIO_OSM_MAX_FILE_SIZE_MB`, default 10 MB) and use `xml.etree.ElementTree.XMLParser` with default settings (entity expansion is already disabled in Python 3.7+).

### ADR-15-02 — Two-step preview → commit workflow

**Decision**: The import is split across two endpoints:
1. `POST /api/v1/workspaces/{id}/osm/preview` — parses the file, returns a list of detected roads, **does not write to the database**.
2. `POST /api/v1/workspaces/{id}/osm/import` — receives the operator's selection (which roads to import, replace-existing flag) and creates the `Road` records.

**Rationale**:
- The operator must be able to review what will be imported before committing. OSM data quality varies — sometimes a road has the wrong name or wrong direction.
- Two-step is a familiar pattern (same as "preview" in many import tools).
- Keeps the parser pure (no DB side-effects) → easier unit testing.

**Trade-off**: The operator uploads the file twice — once for preview, once for commit. Mitigation: the second call sends the *parsed* selection (JSON), not the file again.

### ADR-15-03 — Each OSM `<way>` becomes one `Road`; duplicate names are suffixed

**Decision**: No way merging. If two OSM ways have the same `name` tag, they each become a separate `Road`. To satisfy `BR-05` (unique road names per workspace), duplicates are renamed: `"Rua A"`, `"Rua A (2)"`, `"Rua A (3)"`, etc.

**Rationale**:
- Way merging (concatenating polylines that share endpoints) is non-trivial and OSM has no canonical way to express "these are the same road". The operator can rename manually after import if desired.
- Suffix naming preserves the OSM identity while preventing silent failures.
- Way merging is explicitly listed in this document's §9 as **MVP02 scope**.

### ADR-15-04 — Hide the "Area" toolbar button; keep all Restricted Area code

**Decision**: Remove the "Desenhar área" / "Area" button from the editor toolbar and the corresponding `drawingMode = 'area'` branch in `MapEditor.vue`. **Do not** delete the backend router, repository, model, validation rules, or tests for restricted areas. Do not delete the `RestrictedAreaForm` component (it remains unused but functional).

**Rationale**:
- The user requested removal from the UI, not removal of the feature.
- Removing backend code breaks 4+ existing tests (`test_api_restricted_areas.py`), the `restricted_areas` count in `VersionResponse`, and the export JSON format (Guardian still expects `"restricted_areas": []`).
- Keeping the code dormant is zero-cost: it is invoked only by HTTP requests that no UI sends.
- A future MVP can re-expose the button with one line of HTML.

**Verification**: The export JSON for a workspace with no restricted areas still emits `"restricted_areas": []` — Guardian's `seed_from_json()` requires the key to be present.

---

## 4. Backend Changes

### 4.1 New module: `osm/parser.py`

Pure function module — no I/O beyond reading the input XML. Returns plain
domain objects (not ORM models). 100% unit testable.

**File**: `src/guardianmapstudio/osm/__init__.py` — empty

**File**: `src/guardianmapstudio/osm/parser.py`

```python
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from loguru import logger

from guardianmapstudio.domain.contracts import GeoPoint, RoadDirection

# OSM highway tag values that produce a Road in GuardianMapStudio.
# Pedestrian-only ways are excluded by default but can be opted-in via the
# include_pedestrian flag in OsmParser.parse().
DRIVABLE_HIGHWAY_TAGS: frozenset[str] = frozenset({
    "residential", "service", "unclassified", "living_street",
    "tertiary", "secondary", "primary", "trunk",
    "tertiary_link", "secondary_link", "primary_link", "trunk_link",
})

PEDESTRIAN_HIGHWAY_TAGS: frozenset[str] = frozenset({
    "footway", "path", "cycleway", "pedestrian", "track", "steps",
})


@dataclass(frozen=True, slots=True)
class ParsedRoad:
    """A single road extracted from an OSM XML file.

    This is the parser's output contract — independent of the database.
    The importer (see §4.2) converts these to Road records via MapRepository.
    """
    osm_way_id: int                # OSM way id, for traceability
    name: str                      # never empty (synthetic name if OSM had none)
    coordinates: list[GeoPoint]    # >= 2 points; in OSM way node order
    direction: RoadDirection       # derived from oneway tag
    speed_limit_kmh: int           # 20 if maxspeed missing or invalid
    width_meters: float            # 6.0 if width missing or invalid
    highway_tag: str               # e.g. "residential" — for UI display
    had_name: bool                 # False if name was synthesized
    osm_warnings: list[str]        # e.g. "maxspeed not parseable"


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Outcome of parsing an OSM XML file."""
    roads: list[ParsedRoad]
    skipped_ways: int              # ways present in XML but excluded
    skipped_reasons: dict[str, int]  # {"not_drivable": 12, "no_nodes": 1, ...}
    total_ways_in_file: int


class OsmParser:
    """Parses OpenStreetMap XML exports into ParsedRoad objects.

    Usage:
        parser = OsmParser()
        result = parser.parse(xml_bytes, include_pedestrian=False,
                              include_unnamed=False)
    """

    def parse(
        self,
        xml_bytes: bytes,
        *,
        include_pedestrian: bool = False,
        include_unnamed: bool = False,
    ) -> ParseResult:
        """Parse an OSM XML payload.

        Raises:
            ValueError: if the XML is malformed or not an OSM document.
        """
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as e:
            raise ValueError(f"Malformed OSM XML: {e}") from e

        if root.tag != "osm":
            raise ValueError(
                f"Root element is <{root.tag}>, expected <osm>"
            )

        nodes: dict[int, GeoPoint] = self._index_nodes(root)
        roads, skipped, reasons = self._extract_ways(
            root, nodes,
            include_pedestrian=include_pedestrian,
            include_unnamed=include_unnamed,
        )

        total_ways = len(root.findall("way"))
        logger.info(
            "OSM parse complete: {} roads, {} ways skipped (of {} total)",
            len(roads), skipped, total_ways,
        )
        return ParseResult(
            roads=roads,
            skipped_ways=skipped,
            skipped_reasons=reasons,
            total_ways_in_file=total_ways,
        )

    # --- internals ---

    @staticmethod
    def _index_nodes(root: ET.Element) -> dict[int, GeoPoint]:
        """Build {node_id: GeoPoint} from all <node> elements."""
        index: dict[int, GeoPoint] = {}
        for node in root.findall("node"):
            try:
                nid = int(node.get("id", ""))
                lat = float(node.get("lat", ""))
                lng = float(node.get("lon", ""))
                # GeoPoint.__post_init__ raises on out-of-range coords
                index[nid] = GeoPoint(latitude=lat, longitude=lng)
            except (ValueError, TypeError):
                continue
        return index

    def _extract_ways(
        self,
        root: ET.Element,
        nodes: dict[int, GeoPoint],
        *,
        include_pedestrian: bool,
        include_unnamed: bool,
    ) -> tuple[list[ParsedRoad], int, dict[str, int]]:
        roads: list[ParsedRoad] = []
        skipped = 0
        reasons: dict[str, int] = {}

        unnamed_counter = 0

        for way in root.findall("way"):
            way_id_str = way.get("id", "0")
            try:
                way_id = int(way_id_str)
            except ValueError:
                skipped += 1
                reasons["bad_way_id"] = reasons.get("bad_way_id", 0) + 1
                continue

            tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
            highway = tags.get("highway")

            # Filter: must be a highway tag
            if not highway:
                skipped += 1
                reasons["not_highway"] = reasons.get("not_highway", 0) + 1
                continue

            # Filter: drivable vs pedestrian
            if highway in DRIVABLE_HIGHWAY_TAGS:
                pass  # accept
            elif highway in PEDESTRIAN_HIGHWAY_TAGS and include_pedestrian:
                pass  # accept
            else:
                skipped += 1
                reasons["not_drivable"] = reasons.get("not_drivable", 0) + 1
                continue

            # Resolve node references
            coords: list[GeoPoint] = []
            for nd in way.findall("nd"):
                ref_str = nd.get("ref", "")
                try:
                    ref = int(ref_str)
                except ValueError:
                    continue
                point = nodes.get(ref)
                if point is not None:
                    coords.append(point)

            if len(coords) < 2:
                skipped += 1
                reasons["lt_2_points"] = reasons.get("lt_2_points", 0) + 1
                continue

            # Name handling
            name = (tags.get("name") or "").strip()
            had_name = bool(name)
            if not had_name:
                if not include_unnamed:
                    skipped += 1
                    reasons["unnamed"] = reasons.get("unnamed", 0) + 1
                    continue
                unnamed_counter += 1
                name = f"Sem nome {unnamed_counter}"

            # Direction
            oneway = (tags.get("oneway") or "").lower()
            direction = (RoadDirection.ONE_WAY
                         if oneway in ("yes", "true", "1", "-1")
                         else RoadDirection.TWO_WAY)
            # Note: oneway=-1 means reverse direction. For MVP we treat it
            # as one_way and trust the operator to verify direction.

            # Speed limit (best-effort)
            warnings: list[str] = []
            speed_limit, sw = self._parse_maxspeed(tags.get("maxspeed"))
            if sw:
                warnings.append(sw)

            # Width (best-effort)
            width, ww = self._parse_width(tags.get("width"))
            if ww:
                warnings.append(ww)

            roads.append(ParsedRoad(
                osm_way_id=way_id,
                name=name,
                coordinates=coords,
                direction=direction,
                speed_limit_kmh=speed_limit,
                width_meters=width,
                highway_tag=highway,
                had_name=had_name,
                osm_warnings=warnings,
            ))

        return roads, skipped, reasons

    @staticmethod
    def _parse_maxspeed(value: str | None) -> tuple[int, str | None]:
        """Parse OSM maxspeed tag. Returns (kmh, warning_or_none).

        Defaults to 20 km/h (condominium standard) if missing or unparseable.
        """
        if not value:
            return 20, None
        # OSM allows "30", "30 mph", "RU:urban", etc. We accept only plain numbers.
        try:
            cleaned = value.split()[0]
            kmh = int(float(cleaned))
            if kmh <= 0 or kmh > 200:
                return 20, f"maxspeed '{value}' out of range; using 20"
            return kmh, None
        except (ValueError, IndexError):
            return 20, f"maxspeed '{value}' not parseable; using 20"

    @staticmethod
    def _parse_width(value: str | None) -> tuple[float, str | None]:
        """Parse OSM width tag (meters). Defaults to 6.0."""
        if not value:
            return 6.0, None
        try:
            cleaned = value.split()[0].replace(",", ".")
            meters = float(cleaned)
            if meters <= 0 or meters > 50:
                return 6.0, f"width '{value}' out of range; using 6.0"
            return meters, None
        except (ValueError, IndexError):
            return 6.0, f"width '{value}' not parseable; using 6.0"
```

### 4.2 New module: `osm/importer.py`

Thin orchestrator: takes the parser's output + the operator's selection,
delegates to the existing `MapRepository`, then triggers validation. **No
new database access patterns** — every call goes through the existing repo.

**File**: `src/guardianmapstudio/osm/importer.py`

```python
from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from sqlalchemy.orm import Session

from guardianmapstudio.database.repository import MapRepository
from guardianmapstudio.domain.contracts import Road
from guardianmapstudio.osm.parser import ParsedRoad


@dataclass(frozen=True, slots=True)
class ImportSummary:
    created_count: int
    skipped_count: int
    renamed: list[tuple[str, str]]  # (original_name, final_name)
    deleted_existing: int            # > 0 only when replace_existing=True


class OsmImporter:
    """Creates Road entities from ParsedRoad objects in a workspace.

    Reuses MapRepository.create_road() so all existing invariants apply:
    - workspace must be DRAFT (enforced by the router before calling this)
    - road names are unique per workspace (enforced here via suffix)
    - JSON coordinates persisted with ensure_ascii=False (repository handles it)
    """

    def __init__(self, db: Session) -> None:
        self._repo = MapRepository(db)

    def import_roads(
        self,
        workspace_id: int,
        parsed_roads: list[ParsedRoad],
        *,
        replace_existing: bool = False,
    ) -> ImportSummary:
        """Create Roads in the workspace from the given parsed roads.

        Args:
            workspace_id: the active DRAFT Workspace id.
            parsed_roads: roads selected by the operator for import.
            replace_existing: if True, delete all existing roads in the
                workspace first. Use with caution — also deletes any
                waypoints attached to those roads via name reference.

        Returns:
            ImportSummary with counts and renamed list.
        """
        deleted = 0
        if replace_existing:
            deleted = self._delete_all_roads(workspace_id)

        existing_names: set[str] = {
            r.name for r in self._repo.get_roads(workspace_id)
        }

        created = 0
        renamed: list[tuple[str, str]] = []

        for pr in parsed_roads:
            final_name = self._dedupe_name(pr.name, existing_names)
            if final_name != pr.name:
                renamed.append((pr.name, final_name))
            existing_names.add(final_name)

            self._repo.create_road(
                workspace_id=workspace_id,
                name=final_name,
                coordinates=pr.coordinates,
                speed_limit_kmh=pr.speed_limit_kmh,
                direction=pr.direction,
                width_meters=pr.width_meters,
            )
            created += 1

        logger.info(
            "OSM import: created={} renamed={} deleted_existing={}",
            created, len(renamed), deleted,
        )
        return ImportSummary(
            created_count=created,
            skipped_count=0,
            renamed=renamed,
            deleted_existing=deleted,
        )

    def _delete_all_roads(self, workspace_id: int) -> int:
        """Delete every Road in the workspace. Used by replace_existing."""
        roads: list[Road] = self._repo.get_roads(workspace_id)
        for r in roads:
            # MapRepository.delete_road rejects roads with dependents; for
            # replace_existing we accept the risk and let those raise — the
            # router converts to 409 with a clear message.
            self._repo.delete_road(r.id)
        return len(roads)

    @staticmethod
    def _dedupe_name(name: str, taken: set[str]) -> str:
        """Return `name` if free, else `name (N)` with smallest N >= 2."""
        if name not in taken:
            return name
        n = 2
        while f"{name} ({n})" in taken:
            n += 1
        return f"{name} ({n})"
```

> **Note on `replace_existing` and dependents**: The existing
> `MapRepository.delete_road()` rejects deletion when a road has dependent
> waypoints or crossroads (BR-06). The router (§4.4) translates that into
> a `409` response. The operator can either uncheck `replace_existing` or
> delete the conflicting waypoints first.

### 4.3 Schema additions (`api/schemas.py`)

Append to the existing `schemas.py` — do not modify any existing class.

```python
# --- OSM Import (appended) ---

class ParsedRoadDTO(BaseModel):
    osm_way_id: int
    name: str
    coordinates: list[GeoPointDTO]
    direction: str           # "two_way" | "one_way"
    speed_limit_kmh: int
    width_meters: float
    highway_tag: str         # e.g. "residential"
    had_name: bool
    osm_warnings: list[str]


class OsmPreviewResponse(BaseModel):
    """Returned by POST /osm/preview. The frontend uses osm_way_id to
    correlate the operator's selection in the subsequent /osm/import call."""
    roads: list[ParsedRoadDTO]
    total_ways_in_file: int
    skipped_ways: int
    skipped_reasons: dict[str, int]


class OsmImportRequest(BaseModel):
    """Payload for POST /osm/import — sent after the operator confirms preview."""
    roads: list[ParsedRoadDTO]
    replace_existing: bool = False


class OsmImportResponse(BaseModel):
    workspace_id: int
    created_count: int
    deleted_existing: int
    renamed: list[dict[str, str]]   # [{"from": "...", "to": "..."}, ...]
```

### 4.4 New router: `api/routers/osm_import.py`

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from guardianmapstudio.api.deps import DbSession, get_settings
from guardianmapstudio.api.errors import ErrorCode
from guardianmapstudio.api.schemas import (
    GeoPointDTO,
    OsmImportRequest,
    OsmImportResponse,
    OsmPreviewResponse,
    ParsedRoadDTO,
)
from guardianmapstudio.api.routers._validation_helper import (
    _run_validation_after_write,
)
from guardianmapstudio.config.settings import GuardianMapStudioSettings
from guardianmapstudio.database.repository import WorkspaceRepository
from guardianmapstudio.domain.contracts import (
    GeoPoint,
    RoadDirection,
    WorkspaceState,
)
from guardianmapstudio.osm.importer import OsmImporter
from guardianmapstudio.osm.parser import OsmParser, ParsedRoad

router = APIRouter()


# Helper: ParsedRoad ⇄ ParsedRoadDTO
def _parsed_road_to_dto(pr: ParsedRoad) -> ParsedRoadDTO:
    return ParsedRoadDTO(
        osm_way_id=pr.osm_way_id,
        name=pr.name,
        coordinates=[GeoPointDTO(lat=p.latitude, lng=p.longitude)
                     for p in pr.coordinates],
        direction=pr.direction.value,
        speed_limit_kmh=pr.speed_limit_kmh,
        width_meters=pr.width_meters,
        highway_tag=pr.highway_tag,
        had_name=pr.had_name,
        osm_warnings=list(pr.osm_warnings),
    )


def _dto_to_parsed_road(dto: ParsedRoadDTO) -> ParsedRoad:
    return ParsedRoad(
        osm_way_id=dto.osm_way_id,
        name=dto.name,
        coordinates=[GeoPoint(latitude=p.lat, longitude=p.lng)
                     for p in dto.coordinates],
        direction=RoadDirection(dto.direction),
        speed_limit_kmh=dto.speed_limit_kmh,
        width_meters=dto.width_meters,
        highway_tag=dto.highway_tag,
        had_name=dto.had_name,
        osm_warnings=list(dto.osm_warnings),
    )


def _require_draft(workspace_id: int, db: Session) -> None:
    ws_repo = WorkspaceRepository(db)
    ws = ws_repo.get(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail={
            "error": ErrorCode.NOT_FOUND.value,
            "message": f"Workspace {workspace_id} not found",
            "detail": {},
        })
    if ws.state != WorkspaceState.DRAFT:
        raise HTTPException(status_code=409, detail={
            "error": ErrorCode.WORKSPACE_NOT_DRAFT.value,
            "message": "OSM import requires a DRAFT workspace",
            "detail": {"current_state": ws.state.value},
        })


@router.post(
    "/{workspace_id}/osm/preview",
    response_model=OsmPreviewResponse,
    status_code=status.HTTP_200_OK,
)
async def preview_osm(
    workspace_id: int,
    db: DbSession,
    settings: Annotated[GuardianMapStudioSettings, Depends(get_settings)],
    file: UploadFile = File(...),
    include_pedestrian: bool = False,
    include_unnamed: bool = False,
) -> OsmPreviewResponse:
    """Parse an OSM XML upload and return the detected roads.

    Does NOT write to the database. The frontend uses this response to
    show a preview; the operator confirms with POST /osm/import.
    """
    _require_draft(workspace_id, db)

    max_bytes = settings.osm_max_file_size_mb * 1024 * 1024
    payload = await file.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise HTTPException(status_code=413, detail={
            "error": ErrorCode.PAYLOAD_TOO_LARGE.value,
            "message": f"File exceeds {settings.osm_max_file_size_mb} MB limit",
            "detail": {"max_mb": settings.osm_max_file_size_mb},
        })

    try:
        result = OsmParser().parse(
            payload,
            include_pedestrian=include_pedestrian,
            include_unnamed=include_unnamed,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail={
            "error": ErrorCode.OSM_PARSE_ERROR.value,
            "message": str(e),
            "detail": {},
        }) from e

    if len(result.roads) > settings.osm_max_ways:
        raise HTTPException(status_code=422, detail={
            "error": ErrorCode.OSM_TOO_MANY_WAYS.value,
            "message": (
                f"File contains {len(result.roads)} drivable ways; "
                f"limit is {settings.osm_max_ways}. "
                "Trim the OSM export bounding box."
            ),
            "detail": {
                "ways_found": len(result.roads),
                "max_allowed": settings.osm_max_ways,
            },
        })

    return OsmPreviewResponse(
        roads=[_parsed_road_to_dto(r) for r in result.roads],
        total_ways_in_file=result.total_ways_in_file,
        skipped_ways=result.skipped_ways,
        skipped_reasons=result.skipped_reasons,
    )


@router.post(
    "/{workspace_id}/osm/import",
    response_model=OsmImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_osm(
    workspace_id: int,
    payload: OsmImportRequest,
    db: DbSession,
) -> OsmImportResponse:
    """Commit the operator-confirmed OSM roads into the workspace.

    Reuses MapRepository.create_road for each road, so all existing
    invariants (BR-05 unique name via suffix, JSON ensure_ascii=False,
    Double precision) apply automatically.
    """
    _require_draft(workspace_id, db)

    parsed = [_dto_to_parsed_road(d) for d in payload.roads]

    try:
        summary = OsmImporter(db).import_roads(
            workspace_id, parsed,
            replace_existing=payload.replace_existing,
        )
        db.commit()
    except ValueError as e:
        # Repository raises ValueError on BR violations (e.g. delete with dependents)
        db.rollback()
        raise HTTPException(status_code=409, detail={
            "error": ErrorCode.ROAD_HAS_DEPENDENTS.value,
            "message": str(e),
            "detail": {},
        }) from e
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail={
            "error": ErrorCode.DATABASE_ERROR.value,
            "message": "Database error during OSM import",
            "detail": {},
        }) from e

    # Re-run validation so has_validation_errors reflects the import
    _run_validation_after_write(workspace_id, db)
    db.commit()

    return OsmImportResponse(
        workspace_id=workspace_id,
        created_count=summary.created_count,
        deleted_existing=summary.deleted_existing,
        renamed=[{"from": a, "to": b} for (a, b) in summary.renamed],
    )
```

> **Refactor note**: The `_run_validation_after_write` helper currently lives
> inline in each router (per the Blueprint §4.5). For this new router, extract
> it into a small shared module `api/routers/_validation_helper.py` and update
> the existing routers to import from there. This is a pure mechanical move
> — no behavior change. If you prefer to avoid touching existing routers,
> duplicate the helper into `osm_import.py` instead; the duplication is small
> and acceptable for a single feature.

### 4.5 Register the router in `main.py`

Append one line to the router registration block:

```python
from guardianmapstudio.api.routers import (
    crossroads, export, osm_import, projects, restricted_areas,
    roads, validation, waypoints, workspaces,
)
# ... existing includes ...
app.include_router(
    osm_import.router,
    prefix="/api/v1/workspaces",
    tags=["osm_import"],
)
```

The prefix matches the existing workspace-scoped routers. The two new
endpoints become:

- `POST /api/v1/workspaces/{id}/osm/preview`
- `POST /api/v1/workspaces/{id}/osm/import`

### 4.6 Settings additions (`config/settings.py`)

Append to the existing `GuardianMapStudioSettings` class:

```python
    # OSM Import
    osm_max_file_size_mb: int = 10
    osm_max_ways: int = 500
```

Environment variables (`.env`):

```env
STUDIO_OSM_MAX_FILE_SIZE_MB=10
STUDIO_OSM_MAX_WAYS=500
```

### 4.7 ErrorCode additions (`api/errors.py`)

Append to the existing `ErrorCode` enum:

```python
class ErrorCode(str, Enum):
    # ... existing values ...
    OSM_PARSE_ERROR = "osm_parse_error"
    OSM_TOO_MANY_WAYS = "osm_too_many_ways"
    PAYLOAD_TOO_LARGE = "payload_too_large"
```

(`ROAD_HAS_DEPENDENTS` and `DATABASE_ERROR` likely already exist; add only
the ones missing.)

### 4.8 Validation after import

The router calls the existing `_run_validation_after_write(workspace_id, db)`
helper after every successful import. This:

- Updates the workspace's `has_validation_errors` flag
- Refreshes `last_validated_at`
- Re-runs every rule in the ValidationEngine (including `workspace.min_roads`,
  which clears after the first import)

No new validation rules are introduced. Existing rules — `road.min_points`
(satisfied since OSM ways have ≥2 nodes), `road.name_unique` (satisfied by
the name suffixing), `road.speed_limit_positive`, `road.width_positive` —
all apply unchanged.

### 4.9 Tests

#### `tests/unit/test_osm_parser.py`

```
test_parse_empty_osm_returns_zero_roads
test_parse_one_residential_way_returns_one_road
test_parse_pedestrian_way_excluded_by_default
test_parse_pedestrian_way_included_when_flag_set
test_parse_unnamed_way_excluded_by_default
test_parse_unnamed_way_included_with_synthetic_name
test_parse_way_with_lt_2_nodes_skipped
test_parse_oneway_yes_sets_one_way_direction
test_parse_oneway_missing_defaults_to_two_way
test_parse_maxspeed_valid_kmh
test_parse_maxspeed_with_mph_unit_falls_back_to_20
test_parse_maxspeed_missing_defaults_to_20
test_parse_width_valid_meters
test_parse_width_invalid_falls_back_to_6
test_parse_malformed_xml_raises_value_error
test_parse_root_not_osm_raises_value_error
test_parse_node_with_invalid_coordinate_skipped
test_parse_way_with_unresolved_node_ref_uses_only_resolved_nodes
test_skipped_reasons_aggregated_correctly
test_unicode_road_name_preserved  # "Avenida São João"
```

A fixture OSM file is included at `tests/fixtures/sample_condominio.osm`
with ~5 ways, mixed types, one duplicate name, one unnamed way.

#### `tests/unit/test_osm_importer.py`

```
test_import_creates_roads_in_workspace
test_import_dedupe_appends_suffix
test_import_dedupe_handles_multiple_collisions
test_import_replace_existing_deletes_first
test_import_empty_list_creates_nothing
test_import_preserves_coordinate_order
```

#### `tests/integration/test_api_osm_import.py`

```
test_preview_returns_200_with_roads
test_preview_rejects_non_xml_file
test_preview_rejects_oversize_file_413
test_preview_rejects_too_many_ways_422
test_preview_requires_draft_workspace_409
test_preview_with_include_pedestrian_returns_more_roads
test_import_creates_roads_201
test_import_renames_duplicates
test_import_replace_existing_clears_workspace
test_import_replace_existing_with_dependents_returns_409
test_import_triggers_validation
test_import_increments_workspace_has_no_errors_when_clean
test_full_flow_preview_then_import
```

#### Coverage target

- `osm/parser.py`: ≥ 95% (it is pure logic, easy to cover)
- `osm/importer.py`: ≥ 90%
- `api/routers/osm_import.py`: ≥ 85%
- **Overall project coverage must remain ≥ 80%** (the existing threshold).

---

## 5. Frontend Changes

### 5.1 Remove the "Area" toolbar button

In the editor toolbar (currently in `components/map/MapEditor.vue` or
wherever the drawing-mode buttons live), find the button bound to
`drawingMode === 'area'` and **delete the button only**.

**Before** (illustrative — exact markup depends on the implementation):

```vue
<button :class="{active: drawingMode==='road'}" @click="setMode('road')">
  Rua
</button>
<button :class="{active: drawingMode==='waypoint'}" @click="setMode('waypoint')">
  Waypoint
</button>
<button :class="{active: drawingMode==='area'}" @click="setMode('area')">
  Área
</button>
<button :class="{active: drawingMode==='select'}" @click="setMode('select')">
  Selecionar
</button>
```

**After**:

```vue
<button :class="{active: drawingMode==='road'}" @click="setMode('road')">
  Rua
</button>
<button :class="{active: drawingMode==='waypoint'}" @click="setMode('waypoint')">
  Waypoint
</button>
<button :class="{active: drawingMode==='select'}" @click="setMode('select')">
  Selecionar
</button>
```

**Do not** remove:

- The `'area'` value from the `DrawingMode` TypeScript union — keeping it
  costs nothing and avoids touching `setMode()` signatures.
- The `drawArea()` method, `RestrictedAreaForm.vue`, `mapStore.createArea`,
  `mapStore.restrictedAreas`, the `areasLayer` Leaflet group, or any
  rendering of existing restricted areas. Restricted areas already saved
  in a workspace must still render as polygons on the map (they came from
  a previously-published version or were created earlier via direct API
  call). Only the toolbar entry point is removed.

> **Justification for keeping the render path**: A workspace branched from
> a version that contained restricted areas will still have them in its
> map. Hiding them visually would mislead the operator about what will be
> exported.

### 5.2 Add the "Importar OSM" toolbar button

Add immediately after the "Selecionar" button:

```vue
<button
  class="import-osm-btn"
  :disabled="!isDraft"
  @click="openOsmImport"
  :title="isDraft ? 'Importar ruas do OpenStreetMap' : 'Disponível apenas em rascunho'"
>
  Importar OSM
</button>
```

The `isDraft` computed comes from the existing `workspaceStore.isDraft`
getter. When the modal is opened, `openOsmImport()` sets a local data
flag `osmImportOpen = true` which conditionally renders the modal.

### 5.3 New component: `components/map/OsmImportModal.vue`

A self-contained modal with five states. Uses the existing styling
conventions (no new CSS framework).

**Props**: `workspace-id: number`, `visible: boolean`
**Emits**: `close`, `imported(summary)`

```
States:
  idle      → file input visible, "Pré-visualizar" button disabled until file selected
  parsing   → spinner, "Analisando arquivo..."
  preview   → table of detected roads with checkboxes + options
  importing → spinner, "Importando N ruas..."
  done      → success summary, "Fechar" button
  error     → error message, "Tentar novamente" button
```

**Preview table columns**: checkbox (default checked), nome OSM, tipo
(`highway`), direção, nº de pontos, avisos (badge if `osm_warnings`
is non-empty).

**Options above the preview table**:

- Checkbox: "Substituir ruas existentes" (maps to `replace_existing`)
- Checkbox: "Incluir vias de pedestre" (`include_pedestrian`) — disabled
  in preview state, controls the *next* preview call
- Checkbox: "Incluir vias sem nome" (`include_unnamed`)

Changing either include-* checkbox in the preview state shows a
"Re-analisar" button that re-uploads the file with the new options.

**File validation client-side**: reject if `file.size > 10 * 1024 * 1024`
or if `file.name` does not end in `.osm` or `.xml`. The server enforces
the same limits.

### 5.4 API client additions (`api/client.ts`)

Append to the existing `api` object:

```typescript
export interface ParsedRoadDTO {
  osm_way_id: number
  name: string
  coordinates: GeoPoint[]
  direction: 'two_way' | 'one_way'
  speed_limit_kmh: number
  width_meters: number
  highway_tag: string
  had_name: boolean
  osm_warnings: string[]
}

export interface OsmPreviewResponse {
  roads: ParsedRoadDTO[]
  total_ways_in_file: number
  skipped_ways: number
  skipped_reasons: Record<string, number>
}

export interface OsmImportResponse {
  workspace_id: number
  created_count: number
  deleted_existing: number
  renamed: { from: string; to: string }[]
}

export const api = {
  // ... existing methods ...

  previewOsm: async (
    wsId: number,
    file: File,
    opts: { includePedestrian?: boolean; includeUnnamed?: boolean } = {},
  ): Promise<OsmPreviewResponse> => {
    const form = new FormData()
    form.append('file', file)
    const params = new URLSearchParams()
    if (opts.includePedestrian) params.set('include_pedestrian', 'true')
    if (opts.includeUnnamed) params.set('include_unnamed', 'true')
    const url = `/api/v1/workspaces/${wsId}/osm/preview?${params.toString()}`
    const res = await fetch(url, { method: 'POST', body: form })
    if (!res.ok) throw await res.json()
    return res.json()
  },

  importOsm: (wsId: number, payload: {
    roads: ParsedRoadDTO[]
    replace_existing: boolean
  }): Promise<OsmImportResponse> =>
    request<OsmImportResponse>(
      'POST', `/api/v1/workspaces/${wsId}/osm/import`, payload,
    ),
}
```

> Note: `previewOsm` uses `fetch` directly because the existing `request()`
> helper sets `Content-Type: application/json`, which is wrong for
> `multipart/form-data`. This is a one-off; the existing helper stays
> untouched.

### 5.5 Map store additions (`stores/map.ts`)

```typescript
actions: {
  // ... existing actions ...

  async previewOsmImport(file: File, opts: { includePedestrian?: boolean; includeUnnamed?: boolean }) {
    const wsId = workspaceStore.workspace?.id
    if (!wsId) throw new Error('No active workspace')
    return await api.previewOsm(wsId, file, opts)
  },

  async commitOsmImport(roads: ParsedRoadDTO[], replaceExisting: boolean) {
    const wsId = workspaceStore.workspace?.id
    if (!wsId) throw new Error('No active workspace')
    const result = await api.importOsm(wsId, { roads, replace_existing: replaceExisting })
    // Reload the full map so the new roads appear
    await this.fetchMap(wsId)
    // Refresh validation (the server already re-ran it; this syncs the store)
    await workspaceStore.runValidation()
    return result
  },
}
```

### 5.6 No changes to existing Leaflet rules

All seven critical Leaflet rules from Blueprint §5.4 continue to apply.
The new modal does not host a Leaflet map — it is a plain form modal —
so none of the map lifecycle rules are at risk.

---

## 6. New Workflow — WF-05: Importar mapa do OSM

```
1. Operator opens the project in GuardianMapStudio (DRAFT Workspace).
2. (Optional) Operator opens openstreetmap.org → navigates to the
   condominium → clicks "Exportar" → downloads <area>.osm.
3. Operator clicks "Importar OSM" in the editor toolbar.
4. OsmImportModal opens (state: idle).
5. Operator selects the .osm file → clicks "Pré-visualizar".
6. Modal calls POST /workspaces/{id}/osm/preview (state: parsing).
7. Preview state: table shows N detected roads. Operator unchecks any
   road to skip. Optionally toggles "Substituir ruas existentes" or
   the include-* options (which triggers re-parse).
8. Operator clicks "Importar selecionadas".
9. Modal calls POST /workspaces/{id}/osm/import (state: importing).
10. Server creates the Roads (with name deduplication), runs validation,
    commits.
11. Modal shows summary: "X ruas importadas, Y renomeadas, Z removidas".
12. Modal closes. Map editor reloads: the OSM roads appear as polylines.
13. Operator continues normally — adds waypoints, stop signs, etc.
14. Standard WF-01 from step 8 onwards (validate → publish → export).
```

### 6.1 Failure recovery in WF-05

- **Step 6 fails (parsing)**: modal shows the parser error and stays in
  preview state with empty list — operator can choose a different file.
- **Step 9 fails (409 from `replace_existing` with dependents)**: modal
  shows the message ("Algumas ruas existentes têm waypoints associados")
  and offers two paths: (a) uncheck "Substituir existentes" and re-import,
  or (b) close the modal, delete the conflicting waypoints, and retry.
- **Step 9 fails (500 database error)**: modal shows generic error;
  no roads were committed (transaction rolled back). Operator may retry.

---

## 7. Implementation Sequence

This is delivered as a **single Stage 6**, executed after MVP01 Stages 1–5
are complete and merged.

### Stage 6.A — Backend OSM module (no router yet)

1. Create `src/guardianmapstudio/osm/__init__.py` (empty).
2. Create `src/guardianmapstudio/osm/parser.py` per §4.1.
3. Create `src/guardianmapstudio/osm/importer.py` per §4.2.
4. Create `tests/fixtures/sample_condominio.osm` (~5 ways).
5. Write `tests/unit/test_osm_parser.py` and `test_osm_importer.py` per §4.9.

**Quality gate**:

```bash
uv run ruff check src/guardianmapstudio/osm/ tests/unit/test_osm_*.py
uv run mypy src/guardianmapstudio/osm/
uv run pytest tests/unit/test_osm_parser.py tests/unit/test_osm_importer.py -v \
    --cov=guardianmapstudio.osm --cov-report=term-missing
```

`osm/` coverage must be ≥ 90%.

### Stage 6.B — Backend router + schemas

1. Append to `src/guardianmapstudio/api/schemas.py` per §4.3.
2. Append to `src/guardianmapstudio/api/errors.py` per §4.7.
3. Append to `src/guardianmapstudio/config/settings.py` per §4.6.
4. Append `.env.example` with the new vars.
5. (Optional refactor) Create `api/routers/_validation_helper.py` and move
   `_run_validation_after_write` from existing routers. If this is not
   desired, duplicate the helper into `osm_import.py`.
6. Create `src/guardianmapstudio/api/routers/osm_import.py` per §4.4.
7. Register the router in `main.py` per §4.5.
8. Write `tests/integration/test_api_osm_import.py` per §4.9.

**Quality gate**:

```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/ -v --cov=guardianmapstudio --cov-fail-under=80
```

All existing tests must still pass — this is the regression guarantee.

### Stage 6.C — Frontend changes

1. Edit `frontend/src/components/map/MapEditor.vue` (or the toolbar
   component): remove the "Área" button per §5.1; add the "Importar OSM"
   button per §5.2.
2. Append to `frontend/src/api/client.ts` per §5.4.
3. Append to `frontend/src/stores/map.ts` per §5.5.
4. Create `frontend/src/components/map/OsmImportModal.vue` per §5.3.
5. Wire the modal into `MapEditor.vue` (or the parent view that owns the
   toolbar): `<OsmImportModal :workspace-id="..." :visible="osmImportOpen" @close="..." />`.

**Quality gate**:

```bash
cd frontend
npm run build           # must succeed with zero TS errors
cd ..
uv run guardianmapstudio
# Manual checks in browser per §8 acceptance criteria
```

### Stage 6.D — End-to-end smoke

Run the WF-05 walkthrough manually, then run the existing WF-01 walkthrough
to confirm nothing else is broken. Confirm:

- Existing restricted areas (if any) still render on the map.
- Existing exports still pass `guardian-seed-map --from-json`.

---

## 8. Acceptance Criteria

### OSM Import — happy path

- [ ] `POST /workspaces/{id}/osm/preview` with a valid `.osm` file returns 200 with `roads[]`
- [ ] Each `ParsedRoadDTO.coordinates` has at least 2 points
- [ ] `oneway=yes` ways are marked `direction: "one_way"`
- [ ] Unicode road names are preserved (e.g. "Avenida São João")
- [ ] `POST /workspaces/{id}/osm/import` with the preview payload returns 201
- [ ] After import, `GET /workspaces/{id}/map` returns the new roads
- [ ] After import, `workspace.has_validation_errors` is `false` if no other errors exist
- [ ] After import, the `workspace.min_roads` validation error is cleared

### OSM Import — edge cases

- [ ] Malformed XML → 422 with `osm_parse_error`
- [ ] File > 10 MB → 413 with `payload_too_large`
- [ ] File with > 500 drivable ways → 422 with `osm_too_many_ways`
- [ ] PUBLISHED workspace → 409 with `workspace_not_draft`
- [ ] Ways with `highway=footway` are excluded unless `include_pedestrian=true`
- [ ] Ways with no `name` tag are excluded unless `include_unnamed=true`
- [ ] Duplicate names are renamed `"X"`, `"X (2)"`, `"X (3)"`
- [ ] `replace_existing=true` with road dependents → 409 with `road_has_dependents`
- [ ] `replace_existing=true` without dependents → existing roads deleted, new roads created

### UI cleanup

- [ ] "Área" / "Area" button no longer appears in the editor toolbar
- [ ] "Importar OSM" button appears in the editor toolbar
- [ ] "Importar OSM" is disabled when workspace state is PUBLISHED
- [ ] Existing restricted areas (from prior versions) still render on the map
- [ ] `GET /workspaces/{id}/restricted-areas` still returns the existing areas (backend intact)
- [ ] Export JSON still contains the `restricted_areas` key (possibly empty array)

### Regression — nothing else broken

- [ ] All Stage 1–5 tests pass with no modification
- [ ] Database still has exactly 11 tables (`test_create_tables_count == 11`)
- [ ] Overall test coverage ≥ 80%
- [ ] `ruff check` zero warnings
- [ ] `mypy --strict` zero errors
- [ ] WF-01 (manual workflow without OSM) completes end-to-end without error
- [ ] Exported JSON from a workspace populated via OSM import passes `guardian-seed-map --from-json`

---

## 9. Out of Scope (Future Work)

Documented here so reviewers know what was deliberately left out.

| Feature | Status | Why deferred |
|---|---|---|
| Automatic endpoint snap between adjacent OSM roads | MVP02 (already in Roadmap §MVP02) | Requires the road-to-segment snap algorithm not in MVP01 SnapEngine |
| Automatic crossroad creation at intersecting OSM ways | MVP02 (already in Roadmap §MVP02) | Requires CrossroadEngine auto-detect mode |
| Merging multi-segment OSM ways with the same name into one `Road` | MVP02 | Non-trivial graph traversal; operator can rename manually for now |
| Import OSM `<relation>` boundary polygons as `RestrictedArea` | MVP02 | UI button for restricted areas is being removed; revisit when re-enabled |
| OSM POIs (`amenity=parking`, `barrier=gate`, etc.) as waypoints | MVP02 | Better solved by the Candidate Entity pipeline (doc 12) once available |
| Import from `.osm.pbf` binary format | Not planned | Adds C++ dependency for ~no benefit in target environment |
| Direct download from OSM Overpass API by bounding box | Not planned | Operator's manual export step is sufficient and avoids network dependency on the Guardian machine |
| Re-projection of input from other CRSs | Not planned | OSM is always EPSG:4326 |
| Undo of an OSM import | Inherited from MVP02 undo/redo | Operator can use `replace_existing=true` to clear and retry; full undo lands in MVP02 |
| Diff preview between OSM data and existing workspace roads | MVP03 | UX-heavy; not needed for the initial productivity gain |

### 9.1 What the MVP02 "smart" OSM feature will add on top of this

When MVP02 OSM ships per Roadmap, it will *extend* (not replace) this
implementation:

- The preview will additionally show "suggested crossroads" between
  intersecting ways.
- The importer will run snap-aware merging on endpoints that coincide
  within 0.5 m, joining multi-segment streets automatically.
- The frontend will gain a side-by-side diff view ("3 ruas novas, 2
  ruas modificadas, 1 rua removida").

The MVP01.5 module designed in this document is the foundation those
features build on — no breaking change is required to move from this
"basic" import to the MVP02 "smart" import.

---

## 10. Notes for Reviewers

1. **Why "MVP01.5" rather than full MVP02**: the user's actual pain point
   is "drawing every road vertex is slow". The basic import solves 80% of
   that pain at 10% of the engineering effort of full MVP02 OSM. The
   sophisticated parts (snap merging, intersection detection) carry their
   own implementation risk and shouldn't be tied to a UX win that's
   independently valuable.

2. **Why we don't delete restricted area code**: the export contract with
   Guardian (`seed_from_json`) expects the `restricted_areas` key to be
   present. The `VersionResponse` schema includes `restricted_area_count`.
   Tests assert these. Deleting the code requires modifying ~6 files and
   risks breaking the Guardian integration test that runs on every CI
   build. The UI removal alone achieves the user's goal at zero risk.

3. **Why the parser is in `osm/` and not `import/`**: `import` is a Python
   keyword; `osm/` is explicit and matches what people will search for.

4. **What changes in the user-facing docs**: doc 04 (MVP01 Spec) gains
   WF-05 in §4; doc 09 (API Spec) gains two endpoints in §11; doc 11
   (Frontend Spec) gains the `OsmImportModal` and loses the area button
   in §4.3. The author may either edit those docs in place or treat this
   complementary spec as the authoritative source for the OSM feature.
