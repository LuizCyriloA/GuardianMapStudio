# GuardianMapStudio — Domain Model v2

This document defines all domain contracts: enums, value objects, aggregates,
domain events, and state machines. Every type defined here is the authoritative
source for the implementation in `src/guardianmapstudio/domain/`.

All dataclasses use `@dataclass(frozen=True, slots=True)` — immutable by design.
All enums use `str, Enum` so values serialize directly to JSON strings.

---

## 1. Enums

### 1.1 WorkspaceState

```python
class WorkspaceState(str, Enum):
    """Lifecycle state of a Workspace."""
    DRAFT     = "draft"      # actively being edited; may have validation errors
    PUBLISHED = "published"  # converted to a Version; read-only
```

**Valid transitions:**

```
DRAFT → PUBLISHED   (via Publish action — requires zero validation ERRORs)
```

There is no transition from PUBLISHED back to DRAFT. A new DRAFT Workspace
is automatically created from the published Version when publishing occurs.

---

### 1.2 ValidationSeverity

```python
class ValidationSeverity(str, Enum):
    """Severity of a validation result."""
    ERROR   = "error"    # blocks Publish; must be fixed
    WARNING = "warning"  # does not block Publish; informational
```

---

### 1.3 WaypointType

```python
class WaypointType(str, Enum):
    """Types of waypoints. Values MUST match Guardian's WaypointType enum exactly."""
    STOP_SIGN  = "stop_sign"   # PARE sign — triggers SLOW AND VERIFY + full stop
    SPEED_BUMP = "speed_bump"  # Physical bump — triggers speed reduction
    GATE       = "gate"        # Condominium gate (entry, exit, or both)
    LANDMARK   = "landmark"    # Informational marker — no Guardian safety behavior
    CURVE      = "curve"       # Road curve requiring reduced speed
    CROSSROAD  = "crossroad"   # Intersection marker (distinct from Crossroad entity)
    STOP_ZONE  = "stop_zone"   # Designated safe stopping position (Guardian ADR-016)
```

---

### 1.4 GateType

```python
class GateType(str, Enum):
    """Gate subtype. Values MUST match Guardian's GateType enum exactly."""
    ENTRY       = "entry"       # vehicles may enter but not exit
    EXIT        = "exit"        # vehicles may exit but not enter
    ENTRY_EXIT  = "entry_exit"  # bidirectional (most common)
    INTERNAL    = "internal"    # internal gate within the condominium
```

---

### 1.5 RestrictionType

```python
class RestrictionType(str, Enum):
    """Restricted area type. Values MUST match Guardian's RestrictionType enum exactly."""
    SPEED_LIMIT      = "speed_limit"       # reduced speed limit
    NO_ENTRY         = "no_entry"          # vehicle must not enter
    PEDESTRIAN_ONLY  = "pedestrian_only"   # reserved for pedestrians
```

---

### 1.6 RoadDirection

```python
class RoadDirection(str, Enum):
    """Road direction constraint. Values MUST match Guardian's RoadDirection enum exactly."""
    TWO_WAY = "two_way"  # default — bidirectional
    ONE_WAY = "one_way"  # unidirectional — direction implied by coordinate order
```

---

## 2. Value Objects

Value objects are immutable, have no identity of their own, and are defined
entirely by their field values.

### 2.1 GeoPoint

```python
@dataclass(frozen=True, slots=True)
class GeoPoint:
    """A single GPS coordinate in EPSG:4326 (WGS84).

    Stored as 7 decimal places (~1 cm precision at equatorial scale).
    In export JSON: serialized as {"lat": latitude, "lng": longitude}.
    """
    latitude: float   # -90.0 to +90.0
    longitude: float  # -180.0 to +180.0

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Invalid longitude: {self.longitude}")

    def to_export(self) -> dict:
        """Serialize to Guardian export format."""
        return {"lat": self.latitude, "lng": self.longitude}
```

---

### 2.2 ValidationResult

```python
@dataclass(frozen=True, slots=True)
class ValidationResult:
    """A single validation finding for a workspace entity.

    Produced by ValidationEngine. Stored in validation_results table.
    Displayed inline on the map (ERROR = red, WARNING = yellow).
    """
    severity: ValidationSeverity
    rule_id: str              # e.g. "road.min_points", "waypoint.outside_road"
    message: str              # human-readable, shown in UI
    affected_entity_type: str # "road", "waypoint", "crossroad", "restricted_area"
    affected_entity_id: int   # FK to the entity in the workspace

    @property
    def is_blocking(self) -> bool:
        """ERRORs block Publish; WARNINGs do not."""
        return self.severity == ValidationSeverity.ERROR
```

