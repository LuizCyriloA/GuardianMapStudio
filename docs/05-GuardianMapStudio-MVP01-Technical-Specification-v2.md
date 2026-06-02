# GuardianMapStudio — MVP01 Technical Specification v2

This document defines the complete technical contracts for MVP01:
database schema, SQLAlchemy models, Pydantic DTOs, repository interfaces,
Guardian export format, and settings. The Implementation Blueprint (doc 13)
generates code directly from this specification.

---

## 1. Settings

File: `src/guardianmapstudio/config/settings.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class GuardianMapStudioSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="STUDIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite:///guardianmapstudio.db"

    # Export
    export_dir: str = "exports"         # default output directory for JSON files
    export_indent: int = 2              # JSON indentation (human-readable)

    # Geometry
    snap_tolerance_m: float = 0.5       # meters (projected) — snap threshold
    coordinate_precision: int = 7       # decimal places for lat/lng rounding

    # Logging
    log_level: str = "INFO"
    log_file: str = "guardianmapstudio.log"
    log_rotation_mb: int = 50
    log_retention_days: int = 30
```

`.env.example`:
```env
STUDIO_HOST=0.0.0.0
STUDIO_PORT=8000
STUDIO_DATABASE_URL=sqlite:///guardianmapstudio.db
STUDIO_EXPORT_DIR=exports
STUDIO_SNAP_TOLERANCE_M=0.5
STUDIO_COORDINATE_PRECISION=7
STUDIO_LOG_LEVEL=INFO
STUDIO_LOG_FILE=guardianmapstudio.log
STUDIO_LOG_ROTATION_MB=50
STUDIO_LOG_RETENTION_DAYS=30
```

---

## 2. Database Schema (11 Tables)

Engine: SQLite (`guardianmapstudio.db`)
ORM: SQLAlchemy 2.0 with `Mapped` and `mapped_column`

### Authoring Tables (5)

#### 2.1 projects

```sql
CREATE TABLE projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at  DATETIME NOT NULL,
    updated_at  DATETIME NOT NULL
);
```

#### 2.2 versions

```sql
CREATE TABLE versions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id           INTEGER NOT NULL REFERENCES projects(id),
    version_number       INTEGER NOT NULL,               -- auto-incremented per project
    name                 TEXT NOT NULL,                  -- e.g. "v3 - Adicionado playground"
    published_at         DATETIME NOT NULL,
    road_count           INTEGER NOT NULL DEFAULT 0,
    waypoint_count       INTEGER NOT NULL DEFAULT 0,
    crossroad_count      INTEGER NOT NULL DEFAULT 0,
    restricted_area_count INTEGER NOT NULL DEFAULT 0,
    UNIQUE (project_id, version_number)
);
CREATE INDEX ix_versions_project_id ON versions(project_id);
```

#### 2.3 workspaces

```sql
CREATE TABLE workspaces (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id            INTEGER NOT NULL REFERENCES projects(id),
    state                 TEXT NOT NULL DEFAULT 'draft',  -- 'draft' | 'published'
    base_version_id       INTEGER REFERENCES versions(id),
    created_at            DATETIME NOT NULL,
    updated_at            DATETIME NOT NULL,
    last_validated_at     DATETIME,
    has_validation_errors BOOLEAN NOT NULL DEFAULT 0,
    CHECK (state IN ('draft', 'published'))
);
CREATE INDEX ix_workspaces_project_id ON workspaces(project_id);
CREATE INDEX ix_workspaces_state      ON workspaces(state);
```

#### 2.4 export_history

```sql
CREATE TABLE export_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id      INTEGER NOT NULL REFERENCES versions(id),
    project_id      INTEGER NOT NULL REFERENCES projects(id),
    exported_at     DATETIME NOT NULL,
    file_path       TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX ix_export_history_version_id ON export_history(version_id);
CREATE INDEX ix_export_history_project_id ON export_history(project_id);
```

#### 2.5 validation_results

```sql
CREATE TABLE validation_results (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id         INTEGER NOT NULL REFERENCES workspaces(id),
    severity             TEXT NOT NULL,   -- 'error' | 'warning'
    rule_id              TEXT NOT NULL,   -- e.g. 'road.min_points'
    message              TEXT NOT NULL,
    affected_entity_type TEXT NOT NULL,   -- 'road'|'waypoint'|'crossroad'|'restricted_area'
    affected_entity_id   INTEGER NOT NULL,
    created_at           DATETIME NOT NULL,
    CHECK (severity IN ('error', 'warning'))
);
CREATE INDEX ix_validation_results_workspace_id ON validation_results(workspace_id);
CREATE INDEX ix_validation_results_severity     ON validation_results(workspace_id, severity);
```

