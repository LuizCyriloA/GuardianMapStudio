# GuardianMapStudio — Implementation Blueprint v3 (Consolidated)

This is the **single source of truth** for Claude Code.
All code needed to implement MVP01 is in this document.
Do NOT read other documents (01–12) unless explicitly instructed.

**Document priority order** — when any two documents appear to conflict,
the higher-priority document wins:

1. This Blueprint (doc 13) — implementation code, overrides everything
2. Technical Specification (doc 05) — database schema, DTOs, error codes
3. Domain Model (doc 08) — enums, aggregates, domain services
4. Spatial Accuracy (doc 03) — geometry algorithms, snap tolerance
5. API Specification (doc 09) — endpoint contracts, request/response shapes
6. All other documents (01, 02, 04, 06, 07, 10, 11, 12) — context only

**Document priority order** — when any two documents appear to conflict,
the higher-priority document wins:

```
1. Blueprint v3 (this file)           ← highest priority
2. Technical Specification (doc 05)   ← DTOs, schemas, SQL
3. Domain Model (doc 08)              ← contracts, events, services
4. Validation & Geometry Engine (doc 10) ← engine implementations
5. API Specification (doc 09)         ← endpoint contracts
6. All remaining docs (01–07, 11–12)  ← context and rationale only
```

**Implementation model**: 5 stages, each with a quality gate.
Do not advance to the next stage until all quality gates pass.

---

## How to use this document

1. Read the full stage section before creating any file
2. Copy the code blocks exactly — do not modify signatures, types, or names
3. Create all files listed in "Files to create"
4. Run the quality gate — fix ALL errors before proceeding
5. Never skip stages or implement features from a future stage

---

## Directory layout

```
guardianmapstudio/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml
├── docs/
├── src/
│   └── guardianmapstudio/
│       ├── __init__.py
│       ├── main.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── contracts.py
│       │   └── events.py
│       ├── database/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── connection.py
│       │   └── repository.py
│       ├── geometry/
│       │   ├── __init__.py
│       │   ├── engine.py
│       │   ├── snap.py
│       │   ├── crossroad.py
│       │   └── validation.py
│       ├── export/
│       │   ├── __init__.py
│       │   └── guardian_exporter.py
│       └── api/
│           ├── __init__.py
│           ├── deps.py
│           ├── schemas.py
│           ├── errors.py
│           └── routers/
│               ├── __init__.py
│               ├── projects.py
│               ├── workspaces.py
│               ├── roads.py
│               ├── waypoints.py
│               ├── crossroads.py
│               ├── restricted_areas.py
│               ├── validation.py
│               └── export.py
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── api/
│       │   ├── client.ts
│       │   └── types.ts
│       ├── stores/
│       │   ├── project.ts
│       │   ├── workspace.ts
│       │   └── map.ts
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppSidebar.vue
│       │   │   └── ValidationPanel.vue
│       │   ├── map/
│       │   │   ├── MapEditor.vue
│       │   │   ├── EntityForm.vue
│       │   │   └── MapLegend.vue
│       │   ├── workspace/
│       │   │   ├── WorkspaceHeader.vue
│       │   │   └── PublishModal.vue
│       │   └── version/
│       │       ├── VersionList.vue
│       │       └── VersionPreview.vue
│       └── views/
│           ├── ProjectList.vue
│           ├── EditorView.vue
│           └── VersionHistoryView.vue
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_contracts.py
│   │   ├── test_geometry_engine.py
│   │   ├── test_snap_engine.py
│   │   ├── test_crossroad_engine.py
│   │   ├── test_validation_engine.py
│   │   ├── test_guardian_exporter.py
│   │   └── test_repository.py
│   └── integration/
│       ├── test_database.py
│       ├── test_api_projects.py
│       ├── test_api_workspaces.py
│       ├── test_api_roads.py
│       ├── test_api_waypoints.py
│       └── test_api_export.py
└── exports/
```


---
---

# STAGE 1 — Foundation

## Objective

Establish the project skeleton, domain contracts, settings, and quality gates.
After this stage: `uv run guardianmapstudio` starts a FastAPI server on port 8000
that responds to `GET /api/v1/health` with `{"status": "ok"}`.

## Files to create in Stage 1

- `pyproject.toml`
- `README.md`
- `.env.example`
- `.gitignore`
- `.pre-commit-config.yaml`
- `.github/workflows/ci.yml`
- `src/guardianmapstudio/__init__.py`
- `src/guardianmapstudio/main.py`
- `src/guardianmapstudio/config/__init__.py`
- `src/guardianmapstudio/config/settings.py`
- `src/guardianmapstudio/domain/__init__.py`
- `src/guardianmapstudio/domain/contracts.py`
- `src/guardianmapstudio/domain/events.py`
- `tests/conftest.py`
- `tests/unit/test_contracts.py`
- All other `__init__.py` files for all packages listed in the directory layout

---

## 1.1 pyproject.toml

```toml
[project]
name = "guardianmapstudio"
version = "0.1.0"
description = "Map authoring tool for Guardian autonomous vehicle platform"
requires-python = ">=3.12"
dependencies = [
    "fastapi==0.115.6",
    "uvicorn[standard]==0.32.1",
    "sqlalchemy==2.0.40",
    "pydantic-settings==2.7.0",
    "shapely==2.0.6",
    "pyproj==3.7.0",
    "loguru==0.7.3",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.3",
    "pytest-cov==6.0.0",
    "pytest-timeout==2.3.1",
    "httpx==0.28.1",
    "ruff==0.8.6",
    "mypy==1.13.0",
    "pre-commit==4.0.1",
]

[project.scripts]
guardianmapstudio = "guardianmapstudio.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/guardianmapstudio"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "S", "B", "LOG"]
ignore = ["S101", "S104", "B008"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "S105", "S106"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
no_implicit_reexport = true

[[tool.mypy.overrides]]
module = ["shapely.*", "pyproj.*"]
ignore_missing_stubs = true
```

---

## 1.2 .env.example

```env
STUDIO_HOST=0.0.0.0
STUDIO_PORT=8000
STUDIO_DATABASE_URL=sqlite:///guardianmapstudio.db
STUDIO_EXPORT_DIR=exports
STUDIO_EXPORT_INDENT=2
STUDIO_SNAP_TOLERANCE_M=0.5
STUDIO_COORDINATE_PRECISION=7
STUDIO_LOG_LEVEL=INFO
STUDIO_LOG_FILE=guardianmapstudio.log
STUDIO_LOG_ROTATION_MB=50
STUDIO_LOG_RETENTION_DAYS=30
```

---

## 1.3 .gitignore

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
.venv/
venv/
.vscode/
.idea/
*.swp
*.db
*.log
.env
exports/
src/guardianmapstudio/static/
node_modules/
frontend/dist/
.coverage
htmlcov/
.pytest_cache/
.DS_Store
Thumbs.db
```

---

## 1.4 .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic==2.9.2
          - pydantic-settings==2.7.0
          - sqlalchemy==2.0.40
          - fastapi==0.115.6
        args: [--strict]
        files: ^src/
```

---

## 1.5 .github/workflows/ci.yml

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - name: Install dependencies
        run: |
          uv sync
          uv sync --extra dev
      - name: Ruff check
        run: uv run ruff check src/ tests/
      - name: Mypy
        run: uv run mypy src/
      - name: Pytest
        run: uv run pytest --cov=guardianmapstudio --cov-fail-under=80 -v
```

---

## 1.6 Settings

File: `src/guardianmapstudio/config/settings.py`

```python
from __future__ import annotations

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
    export_dir: str = "exports"
    export_indent: int = 2

    # Geometry
    snap_tolerance_m: float = 0.5
    coordinate_precision: int = 7

    # Logging
    log_level: str = "INFO"
    log_file: str = "guardianmapstudio.log"
    log_rotation_mb: int = 50
    log_retention_days: int = 30
```

---

## 1.7 Domain Contracts (COMPLETE CODE)

File: `src/guardianmapstudio/domain/contracts.py`

This is the complete file. Copy exactly.

```python
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


# ---------------------------------------------------------------------------
# Enums — string values MUST match Guardian's enums exactly
# ---------------------------------------------------------------------------

class WorkspaceState(str, Enum):
    DRAFT     = "draft"
    PUBLISHED = "published"


class ValidationSeverity(str, Enum):
    ERROR   = "error"
    WARNING = "warning"


class WaypointType(str, Enum):
    STOP_SIGN  = "stop_sign"
    SPEED_BUMP = "speed_bump"
    GATE       = "gate"
    LANDMARK   = "landmark"
    CURVE      = "curve"
    CROSSROAD  = "crossroad"
    STOP_ZONE  = "stop_zone"


class GateType(str, Enum):
    ENTRY       = "entry"
    EXIT        = "exit"
    ENTRY_EXIT  = "entry_exit"
    INTERNAL    = "internal"


class RestrictionType(str, Enum):
    SPEED_LIMIT      = "speed_limit"
    NO_ENTRY         = "no_entry"
    PEDESTRIAN_ONLY  = "pedestrian_only"


class RoadDirection(str, Enum):
    TWO_WAY = "two_way"
    ONE_WAY = "one_way"


# ---------------------------------------------------------------------------
# Value Objects — immutable, no identity
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Invalid longitude: {self.longitude}")

    def to_export(self) -> dict[str, float]:
        return {"lat": self.latitude, "lng": self.longitude}


@dataclass(frozen=True, slots=True)
class ValidationResult:
    severity: ValidationSeverity
    rule_id: str
    message: str
    affected_entity_type: str
    affected_entity_id: int

    @property
    def is_blocking(self) -> bool:
        return self.severity == ValidationSeverity.ERROR


@dataclass(frozen=True, slots=True)
class ExportMeta:
    exported_by: str
    version_id: int
    version_name: str
    project_name: str
    exported_at: str
    schema_version: str


@dataclass(frozen=True, slots=True)
class SnapResult:
    original: GeoPoint
    snapped_to: GeoPoint
    snapped: bool
    distance_meters: float


# ---------------------------------------------------------------------------
# Aggregates — have identity (id field), correspond to database tables
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Project:
    id: int
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Version:
    id: int
    project_id: int
    version_number: int
    name: str
    published_at: datetime
    road_count: int
    waypoint_count: int
    crossroad_count: int
    restricted_area_count: int


@dataclass(frozen=True, slots=True)
class Workspace:
    id: int
    project_id: int
    state: WorkspaceState
    base_version_id: int | None
    created_at: datetime
    updated_at: datetime
    last_validated_at: datetime | None
    has_validation_errors: bool


@dataclass(frozen=True, slots=True)
class Road:
    id: int
    workspace_id: int
    name: str
    coordinates: list[GeoPoint]    # TREAT AS READ-ONLY (frozen protects ref, not contents)
    speed_limit_kmh: int
    direction: RoadDirection
    width_meters: float
    created_at: datetime
    updated_at: datetime

    @property
    def point_count(self) -> int:
        return len(self.coordinates)

    @property
    def is_valid_geometry(self) -> bool:
        return len(self.coordinates) >= 2