---

### 2.3 ExportMeta

```python
@dataclass(frozen=True, slots=True)
class ExportMeta:
    """Provenance block included in every Guardian export JSON.

    Guardian's seed_from_json() ignores unknown keys, so this block
    does not affect import compatibility.
    """
    exported_by: str    # always "GuardianMapStudio"
    version_id: int
    version_name: str
    project_name: str
    exported_at: str    # ISO 8601 UTC string
    schema_version: str # always "1.0" until format changes
```

---

### 2.4 SnapResult

```python
@dataclass(frozen=True, slots=True)
class SnapResult:
    """Result of a snap operation.

    snapped=True means the input point was close enough (< 0.5m projected)
    to an existing geometry and was moved to coincide with it.
    """
    original: GeoPoint
    snapped_to: GeoPoint
    snapped: bool
    distance_meters: float  # projected distance before snap
```

---

## 3. Aggregates

Aggregates are the core domain objects with identity (an `id` field).
They correspond directly to database tables.

### 3.1 Project

```python
@dataclass(frozen=True, slots=True)
class Project:
    """Top-level organizational unit. Represents one condominium.

    A Project contains one or more Versions and one active Workspace.
    Multiple Projects can exist in the same guardianmapstudio.db.
    """
    id: int
    name: str                      # e.g. "Condomínio Parque das Flores"
    description: str
    created_at: datetime
    updated_at: datetime
```

---

### 3.2 Version

```python
@dataclass(frozen=True, slots=True)
class Version:
    """Immutable snapshot of a Project's map at a point in time.

    Created by the Publish action. Can be exported to Guardian.
    Map data is frozen in road_versions and entity_versions tables.
    A Version can never be edited.
    """
    id: int
    project_id: int
    version_number: int    # auto-incremented per project: 1, 2, 3, ...
    name: str              # e.g. "v3 - Adicionado playground"
    published_at: datetime
    road_count: int        # snapshot counts for quick display
    waypoint_count: int
    crossroad_count: int
    restricted_area_count: int
```

---

### 3.3 Workspace

```python
@dataclass(frozen=True, slots=True)
class Workspace:
    """Mutable editing environment for a Project.

    State machine:
        DRAFT → PUBLISHED (via Publish — requires zero validation ERRORs)

    Only one DRAFT Workspace exists per Project at any time.
    When published, a new DRAFT is automatically created from the new Version.

    base_version_id: the Version this Workspace was branched from.
    None for the first Workspace of a new Project.
    """
    id: int
    project_id: int
    state: WorkspaceState
    base_version_id: int | None    # None for first workspace of new project
    created_at: datetime
    updated_at: datetime
    last_validated_at: datetime | None
    has_validation_errors: bool    # cached — True if any ERROR result exists
```

---

### 3.4 Road

```python
@dataclass(frozen=True, slots=True)
class Road:
    """A named drivable polyline within the condominium.

    Road names are used as foreign key references in Waypoints and Crossroads
    in the Guardian export JSON. Name must be unique within a Workspace.

    TREAT AS READ-ONLY: coordinates is a list — frozen=True protects the
    reference, not the list contents. Do not mutate.
    """
    id: int
    workspace_id: int
    name: str                      # unique within workspace
    coordinates: list[GeoPoint]    # minimum 2 points; TREAT AS READ-ONLY
    speed_limit_kmh: int           # km/h; positive integer
    direction: RoadDirection
    width_meters: float            # meters; typical range 4.0–8.0
    created_at: datetime
    updated_at: datetime

    @property
    def point_count(self) -> int:
        return len(self.coordinates)

    @property
    def is_valid_geometry(self) -> bool:
        """A road needs at least 2 points to define a segment."""
        return len(self.coordinates) >= 2
```

---

### 3.5 Waypoint

```python
@dataclass(frozen=True, slots=True)
class Waypoint:
    """A named point of interest on the condominium map.

    Type-specific data lives in extra_data:
        speed_bump  → {"height_cm": <int>}
        gate        → {"gate_type": "<GateType value>"}
        stop_sign   → {}  (heading in heading_degrees field)
        curve, landmark, crossroad, stop_zone → {}

    road_name: the name of the Road this waypoint belongs to.
    None for waypoints not associated with any road (e.g. gates).
    In the export JSON this becomes the "road" key.

    TREAT AS READ-ONLY: extra_data is a dict — do not mutate.
    """
    id: int
    workspace_id: int
    name: str
    waypoint_type: WaypointType
    position: GeoPoint
    road_name: str | None          # None = not on any road (gates, etc.)
    heading_degrees: float | None  # 0–360; only meaningful for stop_sign
    extra_data: dict               # TREAT AS READ-ONLY
    created_at: datetime
    updated_at: datetime
    active: bool = True
```