---

### Map Tables (6)

#### 2.6 roads

```sql
CREATE TABLE roads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id    INTEGER NOT NULL REFERENCES workspaces(id),
    name            TEXT NOT NULL,
    coordinates     TEXT NOT NULL,   -- JSON: [{"lat": ..., "lng": ...}, ...]
    speed_limit_kmh INTEGER NOT NULL DEFAULT 20,
    direction       TEXT NOT NULL DEFAULT 'two_way',
    width_meters    REAL NOT NULL DEFAULT 6.0,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL,
    CHECK (direction IN ('two_way', 'one_way')),
    CHECK (speed_limit_kmh > 0),
    CHECK (width_meters > 0),
    UNIQUE (workspace_id, name)      -- road names unique within a workspace
);
CREATE INDEX ix_roads_workspace_id ON roads(workspace_id);
```

#### 2.7 waypoints

```sql
CREATE TABLE waypoints (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id    INTEGER NOT NULL REFERENCES workspaces(id),
    name            TEXT NOT NULL,
    waypoint_type   TEXT NOT NULL,
    latitude        REAL NOT NULL,   -- Double precision via SQLAlchemy
    longitude       REAL NOT NULL,
    road_name       TEXT,            -- nullable; must match roads.name if set
    heading_degrees REAL,            -- nullable; 0-360; only for stop_sign
    extra_data      TEXT NOT NULL DEFAULT '{}',  -- JSON
    active          BOOLEAN NOT NULL DEFAULT 1,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL,
    CHECK (waypoint_type IN ('stop_sign','speed_bump','gate','landmark',
                             'curve','crossroad','stop_zone')),
    CHECK (heading_degrees IS NULL OR (heading_degrees >= 0 AND heading_degrees <= 360))
);
CREATE INDEX ix_waypoints_workspace_id             ON waypoints(workspace_id);
CREATE INDEX ix_waypoints_workspace_type_active    ON waypoints(workspace_id, waypoint_type, active);
```

#### 2.8 crossroads

```sql
CREATE TABLE crossroads (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id),
    road_a_name  TEXT NOT NULL,
    road_b_name  TEXT NOT NULL,
    latitude     REAL NOT NULL,
    longitude    REAL NOT NULL,
    created_at   DATETIME NOT NULL,
    CHECK (road_a_name != road_b_name)
);
CREATE INDEX ix_crossroads_workspace_id ON crossroads(workspace_id);
```

#### 2.9 restricted_areas

```sql
CREATE TABLE restricted_areas (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id     INTEGER NOT NULL REFERENCES workspaces(id),
    name             TEXT NOT NULL,
    polygon          TEXT NOT NULL,  -- JSON: [{"lat": ..., "lng": ...}, ...]
    restriction_type TEXT NOT NULL,
    speed_limit_kmh  INTEGER,        -- required when restriction_type = 'speed_limit'
    active           BOOLEAN NOT NULL DEFAULT 1,
    created_at       DATETIME NOT NULL,
    updated_at       DATETIME NOT NULL,
    CHECK (restriction_type IN ('speed_limit', 'no_entry', 'pedestrian_only'))
);
CREATE INDEX ix_restricted_areas_workspace_id ON restricted_areas(workspace_id);
```

#### 2.10 road_versions

Immutable copy of roads at publish time.

```sql
CREATE TABLE road_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id      INTEGER NOT NULL REFERENCES versions(id),
    name            TEXT NOT NULL,
    coordinates     TEXT NOT NULL,
    speed_limit_kmh INTEGER NOT NULL,
    direction       TEXT NOT NULL,
    width_meters    REAL NOT NULL
);
CREATE INDEX ix_road_versions_version_id ON road_versions(version_id);
```

#### 2.11 entity_versions

Immutable copy of all entities (waypoints, crossroads, restricted_areas) at publish time.
Uses a single table with `entity_type` discriminator to keep the publish transaction simple.

```sql
CREATE TABLE entity_versions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id       INTEGER NOT NULL REFERENCES versions(id),
    entity_type      TEXT NOT NULL,   -- 'waypoint' | 'crossroad' | 'restricted_area'
    name             TEXT NOT NULL,
    payload          TEXT NOT NULL,   -- full JSON of the entity at publish time
    CHECK (entity_type IN ('waypoint', 'crossroad', 'restricted_area'))
);
CREATE INDEX ix_entity_versions_version_id      ON entity_versions(version_id);
CREATE INDEX ix_entity_versions_version_type    ON entity_versions(version_id, entity_type);
```