@dataclass(frozen=True, slots=True)
class Waypoint:
    id: int
    workspace_id: int
    name: str
    waypoint_type: WaypointType
    position: GeoPoint
    road_name: str | None
    heading_degrees: float | None
    extra_data: dict               # TREAT AS READ-ONLY
    created_at: datetime
    updated_at: datetime
    active: bool = True


@dataclass(frozen=True, slots=True)
class Crossroad:
    id: int
    workspace_id: int
    road_a_name: str
    road_b_name: str
    position: GeoPoint
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RestrictedArea:
    id: int
    workspace_id: int
    name: str
    polygon: list[GeoPoint]        # TREAT AS READ-ONLY
    restriction_type: RestrictionType
    speed_limit_kmh: int | None
    created_at: datetime
    updated_at: datetime
    active: bool = True

    @property
    def is_valid_geometry(self) -> bool:
        return len(self.polygon) >= 3


@dataclass(frozen=True, slots=True)
class ExportRecord:
    id: int
    version_id: int
    project_id: int
    exported_at: datetime
    file_path: str
    file_size_bytes: int
```

---

## 1.8 Domain Events (COMPLETE CODE)

File: `src/guardianmapstudio/domain/events.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class BaseEvent:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class WorkspaceCreatedEvent(BaseEvent):
    workspace_id: int = 0
    project_id: int = 0
    base_version_id: int | None = None


@dataclass(frozen=True, slots=True)
class WorkspacePublishedEvent(BaseEvent):
    workspace_id: int = 0
    version_id: int = 0
    project_id: int = 0
    version_number: int = 0


@dataclass(frozen=True, slots=True)
class ValidationRunEvent(BaseEvent):
    workspace_id: int = 0
    error_count: int = 0
    warning_count: int = 0
    duration_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class ExportCreatedEvent(BaseEvent):
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
    road_name: str = ""


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

## 1.9 main.py (Stage 1 stub)

File: `src/guardianmapstudio/main.py`

```python
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from loguru import logger

from guardianmapstudio.config.settings import GuardianMapStudioSettings


def create_app(settings: GuardianMapStudioSettings | None = None) -> FastAPI:
    if settings is None:
        settings = GuardianMapStudioSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logger.info("GuardianMapStudio starting")
        yield
        logger.info("GuardianMapStudio shutdown")

    app = FastAPI(
        title="GuardianMapStudio",
        description="Map authoring tool for Guardian autonomous vehicle platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "database": "ok", "version": "0.1.0"}

    return app


def main() -> None:
    import uvicorn
    settings = GuardianMapStudioSettings()
    _configure_logging(settings)
    logger.info("GuardianMapStudio starting on {}:{}", settings.host, settings.port)
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port)


def _configure_logging(settings: GuardianMapStudioSettings) -> None:
    logger.remove()
    logger.add(
        sink=sys.stderr,
        level=settings.log_level,
        format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )
    logger.add(
        sink=settings.log_file,
        level="DEBUG",
        rotation=f"{settings.log_rotation_mb} MB",
        retention=f"{settings.log_retention_days} days",
        compression="zip",
        enqueue=True,
    )


if __name__ == "__main__":
    main()
```

---

## 1.10 conftest.py (Stage 1 version)

File: `tests/conftest.py`

```python
from __future__ import annotations

import pytest

from guardianmapstudio.config.settings import GuardianMapStudioSettings


@pytest.fixture
def settings() -> GuardianMapStudioSettings:
    return GuardianMapStudioSettings(
        database_url="sqlite:///:memory:",
        snap_tolerance_m=0.5,
        coordinate_precision=7,
        export_dir="/tmp/gms_test_exports",
    )


# ---------------------------------------------------------------------------
# STAGE 2: Uncomment this block after creating database/models.py
# ---------------------------------------------------------------------------
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
#
# @pytest.fixture
# def db_engine(settings: GuardianMapStudioSettings):
#     from guardianmapstudio.database.models import Base
#     engine = create_engine(settings.database_url)
#     Base.metadata.create_all(engine)
#     yield engine
#     engine.dispose()
#
# @pytest.fixture
# def db_session(db_engine):
#     factory = sessionmaker(bind=db_engine, expire_on_commit=False)
#     with factory() as session:
#         yield session


# ---------------------------------------------------------------------------
# STAGE 4: Uncomment this block after creating api/deps.py
# ---------------------------------------------------------------------------
# from fastapi.testclient import TestClient
#
# @pytest.fixture
# def client(settings: GuardianMapStudioSettings, db_engine):
#     from guardianmapstudio.main import create_app
#     from guardianmapstudio.api.deps import get_db
#     app = create_app(settings)
#     factory = sessionmaker(bind=db_engine, expire_on_commit=False)
#     with TestClient(app) as c:
#         def override_get_db():
#             with factory() as session:
#                 yield session
#         app.dependency_overrides[get_db] = override_get_db
#         yield c
#     app.dependency_overrides.clear()
```

---

## 1.11 Stage 1 Tests

**tests/unit/test_contracts.py**
```
test_geopoint_valid_bounds             → GeoPoint(-20.81, -49.37) creates without error
test_geopoint_invalid_latitude         → GeoPoint(91.0, 0.0) raises ValueError
test_geopoint_invalid_longitude        → GeoPoint(0.0, -181.0) raises ValueError
test_geopoint_to_export                → returns {"lat": -20.81, "lng": -49.37}
test_validation_result_is_blocking     → ERROR severity → is_blocking == True
test_validation_result_warning         → WARNING severity → is_blocking == False
test_workspace_state_values            → WorkspaceState.DRAFT.value == "draft"
test_waypoint_type_matches_guardian    → WaypointType.STOP_SIGN.value == "stop_sign"
test_gate_type_matches_guardian        → GateType.ENTRY_EXIT.value == "entry_exit"
test_restriction_type_matches_guardian → RestrictionType.SPEED_LIMIT.value == "speed_limit"
test_road_direction_matches_guardian   → RoadDirection.TWO_WAY.value == "two_way"
test_all_enums_are_strings             → all enum values are str instances
test_frozen_dataclass_immutable        → assigning to GeoPoint.latitude raises FrozenInstanceError
```

---

## 1.12 Stage 1 Quality Gate

```bash
uv sync
uv sync --extra dev
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/unit/test_contracts.py -v
python3 -c "from guardianmapstudio.main import create_app; app = create_app(); print('App created OK')"
```



---
---

# STAGE 2 — Database

## Objective

Implement the database layer: 11 tables, SQLAlchemy models, repositories,
and connection management. After this stage, `create_tables()` creates all
11 tables and all repositories are tested with in-memory SQLite.

## Files to create in Stage 2

- `src/guardianmapstudio/database/__init__.py`
- `src/guardianmapstudio/database/models.py`
- `src/guardianmapstudio/database/connection.py`
- `src/guardianmapstudio/database/repository.py`
- `tests/unit/test_repository.py`
- `tests/integration/test_database.py`

**First action**: Open `tests/conftest.py` and uncomment the block marked
`STAGE 2`. This adds `db_engine` and `db_session` fixtures.
Do NOT uncomment the `STAGE 4` block yet.

---

## 2.1 Connection

File: `src/guardianmapstudio/database/connection.py`

```python
from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from guardianmapstudio.config.settings import GuardianMapStudioSettings
from guardianmapstudio.database.models import Base


def get_engine(settings: GuardianMapStudioSettings) -> Engine:
    """Create the SQLAlchemy engine. Call once at startup."""
    connect_args: dict[str, bool] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, connect_args=connect_args)


def create_tables(engine: Engine) -> None:
    """Create all 11 tables. Idempotent."""
    Base.metadata.create_all(engine)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a session factory. Stored in app.state by lifespan."""
    return sessionmaker(bind=engine, expire_on_commit=False)
```

---

## 2.2 Models (COMPLETE CODE)

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

    project:         Mapped[ProjectModel]              = relationship(back_populates="versions")
    road_versions:   Mapped[list[RoadVersionModel]]    = relationship(back_populates="version")
    entity_versions: Mapped[list[EntityVersionModel]]  = relationship(back_populates="version")


