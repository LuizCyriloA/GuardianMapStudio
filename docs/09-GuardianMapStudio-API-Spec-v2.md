# GuardianMapStudio — API Specification v2

All endpoints are prefixed with `/api/v1`.
The frontend (Vue 3 SPA) is served at `/` from `frontend/dist/`.
FastAPI auto-generates OpenAPI docs at `/docs` and `/redoc`.

**Base URL**: `http://localhost:8000` (configurable via `STUDIO_PORT`)
**Content-Type**: `application/json` on all requests and responses
**Authentication**: None in MVP01

---

## Conventions

### Success responses
- `200 OK` — read or update succeeded
- `201 Created` — resource created; body contains the new resource
- `204 No Content` — delete succeeded; empty body

### Error responses

All errors use the same shape:
```json
{
  "error": "machine_readable_code",
  "message": "Human-readable description",
  "detail": {}
}
```

| Status | When |
|---|---|
| `404` | Resource not found |
| `409` | Conflict (duplicate name, invalid state transition, has dependents) |
| `422` | Validation failed (invalid enum, missing field, business rule violation) |
| `500` | Server error (database failure, export write error) |

### Resource scoping
All map entities (roads, waypoints, crossroads, restricted areas) belong to a workspace.
The workspace must be in `DRAFT` state for any write operation.
Read operations work on any workspace state.

---

## 1. Projects

### `GET /api/v1/projects`

List all projects.

