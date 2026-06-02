# GuardianMapStudio — AI Mapping Architecture v1

## 1. Purpose

This document defines the AI-assisted map authoring architecture for MVP02+.
In MVP01, all map editing is manual. In MVP02, Guardian session recordings
are analyzed by a detection pipeline that suggests map entities for the
operator to review, accept, or reject.

> **⚠ MVP01 IMPLEMENTATION SCOPE: This entire document is MVP02+ planning.**
>
> **Nothing in this document should be implemented in MVP01.**
> No `CandidateEntity` table, no detection pipeline, no review workflow,
> no AI-related API endpoints. If Claude Code reads this document during
> MVP01 implementation, it must ignore all content and return to the
> Implementation Blueprint (doc 13).
>
> The database has exactly 11 tables in MVP01 — `candidate_entities` is
> NOT one of them. Adding it prematurely would break the `create_tables`
> test that asserts exactly 11 tables.

---

## 2. Core Concept: CandidateEntity *(MVP02+ only — does not exist in MVP01)*

A `CandidateEntity` is an AI-suggested map entity that has not yet been
reviewed by a human operator. It is distinct from a confirmed entity
(`Waypoint`, `Crossroad`, `RestrictedArea`).

```
Guardian session recording
        │
        ▼
  Detection Pipeline (AI)
        │
        ▼
  CandidateEntity (unreviewed)
        │
    ┌───┴───┐
    ▼       ▼
 Accept   Reject
    │
    ▼
Waypoint / Crossroad / Area (confirmed)
```

**Key rule**: A Workspace containing unreviewed CandidateEntities cannot be
Published. The operator must Accept or Reject every candidate before Publish.

---

## 3. Detection Pipeline (MVP02)

### 3.1 Input

A Guardian session recording directory:
```
sessions/session_20260601_143022/
├── front_camera.mp4
├── events.jsonl          ← contains ObjectDetectedEvent, GPSUpdateEvent
├── decisions.jsonl
└── metadata.json
```

### 3.2 Processing steps

```
1. Load front_camera.mp4 and events.jsonl
2. For each frame with GPS position:
   a. Run frame through entity detector (YOLO fine-tuned for map entities)
   b. Classes: stop_sign, speed_bump, gate
   c. Filter by confidence threshold (configurable, default: 0.75)
   d. Associate GPS position from events.jsonl (nearest by timestamp)
   e. Deduplicate: if candidate within 2m of existing candidate → skip
3. Cluster detections by GPS position (DBSCAN, eps=3m)
4. For each cluster centroid:
   a. Create CandidateEntity with:
      - suggested_type (stop_sign / speed_bump / gate)
      - position (GeoPoint — cluster centroid)
      - confidence (mean of cluster confidences)
      - frame_samples (list of frame numbers with detections)
      - source_session (session name)
5. Store CandidateEntities in workspace
6. Notify operator via UI
```

### 3.3 Output

A set of `CandidateEntity` records in the workspace, visible on the map
as dashed-outline markers with a distinct color (amber/orange).

---

## 4. CandidateEntity Data Model *(MVP02 only — NOT in MVP01 database)*

> **Do NOT create this table in MVP01.** The `candidate_entities` table is added
> in an MVP02 database migration. The MVP01 database has exactly 11 tables.

```python
@dataclass(frozen=True, slots=True)
class CandidateEntity:
    """AI-suggested entity awaiting operator review.

    Must not appear in Guardian export. Only confirmed entities are exported.
    """
    id: int
    workspace_id: int
    suggested_type: WaypointType       # stop_sign, speed_bump, gate
    position: GeoPoint
    confidence: float                  # 0.0–1.0
    frame_samples: list[int]           # frame numbers where detected
    source_session: str                # session name from Guardian
    created_at: datetime
    reviewed: bool = False
    accepted: bool = False
    # If accepted, the confirmed Waypoint id is stored here
    confirmed_waypoint_id: int | None = None
```

Database table: `candidate_entities` (added in MVP02 migration)

---

## 5. Review Workflow (MVP02)

### 5.1 UI behavior

Candidate markers appear on the Leaflet map with:
- Dashed outline circle (amber color `#ffaa00`)
- Emoji icon matching suggested type (same as confirmed waypoints)
- Confidence percentage shown in popup

Operator actions per candidate:
- **Accept**: candidate becomes a confirmed Waypoint with suggested type and position.
  Operator may edit name and extra_data before confirming.
- **Reject**: candidate is removed from map and marked as rejected in DB.
- **Ignore**: skip for now — candidate remains unreviewed.
  Publish is blocked while any unreviewed candidates exist.

### 5.2 Bulk actions

- "Accept all (confidence > 90%)" — accepts high-confidence candidates automatically
- "Reject all" — rejects all remaining unreviewed candidates

### 5.3 API endpoints *(MVP02 additions — NOT in MVP01)*

> **Do NOT implement these endpoints in MVP01.** They are added to the routers
> in MVP02 only, alongside the `candidate_entities` table migration.

```
GET    /api/v1/workspaces/{id}/candidates         → list all candidates
POST   /api/v1/workspaces/{id}/candidates/analyze → trigger detection on a session
POST   /api/v1/candidates/{id}/accept            → accept with optional edits
POST   /api/v1/candidates/{id}/reject            → reject
```

---

## 6. Future AI Modules (MVP03+)

### 6.1 Road network extraction

Analyze GPS trajectory from multiple Guardian sessions to suggest road layouts:
- Cluster GPS positions into road centerlines
- Suggest road start/end points
- Estimate road width from trajectory spread

### 6.2 Restricted area detection

Use object detection + GPS to identify zones where pedestrians appear frequently:
- Candidate restricted areas suggested as polygons
- Operator adjusts polygon vertices and sets restriction type

### 6.3 Map drift detection

Compare latest Guardian session trajectories with existing map:
- Alert operator when actual vehicle path deviates significantly from mapped roads
- Suggest map updates based on observed paths

### 6.4 Speed bump height estimation

Use stereo camera or depth estimation to measure speed bump height automatically,
pre-filling `extra_data.height_cm` for accepted candidates.

---

## 7. Integration with Existing Architecture

The AI pipeline is a background job, not a synchronous API call.
In MVP02, it runs as a separate process triggered by the operator:

```
Operator: "Analyze session X"
    │
    ▼
POST /api/v1/workspaces/{id}/candidates/analyze
    │ (returns job_id immediately)
    ▼
Background worker (subprocess or thread)
    │ runs detection pipeline (may take 2–10 minutes)
    ▼
CandidateEntities stored in DB
    │
    ▼
Frontend polls GET /api/v1/workspaces/{id}/candidates
    │ every 5 seconds until job_status == 'complete'
    ▼
Candidate markers appear on map
```

This design keeps the FastAPI request-response cycle fast and avoids
HTTP timeouts during long-running video analysis.

---

## 8. Model Training Notes

The entity detector for MVP02 requires a fine-tuned YOLOv8 model
trained on Brazilian condominium imagery. This is a separate project
from GuardianMapStudio itself.

Training data requirements:
- Minimum 500 labeled frames per class (stop_sign, speed_bump, gate)
- Images from front-facing camera at 1280×720 resolution
- Labels in YOLO format (class_id, cx, cy, w, h normalized)
- Validation set: 20% of data, held out strictly

Until a fine-tuned model is available, MVP02 uses the standard YOLOv8n
model (same as Guardian) for stop_sign and gate detection only.
Speed bump detection requires a custom model — not available in standard COCO.