class WorkspaceModel(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("state IN ('draft', 'published')", name="ck_workspaces_state"),
        Index("ix_workspaces_project_id", "project_id"),
        Index("ix_workspaces_state", "state"),
    )

    id:                    Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id:            Mapped[int]            = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    state:                 Mapped[str]            = mapped_column(String(20), default="draft", nullable=False)
    base_version_id:       Mapped[int | None]     = mapped_column(Integer, ForeignKey("versions.id"), nullable=True)
    created_at:            Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False,
                                                       default=lambda: datetime.now(timezone.utc))
    updated_at:            Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False,
                                                       default=lambda: datetime.now(timezone.utc),
                                                       onupdate=lambda: datetime.now(timezone.utc))
    last_validated_at:     Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    has_validation_errors: Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)

    project:            Mapped[ProjectModel]                = relationship(back_populates="workspaces")
    roads:              Mapped[list[RoadModel]]             = relationship(back_populates="workspace", cascade="all, delete-orphan")
    waypoints:          Mapped[list[WaypointModel]]         = relationship(back_populates="workspace", cascade="all, delete-orphan")
    crossroads:         Mapped[list[CrossroadModel]]        = relationship(back_populates="workspace", cascade="all, delete-orphan")
    areas:              Mapped[list[RestrictedAreaModel]]    = relationship(back_populates="workspace", cascade="all, delete-orphan")
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
        Index("ix_validation_results_severity", "workspace_id", "severity"),
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
        CheckConstraint("speed_limit_kmh > 0", name="ck_roads_speed_limit"),
        CheckConstraint("width_meters > 0", name="ck_roads_width"),
        UniqueConstraint("workspace_id", "name", name="uq_roads_workspace_name"),
        Index("ix_roads_workspace_id", "workspace_id"),
    )

    id:              Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id:    Mapped[int]      = mapped_column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name:            Mapped[str]      = mapped_column(String(200), nullable=False)
    coordinates:     Mapped[str]      = mapped_column(Text, nullable=False)
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
        Index("ix_waypoints_workspace_id", "workspace_id"),
        Index("ix_waypoints_workspace_type_active", "workspace_id", "waypoint_type", "active"),
    )

    id:              Mapped[int]          = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id:    Mapped[int]          = mapped_column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name:            Mapped[str]          = mapped_column(String(200), nullable=False)
    waypoint_type:   Mapped[str]          = mapped_column(String(30), nullable=False)
    latitude:        Mapped[float]        = mapped_column(Double, nullable=False)
    longitude:       Mapped[float]        = mapped_column(Double, nullable=False)
    road_name:       Mapped[str | None]   = mapped_column(String(200), nullable=True)
    heading_degrees: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra_data:      Mapped[str]          = mapped_column(Text, default="{}", nullable=False)
    active:          Mapped[bool]         = mapped_column(Boolean, default=True, nullable=False)
    created_at:      Mapped[datetime]     = mapped_column(DateTime(timezone=True), nullable=False,
                                               default=lambda: datetime.now(timezone.utc))
    updated_at:      Mapped[datetime]     = mapped_column(DateTime(timezone=True), nullable=False,
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

    id:               Mapped[int]         = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id:     Mapped[int]         = mapped_column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name:             Mapped[str]         = mapped_column(String(200), nullable=False)
    polygon:          Mapped[str]         = mapped_column(Text, nullable=False)
    restriction_type: Mapped[str]         = mapped_column(String(30), nullable=False)
    speed_limit_kmh:  Mapped[int | None]  = mapped_column(Integer, nullable=True)
    active:           Mapped[bool]        = mapped_column(Boolean, default=True, nullable=False)
    created_at:       Mapped[datetime]    = mapped_column(DateTime(timezone=True), nullable=False,
                                               default=lambda: datetime.now(timezone.utc))
    updated_at:       Mapped[datetime]    = mapped_column(DateTime(timezone=True), nullable=False,
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
        Index("ix_entity_versions_version_id", "version_id"),
        Index("ix_entity_versions_version_type", "version_id", "entity_type"),
    )

    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id:  Mapped[int] = mapped_column(Integer, ForeignKey("versions.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name:        Mapped[str] = mapped_column(String(200), nullable=False)
    payload:     Mapped[str] = mapped_column(Text, nullable=False)

    version: Mapped[VersionModel] = relationship(back_populates="entity_versions")
```

---

## 2.3 Repository (IMPLEMENTATION GUIDE)

File: `src/guardianmapstudio/database/repository.py`

Implement 6 repositories with 36 total methods. Each repository receives
a `Session` in `__init__`. All methods return domain contracts, never ORM models.

**Critical conversion rules:**
- `slots=True` removes `__dict__` — never use `model.__dict__`
- JSON fields (`coordinates`, `polygon`, `extra_data`) must be deserialized with `json.loads()`
- Coordinates JSON uses `{lat, lng}` keys → convert to `GeoPoint(latitude=p["lat"], longitude=p["lng"])`
- Waypoint `position` must be constructed: `GeoPoint(latitude=model.latitude, longitude=model.longitude)`
- Enum fields stored as strings → convert: `RoadDirection(model.direction)`

**Repository method signatures** (implement all):

```python
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from guardianmapstudio.domain.contracts import (
    Project, Version, Workspace, Road, Waypoint, Crossroad,
    RestrictedArea, ExportRecord, ValidationResult,
    GeoPoint, RoadDirection, WaypointType, RestrictionType,
    WorkspaceState, ValidationSeverity,
)
from guardianmapstudio.database.models import (
    ProjectModel, VersionModel, WorkspaceModel, RoadModel,
    WaypointModel, CrossroadModel, RestrictedAreaModel,
    ExportHistoryModel, ValidationResultModel,
    RoadVersionModel, EntityVersionModel,
)


class ProjectRepository:
    def __init__(self, db: Session) -> None: ...
    def create(self, name: str, description: str = "") -> Project: ...
    def get_by_id(self, project_id: int) -> Project | None: ...
    def get_all(self) -> list[Project]: ...
    def update(self, project_id: int, name: str, description: str) -> Project | None: ...
    def delete(self, project_id: int) -> bool: ...


class VersionRepository:
    def __init__(self, db: Session) -> None: ...
    def create(self, project_id: int, name: str, road_count: int,
               waypoint_count: int, crossroad_count: int,
               restricted_area_count: int) -> Version: ...
    def get_by_id(self, version_id: int) -> Version | None: ...
    def get_all_for_project(self, project_id: int) -> list[Version]: ...
    def get_latest_for_project(self, project_id: int) -> Version | None: ...
    def next_version_number(self, project_id: int) -> int: ...


class WorkspaceRepository:
    def __init__(self, db: Session) -> None: ...
    def create(self, project_id: int, base_version_id: int | None = None) -> Workspace: ...
    def get_by_id(self, workspace_id: int) -> Workspace | None: ...
    def get_active_draft(self, project_id: int) -> Workspace | None: ...
    def set_published(self, workspace_id: int) -> Workspace | None: ...
    def update_validation_state(self, workspace_id: int,
                                has_errors: bool, validated_at: datetime) -> None: ...


class MapRepository:
    """19 methods: roads(5) + waypoints(5) + crossroads(4) + areas(5)"""
    def __init__(self, db: Session) -> None: ...

    # Roads
    def create_road(self, workspace_id: int, name: str, coordinates_json: str,
                    speed_limit_kmh: int, direction: str, width_meters: float) -> Road: ...
    def get_road(self, road_id: int) -> Road | None: ...
    def get_roads(self, workspace_id: int) -> list[Road]: ...
    def update_road(self, road_id: int, **kwargs: object) -> Road | None: ...
    def delete_road(self, road_id: int) -> bool: ...

    # Waypoints
    def create_waypoint(self, workspace_id: int, name: str, waypoint_type: str,
                        latitude: float, longitude: float, road_name: str | None,
                        heading_degrees: float | None, extra_data_json: str) -> Waypoint: ...
    def get_waypoint(self, waypoint_id: int) -> Waypoint | None: ...
    def get_waypoints(self, workspace_id: int) -> list[Waypoint]: ...
    def update_waypoint(self, waypoint_id: int, **kwargs: object) -> Waypoint | None: ...
    def delete_waypoint(self, waypoint_id: int) -> bool: ...

    # Crossroads
    def create_crossroad(self, workspace_id: int, road_a_name: str,
                         road_b_name: str, latitude: float, longitude: float) -> Crossroad: ...
    def get_crossroad(self, crossroad_id: int) -> Crossroad | None: ...
    def get_crossroads(self, workspace_id: int) -> list[Crossroad]: ...
    def delete_crossroad(self, crossroad_id: int) -> bool: ...

    # Restricted Areas
    def create_area(self, workspace_id: int, name: str, polygon_json: str,
                    restriction_type: str, speed_limit_kmh: int | None) -> RestrictedArea: ...
    def get_area(self, area_id: int) -> RestrictedArea | None: ...
    def get_areas(self, workspace_id: int) -> list[RestrictedArea]: ...
    def update_area(self, area_id: int, **kwargs: object) -> RestrictedArea | None: ...
    def delete_area(self, area_id: int) -> bool: ...

    # Conversion helpers (private)
    def _road_to_domain(self, model: RoadModel) -> Road: ...
    def _waypoint_to_domain(self, model: WaypointModel) -> Waypoint: ...
    def _crossroad_to_domain(self, model: CrossroadModel) -> Crossroad: ...
    def _area_to_domain(self, model: RestrictedAreaModel) -> RestrictedArea: ...


class ValidationRepository:
    def __init__(self, db: Session) -> None: ...
    def replace_results(self, workspace_id: int, results: list[ValidationResult]) -> None: ...
    def get_results(self, workspace_id: int) -> list[ValidationResult]: ...
    def count_errors(self, workspace_id: int) -> int: ...


class ExportRepository:
    def __init__(self, db: Session) -> None: ...
    def create_record(self, version_id: int, project_id: int,
                      file_path: str, file_size_bytes: int) -> ExportRecord: ...
    def get_history(self, project_id: int) -> list[ExportRecord]: ...
```

**Example `_road_to_domain` implementation** (pattern for all conversions):

```python
def _road_to_domain(self, model: RoadModel) -> Road:
    raw_coords = json.loads(model.coordinates)
    return Road(
        id=model.id,
        workspace_id=model.workspace_id,
        name=model.name,
        coordinates=[GeoPoint(latitude=p["lat"], longitude=p["lng"])
                     for p in raw_coords],
        speed_limit_kmh=model.speed_limit_kmh,
        direction=RoadDirection(model.direction),
        width_meters=model.width_meters,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
```

**JSON serialization rule** — when writing to TEXT columns (`coordinates`,
`polygon`, `extra_data`), always use `ensure_ascii=False`:

```python
import json

# CORRECT — accented names preserved as UTF-8
model.coordinates = json.dumps(coords, ensure_ascii=False)

# WRONG — "Rua São José" becomes "Rua S\u00e3o Jos\u00e9"
model.coordinates = json.dumps(coords)
```

---

## 2.4 Stage 2 Tests

**tests/integration/test_database.py**
```
test_create_tables_all_11              → all 11 table names present
test_road_name_unique_constraint       → duplicate name → IntegrityError
test_waypoint_type_check_constraint    → invalid type → IntegrityError
test_workspace_state_check_constraint  → invalid state → IntegrityError
test_double_precision_preserved        → lat/lng 7dp without loss
test_updated_at_changes_on_update      → updated_at changes after update
test_cascade_delete_workspace          → delete workspace removes all children
```

**tests/unit/test_repository.py**
```
test_create_project                    → project created with correct fields
test_get_project_returns_domain        → returns Project, not ORM model
test_create_workspace_from_project     → workspace created with DRAFT state
test_get_active_draft                  → returns DRAFT workspace for project
test_create_road_returns_domain        → Road with list[GeoPoint] coordinates
test_road_coordinates_are_geopoints    → each coordinate is GeoPoint instance
test_waypoint_position_is_geopoint     → position field is GeoPoint instance
test_waypoint_extra_data_is_dict       → extra_data is dict, not str
test_version_number_increments         → next_version_number returns 1, 2, 3
test_validation_replace_results        → replaces old results entirely
test_export_record_created             → ExportRecord stored and retrievable
```

---

## 2.5 Stage 2 Quality Gate

```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/unit/ tests/integration/test_database.py -v

python3 -c "
from sqlalchemy import create_engine, inspect
from guardianmapstudio.database.connection import create_tables
engine = create_engine('sqlite:///:memory:')
create_tables(engine)
tables = sorted(inspect(engine).get_table_names())
assert len(tables) == 11, f'Expected 11, got {len(tables)}: {tables}'
print('✅ 11 tables:', tables)
"
```



---
---

# STAGE 3 — Geometry Engines + Exporter

## Objective

Implement all four geometry engines and the Guardian exporter.
After this stage, the full validation pipeline and export work end-to-end
with unit tests. No API or frontend yet.

## Files to create in Stage 3

- `src/guardianmapstudio/geometry/__init__.py`
- `src/guardianmapstudio/geometry/engine.py`
- `src/guardianmapstudio/geometry/snap.py`
- `src/guardianmapstudio/geometry/crossroad.py`
- `src/guardianmapstudio/geometry/validation.py`
- `src/guardianmapstudio/export/__init__.py`
- `src/guardianmapstudio/export/guardian_exporter.py`
- `tests/unit/test_geometry_engine.py`
- `tests/unit/test_snap_engine.py`
- `tests/unit/test_crossroad_engine.py`
- `tests/unit/test_validation_engine.py`
- `tests/unit/test_guardian_exporter.py`

---

## 3.1 GeometryEngine (COMPLETE CODE)

File: `src/guardianmapstudio/geometry/engine.py`

**Critical rules:**
- `EARTH_RADIUS_M = 6_371_000` — must match Guardian exactly
- `haversine_distance()` uses `math.asin(math.sqrt(h))` — not `math.atan2`
- `_to_local()` identical to Guardian's `geo_utils._to_local()`
- `from_centroid()` handles both hemispheres

```python
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pyproj
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

from guardianmapstudio.domain.contracts import GeoPoint, Road, Waypoint, Crossroad, RestrictedArea

EARTH_RADIUS_M = 6_371_000   # must match Guardian's geo_utils.EARTH_RADIUS_M exactly


class GeometryEngine:
    """Spatial computation engine.

    Holds the projected CRS transformer and STRtree indices for a workspace.
    STRtrees are built lazily and invalidated on every edit operation.

    Usage:
        engine = GeometryEngine.from_centroid(lat=-20.81, lng=-49.38)
        dist = engine.haversine_distance(a, b)
        snapped = engine.snap_point(new_point, candidates)
    """

    def __init__(self, epsg_projected: int) -> None:
        self._transformer = Transformer.from_crs(
            "EPSG:4326",
            f"EPSG:{epsg_projected}",
            always_xy=True,   # input: (longitude, latitude)
        )
        self._epsg = epsg_projected
        # STRtree caches — rebuilt lazily after invalidation
        self._waypoint_tree: STRtree | None = None
        self._road_tree: STRtree | None = None
        self._area_tree: STRtree | None = None
        self._waypoint_index: list[Waypoint] = []
        self._road_index: list[Road] = []
        self._area_index: list[RestrictedArea] = []

    @classmethod
    def from_centroid(cls, lat: float, lng: float) -> "GeometryEngine":
        """Create engine with UTM projection appropriate for the given location.

        Current implementation: SIRGAS 2000 / UTM Southern Hemisphere only.
        This covers 100% of Brazilian territory (the target deployment environment).

        For global support (future): replace with pyproj.database.query_utm_crs_info()
        which auto-detects the correct UTM zone and hemisphere for any coordinate.
        """
        zone = int((lng + 180) / 6) + 1
        if lat >= 0:
            # Northern hemisphere — WGS 84 / UTM Zone Nk (EPSG: 32600 + zone)
            # Untested: no Brazilian condominium is in the Northern hemisphere.
            epsg = 32600 + zone
        else:
            # Southern hemisphere — SIRGAS 2000 / UTM Zone Sk (EPSG: 31960 + zone)
            epsg = 31960 + zone
        return cls(epsg)

    # ------------------------------------------------------------------
    # Projection
    # ------------------------------------------------------------------

    def project(self, point: GeoPoint) -> tuple[float, float]:
        """Project EPSG:4326 → UTM. Returns (x_meters, y_meters)."""
        x, y = self._transformer.transform(point.longitude, point.latitude)
        return x, y

    def project_all(self, points: list[GeoPoint]) -> list[tuple[float, float]]:
        """Project a list of GeoPoints to UTM."""
        return [self.project(p) for p in points]

    # ------------------------------------------------------------------
    # Distances
    # ------------------------------------------------------------------

    def haversine_distance(self, a: GeoPoint, b: GeoPoint) -> float:
        """Great-circle distance in meters. Same formula as Guardian geo_utils."""
        lat1 = math.radians(a.latitude)
        lat2 = math.radians(b.latitude)
        dlat = math.radians(b.latitude - a.latitude)
        dlng = math.radians(b.longitude - a.longitude)
        h = (math.sin(dlat / 2) ** 2
             + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2)
        return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))

    def projected_distance(self, a: GeoPoint, b: GeoPoint) -> float:
        """Euclidean distance in projected meters. More accurate than haversine
        for very short distances (< 100m) such as snap tolerance checks."""
        ax, ay = self.project(a)
        bx, by = self.project(b)
        return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)

    def point_to_segment_distance(
        self, point: GeoPoint, seg_start: GeoPoint, seg_end: GeoPoint
    ) -> float:
        """Minimum distance in meters from point to a line segment.
        Uses flat local projection (same as Guardian geo_utils._to_local)."""
        px, py = self._to_local(point, seg_start)
        ex, ey = self._to_local(seg_end, seg_start)
        seg_len_sq = ex * ex + ey * ey
        if seg_len_sq == 0:
            return math.sqrt(px * px + py * py)
        t = max(0.0, min(1.0, (px * ex + py * ey) / seg_len_sq))
        nx, ny = t * ex, t * ey
        return math.sqrt((px - nx) ** 2 + (py - ny) ** 2)

    def _to_local(self, point: GeoPoint, origin: GeoPoint) -> tuple[float, float]:
        """Local flat metric coordinates relative to origin (same as Guardian)."""
        dlat = math.radians(point.latitude - origin.latitude)
        dlng = math.radians(point.longitude - origin.longitude)
        avg_lat = math.radians((point.latitude + origin.latitude) / 2)
        x = dlng * math.cos(avg_lat) * EARTH_RADIUS_M
        y = dlat * EARTH_RADIUS_M
        return x, y

    # ------------------------------------------------------------------
    # Geometry checks
    # ------------------------------------------------------------------

    def roads_intersect(self, road_a: Road, road_b: Road) -> bool:
        """Check if two road polylines geometrically intersect."""
        coords_a = [(p.longitude, p.latitude) for p in road_a.coordinates]
        coords_b = [(p.longitude, p.latitude) for p in road_b.coordinates]
        if len(coords_a) < 2 or len(coords_b) < 2:
            return False
        return LineString(coords_a).intersects(LineString(coords_b))

    def point_inside_polygon(self, point: GeoPoint, area: RestrictedArea) -> bool:
        """Ray-casting containment test."""
        poly_coords = [(p.longitude, p.latitude) for p in area.polygon]
        return Polygon(poly_coords).contains(Point(point.longitude, point.latitude))

    # ------------------------------------------------------------------
    # STRtree management
    # ------------------------------------------------------------------

    def build_waypoint_tree(self, waypoints: list[Waypoint]) -> None:
        """Build (or rebuild) the waypoint spatial index."""
        self._waypoint_index = waypoints
        points = [Point(w.position.longitude, w.position.latitude) for w in waypoints]
        self._waypoint_tree = STRtree(points)

    def build_road_tree(self, roads: list[Road]) -> None:
        """Build (or rebuild) the road spatial index (uses bounding boxes)."""
        self._road_index = roads
        lines = [
            LineString([(p.longitude, p.latitude) for p in r.coordinates])
            for r in roads
        ]
        self._road_tree = STRtree(lines)

    def build_area_tree(self, areas: list[RestrictedArea]) -> None:
        """Build (or rebuild) the restricted area spatial index."""
        self._area_index = areas
        polys = [
            Polygon([(p.longitude, p.latitude) for p in a.polygon])
            for a in areas
        ]
        self._area_tree = STRtree(polys)

    def invalidate_all(self) -> None:
        """Invalidate all STRtree caches. Call after any workspace edit."""
        self._waypoint_tree = None
        self._road_tree = None
        self._area_tree = None
        self._waypoint_index = []
        self._road_index = []
        self._area_index = []

```

---

## 3.2 SnapEngine (COMPLETE CODE)

File: `src/guardianmapstudio/geometry/snap.py`

**Critical rules:**
- MVP01 snap candidates: road endpoints + waypoint positions only
- Road-to-segment snapping is MVP02
- Always returns SnapResult, even when snapped=False

```python
from __future__ import annotations

from shapely.geometry import Point

from guardianmapstudio.domain.contracts import GeoPoint, Road, Waypoint, SnapResult
from guardianmapstudio.geometry.engine import GeometryEngine


class SnapEngine:
    """Snaps new points to existing geometry within tolerance.

    Snap candidates (MVP01):
      - Road endpoints (first and last point of each road)
      - Existing waypoint positions

    Road midpoint vertices and road-to-segment snapping: MVP02.
    """

    def __init__(self, engine: GeometryEngine, tolerance_m: float = 0.5) -> None:
        self._engine = engine
        self._tolerance_m = tolerance_m

    def snap(
        self,
        new_point: GeoPoint,
        roads: list[Road],
        waypoints: list[Waypoint],
    ) -> SnapResult:
        """Find closest snap candidate within tolerance.

        Returns SnapResult with snapped=True if any candidate is within
        self._tolerance_m (projected meters).
        """
        candidates: list[GeoPoint] = []

        # Collect road endpoints
        for road in roads:
            if len(road.coordinates) >= 2:
                candidates.append(road.coordinates[0])
                candidates.append(road.coordinates[-1])

        # Collect waypoint positions
        for wp in waypoints:
            candidates.append(wp.position)

        if not candidates:
            return SnapResult(
                original=new_point,
                snapped_to=new_point,
                snapped=False,
                distance_meters=0.0,
            )

        # Find closest candidate in projected space
        best_candidate: GeoPoint | None = None
        best_dist = float("inf")

        for candidate in candidates:
            dist = self._engine.projected_distance(new_point, candidate)
            if dist < best_dist:
                best_dist = dist
                best_candidate = candidate

        if best_candidate is not None and best_dist <= self._tolerance_m:
            return SnapResult(
                original=new_point,
                snapped_to=best_candidate,
                snapped=True,
                distance_meters=best_dist,
            )

        return SnapResult(
            original=new_point,
            snapped_to=new_point,
            snapped=False,
            distance_meters=0.0,
        )

```

---

## 3.3 CrossroadEngine (COMPLETE CODE)

File: `src/guardianmapstudio/geometry/crossroad.py`

```python
from __future__ import annotations

from shapely.geometry import LineString

from guardianmapstudio.domain.contracts import GeoPoint, Road, Crossroad
from guardianmapstudio.geometry.engine import GeometryEngine


class CrossroadEngine:
    """Geometric crossroad analysis.

    MVP01: validates that manually placed crossroads are near actual intersections.
    MVP02: auto-detects intersections and suggests crossroad placement.
    """

    # Crossroad marker must be within this many meters of the actual
    # road intersection to pass the crossroad.roads_intersect WARNING check.
    INTERSECTION_PROXIMITY_M = 1.0

    def __init__(self, engine: GeometryEngine) -> None:
        self._engine = engine

    def roads_intersect(self, road_a: Road, road_b: Road) -> bool:
        """Return True if the two road polylines geometrically cross."""
        return self._engine.roads_intersect(road_a, road_b)

    def find_intersection_point(
        self, road_a: Road, road_b: Road
    ) -> GeoPoint | None:
        """Return the approximate intersection GeoPoint, or None if roads don't cross.

        Uses Shapely's intersection() which returns the exact crossing point
        in EPSG:4326. Only returns a point (not a line — parallel roads
        that overlap return None).
        """
        coords_a = [(p.longitude, p.latitude) for p in road_a.coordinates]
        coords_b = [(p.longitude, p.latitude) for p in road_b.coordinates]
        if len(coords_a) < 2 or len(coords_b) < 2:
            return None

        intersection = LineString(coords_a).intersection(LineString(coords_b))
        if intersection.is_empty or intersection.geom_type != "Point":
            return None

        return GeoPoint(latitude=intersection.y, longitude=intersection.x)

    def crossroad_is_near_intersection(
        self, crossroad: Crossroad, road_a: Road, road_b: Road
    ) -> bool:
        """Check if a crossroad marker is placed near the actual road intersection.

        Returns True (valid) if:
          - The two roads geometrically intersect, AND
          - The crossroad position is within INTERSECTION_PROXIMITY_M of
            the intersection point.

        Returns False (warning) if the roads don't intersect or the marker
        is placed too far from the actual crossing.
        """
        intersection_point = self.find_intersection_point(road_a, road_b)
        if intersection_point is None:
            return False

        dist = self._engine.projected_distance(crossroad.position, intersection_point)
        return dist <= self.INTERSECTION_PROXIMITY_M

```

---

## 3.4 ValidationEngine (COMPLETE CODE)

File: `src/guardianmapstudio/geometry/validation.py`

**All 19 rules must be present. Do not omit any.**

Roads (5): `road.min_points`, `road.name_unique`, `road.speed_limit_positive`,
`road.width_positive`, `road.no_waypoints`

Waypoints (6): `waypoint.name_not_empty`, `waypoint.road_exists`,
`waypoint.heading_range`, `waypoint.speed_bump_height`,
`waypoint.gate_type_valid`, `waypoint.duplicate_position`

Crossroads (4): `crossroad.road_a_exists`, `crossroad.road_b_exists`,
`crossroad.roads_distinct`, `crossroad.roads_intersect`

Restricted areas (4): `area.min_points`, `area.name_not_empty`,
`area.speed_limit_required`, `area.speed_limit_positive`

Workspace (1): `workspace.min_roads`

```python
from __future__ import annotations

from guardianmapstudio.domain.contracts import (
    ValidationResult, ValidationSeverity,
    Road, Waypoint, Crossroad, RestrictedArea,
    GateType, WaypointType,
)
from guardianmapstudio.geometry.engine import GeometryEngine
from guardianmapstudio.geometry.crossroad import CrossroadEngine


class ValidationEngine:
    """Applies all validation rules to a workspace.

    Usage:
        engine = ValidationEngine(geometry_engine)
        results = engine.validate(roads, waypoints, crossroads, areas)
        errors = [r for r in results if r.is_blocking]
    """

    DUPLICATE_POSITION_M = 0.5      # matches snap tolerance (doc 03)
    CROSSROAD_PROXIMITY_M = 1.0     # matches CrossroadEngine.INTERSECTION_PROXIMITY_M

    def __init__(self, geometry_engine: GeometryEngine) -> None:
        self._geo = geometry_engine
        self._crossroad_engine = CrossroadEngine(geometry_engine)

    def validate(
        self,
        roads: list[Road],
        waypoints: list[Waypoint],
        crossroads: list[Crossroad],
        areas: list[RestrictedArea],
    ) -> list[ValidationResult]:
        """Run all rules. Returns complete list of errors and warnings."""
        results: list[ValidationResult] = []

        results.extend(self._validate_workspace(roads))
        results.extend(self._validate_roads(roads))
        results.extend(self._validate_waypoints(waypoints, roads))
        results.extend(self._validate_crossroads(crossroads, roads))
        results.extend(self._validate_areas(areas))

        return results

    # ------------------------------------------------------------------
    # Workspace-level rules
    # ------------------------------------------------------------------

    def _validate_workspace(self, roads: list[Road]) -> list[ValidationResult]:
        results = []
        # workspace.min_roads: ERROR if no roads at all
        if len(roads) == 0:
            results.append(ValidationResult(
                severity=ValidationSeverity.ERROR,
                rule_id="workspace.min_roads",
                message="The workspace has no roads. Add at least one road before publishing.",
                affected_entity_type="workspace",
                affected_entity_id=0,
            ))
        return results

    # ------------------------------------------------------------------
    # Road rules
    # ------------------------------------------------------------------

    def _validate_roads(self, roads: list[Road]) -> list[ValidationResult]:
        results = []
        road_names: dict[str, int] = {}

        for road in roads:
            # road.min_points
            if len(road.coordinates) < 2:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="road.min_points",
                    message=f"Road '{road.name}' has only {len(road.coordinates)} point(s). Minimum is 2.",
                    affected_entity_type="road",
                    affected_entity_id=road.id,
                ))

            # road.name_unique
            if road.name in road_names:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="road.name_unique",
                    message=f"Road name '{road.name}' is already used by another road in this workspace.",
                    affected_entity_type="road",
                    affected_entity_id=road.id,
                ))
            else:
                road_names[road.name] = road.id

            # road.speed_limit_positive
            if road.speed_limit_kmh <= 0:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="road.speed_limit_positive",
                    message=f"Road '{road.name}' has invalid speed limit: {road.speed_limit_kmh} km/h. Must be > 0.",
                    affected_entity_type="road",
                    affected_entity_id=road.id,
                ))

            # road.width_positive
            if road.width_meters <= 0:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="road.width_positive",
                    message=f"Road '{road.name}' has invalid width: {road.width_meters} m. Must be > 0.",
                    affected_entity_type="road",
                    affected_entity_id=road.id,
                ))

        # road.no_waypoints is checked in _validate_waypoints() because it
        # needs both the roads list and the waypoints list simultaneously.
        # It is NOT checked here to avoid requiring waypoints as a parameter
        # of _validate_roads().

        return results

    def _validate_roads_waypoint_coverage(
        self, roads: list[Road], waypoints: list[Waypoint]
    ) -> list[ValidationResult]:
        """road.no_waypoints — separate method because it needs waypoints."""
        results = []
        roads_with_waypoints = {w.road_name for w in waypoints if w.road_name is not None}
        for road in roads:
            if road.name not in roads_with_waypoints:
                results.append(ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    rule_id="road.no_waypoints",
                    message=f"Road '{road.name}' has no waypoints. Consider adding stop signs, speed bumps, or other markers.",
                    affected_entity_type="road",
                    affected_entity_id=road.id,
                ))
        return results

    # ------------------------------------------------------------------
    # Waypoint rules
    # ------------------------------------------------------------------

    def _validate_waypoints(
        self, waypoints: list[Waypoint], roads: list[Road]
    ) -> list[ValidationResult]:
        results = []
        road_names = {r.name for r in roads}

        for wp in waypoints:
            # waypoint.name_not_empty
            if not wp.name or not wp.name.strip():
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="waypoint.name_not_empty",
                    message="A waypoint has an empty name. All waypoints must have a non-blank name.",
                    affected_entity_type="waypoint",
                    affected_entity_id=wp.id,
                ))

            # waypoint.road_exists
            if wp.road_name is not None and wp.road_name not in road_names:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="waypoint.road_exists",
                    message=f"Waypoint '{wp.name}' references road '{wp.road_name}' which does not exist in this workspace.",
                    affected_entity_type="waypoint",
                    affected_entity_id=wp.id,
                ))

            # waypoint.heading_range
            if wp.heading_degrees is not None:
                if not (0.0 <= wp.heading_degrees <= 360.0):
                    results.append(ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="waypoint.heading_range",
                        message=f"Waypoint '{wp.name}' heading {wp.heading_degrees}° is outside valid range 0–360.",
                        affected_entity_type="waypoint",
                        affected_entity_id=wp.id,
                    ))

            # waypoint.speed_bump_height
            if wp.waypoint_type == WaypointType.SPEED_BUMP:
                height = wp.extra_data.get("height_cm")
                if height is None or not isinstance(height, (int, float)) or height <= 0:
                    results.append(ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="waypoint.speed_bump_height",
                        message=f"Speed bump '{wp.name}' must have extra_data.height_cm > 0.",
                        affected_entity_type="waypoint",
                        affected_entity_id=wp.id,
                    ))

            # waypoint.gate_type_valid
            if wp.waypoint_type == WaypointType.GATE:
                gate_type = wp.extra_data.get("gate_type")
                valid_gate_types = {gt.value for gt in GateType}
                if gate_type not in valid_gate_types:
                    results.append(ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="waypoint.gate_type_valid",
                        message=f"Gate '{wp.name}' must have extra_data.gate_type set to one of: {sorted(valid_gate_types)}.",
                        affected_entity_type="waypoint",
                        affected_entity_id=wp.id,
                    ))

        # waypoint.duplicate_position: WARNING for pairs within 0.5m
        # Complexity: O(n²) where n = number of waypoints.
        # Acceptable for MVP01 (max ~80 waypoints per condominium map).
        # For n=80: 3,160 comparisons per validation run — negligible.
        # If maps grow beyond 500 waypoints, replace with STRtree nearest-neighbor.
        for i, wp_a in enumerate(waypoints):
            for wp_b in waypoints[i + 1:]:
                dist = self._geo.haversine_distance(wp_a.position, wp_b.position)
                if dist < self.DUPLICATE_POSITION_M:
                    results.append(ValidationResult(
                        severity=ValidationSeverity.WARNING,
                        rule_id="waypoint.duplicate_position",
                        message=(
                            f"Waypoints '{wp_a.name}' and '{wp_b.name}' are {dist:.2f}m apart "
                            f"(less than snap tolerance of {self.DUPLICATE_POSITION_M}m). "
                            "They may be duplicates."
                        ),
                        affected_entity_type="waypoint",
                        affected_entity_id=wp_a.id,
                    ))

        # road.no_waypoints: WARNING for each road with no associated waypoints
        # Placed here because it needs both roads and waypoints lists
        results.extend(self._validate_roads_waypoint_coverage(roads, waypoints))

        return results

    # ------------------------------------------------------------------
    # Crossroad rules
    # ------------------------------------------------------------------

    def _validate_crossroads(
        self, crossroads: list[Crossroad], roads: list[Road]
    ) -> list[ValidationResult]:
        results = []
        road_map: dict[str, Road] = {r.name: r for r in roads}

        for cr in crossroads:
            road_a = road_map.get(cr.road_a_name)
            road_b = road_map.get(cr.road_b_name)

            # crossroad.road_a_exists
            if road_a is None:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="crossroad.road_a_exists",
                    message=f"Crossroad references road '{cr.road_a_name}' which does not exist in this workspace.",
                    affected_entity_type="crossroad",
                    affected_entity_id=cr.id,
                ))

            # crossroad.road_b_exists
            if road_b is None:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="crossroad.road_b_exists",
                    message=f"Crossroad references road '{cr.road_b_name}' which does not exist in this workspace.",
                    affected_entity_type="crossroad",
                    affected_entity_id=cr.id,
                ))

            # crossroad.roads_distinct
            if cr.road_a_name == cr.road_b_name:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="crossroad.roads_distinct",
                    message=f"Crossroad has road_a and road_b both set to '{cr.road_a_name}'. They must be different roads.",
                    affected_entity_type="crossroad",
                    affected_entity_id=cr.id,
                ))

            # crossroad.roads_intersect (WARNING — only if both roads exist)
            if road_a is not None and road_b is not None:
                near = self._crossroad_engine.crossroad_is_near_intersection(cr, road_a, road_b)
                if not near:
                    results.append(ValidationResult(
                        severity=ValidationSeverity.WARNING,
                        rule_id="crossroad.roads_intersect",
                        message=(
                            f"Crossroad between '{cr.road_a_name}' and '{cr.road_b_name}' is not "
                            f"near a geometric intersection of those roads "
                            f"(within {self.CROSSROAD_PROXIMITY_M}m). "
                            "Check that the roads actually cross at this point."
                        ),
                        affected_entity_type="crossroad",
                        affected_entity_id=cr.id,
                    ))

        return results

    # ------------------------------------------------------------------
    # Restricted area rules
    # ------------------------------------------------------------------

    def _validate_areas(self, areas: list[RestrictedArea]) -> list[ValidationResult]:
        results = []

        for area in areas:
            # area.min_points
            if len(area.polygon) < 3:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="area.min_points",
                    message=f"Restricted area '{area.name}' has only {len(area.polygon)} point(s). Polygon requires at least 3.",
                    affected_entity_type="restricted_area",
                    affected_entity_id=area.id,
                ))

            # area.name_not_empty
            if not area.name or not area.name.strip():
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="area.name_not_empty",
                    message="A restricted area has an empty name. All areas must have a non-blank name.",
                    affected_entity_type="restricted_area",
                    affected_entity_id=area.id,
                ))

            # area.speed_limit_required
            if area.restriction_type.value == "speed_limit" and area.speed_limit_kmh is None:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="area.speed_limit_required",
                    message=f"Restricted area '{area.name}' has restriction type 'speed_limit' but no speed_limit_kmh set.",
                    affected_entity_type="restricted_area",
                    affected_entity_id=area.id,
                ))

            # area.speed_limit_positive
            if area.speed_limit_kmh is not None and area.speed_limit_kmh <= 0:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="area.speed_limit_positive",
                    message=f"Restricted area '{area.name}' has speed_limit_kmh={area.speed_limit_kmh}. Must be > 0.",
                    affected_entity_type="restricted_area",
                    affected_entity_id=area.id,
                ))

        return results