**Response 200**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Condomínio Parque das Flores",
      "description": "Mapa principal do condomínio",
      "created_at": "2026-06-01T10:00:00+00:00",
      "updated_at": "2026-06-01T14:30:00+00:00"
    }
  ],
  "total": 1
}
```

---

### `POST /api/v1/projects`

Create a new project. A first empty DRAFT Workspace is automatically created.

**Request body**
```json
{
  "name": "Condomínio Parque das Flores",
  "description": "Mapa principal do condomínio"
}
```

**Response 201**
```json
{
  "id": 1,
  "name": "Condomínio Parque das Flores",
  "description": "Mapa principal do condomínio",
  "created_at": "2026-06-01T10:00:00+00:00",
  "updated_at": "2026-06-01T10:00:00+00:00"
}
```

---

### `GET /api/v1/projects/{project_id}`

Get a single project.

**Response 200** — same as item in list above
**Response 404** — `not_found`

---

### `PATCH /api/v1/projects/{project_id}`

Update project name or description.

**Request body** (all fields optional)
```json
{
  "name": "Condomínio Parque das Flores — Fase 2",
  "description": "Inclui área de lazer reformada"
}
```

**Response 200** — updated project

---

### `GET /api/v1/projects/{project_id}/versions`

List all published versions for a project, newest first.

**Response 200**
```json
{
  "items": [
    {
      "id": 3,
      "project_id": 1,
      "version_number": 3,
      "name": "v3 - Adicionado playground",
      "published_at": "2026-06-01T14:35:00+00:00",
      "road_count": 4,
      "waypoint_count": 12,
      "crossroad_count": 2,
      "restricted_area_count": 1
    }
  ],
  "total": 3
}
```

---

## 2. Workspaces

### `GET /api/v1/projects/{project_id}/workspace`

Get the active DRAFT workspace for a project.
Every project always has exactly one DRAFT workspace.

**Response 200**
```json
{
  "id": 7,
  "project_id": 1,
  "state": "draft",
  "base_version_id": 3,
  "created_at": "2026-06-01T14:36:00+00:00",
  "updated_at": "2026-06-01T15:10:00+00:00",
  "last_validated_at": "2026-06-01T15:09:00+00:00",
  "has_validation_errors": false
}
```

**Response 404** — `not_found` (project does not exist)

---

### `POST /api/v1/workspaces/{workspace_id}/validate`

Run the ValidationEngine on the workspace.
Replaces all previous validation results.
Called automatically by the frontend after every map edit.
Can also be called manually before Publish.

**Request body**: empty `{}`

**Response 200**
```json
{
  "workspace_id": 7,
  "error_count": 1,
  "warning_count": 2,
  "can_publish": false,
  "validated_at": "2026-06-01T15:09:00+00:00",
  "results": [
    {
      "id": 14,
      "severity": "error",
      "rule_id": "road.min_points",
      "message": "Road 'Rua do Fundo' has only 1 point. Minimum is 2.",
      "affected_entity_type": "road",
      "affected_entity_id": 23
    },
    {
      "id": 15,
      "severity": "warning",
      "rule_id": "road.no_waypoints",
      "message": "Road 'Rua Lateral' has no waypoints.",
      "affected_entity_type": "road",
      "affected_entity_id": 24
    }
  ]
}
```

**Response 404** — `not_found` (workspace does not exist)

---

### `GET /api/v1/workspaces/{workspace_id}/validation`

Get the latest cached validation results without re-running.
Returns empty results if validation has never been run.

**Response 200** — same shape as validate endpoint above

---

### `POST /api/v1/workspaces/{workspace_id}/publish`

Publish the workspace as a new immutable Version.
Runs validation internally — fails if any ERRORs exist.
Creates a new DRAFT workspace from the published Version automatically.

**Request body**
```json
{
  "version_name": "v4 - Corrigido número de pontos"
}
```

**Response 201**
```json
{
  "id": 4,
  "project_id": 1,
  "version_number": 4,
  "name": "v4 - Corrigido número de pontos",
  "published_at": "2026-06-01T16:00:00+00:00",
  "road_count": 4,
  "waypoint_count": 12,
  "crossroad_count": 2,
  "restricted_area_count": 1
}
```

**Response 404** — `not_found`
**Response 409** — `workspace_not_draft` (workspace already published)
**Response 422** — `validation_errors_blocking`
```json
{
  "error": "validation_errors_blocking",
  "message": "Cannot publish: 1 validation error must be fixed first.",
  "detail": {
    "error_count": 1,
    "errors": [
      {
        "rule_id": "road.min_points",
        "message": "Road 'Rua do Fundo' has only 1 point. Minimum is 2.",
        "affected_entity_type": "road",
        "affected_entity_id": 23
      }
    ]
  }
}
```

---

## 3. Export

### `POST /api/v1/versions/{version_id}/export`

Export a published Version as a Guardian-compatible JSON file.
Writes the file to `STUDIO_EXPORT_DIR/<project_name>_v<version_number>.json`.
Records the export in `export_history`.

**Request body**: empty `{}`

**Response 201**
```json
{
  "export_id": 5,
  "version_id": 4,
  "file_path": "/home/user/guardianmapstudio/exports/Condomininho_v4.json",
  "file_size_bytes": 2847,
  "exported_at": "2026-06-01T16:05:00+00:00"
}
```

**Response 404** — `not_found`
**Response 500** — `export_write_error`

---

### `GET /api/v1/projects/{project_id}/exports`

List all exports for a project, newest first.

**Response 200**
```json
{
  "items": [
    {
      "export_id": 5,
      "version_id": 4,
      "file_path": "/home/user/guardianmapstudio/exports/Condomininho_v4.json",
      "file_size_bytes": 2847,
      "exported_at": "2026-06-01T16:05:00+00:00"
    }
  ],
  "total": 1
}
```

---

### `GET /api/v1/versions/{version_id}/export/download`

Download the most recent export JSON for a version directly from the browser.
Returns the file as `application/json` with `Content-Disposition: attachment`.

**Response 200** — JSON file download
**Response 404** — `not_found` (version or no export exists for this version)

---

## 4. Roads

All road endpoints are scoped to a workspace.
Write operations require workspace state == `draft`.

### `GET /api/v1/workspaces/{workspace_id}/roads`

List all roads in the workspace.

**Response 200**
```json
[
  {
    "id": 23,
    "workspace_id": 7,
    "name": "Rua Principal",
    "coordinates": [
      {"lat": -20.8100, "lng": -49.3756},
      {"lat": -20.8105, "lng": -49.3756},
      {"lat": -20.8110, "lng": -49.3756}
    ],
    "speed_limit_kmh": 20,
    "direction": "two_way",
    "width_meters": 6.0,
    "created_at": "2026-06-01T10:05:00+00:00",
    "updated_at": "2026-06-01T10:05:00+00:00"
  }
]
```

---

### `POST /api/v1/workspaces/{workspace_id}/roads`

Create a new road.

**Request body**
```json
{
  "name": "Rua Secundária",
  "coordinates": [
    {"lat": -20.8105, "lng": -49.3760},
    {"lat": -20.8105, "lng": -49.3756}
  ],
  "speed_limit_kmh": 15,
  "direction": "two_way",
  "width_meters": 5.0
}
```

**Response 201** — created road (same shape as list item)
**Response 409** — `workspace_not_draft` or `road_name_duplicate`
**Response 422** — `invalid_enum_value` (direction), `missing_required_field`

---

### `GET /api/v1/workspaces/{workspace_id}/roads/{road_id}`

Get a single road.

**Response 200** — road object
**Response 404** — `not_found`

---

### `PATCH /api/v1/workspaces/{workspace_id}/roads/{road_id}`

Update a road. All fields optional — only sent fields are updated.

**Request body** (example: update coordinates only)
```json
{
  "coordinates": [
    {"lat": -20.8105, "lng": -49.3762},
    {"lat": -20.8105, "lng": -49.3756}
  ]
}
```

**Response 200** — updated road
**Response 404** — `not_found`
**Response 409** — `workspace_not_draft` or `road_name_duplicate`

---

### `DELETE /api/v1/workspaces/{workspace_id}/roads/{road_id}`

Delete a road.
Fails if any Waypoint references this road by name or if any Crossroad references it.

**Response 204** — deleted
**Response 404** — `not_found`
**Response 409** — `workspace_not_draft` or `road_has_dependents`
```json
{
  "error": "road_has_dependents",
  "message": "Cannot delete road 'Rua Principal': 3 waypoints and 1 crossroad reference it.",
  "detail": {
    "waypoint_count": 3,
    "crossroad_count": 1
  }
}
```

---

## 5. Waypoints

### `GET /api/v1/workspaces/{workspace_id}/waypoints`

List all waypoints. Optional filter: `?type=speed_bump`

**Query params**
- `type` (optional) — filter by waypoint_type value
- `active` (optional, default `true`) — filter by active flag

**Response 200**
```json
[
  {
    "id": 41,
    "workspace_id": 7,
    "name": "Lombada 1",
    "waypoint_type": "speed_bump",
    "lat": -20.8103,
    "lng": -49.3756,
    "road_name": "Rua Principal",
    "heading_degrees": null,
    "extra_data": {"height_cm": 10},
    "active": true,
    "created_at": "2026-06-01T10:10:00+00:00",
    "updated_at": "2026-06-01T10:10:00+00:00"
  }
]
```

---

### `POST /api/v1/workspaces/{workspace_id}/waypoints`

Create a waypoint. Snap is applied automatically if the position is within
`STUDIO_SNAP_TOLERANCE_M` of an existing road endpoint or waypoint.

**Request body**
```json
{
  "name": "PARE - Cruzamento",
  "waypoint_type": "stop_sign",
  "lat": -20.8105,
  "lng": -49.3756,
  "road_name": "Rua Principal",
  "heading_degrees": 90.0,
  "extra_data": {}
}
```

**Response 201** — created waypoint
```json
{
  "id": 42,
  "workspace_id": 7,
  "name": "PARE - Cruzamento",
  "waypoint_type": "stop_sign",
  "lat": -20.8105,
  "lng": -49.3756,
  "road_name": "Rua Principal",
  "heading_degrees": 90.0,
  "extra_data": {},
  "active": true,
  "created_at": "2026-06-01T10:15:00+00:00",
  "updated_at": "2026-06-01T10:15:00+00:00",
  "snapped": false
}
```

> **Note**: The `snapped` field in the create response indicates whether the
> position was adjusted by the SnapEngine. It is only present in the create
> response, not in list/get responses.

**Response 409** — `workspace_not_draft`
**Response 422** — `invalid_enum_value`, `missing_required_field`

---

### `GET /api/v1/workspaces/{workspace_id}/waypoints/{waypoint_id}`

Get a single waypoint.

**Response 200** — waypoint object
**Response 404** — `not_found`

---

### `PATCH /api/v1/workspaces/{workspace_id}/waypoints/{waypoint_id}`

Update a waypoint.

**Request body** (example: move position)
```json
{
  "lat": -20.8104,
  "lng": -49.3757
}
```

**Response 200** — updated waypoint
**Response 404** — `not_found`
**Response 409** — `workspace_not_draft`

---

### `DELETE /api/v1/workspaces/{workspace_id}/waypoints/{waypoint_id}`

Delete a waypoint.

**Response 204** — deleted
**Response 404** — `not_found`
**Response 409** — `workspace_not_draft`

---

## 6. Crossroads

### `GET /api/v1/workspaces/{workspace_id}/crossroads`

List all crossroads.

**Response 200**
```json
[
  {
    "id": 11,
    "workspace_id": 7,
    "road_a_name": "Rua Principal",
    "road_b_name": "Rua Secundária",
    "lat": -20.8105,
    "lng": -49.3756,
    "created_at": "2026-06-01T10:20:00+00:00"
  }
]
```

---

### `POST /api/v1/workspaces/{workspace_id}/crossroads`

Create a crossroad. Both road names must exist in the workspace.

**Request body**
```json
{
  "road_a_name": "Rua Principal",
  "road_b_name": "Rua Secundária",
  "lat": -20.8105,
  "lng": -49.3756
}
```

**Response 201** — created crossroad
**Response 409** — `workspace_not_draft`
**Response 422** — `missing_required_field`
```json
{
  "error": "missing_required_field",
  "message": "Road 'Rua Inexistente' does not exist in this workspace.",
  "detail": {"field": "road_a_name", "value": "Rua Inexistente"}
}
```

---

### `DELETE /api/v1/workspaces/{workspace_id}/crossroads/{crossroad_id}`

Delete a crossroad.

**Response 204** — deleted
**Response 404** — `not_found`
**Response 409** — `workspace_not_draft`

---

## 7. Restricted Areas

### `GET /api/v1/workspaces/{workspace_id}/restricted-areas`

List all restricted areas.

**Response 200**
```json
[
  {
    "id": 5,
    "workspace_id": 7,
    "name": "Playground",
    "polygon": [
      {"lat": -20.8106, "lng": -49.3758},
      {"lat": -20.8106, "lng": -49.3754},
      {"lat": -20.8108, "lng": -49.3754},
      {"lat": -20.8108, "lng": -49.3758}
    ],
    "restriction_type": "speed_limit",
    "speed_limit_kmh": 10,
    "active": true,
    "created_at": "2026-06-01T10:25:00+00:00",
    "updated_at": "2026-06-01T10:25:00+00:00"
  }
]
```

---

### `POST /api/v1/workspaces/{workspace_id}/restricted-areas`

Create a restricted area. Polygon must have at least 3 points.

**Request body**
```json
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
```

**Response 201** — created area
**Response 409** — `workspace_not_draft`
**Response 422** — `invalid_enum_value`, `missing_required_field`

---

### `PATCH /api/v1/workspaces/{workspace_id}/restricted-areas/{area_id}`

Update a restricted area.

**Response 200** — updated area
**Response 404** — `not_found`
**Response 409** — `workspace_not_draft`

---

### `DELETE /api/v1/workspaces/{workspace_id}/restricted-areas/{area_id}`

Delete a restricted area.

**Response 204** — deleted
**Response 404** — `not_found`
**Response 409** — `workspace_not_draft`

---

## 8. Map (Bulk Read)

### `GET /api/v1/workspaces/{workspace_id}/map`

Return the full workspace map in a single request.
Used by the frontend on initial load and after Publish to refresh the Leaflet map.

**Response 200**
```json
{
  "workspace_id": 7,
  "state": "draft",
  "roads": [...],
  "waypoints": [...],
  "crossroads": [...],
  "restricted_areas": [...]
}
```

Each sub-array uses the same format as the individual list endpoints.

---

### `GET /api/v1/versions/{version_id}/map`

Return the full map for a published Version.
Reads from `road_versions` and `entity_versions` tables.
Used for version history preview.

**Response 200** — same shape as workspace map above, but `state: "published"`
**Response 404** — `not_found`

---

## 9. Health

### `GET /api/v1/health`

System health check. Used by the frontend status bar.

**Response 200**
```json
{
  "status": "ok",
  "database": "ok",
  "version": "1.0.0"
}
```

**Response 503** (if database unreachable)
```json
{
  "status": "degraded",
  "database": "error",
  "version": "1.0.0"
}
```

---

## 10. Snap Preview

### `POST /api/v1/workspaces/{workspace_id}/snap`

Preview snap result for a coordinate without saving anything.
Used by the frontend to show snap indicator before the user confirms placement.

**Request body**
```json
{
  "lat": -20.81052,
  "lng": -49.37558
}
```

**Response 200**
```json
{
  "original": {"lat": -20.81052, "lng": -49.37558},
  "snapped_to": {"lat": -20.8105, "lng": -49.3756},
  "snapped": true,
  "distance_meters": 0.28
}
```

If no snap candidate within tolerance:
```json
{
  "original": {"lat": -20.81052, "lng": -49.37558},
  "snapped_to": {"lat": -20.81052, "lng": -49.37558},
  "snapped": false,
  "distance_meters": 0.0
}
```

---

## 11. Full Endpoint Summary

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/projects` | List all projects |
| `POST` | `/api/v1/projects` | Create project + first workspace |
| `GET` | `/api/v1/projects/{id}` | Get project |
| `PATCH` | `/api/v1/projects/{id}` | Update project |
| `GET` | `/api/v1/projects/{id}/versions` | List versions |
| `GET` | `/api/v1/projects/{id}/workspace` | Get active DRAFT workspace |
| `GET` | `/api/v1/projects/{id}/exports` | List exports |
| `GET` | `/api/v1/workspaces/{id}/map` | Full map (bulk read) |
| `POST` | `/api/v1/workspaces/{id}/validate` | Run validation |
| `GET` | `/api/v1/workspaces/{id}/validation` | Get cached validation results |
| `POST` | `/api/v1/workspaces/{id}/publish` | Publish → create Version |
| `POST` | `/api/v1/workspaces/{id}/snap` | Preview snap for coordinate |
| `GET` | `/api/v1/workspaces/{id}/roads` | List roads |
| `POST` | `/api/v1/workspaces/{id}/roads` | Create road |
| `GET` | `/api/v1/workspaces/{id}/roads/{id}` | Get road |
| `PATCH` | `/api/v1/workspaces/{id}/roads/{id}` | Update road |
| `DELETE` | `/api/v1/workspaces/{id}/roads/{id}` | Delete road |
| `GET` | `/api/v1/workspaces/{id}/waypoints` | List waypoints |
| `POST` | `/api/v1/workspaces/{id}/waypoints` | Create waypoint |
| `GET` | `/api/v1/workspaces/{id}/waypoints/{id}` | Get waypoint |
| `PATCH` | `/api/v1/workspaces/{id}/waypoints/{id}` | Update waypoint |
| `DELETE` | `/api/v1/workspaces/{id}/waypoints/{id}` | Delete waypoint |
| `GET` | `/api/v1/workspaces/{id}/crossroads` | List crossroads |
| `POST` | `/api/v1/workspaces/{id}/crossroads` | Create crossroad |
| `DELETE` | `/api/v1/workspaces/{id}/crossroads/{id}` | Delete crossroad |
| `GET` | `/api/v1/workspaces/{id}/restricted-areas` | List restricted areas |
| `POST` | `/api/v1/workspaces/{id}/restricted-areas` | Create restricted area |
| `PATCH` | `/api/v1/workspaces/{id}/restricted-areas/{id}` | Update restricted area |
| `DELETE` | `/api/v1/workspaces/{id}/restricted-areas/{id}` | Delete restricted area |
| `GET` | `/api/v1/versions/{id}/map` | Full map for a published version |
| `POST` | `/api/v1/versions/{id}/export` | Export version to Guardian JSON |
| `GET` | `/api/v1/versions/{id}/export/download` | Download export file |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/` | Serve Vue 3 SPA |
| `GET` | `/docs` | OpenAPI UI (FastAPI auto-generated) |
