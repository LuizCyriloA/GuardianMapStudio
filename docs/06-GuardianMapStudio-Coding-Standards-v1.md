# GuardianMapStudio — Coding Standards v1

These standards apply to all code in the GuardianMapStudio project.
They mirror Guardian's standards where applicable and extend them for
the web application context (FastAPI, Vue 3, TypeScript).

---

## 1. Python Standards

### 1.1 Language version and type hints

- Python 3.12 — no compatibility with older versions
- Type hints are **mandatory** on every function signature and return type
- `from __future__ import annotations` at the top of every Python file
- No `Any` type without a comment explaining why it cannot be avoided
- `mypy --strict` must pass with zero errors

### 1.2 Naming conventions

| Kind | Convention | Example |
|---|---|---|
| Classes | PascalCase | `GeometryEngine`, `WorkspaceRepository` |
| Functions and methods | snake_case | `validate_road()`, `get_active_draft()` |
| Variables | snake_case | `road_count`, `snap_result` |
| Constants | UPPER_SNAKE_CASE | `EARTH_RADIUS_M`, `SNAP_TOLERANCE_M` |
| Private methods | leading underscore | `_validate_roads()`, `_to_local()` |
| Type aliases | PascalCase | `WorkspaceId = int` |
| Pydantic models | PascalCase + suffix | `RoadCreate`, `RoadResponse` |
| SQLAlchemy models | PascalCase + `Model` suffix | `RoadModel`, `WorkspaceModel` |
| Repository classes | PascalCase + `Repository` suffix | `MapRepository`, `WorkspaceRepository` |
| Routers | lowercase filename | `roads.py`, `workspaces.py` |

### 1.3 Import order

Enforced by `ruff` (isort rules). Order:
1. `from __future__ import annotations`
2. Standard library imports
3. Third-party imports (FastAPI, SQLAlchemy, Pydantic, Shapely, pyproj)
4. Local application imports (`guardianmapstudio.*`)

Each group separated by a blank line. No star imports (`from module import *`).

### 1.4 Dataclasses

All domain value objects and aggregates use `@dataclass(frozen=True, slots=True)`.
No mutable dataclasses in the domain layer.

```python
# Correct
@dataclass(frozen=True, slots=True)
class GeoPoint:
    latitude: float
    longitude: float

# Wrong — never do this in domain layer
@dataclass
class GeoPoint:
    latitude: float
    longitude: float
```

### 1.5 Error handling

- No bare `except:` — always catch a specific exception type
- No `except Exception:` without logging and re-raising or explicit justification
- All exceptions in API handlers must produce an `ErrorResponse` (doc 05, section 4.10)
- FastAPI `HTTPException` is used only in router functions — never in services or repositories
- Domain errors use a `DomainError` base class

```python
# Correct
try:
    result = repo.get_road(road_id)
except sqlalchemy.exc.SQLAlchemyError:
    logger.error("Database error fetching road {}", road_id, exc_info=True)
    raise

# Wrong
try:
    result = repo.get_road(road_id)
except:
    pass
```

### 1.6 Logging

- Loguru only — no `print()`, no `logging` stdlib module
- Use lazy evaluation: `logger.info("Road {} created", road.name)` not f-strings
- All unhandled exceptions logged at ERROR or CRITICAL before propagating
- GPS or spatial data in logs: always round to 5 decimal places maximum

```python
# Correct
logger.info("Road '{}' created in workspace {}", road.name, workspace_id)

# Wrong — f-string defeats lazy evaluation
logger.info(f"Road '{road.name}' created in workspace {workspace_id}")
```

### 1.7 No direct SQL

All database access goes through repository classes.
No `db.execute(text("SELECT ..."))` outside of `database/` modules.
No SQLAlchemy queries in routers, services, or domain code.

### 1.8 No hardcoded operational values

All configurable values come from `GuardianMapStudioSettings`.
No hardcoded ports, paths, or thresholds outside of `settings.py` and constants.

```python
# Correct — read from settings
snap_engine = SnapEngine(geo, tolerance_m=settings.snap_tolerance_m)

# Wrong
snap_engine = SnapEngine(geo, tolerance_m=0.5)
```

Exception: named constants in geometry code (`EARTH_RADIUS_M`, `INTERSECTION_PROXIMITY_M`)
are acceptable because they are physical or algorithmic constants, not operational values.

---

## 2. FastAPI Conventions

### 2.1 Router structure

Each resource has its own router file in `src/guardianmapstudio/api/routers/`.
Routers are registered in `main.py` with a consistent prefix.