```

---

## 3.5 GuardianExporter (COMPLETE CODE)

File: `src/guardianmapstudio/export/guardian_exporter.py`

**Critical rules:**
- Waypoint key is `"type"` — NOT `"waypoint_type"` (Guardian expects `"type"`)
- `"road"` key always present in waypoint export, even when null
- `"extra_data"` always present, even when `{}`
- `"heading_degrees"` only included when not None (key omitted entirely)
- `active=False` waypoints excluded from export
- `meta` block always present with `schema_version: "1.0"`
- `json.dumps(..., indent=2, ensure_ascii=False)` — UTF-8, human-readable

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from guardianmapstudio.domain.contracts import (
    Road, Waypoint, Crossroad, RestrictedArea,
    ExportMeta, ExportRecord, Version,
)


class GuardianExporter:
    """Produces the canonical Guardian JSON export file.

    The output must pass Guardian's seed_from_json() without error.
    Field names and structure match exactly what Guardian expects.
    """

    SCHEMA_VERSION = "1.0"

    def export(
        self,
        version: Version,
        project_name: str,
        roads: list[Road],
        waypoints: list[Waypoint],
        crossroads: list[Crossroad],
        areas: list[RestrictedArea],
        output_path: Path,
        coordinate_precision: int = 7,
    ) -> int:
        """Write the export JSON file. Returns file size in bytes."""
        meta = {
            "exported_by": "GuardianMapStudio",
            "version_id": version.id,
            "version_name": version.name,
            "project_name": project_name,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": self.SCHEMA_VERSION,
        }

        p = coordinate_precision

        data = {
            "meta": meta,
            "roads": [
                {
                    "name": r.name,
                    "coordinates": [
                        {"lat": round(pt.latitude, p), "lng": round(pt.longitude, p)}
                        for pt in r.coordinates
                    ],
                    "speed_limit_kmh": r.speed_limit_kmh,
                    "direction": r.direction.value,
                    "width_meters": r.width_meters,
                }
                for r in roads
            ],
            "waypoints": [
                self._serialize_waypoint(w, p)
                for w in waypoints
                if w.active
            ],
            "crossroads": [
                {
                    "road_a": cr.road_a_name,
                    "road_b": cr.road_b_name,
                    "lat": round(cr.position.latitude, p),
                    "lng": round(cr.position.longitude, p),
                }
                for cr in crossroads
            ],
            "restricted_areas": [
                {
                    "name": a.name,
                    "polygon": [
                        {"lat": round(pt.latitude, p), "lng": round(pt.longitude, p)}
                        for pt in a.polygon
                    ],
                    "restriction_type": a.restriction_type.value,
                    "speed_limit_kmh": a.speed_limit_kmh,
                    "active": a.active,
                }
                for a in areas
            ],
        }

        content = json.dumps(data, indent=2, ensure_ascii=False)
        output_path.write_text(content, encoding="utf-8")
        return len(content.encode("utf-8"))

    def _serialize_waypoint(self, w: Waypoint, precision: int) -> dict:
        """Serialize one Waypoint to Guardian export format.

        Key name is 'type' (NOT 'waypoint_type') — Guardian's seed_from_json()
        expects exactly this key name.
        """
        entry: dict = {
            "name": w.name,
            "type": w.waypoint_type.value,   # Guardian expects "type", not "waypoint_type"
            "lat": round(w.position.latitude, precision),
            "lng": round(w.position.longitude, precision),
            "road": w.road_name,             # string or null — never omit
            "extra_data": w.extra_data,      # always included, even when {}
        }
        # heading_degrees: only include key when not None
        if w.heading_degrees is not None:
            entry["heading_degrees"] = round(w.heading_degrees, 1)
        return entry

```