**Payload JSON format by entity_type:**

When `entity_type = 'waypoint'`:
```json
{
  "waypoint_type": "speed_bump",
  "lat": -20.8103,
  "lng": -49.3756,
  "road_name": "Rua Principal",
  "heading_degrees": null,
  "extra_data": {"height_cm": 10},
  "active": true
}
```

When `entity_type = 'crossroad'`:
```json
{
  "road_a_name": "Rua Principal",
  "road_b_name": "Rua Secundária",
  "lat": -20.8105,
  "lng": -49.3756
}
```

When `entity_type = 'restricted_area'`:
```json
{
  "polygon": [
    {"lat": -20.8106, "lng": -49.3758},
    {"lat": -20.8106, "lng": -49.3754},
    {"lat": -20.8108, "lng": -49.3754},
    {"lat": -20.8108, "lng": -49.3758}
  ],
  "restriction_type": "speed_limit",
  "speed_limit_kmh": 10,
  "active": true
}
```

The `name` column in `entity_versions` is always populated (redundant with payload)
to enable quick listing queries without deserializing the JSON.

The `PublishService` serializes each entity to JSON using `json.dumps()` and stores
the complete state. The `ExportService` reads from `entity_versions` and deserializes
back to produce the Guardian export file.

---

## 3. SQLAlchemy Models

File: `src/guardianmapstudio/database/models.py`

