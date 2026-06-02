from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from guardianmapstudio.database.models import (
    CrossroadModel,
    ExportHistoryModel,
    ProjectModel,
    RestrictedAreaModel,
    RoadModel,
    ValidationResultModel,
    VersionModel,
    WaypointModel,
    WorkspaceModel,
)
from guardianmapstudio.domain.contracts import (
    Crossroad,
    ExportRecord,
    GeoPoint,
    Project,
    RestrictedArea,
    RestrictionType,
    Road,
    RoadDirection,
    ValidationResult,
    ValidationSeverity,
    Version,
    Waypoint,
    WaypointType,
    Workspace,
    WorkspaceState,
)

# ---------------------------------------------------------------------------
# ProjectRepository
# ---------------------------------------------------------------------------


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, name: str, description: str = "") -> Project:
        model = ProjectModel(name=name, description=description)
        self._db.add(model)
        self._db.flush()
        # BR-01: every Project gets an initial DRAFT workspace
        ws = WorkspaceModel(project_id=model.id, state="draft")
        self._db.add(ws)
        self._db.commit()
        self._db.refresh(model)
        return self._to_domain(model)

    def get_by_id(self, project_id: int) -> Project | None:
        model = self._db.get(ProjectModel, project_id)
        return self._to_domain(model) if model else None

    def get_all(self) -> list[Project]:
        rows = self._db.execute(select(ProjectModel)).scalars().all()
        return [self._to_domain(r) for r in rows]

    def update(self, project_id: int, name: str, description: str) -> Project | None:
        model = self._db.get(ProjectModel, project_id)
        if model is None:
            return None
        model.name = name
        model.description = description
        self._db.commit()
        self._db.refresh(model)
        return self._to_domain(model)

    def delete(self, project_id: int) -> bool:
        model = self._db.get(ProjectModel, project_id)
        if model is None:
            return False
        self._db.delete(model)
        self._db.commit()
        return True

    @staticmethod
    def _to_domain(model: ProjectModel) -> Project:
        return Project(
            id=model.id,
            name=model.name,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


# ---------------------------------------------------------------------------
# VersionRepository
# ---------------------------------------------------------------------------


class VersionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        project_id: int,
        name: str,
        road_count: int,
        waypoint_count: int,
        crossroad_count: int,
        restricted_area_count: int,
    ) -> Version:
        number = self.next_version_number(project_id)
        model = VersionModel(
            project_id=project_id,
            version_number=number,
            name=name,
            published_at=datetime.now(UTC),
            road_count=road_count,
            waypoint_count=waypoint_count,
            crossroad_count=crossroad_count,
            restricted_area_count=restricted_area_count,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._to_domain(model)

    def get_by_id(self, version_id: int) -> Version | None:
        model = self._db.get(VersionModel, version_id)
        return self._to_domain(model) if model else None

    def get_all_for_project(self, project_id: int) -> list[Version]:
        rows = (
            self._db.execute(
                select(VersionModel)
                .where(VersionModel.project_id == project_id)
                .order_by(VersionModel.version_number)
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]

    def get_latest_for_project(self, project_id: int) -> Version | None:
        row = (
            self._db.execute(
                select(VersionModel)
                .where(VersionModel.project_id == project_id)
                .order_by(VersionModel.version_number.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        return self._to_domain(row) if row else None

    def next_version_number(self, project_id: int) -> int:
        latest = self.get_latest_for_project(project_id)
        return (latest.version_number + 1) if latest else 1

    @staticmethod
    def _to_domain(model: VersionModel) -> Version:
        return Version(
            id=model.id,
            project_id=model.project_id,
            version_number=model.version_number,
            name=model.name,
            published_at=model.published_at,
            road_count=model.road_count,
            waypoint_count=model.waypoint_count,
            crossroad_count=model.crossroad_count,
            restricted_area_count=model.restricted_area_count,
        )


# ---------------------------------------------------------------------------
# WorkspaceRepository
# ---------------------------------------------------------------------------


class WorkspaceRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, project_id: int, base_version_id: int | None = None) -> Workspace:
        model = WorkspaceModel(
            project_id=project_id,
            state="draft",
            base_version_id=base_version_id,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._to_domain(model)

    def get_by_id(self, workspace_id: int) -> Workspace | None:
        model = self._db.get(WorkspaceModel, workspace_id)
        return self._to_domain(model) if model else None

    def get_active_draft(self, project_id: int) -> Workspace | None:
        row = (
            self._db.execute(
                select(WorkspaceModel)
                .where(
                    WorkspaceModel.project_id == project_id,
                    WorkspaceModel.state == "draft",
                )
                .limit(1)
            )
            .scalars()
            .first()
        )
        return self._to_domain(row) if row else None

    def set_published(self, workspace_id: int) -> Workspace | None:
        model = self._db.get(WorkspaceModel, workspace_id)
        if model is None:
            return None
        model.state = "published"
        self._db.commit()
        self._db.refresh(model)
        return self._to_domain(model)

    def update_validation_state(
        self, workspace_id: int, has_errors: bool, validated_at: datetime
    ) -> None:
        model = self._db.get(WorkspaceModel, workspace_id)
        if model is not None:
            model.has_validation_errors = has_errors
            model.last_validated_at = validated_at
            self._db.commit()

    @staticmethod
    def _to_domain(model: WorkspaceModel) -> Workspace:
        return Workspace(
            id=model.id,
            project_id=model.project_id,
            state=WorkspaceState(model.state),
            base_version_id=model.base_version_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_validated_at=model.last_validated_at,
            has_validation_errors=model.has_validation_errors,
        )


# ---------------------------------------------------------------------------
# MapRepository
# ---------------------------------------------------------------------------


class MapRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # ------ Roads ------

    def create_road(
        self,
        workspace_id: int,
        name: str,
        coordinates_json: str,
        speed_limit_kmh: int,
        direction: str,
        width_meters: float,
    ) -> Road:
        model = RoadModel(
            workspace_id=workspace_id,
            name=name,
            coordinates=coordinates_json,
            speed_limit_kmh=speed_limit_kmh,
            direction=direction,
            width_meters=width_meters,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._road_to_domain(model)

    def get_road(self, road_id: int) -> Road | None:
        model = self._db.get(RoadModel, road_id)
        return self._road_to_domain(model) if model else None

    def get_roads(self, workspace_id: int) -> list[Road]:
        rows = (
            self._db.execute(
                select(RoadModel).where(RoadModel.workspace_id == workspace_id)
            )
            .scalars()
            .all()
        )
        return [self._road_to_domain(r) for r in rows]

    def update_road(self, road_id: int, **kwargs: Any) -> Road | None:
        model = self._db.get(RoadModel, road_id)
        if model is None:
            return None
        for key, value in kwargs.items():
            setattr(model, key, value)
        self._db.commit()
        self._db.refresh(model)
        return self._road_to_domain(model)

    def delete_road(self, road_id: int) -> bool:
        model = self._db.get(RoadModel, road_id)
        if model is None:
            return False
        self._db.delete(model)
        self._db.commit()
        return True

    # ------ Waypoints ------

    def create_waypoint(
        self,
        workspace_id: int,
        name: str,
        waypoint_type: str,
        latitude: float,
        longitude: float,
        road_name: str | None,
        heading_degrees: float | None,
        extra_data_json: str,
    ) -> Waypoint:
        model = WaypointModel(
            workspace_id=workspace_id,
            name=name,
            waypoint_type=waypoint_type,
            latitude=latitude,
            longitude=longitude,
            road_name=road_name,
            heading_degrees=heading_degrees,
            extra_data=extra_data_json,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._waypoint_to_domain(model)

    def get_waypoint(self, waypoint_id: int) -> Waypoint | None:
        model = self._db.get(WaypointModel, waypoint_id)
        return self._waypoint_to_domain(model) if model else None

    def get_waypoints(self, workspace_id: int) -> list[Waypoint]:
        rows = (
            self._db.execute(
                select(WaypointModel).where(WaypointModel.workspace_id == workspace_id)
            )
            .scalars()
            .all()
        )
        return [self._waypoint_to_domain(r) for r in rows]

    def update_waypoint(self, waypoint_id: int, **kwargs: Any) -> Waypoint | None:
        model = self._db.get(WaypointModel, waypoint_id)
        if model is None:
            return None
        for key, value in kwargs.items():
            setattr(model, key, value)
        self._db.commit()
        self._db.refresh(model)
        return self._waypoint_to_domain(model)

    def delete_waypoint(self, waypoint_id: int) -> bool:
        model = self._db.get(WaypointModel, waypoint_id)
        if model is None:
            return False
        self._db.delete(model)
        self._db.commit()
        return True

    # ------ Crossroads ------

    def create_crossroad(
        self,
        workspace_id: int,
        road_a_name: str,
        road_b_name: str,
        latitude: float,
        longitude: float,
    ) -> Crossroad:
        model = CrossroadModel(
            workspace_id=workspace_id,
            road_a_name=road_a_name,
            road_b_name=road_b_name,
            latitude=latitude,
            longitude=longitude,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._crossroad_to_domain(model)

    def get_crossroad(self, crossroad_id: int) -> Crossroad | None:
        model = self._db.get(CrossroadModel, crossroad_id)
        return self._crossroad_to_domain(model) if model else None

    def get_crossroads(self, workspace_id: int) -> list[Crossroad]:
        rows = (
            self._db.execute(
                select(CrossroadModel).where(CrossroadModel.workspace_id == workspace_id)
            )
            .scalars()
            .all()
        )
        return [self._crossroad_to_domain(r) for r in rows]

    def delete_crossroad(self, crossroad_id: int) -> bool:
        model = self._db.get(CrossroadModel, crossroad_id)
        if model is None:
            return False
        self._db.delete(model)
        self._db.commit()
        return True

    # ------ Restricted Areas ------

    def create_area(
        self,
        workspace_id: int,
        name: str,
        polygon_json: str,
        restriction_type: str,
        speed_limit_kmh: int | None,
    ) -> RestrictedArea:
        model = RestrictedAreaModel(
            workspace_id=workspace_id,
            name=name,
            polygon=polygon_json,
            restriction_type=restriction_type,
            speed_limit_kmh=speed_limit_kmh,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._area_to_domain(model)

    def get_area(self, area_id: int) -> RestrictedArea | None:
        model = self._db.get(RestrictedAreaModel, area_id)
        return self._area_to_domain(model) if model else None

    def get_areas(self, workspace_id: int) -> list[RestrictedArea]:
        rows = (
            self._db.execute(
                select(RestrictedAreaModel).where(
                    RestrictedAreaModel.workspace_id == workspace_id
                )
            )
            .scalars()
            .all()
        )
        return [self._area_to_domain(r) for r in rows]

    def update_area(self, area_id: int, **kwargs: Any) -> RestrictedArea | None:
        model = self._db.get(RestrictedAreaModel, area_id)
        if model is None:
            return None
        for key, value in kwargs.items():
            setattr(model, key, value)
        self._db.commit()
        self._db.refresh(model)
        return self._area_to_domain(model)

    def delete_area(self, area_id: int) -> bool:
        model = self._db.get(RestrictedAreaModel, area_id)
        if model is None:
            return False
        self._db.delete(model)
        self._db.commit()
        return True

    # ------ Conversion helpers ------

    @staticmethod
    def _road_to_domain(model: RoadModel) -> Road:
        raw_coords = json.loads(model.coordinates)
        return Road(
            id=model.id,
            workspace_id=model.workspace_id,
            name=model.name,
            coordinates=[
                GeoPoint(latitude=p["lat"], longitude=p["lng"]) for p in raw_coords
            ],
            speed_limit_kmh=model.speed_limit_kmh,
            direction=RoadDirection(model.direction),
            width_meters=model.width_meters,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _waypoint_to_domain(model: WaypointModel) -> Waypoint:
        extra: dict[str, Any] = json.loads(model.extra_data)
        return Waypoint(
            id=model.id,
            workspace_id=model.workspace_id,
            name=model.name,
            waypoint_type=WaypointType(model.waypoint_type),
            position=GeoPoint(latitude=model.latitude, longitude=model.longitude),
            road_name=model.road_name,
            heading_degrees=model.heading_degrees,
            extra_data=extra,
            created_at=model.created_at,
            updated_at=model.updated_at,
            active=model.active,
        )

    @staticmethod
    def _crossroad_to_domain(model: CrossroadModel) -> Crossroad:
        return Crossroad(
            id=model.id,
            workspace_id=model.workspace_id,
            road_a_name=model.road_a_name,
            road_b_name=model.road_b_name,
            position=GeoPoint(latitude=model.latitude, longitude=model.longitude),
            created_at=model.created_at,
        )

    @staticmethod
    def _area_to_domain(model: RestrictedAreaModel) -> RestrictedArea:
        raw_poly = json.loads(model.polygon)
        return RestrictedArea(
            id=model.id,
            workspace_id=model.workspace_id,
            name=model.name,
            polygon=[
                GeoPoint(latitude=p["lat"], longitude=p["lng"]) for p in raw_poly
            ],
            restriction_type=RestrictionType(model.restriction_type),
            speed_limit_kmh=model.speed_limit_kmh,
            created_at=model.created_at,
            updated_at=model.updated_at,
            active=model.active,
        )


# ---------------------------------------------------------------------------
# ValidationRepository
# ---------------------------------------------------------------------------


class ValidationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def replace_results(self, workspace_id: int, results: list[ValidationResult]) -> None:
        self._db.execute(
            delete(ValidationResultModel).where(
                ValidationResultModel.workspace_id == workspace_id
            )
        )
        for r in results:
            model = ValidationResultModel(
                workspace_id=workspace_id,
                severity=r.severity.value,
                rule_id=r.rule_id,
                message=r.message,
                affected_entity_type=r.affected_entity_type,
                affected_entity_id=r.affected_entity_id,
            )
            self._db.add(model)
        self._db.commit()

    def get_results(self, workspace_id: int) -> list[ValidationResult]:
        rows = (
            self._db.execute(
                select(ValidationResultModel).where(
                    ValidationResultModel.workspace_id == workspace_id
                )
            )
            .scalars()
            .all()
        )
        return [
            ValidationResult(
                severity=ValidationSeverity(r.severity),
                rule_id=r.rule_id,
                message=r.message,
                affected_entity_type=r.affected_entity_type,
                affected_entity_id=r.affected_entity_id,
            )
            for r in rows
        ]

    def count_errors(self, workspace_id: int) -> int:
        rows = (
            self._db.execute(
                select(ValidationResultModel).where(
                    ValidationResultModel.workspace_id == workspace_id,
                    ValidationResultModel.severity == "error",
                )
            )
            .scalars()
            .all()
        )
        return len(rows)


# ---------------------------------------------------------------------------
# ExportRepository
# ---------------------------------------------------------------------------


class ExportRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_record(
        self,
        version_id: int,
        project_id: int,
        file_path: str,
        file_size_bytes: int,
    ) -> ExportRecord:
        model = ExportHistoryModel(
            version_id=version_id,
            project_id=project_id,
            exported_at=datetime.now(UTC),
            file_path=file_path,
            file_size_bytes=file_size_bytes,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._to_domain(model)

    def get_history(self, project_id: int) -> list[ExportRecord]:
        rows = (
            self._db.execute(
                select(ExportHistoryModel).where(
                    ExportHistoryModel.project_id == project_id
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]

    @staticmethod
    def _to_domain(model: ExportHistoryModel) -> ExportRecord:
        return ExportRecord(
            id=model.id,
            version_id=model.version_id,
            project_id=model.project_id,
            exported_at=model.exported_at,
            file_path=model.file_path,
            file_size_bytes=model.file_size_bytes,
        )