---

## 3.6 Stage 3 Tests

**tests/unit/test_geometry_engine.py**
```
test_haversine_known_distance          → two points 100m apart return ~100m
test_haversine_matches_guardian        → same result as Guardian's formula
test_projected_distance_snap_scale     → 0.5m in projection matches tolerance
test_roads_intersect_crossing          → perpendicular roads return True
test_roads_intersect_parallel          → parallel roads return False
test_point_inside_polygon              → known interior point returns True
test_point_outside_polygon             → known exterior point returns False
```

**tests/unit/test_snap_engine.py**
```
test_snap_within_tolerance             → point 0.3m from endpoint → snapped=True
test_snap_outside_tolerance            → point 0.6m from endpoint → snapped=False
test_snap_exact_coincident             → point at 0.0m → snapped=True, dist=0.0
test_snap_no_candidates                → empty workspace → snapped=False
test_snap_returns_closest              → two candidates, returns nearest
test_snap_respects_custom_tolerance    → tolerance=1.0m snaps at 0.8m
```

**tests/unit/test_crossroad_engine.py**
```
test_roads_intersect_crossing          → perpendicular roads return True
test_roads_intersect_parallel          → parallel non-crossing return False
test_find_intersection_point           → returns GeoPoint near actual crossing
test_find_intersection_no_cross        → parallel roads return None
test_crossroad_near_intersection       → marker within 1m → True
test_crossroad_far_from_intersection   → marker 2m away → False
test_single_point_road_no_intersection → road with <2 points returns False
```

