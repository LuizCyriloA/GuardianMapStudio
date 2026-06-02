from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

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
