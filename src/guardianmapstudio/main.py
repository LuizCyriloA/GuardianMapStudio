from __future__ import annotations

import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

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

    from guardianmapstudio.api.routers import (  # noqa: PLC0415
        crossroads,
        export,
        osm_import,
        projects,
        restricted_areas,
        roads,
        validation,
        waypoints,
        workspaces,
    )

    app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
    app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["workspaces"])
    app.include_router(roads.router, prefix="/api/v1/workspaces", tags=["roads"])
    app.include_router(waypoints.router, prefix="/api/v1/workspaces", tags=["waypoints"])
    app.include_router(crossroads.router, prefix="/api/v1/workspaces", tags=["crossroads"])
    app.include_router(restricted_areas.router, prefix="/api/v1/workspaces", tags=["areas"])
    app.include_router(validation.router, prefix="/api/v1/workspaces", tags=["validation"])
    app.include_router(export.router, prefix="/api/v1", tags=["export"])
    app.include_router(osm_import.router, prefix="/api/v1/workspaces", tags=["osm_import"])

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