**tests/unit/test_validation_engine.py**
```
test_road_min_points_error             → road with 1 point → ERROR
test_road_name_unique_error            → two roads same name → ERROR
test_road_speed_limit_error            → speed_limit=0 → ERROR
test_road_no_waypoints_warning         → road with no waypoints → WARNING
test_waypoint_name_empty_error         → blank name → ERROR
test_waypoint_road_exists_error        → road_name missing → ERROR
test_waypoint_speed_bump_no_height     → speed_bump without height_cm → ERROR
test_waypoint_gate_invalid_type        → gate with bad gate_type → ERROR
test_waypoint_heading_out_of_range     → heading=400 → ERROR
test_waypoint_duplicate_position       → two waypoints 0.3m apart → WARNING
test_crossroad_road_a_missing          → road_a not in workspace → ERROR
test_crossroad_roads_identical         → road_a == road_b → ERROR
test_crossroad_not_near_intersection   → marker far from crossing → WARNING
test_area_min_points_error             → polygon 2 points → ERROR
test_area_speed_limit_required         → speed_limit type, no value → ERROR
test_workspace_no_roads_error          → empty workspace → ERROR
test_valid_workspace_no_results        → correct map → empty results
test_can_publish_with_warnings         → warnings only → error_count=0
```

**tests/unit/test_guardian_exporter.py**
```
test_export_produces_valid_json        → output is parseable JSON
test_export_meta_fields_present        → meta block has all required keys
test_export_schema_version_1_0         → meta.schema_version == "1.0"
test_waypoint_type_key_is_type         → key is "type" not "waypoint_type"
test_waypoint_road_key_present         → "road" key always present (even null)
test_heading_omitted_when_null         → no heading_degrees key when null
test_extra_data_always_present         → extra_data: {} for no extras
test_inactive_waypoints_excluded       → active=False not in export
test_coordinate_precision_7dp          → lat/lng rounded to 7 decimal places
test_export_utf8_accented_names        → road names with accents preserved
```

---

## 3.7 Stage 3 Quality Gate

```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/unit/ -v --cov=guardianmapstudio.geometry \
  --cov=guardianmapstudio.export --cov-report=term-missing
```

Geometry engine coverage target: ≥ 90%
Guardian exporter coverage target: 100%


---
---

# STAGE 4 — REST API (Backend)

## Objective

Implement the complete FastAPI REST API (33 endpoints).
After this stage, all endpoints work with real SQLite database.
Frontend is not yet built.

## Files to create in Stage 4

- `src/guardianmapstudio/api/__init__.py`
- `src/guardianmapstudio/api/deps.py`
- `src/guardianmapstudio/api/schemas.py`
- `src/guardianmapstudio/api/errors.py`
- `src/guardianmapstudio/api/routers/__init__.py`
- `src/guardianmapstudio/api/routers/projects.py`
- `src/guardianmapstudio/api/routers/workspaces.py`
- `src/guardianmapstudio/api/routers/roads.py`
- `src/guardianmapstudio/api/routers/waypoints.py`
- `src/guardianmapstudio/api/routers/crossroads.py`
- `src/guardianmapstudio/api/routers/restricted_areas.py`
- `src/guardianmapstudio/api/routers/validation.py`
- `src/guardianmapstudio/api/routers/export.py`
- `tests/integration/test_api_projects.py`
- `tests/integration/test_api_workspaces.py`
- `tests/integration/test_api_roads.py`
- `tests/integration/test_api_waypoints.py`
- `tests/integration/test_api_export.py`

**First action**: Open `tests/conftest.py` and uncomment the block marked
`STAGE 4`. This adds the `client` fixture for integration API tests.

**Also**: Replace `src/guardianmapstudio/main.py` with the Stage 4 version below.

---

## 4.1 ErrorCode enum (COMPLETE CODE)

File: `src/guardianmapstudio/api/errors.py`

```python
from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
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

---

## 4.2 Pydantic Schemas (COMPLETE CODE)

File: `src/guardianmapstudio/api/schemas.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class GeoPointDTO(BaseModel):
    lat: float
    lng: float


# --- Project ---

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


# --- Version ---

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


# --- Workspace ---

class WorkspaceResponse(BaseModel):
    id: int
    project_id: int
    state: Literal["draft", "published"]
    base_version_id: int | None
    created_at: datetime
    updated_at: datetime
    last_validated_at: datetime | None
    has_validation_errors: bool
    model_config = ConfigDict(from_attributes=True)

class PublishRequest(BaseModel):
    version_name: str


# --- Road ---

