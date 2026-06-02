from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    versions: Mapped[list[VersionModel]] = relationship(back_populates="project")
    workspaces: Mapped[list[WorkspaceModel]] = relationship(back_populates="project")


class VersionModel(Base):
    __tablename__ = "versions"
    __table_args__ = (
        UniqueConstraint("project_id", "version_number", name="uq_versions_project_number"),
        Index("ix_versions_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    road_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    waypoint_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    crossroad_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    restricted_area_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    project: Mapped[ProjectModel] = relationship(back_populates="versions")
    road_versions: Mapped[list[RoadVersionModel]] = relationship(back_populates="version")
    entity_versions: Mapped[list[EntityVersionModel]] = relationship(
        back_populates="version"
    )


class WorkspaceModel(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("state IN ('draft', 'published')", name="ck_workspaces_state"),
        Index("ix_workspaces_project_id", "project_id"),
        Index("ix_workspaces_state", "state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    base_version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("versions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )
    last_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    has_validation_errors: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    project: Mapped[ProjectModel] = relationship(back_populates="workspaces")
    roads: Mapped[list[RoadModel]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    waypoints: Mapped[list[WaypointModel]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    crossroads: Mapped[list[CrossroadModel]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    areas: Mapped[list[RestrictedAreaModel]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    validation_results: Mapped[list[ValidationResultModel]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )


class ExportHistoryModel(Base):
    __tablename__ = "export_history"
    __table_args__ = (
        Index("ix_export_history_version_id", "version_id"),
        Index("ix_export_history_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("versions.id"), nullable=False
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False
    )
    exported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ValidationResultModel(Base):
    __tablename__ = "validation_results"
    __table_args__ = (
        CheckConstraint("severity IN ('error', 'warning')", name="ck_validation_severity"),
        Index("ix_validation_results_workspace_id", "workspace_id"),
        Index("ix_validation_results_severity", "workspace_id", "severity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id"), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    affected_entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    affected_entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    coordinates: Mapped[str] = mapped_column(Text, nullable=False)
    speed_limit_kmh: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), default="two_way", nullable=False)
    width_meters: Mapped[float] = mapped_column(Float, default=6.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="roads")


class WaypointModel(Base):
    __tablename__ = "waypoints"
    __table_args__ = (
        CheckConstraint(
            "waypoint_type IN "
            "('stop_sign','speed_bump','gate','landmark','curve','crossroad','stop_zone')",
            name="ck_waypoints_type",
        ),
        CheckConstraint(
            "heading_degrees IS NULL OR (heading_degrees >= 0 AND heading_degrees <= 360)",
            name="ck_waypoints_heading",
        ),
        Index("ix_waypoints_workspace_id", "workspace_id"),
        Index(
            "ix_waypoints_workspace_type_active",
            "workspace_id",
            "waypoint_type",
            "active",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    waypoint_type: Mapped[str] = mapped_column(String(30), nullable=False)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    road_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    heading_degrees: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra_data: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="waypoints")


class CrossroadModel(Base):
    __tablename__ = "crossroads"
    __table_args__ = (
        CheckConstraint("road_a_name != road_b_name", name="ck_crossroads_distinct_roads"),
        Index("ix_crossroads_workspace_id", "workspace_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id"), nullable=False
    )
    road_a_name: Mapped[str] = mapped_column(String(200), nullable=False)
    road_b_name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    polygon: Mapped[str] = mapped_column(Text, nullable=False)
    restriction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    speed_limit_kmh: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="areas")


class RoadVersionModel(Base):
    __tablename__ = "road_versions"
    __table_args__ = (Index("ix_road_versions_version_id", "version_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("versions.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    coordinates: Mapped[str] = mapped_column(Text, nullable=False)
    speed_limit_kmh: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    width_meters: Mapped[float] = mapped_column(Float, nullable=False)

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("versions.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)

    version: Mapped[VersionModel] = relationship(back_populates="entity_versions")
