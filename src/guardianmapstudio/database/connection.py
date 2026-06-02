from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from guardianmapstudio.config.settings import GuardianMapStudioSettings
from guardianmapstudio.database.models import Base


def get_engine(settings: GuardianMapStudioSettings) -> Engine:
    connect_args: dict[str, bool] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, connect_args=connect_args)


def create_tables(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