```python
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Double, Float,
    ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ProjectModel(Base):
    __tablename__ = "projects"

    id:          Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:        Mapped[str]      = mapped_column(String(200), nullable=False)
    description: Mapped[str]      = mapped_column(Text, default="", nullable=False)
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                       default=lambda: datetime.now(timezone.utc))
    updated_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                       default=lambda: datetime.now(timezone.utc),
                                       onupdate=lambda: datetime.now(timezone.utc))

    versions:   Mapped[list[VersionModel]]   = relationship(back_populates="project")
    workspaces: Mapped[list[WorkspaceModel]] = relationship(back_populates="project")


class VersionModel(Base):
    __tablename__ = "versions"
    __table_args__ = (
        UniqueConstraint("project_id", "version_number", name="uq_versions_project_number"),
        Index("ix_versions_project_id", "project_id"),
    )

    id:                    Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id:            Mapped[int]      = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    version_number:        Mapped[int]      = mapped_column(Integer, nullable=False)
    name:                  Mapped[str]      = mapped_column(String(200), nullable=False)
    published_at:          Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    road_count:            Mapped[int]      = mapped_column(Integer, default=0, nullable=False)
    waypoint_count:        Mapped[int]      = mapped_column(Integer, default=0, nullable=False)
    crossroad_count:       Mapped[int]      = mapped_column(Integer, default=0, nullable=False)
    restricted_area_count: Mapped[int]      = mapped_column(Integer, default=0, nullable=False)

    project:        Mapped[ProjectModel]        = relationship(back_populates="versions")
    road_versions:  Mapped[list[RoadVersionModel]]   = relationship(back_populates="version")
    entity_versions: Mapped[list[EntityVersionModel]] = relationship(back_populates="version")


class WorkspaceModel(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("state IN ('draft', 'published')", name="ck_workspaces_state"),
        Index("ix_workspaces_project_id", "project_id"),
        Index("ix_workspaces_state",      "state"),
    )

    id:                    Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id:            Mapped[int]           = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    state:                 Mapped[str]           = mapped_column(String(20), default="draft", nullable=False)
    base_version_id:       Mapped[int | None]    = mapped_column(Integer, ForeignKey("versions.id"), nullable=True)
    created_at:            Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False,
                                                      default=lambda: datetime.now(timezone.utc))
    updated_at:            Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False,
                                                      default=lambda: datetime.now(timezone.utc),
                                                      onupdate=lambda: datetime.now(timezone.utc))
    last_validated_at:     Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    has_validation_errors: Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)

    project:    Mapped[ProjectModel]           = relationship(back_populates="workspaces")
    roads:      Mapped[list[RoadModel]]        = relationship(back_populates="workspace", cascade="all, delete-orphan")
    waypoints:  Mapped[list[WaypointModel]]    = relationship(back_populates="workspace", cascade="all, delete-orphan")
    crossroads: Mapped[list[CrossroadModel]]   = relationship(back_populates="workspace", cascade="all, delete-orphan")
    areas:      Mapped[list[RestrictedAreaModel]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    validation_results: Mapped[list[ValidationResultModel]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class ExportHistoryModel(Base):
    __tablename__ = "export_history"
    __table_args__ = (
        Index("ix_export_history_version_id", "version_id"),
        Index("ix_export_history_project_id", "project_id"),
    )

    id:              Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id:      Mapped[int]      = mapped_column(Integer, ForeignKey("versions.id"), nullable=False)
    project_id:      Mapped[int]      = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    exported_at:     Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    file_path:       Mapped[str]      = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int]      = mapped_column(Integer, default=0, nullable=False)


class ValidationResultModel(Base):
    __tablename__ = "validation_results"
    __table_args__ = (
        CheckConstraint("severity IN ('error', 'warning')", name="ck_validation_severity"),
        Index("ix_validation_results_workspace_id", "workspace_id"),
        Index("ix_validation_results_severity",     "workspace_id", "severity"),
    )

    id:                   Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id:         Mapped[int]      = mapped_column(Integer, ForeignKey("workspaces.id"), nullable=False)
    severity:             Mapped[str]      = mapped_column(String(10), nullable=False)
    rule_id:              Mapped[str]      = mapped_column(String(50), nullable=False)
    message:              Mapped[str]      = mapped_column(Text, nullable=False)
    affected_entity_type: Mapped[str]      = mapped_column(String(30), nullable=False)
    affected_entity_id:   Mapped[int]      = mapped_column(Integer, nullable=False)
    created_at:           Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                default=lambda: datetime.now(timezone.utc))

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="validation_results")


class RoadModel(Base):
    __tablename__ = "roads"
    __table_args__ = (
        CheckConstraint("direction IN ('two_way', 'one_way')", name="ck_roads_direction"),
        CheckConstraint("speed_limit_kmh > 0",                name="ck_roads_speed_limit"),
        CheckConstraint("width_meters > 0",                   name="ck_roads_width"),
        UniqueConstraint("workspace_id", "name",              name="uq_roads_workspace_name"),
        Index("ix_roads_workspace_id", "workspace_id"),
    )

    id:              Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id:    Mapped[int]      = mapped_column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name:            Mapped[str]      = mapped_column(String(200), nullable=False)
    coordinates:     Mapped[str]      = mapped_column(Text, nullable=False)     # JSON
    speed_limit_kmh: Mapped[int]      = mapped_column(Integer, default=20, nullable=False)
    direction:       Mapped[str]      = mapped_column(String(10), default="two_way", nullable=False)
    width_meters:    Mapped[float]    = mapped_column(Float, default=6.0, nullable=False)
    created_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                           default=lambda: datetime.now(timezone.utc))
    updated_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                           default=lambda: datetime.now(timezone.utc),
                                           onupdate=lambda: datetime.now(timezone.utc))

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="roads")


class WaypointModel(Base):
    __tablename__ = "waypoints"
    __table_args__ = (
        CheckConstraint(
            "waypoint_type IN ('stop_sign','speed_bump','gate','landmark','curve','crossroad','stop_zone')",
            name="ck_waypoints_type",
        ),
        CheckConstraint(
            "heading_degrees IS NULL OR (heading_degrees >= 0 AND heading_degrees <= 360)",
            name="ck_waypoints_heading",
        ),
        Index("ix_waypoints_workspace_id",          "workspace_id"),
        Index("ix_waypoints_workspace_type_active", "workspace_id", "waypoint_type", "active"),
    )

    id:              Mapped[int]         = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id:    Mapped[int]         = mapped_column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name:            Mapped[str]         = mapped_column(String(200), nullable=False)
    waypoint_type:   Mapped[str]         = mapped_column(String(30), nullable=False)
    latitude:        Mapped[float]       = mapped_column(Double, nullable=False)  # Double for GPS precision
    longitude:       Mapped[float]       = mapped_column(Double, nullable=False)
    road_name:       Mapped[str | None]  = mapped_column(String(200), nullable=True)
    heading_degrees: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra_data:      Mapped[str]         = mapped_column(Text, default="{}", nullable=False)  # JSON
    active:          Mapped[bool]        = mapped_column(Boolean, default=True, nullable=False)
    created_at:      Mapped[datetime]    = mapped_column(DateTime(timezone=True), nullable=False,
                                              default=lambda: datetime.now(timezone.utc))
    updated_at:      Mapped[datetime]    = mapped_column(DateTime(timezone=True), nullable=False,
                                              default=lambda: datetime.now(timezone.utc),
                                              onupdate=lambda: datetime.now(timezone.utc))

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="waypoints")


class CrossroadModel(Base):
    __tablename__ = "crossroads"
    __table_args__ = (
        CheckConstraint("road_a_name != road_b_name", name="ck_crossroads_distinct_roads"),
        Index("ix_crossroads_workspace_id", "workspace_id"),
    )

    id:           Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int]      = mapped_column(Integer, ForeignKey("workspaces.id"), nullable=False)
    road_a_name:  Mapped[str]      = mapped_column(String(200), nullable=False)
    road_b_name:  Mapped[str]      = mapped_column(String(200), nullable=False)
    latitude:     Mapped[float]    = mapped_column(Double, nullable=False)
    longitude:    Mapped[float]    = mapped_column(Double, nullable=False)
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                        default=lambda: datetime.now(timezone.utc))

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="crossroads")


class RestrictedAreaModel(Base):
    __tablename__ = "restricted_areas"
    __table_args__ = (
        CheckConstraint(
            "restriction_type IN ('speed_limit', 'no_entry', 'pedestrian_only')",
            name="ck_areas_restriction_type",
        ),
        Index("ix_restricted_areas_workspace_id", "workspace_id"),
    )

    id:               Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id:     Mapped[int]        = mapped_column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name:             Mapped[str]        = mapped_column(String(200), nullable=False)
    polygon:          Mapped[str]        = mapped_column(Text, nullable=False)  # JSON
    restriction_type: Mapped[str]        = mapped_column(String(30), nullable=False)
    speed_limit_kmh:  Mapped[int | None] = mapped_column(Integer, nullable=True)
    active:           Mapped[bool]       = mapped_column(Boolean, default=True, nullable=False)
    created_at:       Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False,
                                              default=lambda: datetime.now(timezone.utc))
    updated_at:       Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False,
                                              default=lambda: datetime.now(timezone.utc),
                                              onupdate=lambda: datetime.now(timezone.utc))

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="areas")


class RoadVersionModel(Base):
    __tablename__ = "road_versions"
    __table_args__ = (Index("ix_road_versions_version_id", "version_id"),)

    id:              Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id:      Mapped[int]   = mapped_column(Integer, ForeignKey("versions.id"), nullable=False)
    name:            Mapped[str]   = mapped_column(String(200), nullable=False)
    coordinates:     Mapped[str]   = mapped_column(Text, nullable=False)
    speed_limit_kmh: Mapped[int]   = mapped_column(Integer, nullable=False)
    direction:       Mapped[str]   = mapped_column(String(10), nullable=False)
    width_meters:    Mapped[float] = mapped_column(Float, nullable=False)

    version: Mapped[VersionModel] = relationship(back_populates="road_versions")


class EntityVersionModel(Base):
    __tablename__ = "entity_versions"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('waypoint', 'crossroad', 'restricted_area')",
            name="ck_entity_versions_type",
        ),
        Index("ix_entity_versions_version_id",   "version_id"),
        Index("ix_entity_versions_version_type", "version_id", "entity_type"),
    )

    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id:  Mapped[int] = mapped_column(Integer, ForeignKey("versions.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name:        Mapped[str] = mapped_column(String(200), nullable=False)
    payload:     Mapped[str] = mapped_column(Text, nullable=False)  # full entity JSON at publish time

    version: Mapped[VersionModel] = relationship(back_populates="entity_versions")
```

