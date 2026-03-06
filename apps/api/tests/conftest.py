import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.config as _config_module

# Set FERNET_KEY before app import (CalendarService reads it at instantiation)
_config_module.settings.FERNET_KEY = Fernet.generate_key().decode()

from app.core.security import create_access_token, hash_password  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# --- Fake Redis ---
class FakeRedis:
    """Minimal in-memory Redis replacement for tests."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._sorted_sets: dict[str, dict[str, float]] = {}

    async def setex(self, key: str, ttl: int, value: str):
        self._store[key] = value

    async def exists(self, key: str) -> int:
        return 1 if key in self._store else 0

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def delete(self, *keys: str):
        for key in keys:
            self._store.pop(key, None)

    async def keys(self, pattern: str = "*") -> list[str]:
        if pattern == "*":
            return list(self._store.keys())
        # Simple glob: only support "prefix*" pattern
        prefix = pattern.rstrip("*")
        return [k for k in self._store if k.startswith(prefix)]

    def pipeline(self):
        return FakePipeline(self)

    async def aclose(self):
        pass


class FakePipeline:
    def __init__(self, redis: FakeRedis):
        self._redis = redis
        self._commands: list = []

    def zremrangebyscore(self, key, min_score, max_score):
        self._commands.append(("zremrangebyscore", key, min_score, max_score))
        return self

    def zadd(self, key, mapping):
        self._commands.append(("zadd", key, mapping))
        return self

    def zcard(self, key):
        self._commands.append(("zcard", key))
        return self

    def expire(self, key, ttl):
        self._commands.append(("expire", key, ttl))
        return self

    async def execute(self):
        results = []
        for cmd in self._commands:
            if cmd[0] == "zremrangebyscore":
                key = cmd[1]
                min_s, max_s = cmd[2], cmd[3]
                ss = self._redis._sorted_sets.get(key, {})
                to_del = [m for m, s in ss.items() if min_s <= s <= max_s]
                for m in to_del:
                    del ss[m]
                results.append(len(to_del))
            elif cmd[0] == "zadd":
                key = cmd[1]
                mapping = cmd[2]
                if key not in self._redis._sorted_sets:
                    self._redis._sorted_sets[key] = {}
                self._redis._sorted_sets[key].update(mapping)
                results.append(len(mapping))
            elif cmd[0] == "zcard":
                key = cmd[1]
                results.append(len(self._redis._sorted_sets.get(key, {})))
            elif cmd[0] == "expire":
                results.append(True)
        self._commands.clear()
        return results


fake_redis = FakeRedis()


@pytest.fixture(autouse=True)
def _reset_fake_redis():
    fake_redis._store.clear()
    fake_redis._sorted_sets.clear()


# Patch redis globally
import app.core.redis as redis_module  # noqa: E402

redis_module.redis_client = fake_redis


@pytest.fixture(autouse=True, scope="session")
async def _setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db():
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
async def _clean_tables(db: AsyncSession):
    """Truncate all tables between tests."""
    yield
    for table in reversed(Base.metadata.sorted_tables):
        await db.execute(table.delete())
    await db.commit()


async def _override_get_db():
    async with test_session_factory() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    """Create a standard test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    """Return Authorization headers for the test user."""
    token, _ = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}