```python
# main.py
app.include_router(projects.router,        prefix="/api/v1/projects",        tags=["projects"])
app.include_router(workspaces.router,      prefix="/api/v1/workspaces",      tags=["workspaces"])
app.include_router(roads.router,           prefix="/api/v1/workspaces",      tags=["roads"])
app.include_router(waypoints.router,       prefix="/api/v1/workspaces",      tags=["waypoints"])
app.include_router(crossroads.router,      prefix="/api/v1/workspaces",      tags=["crossroads"])
app.include_router(restricted_areas.router,prefix="/api/v1/workspaces",      tags=["restricted_areas"])
app.include_router(validation.router,      prefix="/api/v1/workspaces",      tags=["validation"])
app.include_router(export.router,          prefix="/api/v1",                 tags=["export"])
```

### 2.2 Dependency injection

Database sessions are injected via `Annotated` dependencies. Never create
a session directly in a router function.

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from guardianmapstudio.database.connection import get_db

DbSession = Annotated[Session, Depends(get_db)]

@router.get("/{workspace_id}/roads")
def list_roads(workspace_id: int, db: DbSession) -> list[RoadResponse]:
    repo = MapRepository(db)
    roads = repo.get_roads(workspace_id)
    return [RoadResponse.model_validate(r) for r in roads]
```

### 2.3 Response models

Every endpoint must declare its `response_model`. No endpoints return `dict`.

### 2.4 HTTP status codes

Use explicit status codes matching the API spec (doc 09):
- `status.HTTP_200_OK` for reads and updates
- `status.HTTP_201_CREATED` for creates
- `status.HTTP_204_NO_CONTENT` for deletes
- `status.HTTP_404_NOT_FOUND` for missing resources
- `status.HTTP_409_CONFLICT` for state conflicts
- `status.HTTP_422_UNPROCESSABLE_ENTITY` for business rule violations

### 2.5 Validation triggers

After every create, update, or delete of a map entity, the router must
trigger a validation run on the workspace. This keeps `has_validation_errors`
current and ensures the UI always reflects the real validation state.

---

## 3. SQLAlchemy Conventions

### 3.1 Session management

Sessions are provided by `get_db()` dependency and closed automatically.
Never store a session in an instance variable that outlives the request.

```python
def get_db():
    with SessionLocal() as session:
        yield session
```

### 3.2 Model conventions

- All models inherit from `Base` (declared in `models.py`)
- Primary keys: `id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)`
- All timestamps use `DateTime(timezone=True)`
- `Double` for latitude and longitude — never `Float`
- JSON fields stored as `Text` — parsed/serialized in repository layer
- `updated_at` on all mutable tables with `onupdate` lambda

### 3.3 Repositories return domain objects

Repositories always return domain contracts (`Road`, `Waypoint`, etc.)
never ORM models. Conversion happens inside the repository via a `_to_domain()` method.

```python
def _road_to_domain(self, model: RoadModel) -> Road:
    import json
    coords = [GeoPoint(latitude=p["lat"], longitude=p["lng"])
              for p in json.loads(model.coordinates)]
    return Road(
        id=model.id,
        workspace_id=model.workspace_id,
        name=model.name,
        coordinates=coords,
        speed_limit_kmh=model.speed_limit_kmh,
        direction=RoadDirection(model.direction),
        width_meters=model.width_meters,
    )
```

---

## 4. Testing Standards

### 4.1 Structure

```
tests/
├── conftest.py              ← shared fixtures (db_session, settings, client)
├── unit/                    ← no database, no HTTP
│   ├── test_geometry_engine.py
│   ├── test_snap_engine.py
│   ├── test_crossroad_engine.py
│   ├── test_validation_engine.py
│   ├── test_guardian_exporter.py
│   └── test_repository.py
└── integration/             ← real SQLite in-memory + TestClient
    ├── test_api_projects.py
    ├── test_api_workspaces.py
    ├── test_api_roads.py
    ├── test_api_waypoints.py
    ├── test_api_export.py
    └── test_database.py
```

### 4.2 Test naming

All test functions named `test_<what>_<expected_result>`:
```python
def test_road_min_points_error()      # correct
def test_road()                       # wrong — too vague
def testRoad()                        # wrong — not snake_case
```

### 4.3 Fixtures

```python
# conftest.py

@pytest.fixture
def settings() -> GuardianMapStudioSettings:
    return GuardianMapStudioSettings(
        database_url="sqlite:///:memory:",
        snap_tolerance_m=0.5,
    )