---

## 4. Pydantic DTOs (Request / Response)

File: `src/guardianmapstudio/api/schemas.py`

All DTOs use Pydantic v2 (`from pydantic import BaseModel`).

### 4.1 Project DTOs

```python
class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
```

### 4.2 Version DTOs

```python
class VersionResponse(BaseModel):
    id: int
    project_id: int
    version_number: int
    name: str
    published_at: datetime
    road_count: int
    waypoint_count: int
    crossroad_count: int
    restricted_area_count: int
    model_config = ConfigDict(from_attributes=True)
```

### 4.3 Workspace DTOs

```python
from typing import Literal

class WorkspaceResponse(BaseModel):
    id: int
    project_id: int
    state: Literal["draft", "published"]   # Literal prevents typos — mypy catches "Draft"
    base_version_id: int | None
    created_at: datetime
    updated_at: datetime
    last_validated_at: datetime | None
    has_validation_errors: bool
    model_config = ConfigDict(from_attributes=True)

class PublishRequest(BaseModel):
    version_name: str                   # e.g. "v3 - Adicionado playground"
```

### 4.4 Road DTOs

```python
class GeoPointDTO(BaseModel):
    lat: float
    lng: float

class RoadCreate(BaseModel):
    name: str
    coordinates: list[GeoPointDTO]      # minimum 2 points
    speed_limit_kmh: int = 20
    direction: str = "two_way"          # 'two_way' | 'one_way'
    width_meters: float = 6.0

class RoadUpdate(BaseModel):
    name: str | None = None
    coordinates: list[GeoPointDTO] | None = None
    speed_limit_kmh: int | None = None
    direction: str | None = None
    width_meters: float | None = None

class RoadResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    coordinates: list[GeoPointDTO]
    speed_limit_kmh: int
    direction: str
    width_meters: float
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

### 4.5 Waypoint DTOs

```python
class WaypointCreate(BaseModel):
    name: str
    waypoint_type: str                  # WaypointType value
    lat: float
    lng: float
    road_name: str | None = None
    heading_degrees: float | None = None
    extra_data: dict = {}
    active: bool = True