class RoadCreate(BaseModel):
    name: str
    coordinates: list[GeoPointDTO]
    speed_limit_kmh: int = 20
    direction: str = "two_way"
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


# --- Waypoint ---

class WaypointCreate(BaseModel):
    name: str
    waypoint_type: str
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


# --- Crossroad ---

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


# --- Restricted Area ---

class RestrictedAreaCreate(BaseModel):
    name: str
    polygon: list[GeoPointDTO]
    restriction_type: str
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


# --- Validation ---

class ValidationResultResponse(BaseModel):
    id: int
    severity: str
    rule_id: str
    message: str
    affected_entity_type: str
    affected_entity_id: int

class ValidationSummaryResponse(BaseModel):
    workspace_id: int
    error_count: int
    warning_count: int
    can_publish: bool
    results: list[ValidationResultResponse]
    validated_at: datetime


# --- Export ---

class ExportResponse(BaseModel):
    export_id: int
    version_id: int
    file_path: str
    file_size_bytes: int
    exported_at: datetime

class ExportHistoryResponse(BaseModel):
    items: list[ExportResponse]
    total: int


# --- Error ---

class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: dict = {}
```

---

## 4.3 Dependency Injection (COMPLETE CODE)

File: `src/guardianmapstudio/api/deps.py`

```python
from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from guardianmapstudio.config.settings import GuardianMapStudioSettings


@lru_cache(maxsize=1)
def get_settings() -> GuardianMapStudioSettings:
    return GuardianMapStudioSettings()