---

### 3.6 Crossroad

```python
@dataclass(frozen=True, slots=True)
class Crossroad:
    """An intersection between exactly two Roads.

    road_a_name and road_b_name must both exist in the same Workspace.
    In the export JSON these become the "road_a" and "road_b" keys.
    Guardian uses crossroads to trigger SLOW AND VERIFY (ADR-015).
    """
    id: int
    workspace_id: int
    road_a_name: str
    road_b_name: str
    position: GeoPoint
    created_at: datetime
```

---

### 3.7 RestrictedArea

```python
@dataclass(frozen=True, slots=True)
class RestrictedArea:
    """A polygonal zone where special rules apply.

    polygon must have at least 3 points.
    speed_limit_kmh only required when restriction_type == SPEED_LIMIT.

    TREAT AS READ-ONLY: polygon is a list — do not mutate.
    """
    id: int
    workspace_id: int
    name: str
    polygon: list[GeoPoint]        # minimum 3 points; TREAT AS READ-ONLY
    restriction_type: RestrictionType
    speed_limit_kmh: int | None    # required when restriction_type == SPEED_LIMIT
    created_at: datetime
    updated_at: datetime
    active: bool = True

    @property
    def is_valid_geometry(self) -> bool:
        return len(self.polygon) >= 3
```

---

### 3.8 ExportRecord

```python
@dataclass(frozen=True, slots=True)
class ExportRecord:
    """Record of a completed export action.

    Stored in the export_history table. Provides full audit trail.
    """
    id: int
    version_id: int
    project_id: int
    exported_at: datetime
    file_path: str       # absolute path to the generated JSON file
    file_size_bytes: int
```

---

## 4. Domain Events

Domain events are published internally when significant state changes occur.
They follow the same pattern as Guardian's domain events: `frozen=True, slots=True`,
timestamp inherited from `BaseEvent`.

```python
@dataclass(frozen=True, slots=True)
class BaseEvent:
    """Base for all GuardianMapStudio domain events."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class WorkspaceCreatedEvent(BaseEvent):
    """Emitted when a new Workspace is created (on new project or after publish)."""
    workspace_id: int = 0
    project_id: int = 0
    base_version_id: int | None = None


@dataclass(frozen=True, slots=True)
class WorkspacePublishedEvent(BaseEvent):
    """Emitted when a Workspace is successfully published as a new Version."""
    workspace_id: int = 0
    version_id: int = 0
    project_id: int = 0
    version_number: int = 0


@dataclass(frozen=True, slots=True)
class ValidationRunEvent(BaseEvent):
    """Emitted after a validation pass completes."""
    workspace_id: int = 0
    error_count: int = 0
    warning_count: int = 0
    duration_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class ExportCreatedEvent(BaseEvent):
    """Emitted when a Guardian export JSON is successfully written to disk."""
    version_id: int = 0
    project_id: int = 0
    file_path: str = ""
    file_size_bytes: int = 0


@dataclass(frozen=True, slots=True)
class RoadCreatedEvent(BaseEvent):
    workspace_id: int = 0
    road_id: int = 0
    road_name: str = ""


@dataclass(frozen=True, slots=True)
class RoadUpdatedEvent(BaseEvent):
    workspace_id: int = 0
    road_id: int = 0


@dataclass(frozen=True, slots=True)
class RoadDeletedEvent(BaseEvent):
    workspace_id: int = 0
    road_id: int = 0
    road_name: str = ""    # name kept for cascade cleanup of waypoints/crossroads


@dataclass(frozen=True, slots=True)
class WaypointCreatedEvent(BaseEvent):
    workspace_id: int = 0
    waypoint_id: int = 0
    waypoint_type: str = ""


@dataclass(frozen=True, slots=True)
class WaypointUpdatedEvent(BaseEvent):
    workspace_id: int = 0
    waypoint_id: int = 0


@dataclass(frozen=True, slots=True)
class WaypointDeletedEvent(BaseEvent):
    workspace_id: int = 0
    waypoint_id: int = 0


@dataclass(frozen=True, slots=True)
class CrossroadCreatedEvent(BaseEvent):
    workspace_id: int = 0
    crossroad_id: int = 0


@dataclass(frozen=True, slots=True)
class CrossroadDeletedEvent(BaseEvent):
    workspace_id: int = 0
    crossroad_id: int = 0


@dataclass(frozen=True, slots=True)
class RestrictedAreaCreatedEvent(BaseEvent):
    workspace_id: int = 0
    area_id: int = 0


@dataclass(frozen=True, slots=True)
class RestrictedAreaUpdatedEvent(BaseEvent):
    workspace_id: int = 0
    area_id: int = 0


@dataclass(frozen=True, slots=True)
class RestrictedAreaDeletedEvent(BaseEvent):
    workspace_id: int = 0
    area_id: int = 0
```