@pytest.fixture
def db_session(settings):
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session

@pytest.fixture
def client(settings, db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
```

### 4.4 Coverage

- Target: ≥ 80% overall
- Geometry engines: ≥ 90% (critical path)
- Guardian exporter: 100% (integration contract)
- `pytest --cov=guardianmapstudio --cov-fail-under=80`

### 4.5 No test should touch guardian.db

Tests must use `sqlite:///:memory:` or a temporary file in `tmp_path`.
Never reference `guardian.db` or `guardianmapstudio.db` by name in tests.

---

## 5. TypeScript / Vue 3 Standards

### 5.1 Language

- TypeScript strict mode (`"strict": true` in `tsconfig.json`)
- Vue 3 Options API (consistent with frontend spec — doc 11)
- No `any` type without justification comment
- All API response types defined in `src/api/types.ts`

### 5.2 Naming conventions

| Kind | Convention | Example |
|---|---|---|
| Components | PascalCase | `MapEditor.vue`, `ValidationPanel.vue` |
| Stores | camelCase | `useWorkspaceStore`, `useMapStore` |
| Composables | `use` prefix | `useLeafletMap()` |
| Types/interfaces | PascalCase | `RoadResponse`, `WorkspaceState` |
| Constants | UPPER_SNAKE_CASE | `API_BASE_URL`, `SNAP_TOLERANCE_M` |
| Event handlers | `on` prefix | `onMapClick`, `onSaveWaypoint` |

### 5.3 API calls

All API calls go through `src/api/client.ts` — no raw `fetch()` in components.

```typescript
// src/api/client.ts
const API_BASE = ''   // same origin — served by FastAPI on port 8000

export const api = {
  async getRoads(workspaceId: number): Promise<RoadResponse[]> {
    const res = await fetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/roads`)
    if (!res.ok) throw new ApiError(await res.json())
    return res.json()
  },
}
```

### 5.4 Leaflet rules

- Always initialize Leaflet maps in `mounted()` + `this.$nextTick()`
- Never in `created()` — DOM element does not exist yet
- Tab switching uses CSS `display: none/block` — never `v-if` on map containers
- Always call `map.invalidateSize()` after a map container becomes visible
- Popup buttons that trigger Vue methods must use `window.app.methodName(id)`

### 5.5 No business logic in components

Components handle rendering and user interaction only.
Business rules, API calls, and state mutations go in Pinia stores.

---

## 6. pyproject.toml Configuration

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
    "pytest-timeout==2.3.1",    # prevent hanging tests — same as Guardian
    "httpx==0.28.1",            # required by FastAPI TestClient
    "ruff==0.8.6",
    "mypy==1.13.0",
    "pre-commit==4.0.1",
]

[project.scripts]
guardianmapstudio = "guardianmapstudio.main:main"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
# E,F,W: pycodestyle/pyflakes (base)
# I: isort (imports)
# N: pep8-naming
# UP: pyupgrade
# S: bandit security rules — detects binding to 0.0.0.0 (S104), unsafe patterns
# B: flake8-bugbear — detects mutable defaults and other bug-prone patterns
# LOG: logging misuse — detects f-string in logger calls (defeats lazy evaluation)
select = ["E", "F", "I", "N", "W", "UP", "S", "B", "LOG"]
ignore = [
    "S101",   # allow assert in tests
    "S104",   # binding to 0.0.0.0 is intentional for web server
    "B008",   # pydantic default argument pattern
]

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

## 7. Quality Gates

Must pass before any commit is accepted:

```bash
uv run ruff check src/ tests/        # zero warnings
uv run mypy src/                     # zero errors (strict mode)
uv run pytest --cov=guardianmapstudio --cov-fail-under=80 -v
```

Pre-commit hooks run `ruff` and `mypy` automatically on every `git commit`.

File: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6        # must match ruff version in pyproject.toml
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0       # must match mypy version in pyproject.toml
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic==2.9.2
          - pydantic-settings==2.7.0   # must match pyproject.toml
          - sqlalchemy==2.0.40         # must match pyproject.toml
          - fastapi==0.115.6           # must match pyproject.toml
        args: [--strict]
        files: ^src/
```

> **Note**: `pydantic==2.9.2` must be listed in `additional_dependencies`
> even though it is a transitive dependency of `pydantic-settings`.
> mypy pre-commit runs in an isolated environment and needs all stubs
> declared explicitly.