SettingsDep = Annotated[GuardianMapStudioSettings, Depends(get_settings)]


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield a DB session from app.state.session_factory (set in lifespan)."""
    factory = request.app.state.session_factory
    with factory() as session:
        yield session


DbSession = Annotated[Session, Depends(get_db)]
```

---

## 4.4 main.py (Stage 4 — REPLACES Stage 1 stub)

File: `src/guardianmapstudio/main.py`

```python
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from loguru import logger

from guardianmapstudio.config.settings import GuardianMapStudioSettings
from guardianmapstudio.database.connection import create_tables, get_engine, get_session_factory


def create_app(settings: GuardianMapStudioSettings | None = None) -> FastAPI:
    if settings is None:
        settings = GuardianMapStudioSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        engine = get_engine(settings)
        create_tables(engine)
        app.state.session_factory = get_session_factory(engine)
        Path(settings.export_dir).mkdir(parents=True, exist_ok=True)
        logger.info("GuardianMapStudio ready")
        yield
        engine.dispose()
        logger.info("GuardianMapStudio shutdown")

    app = FastAPI(
        title="GuardianMapStudio",
        description="Map authoring tool for Guardian autonomous vehicle platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    from guardianmapstudio.api.routers import (
        projects, workspaces, roads, waypoints,
        crossroads, restricted_areas, validation, export,
    )

    app.include_router(projects.router,          prefix="/api/v1/projects",   tags=["projects"])
    app.include_router(workspaces.router,        prefix="/api/v1/workspaces", tags=["workspaces"])
    app.include_router(roads.router,             prefix="/api/v1/workspaces", tags=["roads"])
    app.include_router(waypoints.router,         prefix="/api/v1/workspaces", tags=["waypoints"])
    app.include_router(crossroads.router,        prefix="/api/v1/workspaces", tags=["crossroads"])
    app.include_router(restricted_areas.router,  prefix="/api/v1/workspaces", tags=["areas"])
    app.include_router(validation.router,        prefix="/api/v1/workspaces", tags=["validation"])
    app.include_router(export.router,            prefix="/api/v1",            tags=["export"])

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "database": "ok", "version": "0.1.0"}

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


def main() -> None:
    import uvicorn
    settings = GuardianMapStudioSettings()
    _configure_logging(settings)
    logger.info("GuardianMapStudio starting on {}:{}", settings.host, settings.port)
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port)


def _configure_logging(settings: GuardianMapStudioSettings) -> None:
    logger.remove()
    logger.add(
        sink=sys.stderr,
        level=settings.log_level,
        format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )
    logger.add(
        sink=settings.log_file,
        level="DEBUG",
        rotation=f"{settings.log_rotation_mb} MB",
        retention=f"{settings.log_retention_days} days",
        compression="zip",
        enqueue=True,
    )


if __name__ == "__main__":
    main()
```

---

## 4.5 Router conventions (CRITICAL — read before writing any router)

**Domain→Response conversion pattern** (mandatory for all entities):

```python
from guardianmapstudio.api.schemas import RoadResponse, GeoPointDTO
from guardianmapstudio.domain.contracts import Road

def road_to_response(road: Road) -> RoadResponse:
    """Convert Road domain object to API response.

    NEVER use road.__dict__ (slots=True removes it).
    NEVER use dataclasses.asdict() (converts GeoPoint to {latitude, longitude}
    but GeoPointDTO expects {lat, lng}).
    Always convert explicitly.
    """
    return RoadResponse(
        id=road.id,
        workspace_id=road.workspace_id,
        name=road.name,
        coordinates=[GeoPointDTO(lat=p.latitude, lng=p.longitude)
                     for p in road.coordinates],
        speed_limit_kmh=road.speed_limit_kmh,
        direction=road.direction.value,
        width_meters=road.width_meters,
        created_at=road.created_at,
        updated_at=road.updated_at,
    )
```

Apply the same pattern for `waypoint_to_response`, `crossroad_to_response`,
`area_to_response`. Each router file has its own conversion function.

**Validation auto-run after every write** (mandatory):

After every POST, PATCH, DELETE of a map entity, call this helper:

```python
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from guardianmapstudio.geometry.engine import GeometryEngine
from guardianmapstudio.geometry.validation import ValidationEngine
from guardianmapstudio.database.repository import MapRepository, ValidationRepository, WorkspaceRepository


def _run_validation_after_write(workspace_id: int, db: Session) -> None:
    map_repo = MapRepository(db)
    roads = map_repo.get_roads(workspace_id)
    waypoints = map_repo.get_waypoints(workspace_id)
    crossroads = map_repo.get_crossroads(workspace_id)
    areas = map_repo.get_areas(workspace_id)

    all_points = [p for r in roads for p in r.coordinates]
    if all_points:
        avg_lat = sum(p.latitude for p in all_points) / len(all_points)
        avg_lng = sum(p.longitude for p in all_points) / len(all_points)
    else:
        avg_lat, avg_lng = -23.5, -46.6

    geo = GeometryEngine.from_centroid(avg_lat, avg_lng)
    engine = ValidationEngine(geo)
    results = engine.validate(roads, waypoints, crossroads, areas)

    val_repo = ValidationRepository(db)
    val_repo.replace_results(workspace_id, results)

    ws_repo = WorkspaceRepository(db)
    has_errors = any(r.is_blocking for r in results)
    ws_repo.update_validation_state(workspace_id, has_errors, datetime.now(timezone.utc))
```

**33 endpoints to implement** (full list — see doc 09 for request/response examples):

| Method | Path | Router file |
|---|---|---|
| `GET` | `/api/v1/projects` | projects.py |
| `POST` | `/api/v1/projects` | projects.py |
| `GET` | `/api/v1/projects/{id}` | projects.py |
| `PATCH` | `/api/v1/projects/{id}` | projects.py |
| `GET` | `/api/v1/projects/{id}/versions` | projects.py |
| `GET` | `/api/v1/projects/{id}/workspace` | workspaces.py |
| `GET` | `/api/v1/projects/{id}/exports` | export.py |
| `GET` | `/api/v1/workspaces/{id}/map` | workspaces.py |
| `POST` | `/api/v1/workspaces/{id}/validate` | validation.py |
| `GET` | `/api/v1/workspaces/{id}/validation` | validation.py |
| `POST` | `/api/v1/workspaces/{id}/publish` | workspaces.py |
| `POST` | `/api/v1/workspaces/{id}/snap` | workspaces.py |
| `GET/POST/GET/PATCH/DELETE` | `.../roads` | roads.py (5 endpoints) |
| `GET/POST/GET/PATCH/DELETE` | `.../waypoints` | waypoints.py (5 endpoints) |
| `GET/POST/DELETE` | `.../crossroads` | crossroads.py (3 endpoints) |
| `GET/POST/PATCH/DELETE` | `.../restricted-areas` | restricted_areas.py (4 endpoints) |
| `GET` | `/api/v1/versions/{id}/map` | workspaces.py |
| `POST` | `/api/v1/versions/{id}/export` | export.py |
| `GET` | `/api/v1/versions/{id}/export/download` | export.py |
| `GET` | `/api/v1/health` | main.py |

---

## 4.6 Stage 4 Tests

**tests/integration/test_api_projects.py**
```
test_create_project_returns_201        → POST /projects → 201 + project body
test_create_project_creates_workspace  → workspace with state=draft auto-created
test_list_projects_empty               → GET /projects returns {items: [], total: 0}
test_list_projects_with_data           → returns all created projects
test_get_project_by_id                 → GET /projects/1 returns correct project
test_get_project_not_found             → GET /projects/999 returns 404
```

**tests/integration/test_api_workspaces.py**
```
test_get_workspace_for_project         → GET /projects/1/workspace returns draft
test_validate_empty_workspace          → workspace.min_roads error
test_validate_valid_workspace          → no errors on well-formed map
test_publish_blocked_by_errors         → 422 when errors exist
test_publish_creates_version           → 201 with version_number=1
test_publish_creates_new_draft         → new DRAFT workspace after publish
test_get_validation_cached             → GET returns same results without re-running
```

**tests/integration/test_api_roads.py**
```
test_create_road_returns_201           → POST /workspaces/1/roads → 201
test_create_road_duplicate_name_409    → same name → 409
test_delete_road_with_waypoints_409    → road with waypoints → 409
test_update_road_coordinates           → PATCH updates correctly
test_delete_road_204                   → DELETE returns 204
test_validation_runs_after_create      → has_validation_errors updated after create
```

**tests/integration/test_api_waypoints.py**
```
test_create_waypoint_returns_201       → POST waypoints → 201
test_create_waypoint_snap_applied      → position snaps within 0.5m
test_create_speed_bump_no_height_422   → missing height_cm → 422
test_create_gate_invalid_type_422      → invalid gate_type → 422
test_list_waypoints_by_type            → GET ?type=speed_bump filters correctly
```

**tests/integration/test_api_export.py**
```
test_export_published_version          → POST versions/1/export → 201
test_export_json_valid                 → exported file is valid JSON
test_export_json_passes_format         → all required keys, "type" not "waypoint_type"
test_download_export                   → GET download returns file bytes
test_export_history_recorded           → GET exports shows record
```

---

## 4.7 Stage 4 Quality Gate

```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/ -v --cov=guardianmapstudio --cov-fail-under=80
```



---
---

# STAGE 5 — Frontend (Vue 3 + TypeScript)

## Objective

Implement the Vue 3 + TypeScript frontend. After this stage, the complete
application runs at `http://localhost:8000` and supports the full WF-01
workflow (create → draw → validate → publish → export).

## Files to create in Stage 5

All frontend files listed in the directory layout under `frontend/`.

---

## 5.1 Build setup

File: `frontend/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../src/guardianmapstudio/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

File: `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "jsx": "preserve",
    "lib": ["ES2020", "DOM"],
    "types": ["@types/leaflet"]
  },
  "include": ["src/**/*"]
}
```

File: `frontend/package.json`

```json
{
  "name": "guardianmapstudio-frontend",
  "version": "0.1.0",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "3.4.38",
    "pinia": "2.2.6",
    "axios": "1.7.9",
    "leaflet": "1.9.4"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "5.2.1",
    "@types/leaflet": "1.9.14",
    "vite": "5.4.11",
    "vue-tsc": "2.1.10",
    "typescript": "5.6.3"
  }
}
```

---

## 5.2 API Types (COMPLETE CODE)

File: `frontend/src/api/types.ts`

```typescript
export interface GeoPoint { lat: number; lng: number }

export interface ProjectResponse {
  id: number; name: string; description: string
  created_at: string; updated_at: string
}

export interface VersionResponse {
  id: number; project_id: number; version_number: number; name: string
  published_at: string; road_count: number; waypoint_count: number
  crossroad_count: number; restricted_area_count: number
}

export interface WorkspaceResponse {
  id: number; project_id: number; state: 'draft' | 'published'
  base_version_id: number | null
  has_validation_errors: boolean
  last_validated_at: string | null
  created_at: string; updated_at: string
}

export interface RoadResponse {
  id: number; workspace_id: number; name: string
  coordinates: GeoPoint[]; speed_limit_kmh: number
  direction: 'two_way' | 'one_way'; width_meters: number
  created_at: string; updated_at: string
}

export interface WaypointResponse {
  id: number; workspace_id: number; name: string
  waypoint_type: string; lat: number; lng: number
  road_name: string | null; heading_degrees: number | null
  extra_data: Record<string, unknown>; active: boolean
  created_at: string; updated_at: string
}

export interface CrossroadResponse {
  id: number; workspace_id: number
  road_a_name: string; road_b_name: string
  lat: number; lng: number; created_at: string
}

export interface RestrictedAreaResponse {
  id: number; workspace_id: number; name: string
  polygon: GeoPoint[]; restriction_type: string
  speed_limit_kmh: number | null; active: boolean
  created_at: string; updated_at: string
}

export interface ValidationResultResponse {
  id: number; severity: 'error' | 'warning'
  rule_id: string; message: string
  affected_entity_type: string; affected_entity_id: number
}

export interface ValidationSummaryResponse {
  workspace_id: number; error_count: number; warning_count: number
  can_publish: boolean; results: ValidationResultResponse[]
  validated_at: string
}
```

---

## 5.3 API Client (COMPLETE CODE)

File: `frontend/src/api/client.ts`

```typescript
import type {
  ProjectResponse, VersionResponse, WorkspaceResponse,
  RoadResponse, WaypointResponse, CrossroadResponse,
  RestrictedAreaResponse, ValidationSummaryResponse, GeoPoint,
} from './types'

const API = ''

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const opts: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body) opts.body = JSON.stringify(body)
  const res = await fetch(`${API}${path}`, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'unknown', message: res.statusText }))
    throw err
  }
  if (res.status === 204) return {} as T
  return res.json()
}

export const api = {
  // Projects
  getProjects: () => request<{ items: ProjectResponse[]; total: number }>('GET', '/api/v1/projects'),
  createProject: (name: string, description = '') =>
    request<ProjectResponse>('POST', '/api/v1/projects', { name, description }),
  getProject: (id: number) => request<ProjectResponse>('GET', `/api/v1/projects/${id}`),

  // Versions
  getVersions: (projectId: number) =>
    request<{ items: VersionResponse[] }>('GET', `/api/v1/projects/${projectId}/versions`),

  // Workspace
  getWorkspace: (projectId: number) =>
    request<WorkspaceResponse>('GET', `/api/v1/projects/${projectId}/workspace`),
  validate: (workspaceId: number) =>
    request<ValidationSummaryResponse>('POST', `/api/v1/workspaces/${workspaceId}/validate`, {}),
  getValidation: (workspaceId: number) =>
    request<ValidationSummaryResponse>('GET', `/api/v1/workspaces/${workspaceId}/validation`),
  publish: (workspaceId: number, versionName: string) =>
    request<VersionResponse>('POST', `/api/v1/workspaces/${workspaceId}/publish`, { version_name: versionName }),
  snap: (workspaceId: number, lat: number, lng: number) =>
    request<{ original: GeoPoint; snapped_to: GeoPoint; snapped: boolean; distance_meters: number }>(
      'POST', `/api/v1/workspaces/${workspaceId}/snap`, { lat, lng }),

  // Map (bulk)
  getMap: (workspaceId: number) =>
    request<{ roads: RoadResponse[]; waypoints: WaypointResponse[]; crossroads: CrossroadResponse[]; restricted_areas: RestrictedAreaResponse[] }>(
      'GET', `/api/v1/workspaces/${workspaceId}/map`),

  // Roads
  getRoads: (wsId: number) => request<RoadResponse[]>('GET', `/api/v1/workspaces/${wsId}/roads`),
  createRoad: (wsId: number, data: object) => request<RoadResponse>('POST', `/api/v1/workspaces/${wsId}/roads`, data),
  updateRoad: (wsId: number, id: number, data: object) => request<RoadResponse>('PATCH', `/api/v1/workspaces/${wsId}/roads/${id}`, data),
  deleteRoad: (wsId: number, id: number) => request<void>('DELETE', `/api/v1/workspaces/${wsId}/roads/${id}`),

  // Waypoints
  getWaypoints: (wsId: number) => request<WaypointResponse[]>('GET', `/api/v1/workspaces/${wsId}/waypoints`),
  createWaypoint: (wsId: number, data: object) => request<WaypointResponse>('POST', `/api/v1/workspaces/${wsId}/waypoints`, data),
  updateWaypoint: (wsId: number, id: number, data: object) => request<WaypointResponse>('PATCH', `/api/v1/workspaces/${wsId}/waypoints/${id}`, data),
  deleteWaypoint: (wsId: number, id: number) => request<void>('DELETE', `/api/v1/workspaces/${wsId}/waypoints/${id}`),

  // Crossroads
  getCrossroads: (wsId: number) => request<CrossroadResponse[]>('GET', `/api/v1/workspaces/${wsId}/crossroads`),
  createCrossroad: (wsId: number, data: object) => request<CrossroadResponse>('POST', `/api/v1/workspaces/${wsId}/crossroads`, data),
  deleteCrossroad: (wsId: number, id: number) => request<void>('DELETE', `/api/v1/workspaces/${wsId}/crossroads/${id}`),

  // Restricted areas
  getAreas: (wsId: number) => request<RestrictedAreaResponse[]>('GET', `/api/v1/workspaces/${wsId}/restricted-areas`),
  createArea: (wsId: number, data: object) => request<RestrictedAreaResponse>('POST', `/api/v1/workspaces/${wsId}/restricted-areas`, data),
  updateArea: (wsId: number, id: number, data: object) => request<RestrictedAreaResponse>('PATCH', `/api/v1/workspaces/${wsId}/restricted-areas/${id}`, data),
  deleteArea: (wsId: number, id: number) => request<void>('DELETE', `/api/v1/workspaces/${wsId}/restricted-areas/${id}`),

  // Export
  exportVersion: (versionId: number) =>
    request<{ export_id: number; file_path: string }>('POST', `/api/v1/versions/${versionId}/export`, {}),
  downloadExport: (versionId: number) => `/api/v1/versions/${versionId}/export/download`,
  getExports: (projectId: number) =>
    request<{ items: Array<{ export_id: number; version_id: number; file_path: string; exported_at: string }>; total: number }>(
      'GET', `/api/v1/projects/${projectId}/exports`),
}
```

---

## 5.4 Critical Leaflet Rules

These rules apply to EVERY Leaflet map instance. Violating any one of them
causes bugs that are extremely hard to diagnose.

| # | Rule | Why |
|---|---|---|
| 1 | Always init in `mounted()` + `this.$nextTick()` | DOM element doesn't exist in `created()` |
| 2 | Never use `v-if` on a map container | `v-if` destroys the Leaflet instance |
| 3 | Call `map.invalidateSize()` on visibility change | Leaflet loses dimensions when hidden |
| 4 | Popup buttons use `window.guardianApp.method()` | Vue directives don't work in HTML popups |
| 5 | Expose app: `window.guardianApp = app.mount('#app')` | Required for rule 4 |
| 6 | Tiles: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` | No API key required |
| 7 | Default zoom: `18` | Right scale for condominium editing |

---

## 5.5 MapEditor markers — no emojis

Use letter markers with color-coded circles, not emojis:

| Type | Letter | Circle color | Fill |
|---|---|---|---|
| stop_sign | P | `#E24B4A` | white |
| speed_bump | L | `#EF9F27` | `#EF9F27` (text white) |
| gate | G | `#1D9E75` | `#1D9E75` (text white) |
| curve | C | `#888780` | white |
| landmark | M | `#534AB7` | white |
| stop_zone | S | `#378ADD` | white |

Roads: `#378ADD` (two_way), `#ff7800` (one_way, with direction arrows).
Areas: `#EF9F27` opacity 0.2 (speed_limit), `#E24B4A` opacity 0.15 (no_entry), `#44ff44` opacity 0.15 (pedestrian_only).

---

## 5.6 Components to implement

Implement all components as specified in doc 11, sections 3–9.
The 3 Pinia stores (project, workspace, map) must match the interfaces in doc 11 exactly.

---

## 5.7 Stage 5 Quality Gate

```bash
cd frontend
npm ci
npm run build
cd ..

uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/ -v --cov=guardianmapstudio --cov-fail-under=80

uv run guardianmapstudio
```

**Manual WF-01 checklist** (open http://localhost:8000):
```
[ ] App loads
[ ] Create project → appears in list
[ ] DRAFT workspace opens
[ ] Draw road → appears on map
[ ] Road with 1 point → ERROR inline
[ ] Place speed_bump → persisted
[ ] speed_bump without height_cm → ERROR
[ ] Publish disabled when errors exist
[ ] Fix errors → Publish enabled
[ ] Publish → Version v1 created
[ ] New DRAFT workspace created
[ ] Export v1 → JSON downloaded
[ ] JSON has "type" key (not "waypoint_type")
[ ] JSON has meta.schema_version: "1.0"
[ ] guardian-seed-map --from-json <file> succeeds
[ ] Guardian HUD shows correct road name
```


---

## README.md

```markdown
# GuardianMapStudio

Visual map authoring tool for the Guardian autonomous vehicle platform.

## Prerequisites

- Python 3.12+, uv, Node.js 20+

## Install & Run

uv sync && uv sync --extra dev
cd frontend && npm ci && npm run build && cd ..
uv run guardianmapstudio
# Open http://localhost:8000

## Test

uv run pytest --cov=guardianmapstudio --cov-fail-under=80 -v

## Export to Guardian

1. Create and publish a map version in the browser
2. Click Export → download JSON
3. Run: uv run guardian-seed-map --from-json <file>
4. Restart Guardian
```