---

## 5. Invariants and Business Rules

These rules are enforced at the domain layer, before any database write.

### 5.1 Road

| Rule | Severity | Description |
|---|---|---|
| `road.min_points` | ERROR | Road must have at least 2 GeoPoints |
| `road.name_unique` | ERROR | Road name must be unique within the Workspace |
| `road.speed_limit_positive` | ERROR | speed_limit_kmh must be > 0 |
| `road.width_positive` | ERROR | width_meters must be > 0 |
| `road.no_waypoints` | WARNING | Road has no associated Waypoints |

### 5.2 Waypoint

| Rule | Severity | Description |
|---|---|---|
| `waypoint.road_exists` | ERROR | If road_name is set, it must reference an existing Road |
| `waypoint.heading_range` | ERROR | heading_degrees must be 0–360 if present |
| `waypoint.speed_bump_height` | ERROR | speed_bump must have extra_data.height_cm > 0 |
| `waypoint.gate_type_valid` | ERROR | gate must have extra_data.gate_type in GateType values |
| `waypoint.name_not_empty` | ERROR | name must not be blank |
| `waypoint.duplicate_position` | WARNING | Two waypoints at the same position (< 0.5m) |

### 5.3 Crossroad

| Rule | Severity | Description |
|---|---|---|
| `crossroad.road_a_exists` | ERROR | road_a_name must reference an existing Road |
| `crossroad.road_b_exists` | ERROR | road_b_name must reference an existing Road |
| `crossroad.roads_distinct` | ERROR | road_a_name != road_b_name |
| `crossroad.roads_intersect` | WARNING | The two roads do not geometrically intersect near the crossroad position |

### 5.4 RestrictedArea

| Rule | Severity | Description |
|---|---|---|
| `area.min_points` | ERROR | Polygon must have at least 3 GeoPoints |
| `area.speed_limit_required` | ERROR | speed_limit_kmh required when restriction_type == SPEED_LIMIT |
| `area.speed_limit_positive` | ERROR | speed_limit_kmh must be > 0 |
| `area.name_not_empty` | ERROR | name must not be blank |

### 5.5 Workspace Publish

| Rule | Check |
|---|---|
| Zero ERRORs | All ValidationResults with severity == ERROR must be absent |
| At least one Road | Workspace must have at least 1 Road |

---

## 6. Domain Services

Domain services implement operations that involve multiple aggregates.

### 6.1 PublishService

```
Input:  workspace_id
Output: Version (new) | raises DomainError

Steps:
  1. Load Workspace — must be in DRAFT state
  2. Run ValidationEngine — must return zero ERRORs
  3. Create Version record (next version_number for the project)
  4. Copy all Roads → road_versions (with version_id)
  5. Copy all Waypoints, Crossroads, RestrictedAreas → entity_versions (with version_id)
  6. Set Workspace.state = PUBLISHED
  7. Create new DRAFT Workspace based on the new Version
  8. Publish WorkspacePublishedEvent
  9. Return new Version
```

### 6.2 ExportService

```
Input:  version_id, output_path: str
Output: ExportRecord | raises DomainError

Steps:
  1. Load Version — must exist
  2. Load all road_versions for this version_id
  3. Load all entity_versions for this version_id
  4. Build ExportMeta with provenance
  5. Serialize to Guardian export JSON format (ADR-002)
  6. Write to output_path with indent=2
  7. Create ExportRecord
  8. Publish ExportCreatedEvent
  9. Return ExportRecord
```

### 6.3 ValidationService

```
Input:  workspace_id
Output: list[ValidationResult]

Steps:
  1. Load all Roads, Waypoints, Crossroads, RestrictedAreas for workspace
  2. Run ValidationEngine (all rule groups)
  3. Store results in validation_results table (replace previous results)
  4. Update Workspace.last_validated_at and has_validation_errors
  5. Publish ValidationRunEvent
  6. Return results
```

---

## 7. File Location

```
src/guardianmapstudio/domain/
├── __init__.py
├── contracts.py   ← all enums, value objects, and aggregates defined above
└── events.py      ← all domain events defined above
```

All imports of domain types throughout the codebase come from
`guardianmapstudio.domain.contracts` or `guardianmapstudio.domain.events`.
No type is redefined in another module.