class WaypointUpdate(BaseModel):
    name: str | None = None
    waypoint_type: str | None = None
    lat: float | None = None
    lng: float | None = None
    road_name: str | None = None
    heading_degrees: float | None = None
    extra_data: dict | None = None
    active: bool | None = None

class WaypointResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    waypoint_type: str
    lat: float
    lng: float
    road_name: str | None
    heading_degrees: float | None
    extra_data: dict
    active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

### 4.6 Crossroad DTOs

```python
class CrossroadCreate(BaseModel):
    road_a_name: str
    road_b_name: str
    lat: float
    lng: float

class CrossroadResponse(BaseModel):
    id: int
    workspace_id: int
    road_a_name: str
    road_b_name: str
    lat: float
    lng: float
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

### 4.7 RestrictedArea DTOs

```python
class RestrictedAreaCreate(BaseModel):
    name: str
    polygon: list[GeoPointDTO]          # minimum 3 points
    restriction_type: str               # RestrictionType value
    speed_limit_kmh: int | None = None
    active: bool = True

class RestrictedAreaUpdate(BaseModel):
    name: str | None = None
    polygon: list[GeoPointDTO] | None = None
    restriction_type: str | None = None
    speed_limit_kmh: int | None = None
    active: bool | None = None

class RestrictedAreaResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    polygon: list[GeoPointDTO]
    restriction_type: str
    speed_limit_kmh: int | None
    active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

### 4.8 Validation DTOs

```python
class ValidationResultResponse(BaseModel):
    id: int
    severity: str                       # 'error' | 'warning'
    rule_id: str
    message: str
    affected_entity_type: str
    affected_entity_id: int

class ValidationSummaryResponse(BaseModel):
    workspace_id: int
    error_count: int
    warning_count: int
    can_publish: bool                   # True when error_count == 0
    results: list[ValidationResultResponse]
    validated_at: datetime
```

### 4.9 Export DTOs

```python
class ExportResponse(BaseModel):
    export_id: int
    version_id: int
    file_path: str
    file_size_bytes: int
    exported_at: datetime

class ExportHistoryResponse(BaseModel):
    items: list[ExportResponse]
    total: int
```

### 4.10 Error Response

```python
class ErrorResponse(BaseModel):
    error: str                          # machine-readable code, e.g. "workspace_not_found"
    message: str                        # human-readable description
    detail: dict = {}                   # optional extra context
```

---

## 5. Guardian Export Format (Canonical)

Produced by `GuardianExporter`. Must pass Guardian's `seed_from_json()` without error.

```json
{
  "meta": {
    "exported_by": "GuardianMapStudio",
    "version_id": 3,
    "version_name": "v3 - Adicionado playground",
    "project_name": "Condomínio Exemplo",
    "exported_at": "2026-06-01T14:35:22+00:00",
    "schema_version": "1.0"
  },
  "roads": [
    {
      "name": "Rua Principal",
      "coordinates": [
        {"lat": -20.8100, "lng": -49.3756},
        {"lat": -20.8105, "lng": -49.3756},
        {"lat": -20.8110, "lng": -49.3756}
      ],
      "speed_limit_kmh": 20,
      "direction": "two_way",
      "width_meters": 6.0
    }
  ],
  "waypoints": [
    {"name": "Lombada 1",           "type": "speed_bump", "lat": -20.8103, "lng": -49.3756,
     "road": "Rua Principal",  "extra_data": {"height_cm": 10}},
    {"name": "PARE - Cruzamento",   "type": "stop_sign",  "lat": -20.8105, "lng": -49.3756,
     "road": "Rua Principal",  "heading_degrees": 90.0, "extra_data": {}},
    {"name": "Portaria Principal",  "type": "gate",       "lat": -20.8100, "lng": -49.3756,
     "road": null,             "extra_data": {"gate_type": "entry_exit"}},
    {"name": "Curva Perigosa",      "type": "curve",      "lat": -20.8107, "lng": -49.3754,
     "road": "Rua Principal",  "extra_data": {}}
  ],
  "crossroads": [
    {"road_a": "Rua Principal", "road_b": "Rua Secundária",
     "lat": -20.8105, "lng": -49.3756}
  ],
  "restricted_areas": [
    {
      "name": "Playground",
      "polygon": [
        {"lat": -20.8106, "lng": -49.3758},
        {"lat": -20.8106, "lng": -49.3754},
        {"lat": -20.8108, "lng": -49.3754},
        {"lat": -20.8108, "lng": -49.3758}
      ],
      "restriction_type": "speed_limit",
      "speed_limit_kmh": 10,
      "active": true
    }
  ]
}
```

