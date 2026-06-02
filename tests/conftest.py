from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
# STAGE 2: db_engine and db_session fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_engine(settings: GuardianMapStudioSettings):  # type: ignore[no-untyped-def]
    from guardianmapstudio.database.models import Base
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):  # type: ignore[no-untyped-def]
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    with factory() as session:
        yield session


# ---------------------------------------------------------------------------
# STAGE 4: client fixture for integration API tests
# ---------------------------------------------------------------------------


@pytest.fixture
def client(settings: GuardianMapStudioSettings, db_engine):  # type: ignore[no-untyped-def]
    from guardianmapstudio.api.deps import get_db
    from guardianmapstudio.main import create_app
    app = create_app(settings)
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    with TestClient(app) as c:
        def override_get_db():  # type: ignore[no-untyped-def]
            with factory() as session:
                yield session
        app.dependency_overrides[get_db] = override_get_db
        yield c
    app.dependency_overrides.clear()
