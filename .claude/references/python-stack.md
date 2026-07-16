# Python Stack Reference (load on demand)

> Detailed patterns and examples for the Python/FastAPI/SQLAlchemy stack.
> The non-negotiable house rules live in `.claude/CLAUDE.md`; this file is the
> long-form reference — read it when you need a concrete example, not every session.

## Type Hints

### Required mypy settings (pyproject.toml)
```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_any_generics = true
```

### Preferred patterns
```python
from typing import TypeVar, Generic, Protocol
from collections.abc import Sequence, Mapping, Callable
from dataclasses import dataclass

# Modern syntax (3.10+)
def process(items: list[str]) -> dict[str, int]: ...

# Union with | (3.10+)
def get_user(id: str) -> User | None: ...

# TypeVar for generics
T = TypeVar('T')
def first(items: Sequence[T]) -> T | None:
    return items[0] if items else None

# Protocol for structural typing
class Repository(Protocol[T]):
    def get(self, id: str) -> T | None: ...
    def save(self, entity: T) -> T: ...

# dataclasses for data structures
@dataclass(frozen=True)
class User:
    id: str
    email: str
    name: str

# TypedDict for dict structures
from typing import TypedDict
class UserDict(TypedDict):
    id: str
    email: str
    name: str
```

### Forbidden
```python
def process(data):        # ❌ untyped
def handle(x: Any) -> Any: # ❌ Any without justification
from typing import List, Dict, Optional  # ❌ use list, dict, X | None
```

## Code Style

### Naming
| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `user_service.py` |
| Classes | PascalCase | `UserService` |
| Functions | snake_case | `get_user_by_id` |
| Variables | snake_case | `is_active` |
| Constants | SCREAMING_SNAKE | `MAX_RETRIES` |
| Private | _leading_underscore | `_internal_method` |
| Type Vars | PascalCase | `T`, `UserT` |

### Import order (enforced by ruff)
```python
# 1. Standard library
import os
from collections.abc import Sequence
from dataclasses import dataclass
# 2. Third-party
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
# 3. Local
from .models import User
from .services import UserService
```

## Error Handling

```python
from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T
    @property
    def is_ok(self) -> bool: return True

@dataclass(frozen=True)
class Err(Generic[E]):
    error: E
    @property
    def is_ok(self) -> bool: return False

Result = Ok[T] | Err[E]

class AppError(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code

class ValidationError(AppError):
    def __init__(self, message: str, details: list[str]):
        super().__init__(message, "VALIDATION_ERROR")
        self.details = details

class NotFoundError(AppError):
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} not found: {id}", "NOT_FOUND")

async def get_user(user_id: str) -> Result[User, AppError]:
    try:
        user = await db.users.get(user_id)
        if user is None:
            return Err(NotFoundError("User", user_id))
        return Ok(user)
    except DatabaseError:
        logger.exception("Database error")
        return Err(AppError("Database error", "DB_ERROR"))
```

## Validation (Pydantic)

```python
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime

class CreateUserInput(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    age: int | None = Field(default=None, ge=0, le=150)

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    created_at: datetime
    model_config = {'from_attributes': True}  # ORM compatibility
```

## Async Patterns

### Preferred
```python
import asyncio, httpx
from contextlib import asynccontextmanager

# httpx for async HTTP, always with timeout
async def fetch_data(url: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

# gather for parallelism
async def fetch_all(urls: list[str]) -> list[dict]:
    return await asyncio.gather(*[fetch_data(u) for u in urls])

# TaskGroup (3.11+) for structured concurrency
async def process_items(items: list[Item]) -> None:
    async with asyncio.TaskGroup() as tg:
        for item in items:
            tg.create_task(process_item(item))

# Context manager for resources
@asynccontextmanager
async def get_db_session():
    session = await create_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

### Forbidden
```python
async def bad():
    import requests          # ❌ blocking in async
    return requests.get(url)
await client.get(url)        # ❌ no timeout
asyncio.create_task(risky()) # ❌ fire-and-forget, may silently fail
```

## Testing (pytest)

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_user_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get.return_value = None
    return repo

@pytest.fixture
def user_service(mock_user_repo: AsyncMock) -> UserService:
    return UserService(mock_user_repo)

# tests/unit/test_user_service.py
class TestUserService:
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_user_repo):
        input = CreateUserInput(email="test@example.com", name="Test")
        mock_user_repo.create.return_value = User(id="1", **input.model_dump())
        result = await user_service.create_user(input)
        assert result.is_ok
        assert result.value.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, user_service, mock_user_repo):
        mock_user_repo.create.side_effect = DuplicateError()
        result = await user_service.create_user(
            CreateUserInput(email="exists@example.com", name="Test"))
        assert not result.is_ok
        assert result.error.code == "DUPLICATE_EMAIL"

# parametrize for equivalence classes (2-3 representatives, not 20)
@pytest.mark.parametrize("email,expected", [
    ("valid@example.com", True),
    ("invalid", False),
    ("", False),
])
def test_email_validation(email: str, expected: bool):
    assert validate_email(email) == expected
```

> Test **value** policy (load-bearing only, ban list, budgets) is canonical in
> `.claude/rules/testing.md`. The examples above show *form*, not *how many*.

## Common Commands

```bash
# Dev (uv)
uv run python -m package_name
uv run uvicorn app.main:app --reload

# Test
uv run pytest              # all
uv run pytest -v           # verbose
uv run pytest --cov        # coverage
uv run pytest -k "name"    # specific

# Quality
uv run ruff check .        # lint
uv run ruff check . --fix  # auto-fix
uv run ruff format .       # format
uv run mypy .              # type check

# Deps
uv add package
uv add --dev pytest
uv sync
```

> Project-specific test invocation (dev Docker, `-o asyncio_mode=auto`, `--noconftest`)
> is recorded in auto-memory `dev_test_infra_blockers.md` — defer to it over the generic commands above.

## Framework-Specific

### FastAPI
```python
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="My API")

async def get_user_service(repo: UserRepository = Depends(get_user_repo)) -> UserService:
    return UserService(repo)

@app.post("/users", response_model=User, status_code=201)
async def create_user(input: CreateUserInput,
                      service: UserService = Depends(get_user_service)) -> User:
    result = await service.create_user(input)
    if not result.is_ok:
        raise HTTPException(status_code=400, detail=result.error.message)
    return result.value

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=400, content={"error": exc.code, "message": str(exc)})
```

### SQLAlchemy (async)
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    async def get(self, id: str) -> UserModel | None:
        return await self.session.get(UserModel, id)
    async def create(self, user: UserModel) -> UserModel:
        self.session.add(user)
        await self.session.flush()
        return user
```

> Project relationships default to `lazy="raise"` — eager-load explicitly with
> `selectinload()`/`joinedload()` at the repository. See [[evaluation]] for the
> production bug this prevents.