**Critical notes for `GuardianExporter`:**

| Rule | Detail |
|---|---|
| `meta` key | Always present; Guardian's `seed_from_json()` ignores unknown keys |
| `waypoints[].type` | Key is `"type"`, NOT `"waypoint_type"` — Guardian expects this name |
| `waypoints[].road` | Road name string or `null` — never omit this key |
| `crossroads[].road_a` | Road name — must match exactly a name in the `roads` array |
| `restricted_areas[].active` | Always include; Guardian uses it for soft-delete filtering |
| `heading_degrees` | Only included when not null — omit key entirely if null |
| `extra_data` | Always included, even when empty (`{}`) |
| `coordinates` order | Must match the original draw order (polyline direction) |
| Encoding | UTF-8 with `ensure_ascii=False` — road names may contain accented characters |
| Indentation | `indent=2` — human-readable, git-diffable |

---

## 6. Repository Interfaces

File: `src/guardianmapstudio/database/repository.py`

Repositories return domain contracts, never ORM models.

**Critical conversion rule**: All domain objects use `@dataclass(frozen=True, slots=True)`.
The `slots=True` decorator removes `__dict__` entirely. This means:
- `road.__dict__` raises `AttributeError` at runtime
- `dataclasses.asdict(road)` converts nested `GeoPoint` to `{"latitude": ..., "longitude": ...}`
  but API schemas expect `{"lat": ..., "lng": ...}` — key mismatch

**Correct conversion pattern in repository `_to_domain()` methods:**
```python
def _road_to_domain(self, model: RoadModel) -> Road:
    import json
    raw_coords = json.loads(model.coordinates)
    return Road(
        id=model.id,
        workspace_id=model.workspace_id,
        name=model.name,
        coordinates=[GeoPoint(latitude=p["lat"], longitude=p["lng"])
                     for p in raw_coords],    # lat/lng from JSON → GeoPoint.latitude/longitude
        speed_limit_kmh=model.speed_limit_kmh,
        direction=RoadDirection(model.direction),
        width_meters=model.width_meters,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
```

**Correct conversion pattern in router `_to_response()` functions:**
```python
# In each router file — never use __dict__ or dataclasses.asdict()
def road_to_response(road: Road) -> RoadResponse:
    return RoadResponse(
        id=road.id,
        workspace_id=road.workspace_id,
        name=road.name,
        coordinates=[GeoPointDTO(lat=p.latitude, lng=p.longitude)
                     for p in road.coordinates],  # GeoPoint.latitude → GeoPointDTO.lat
        speed_limit_kmh=road.speed_limit_kmh,
        direction=road.direction.value,
        width_meters=road.width_meters,
        created_at=road.created_at,
        updated_at=road.updated_at,
    )
```

```python
class ProjectRepository:
    def create(self, name: str, description: str) -> Project
    def get_by_id(self, project_id: int) -> Project | None
    def get_all(self) -> list[Project]
    def update(self, project_id: int, name: str, description: str) -> Project | None
    def delete(self, project_id: int) -> bool

class VersionRepository:
    def create(self, project_id: int, name: str, ...) -> Version
    def get_by_id(self, version_id: int) -> Version | None
    def get_all_for_project(self, project_id: int) -> list[Version]
    def get_latest_for_project(self, project_id: int) -> Version | None
    def next_version_number(self, project_id: int) -> int

class WorkspaceRepository:
    def create(self, project_id: int, base_version_id: int | None) -> Workspace
    def get_by_id(self, workspace_id: int) -> Workspace | None
    def get_active_draft(self, project_id: int) -> Workspace | None
    def set_published(self, workspace_id: int) -> Workspace | None
    def update_validation_state(self, workspace_id: int,
                                has_errors: bool, validated_at: datetime) -> None

class MapRepository:
    # Roads
    def create_road(self, workspace_id: int, road: RoadCreate) -> Road
    def get_road(self, road_id: int) -> Road | None
    def get_roads(self, workspace_id: int) -> list[Road]
    def update_road(self, road_id: int, update: RoadUpdate) -> Road | None
    def delete_road(self, road_id: int) -> bool

    # Waypoints
    def create_waypoint(self, workspace_id: int, wp: WaypointCreate) -> Waypoint
    def get_waypoint(self, waypoint_id: int) -> Waypoint | None
    def get_waypoints(self, workspace_id: int) -> list[Waypoint]
    def update_waypoint(self, waypoint_id: int, update: WaypointUpdate) -> Waypoint | None
    def delete_waypoint(self, waypoint_id: int) -> bool

    # Crossroads
    def create_crossroad(self, workspace_id: int, cr: CrossroadCreate) -> Crossroad
    def get_crossroad(self, crossroad_id: int) -> Crossroad | None
    def get_crossroads(self, workspace_id: int) -> list[Crossroad]
    def delete_crossroad(self, crossroad_id: int) -> bool

    # Restricted Areas
    def create_area(self, workspace_id: int, area: RestrictedAreaCreate) -> RestrictedArea
    def get_area(self, area_id: int) -> RestrictedArea | None
    def get_areas(self, workspace_id: int) -> list[RestrictedArea]
    def update_area(self, area_id: int, update: RestrictedAreaUpdate) -> RestrictedArea | None
    def delete_area(self, area_id: int) -> bool

class ValidationRepository:
    def replace_results(self, workspace_id: int,
                        results: list[ValidationResult]) -> None
    def get_results(self, workspace_id: int) -> list[ValidationResult]
    def count_errors(self, workspace_id: int) -> int

class ExportRepository:
    def create_record(self, version_id: int, project_id: int,
                      file_path: str, file_size_bytes: int) -> ExportRecord
    def get_history(self, project_id: int) -> list[ExportRecord]
```

---

## 7. HTTP Error Codes

### 7.1 Error code constants

File: `src/guardianmapstudio/api/errors.py`

```python
from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Machine-readable error codes returned in ErrorResponse.error field.

    Every error response from the API uses one of these constants.
    The Claude Code implementation must use ErrorCode.VALUE.value — never
    hardcode the string directly in router code.
    """
    NOT_FOUND                  = "not_found"
    WORKSPACE_NOT_DRAFT        = "workspace_not_draft"
    VALIDATION_ERRORS_BLOCKING = "validation_errors_blocking"
    ROAD_NAME_DUPLICATE        = "road_name_duplicate"
    ROAD_HAS_DEPENDENTS        = "road_has_dependents"
    INVALID_ENUM_VALUE         = "invalid_enum_value"
    MISSING_REQUIRED_FIELD     = "missing_required_field"
    EXPORT_WRITE_ERROR         = "export_write_error"
    DATABASE_ERROR             = "database_error"
```

### 7.2 Error code reference table

| Situation | Status | ErrorCode | Example message |
|---|---|---|---|
| Resource not found | 404 | `NOT_FOUND` | "Project with id 99 not found" |
| Workspace not in DRAFT state | 409 | `WORKSPACE_NOT_DRAFT` | "Workspace 7 is published — cannot modify" |
| Publish blocked by validation errors | 422 | `VALIDATION_ERRORS_BLOCKING` | "Cannot publish: 2 validation errors must be fixed first" |
| Road name not unique in workspace | 409 | `ROAD_NAME_DUPLICATE` | "Road name 'Rua Principal' already exists in this workspace" |
| Road referenced by dependents on delete | 409 | `ROAD_HAS_DEPENDENTS` | "Cannot delete: 3 waypoints and 1 crossroad reference this road" |
| Invalid enum value in request | 422 | `INVALID_ENUM_VALUE` | "Invalid waypoint_type 'lamp_post' — valid values: stop_sign, speed_bump, ..." |
| Required field missing in request | 422 | `MISSING_REQUIRED_FIELD` | "Field 'name' is required" |
| Export directory not writable | 500 | `EXPORT_WRITE_ERROR` | "Cannot write to exports/: permission denied" |
| Database error | 500 | `DATABASE_ERROR` | "Database operation failed — see server logs" |

### 7.3 Usage pattern in routers

```python
from guardianmapstudio.api.errors import ErrorCode
from guardianmapstudio.api.schemas import ErrorResponse

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=ErrorResponse(
        error=ErrorCode.NOT_FOUND.value,
        message=f"Road with id {road_id} not found",
    ).model_dump(),
)
```
