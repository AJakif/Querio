<!-- written-by: writer-haiku | model: haiku -->
# Database Seeding Workflow

## Overview

This workflow provides procedures for seeding platform feature gates. The old TechVenture demo dataset is no longer created by the default seed command.

## Seed Data What Gets Created

The default seeding workflow only upserts platform feature gates. It does not create demo organizations, users, jobs, candidates, transcripts, evaluations, rankings, or feedback records.

## Test User Credentials

The default seed does not create login users. Provision a real admin or use the dedicated super-admin seed workflow when an account is needed.

## Workflows

### Workflow 1: Local Development Setup

**Purpose**: Initialize a fresh local development database with seed data.

**Prerequisites**:
- Docker and Docker Compose installed
- Python 3.11+ and virtual environment configured
- `.env` file configured with database credentials

**Steps**:

1. **Start containers** (PostgreSQL, Redis, Chroma, MinIO)
   ```bash
   docker-compose up -d
   ```
   Wait for health checks to pass (~10-15 seconds).

2. **Run database migrations**
   ```bash
   python -m alembic upgrade head
   ```
   Creates schema and applies all pending migrations.

3. **Seed database** (via CLI)
   ```bash
   python run_seed.py
   ```
   Or programmatically:
   ```bash
   python -m alembic.seed_data
   ```

4. **Verify seed data**
   - Check stdout for confirmation of created entities
   - Login to UI with test credentials
   - Query database to validate record counts

**Cleanup**: Delete seed data without stopping containers
   ```bash
   python run_seed.py --delete
   ```

---

### Workflow 2: Docker Containerized Seeding (Development)

**Purpose**: Seed database within Docker environment during local development.

**Prerequisites**:
- Docker Compose stack running
- Services healthy before seeding

**Steps**:

1. **Verify containers are healthy**
   ```bash
   docker-compose ps
   ```
   All services should show health status "healthy" or "running".

2. **Execute seed via container**
   ```bash
   docker-compose exec api python run_seed.py
   ```

3. **Monitor output**
   The command streams stdout/stderr showing:
   - Organizations created: `[ok] Created 1 organizations`
   - Roles: `[ok] Created 5 roles with permissions`
   - Users: `[ok] Created 4 users`
   - Jobs created: `[ok] Created 6 jobs`
   - Candidates created: `[ok] Created 27 candidates`
   - And counts for all entities

4. **Verify from another container**
   ```bash
   docker-compose exec postgres psql -U postgres -d interview_eval -c \
     "SELECT COUNT(*) FROM organizations;"
   ```

---

### Workflow 3: Test Environment Seeding (CI/CD)

**Purpose**: Automated seeding during test or staging deployment pipelines.

**Prerequisites**:
- Migrations applied successfully
- Database ready for data
- Environment variables set

**Implementation**:

1. **In deployment script** (e.g., `deploy.sh`):
   ```bash
   # Apply migrations
   echo "Running migrations..."
   python -m alembic upgrade head

   # Seed database
   echo "Seeding database..."
   python -m alembic.seed_data
   echo "Seed data loaded successfully"
   ```

2. **In GitHub Actions/CI workflow**:
   ```yaml
   - name: Seed Database
     run: |
       source .venv/bin/activate
       python -m alembic upgrade head
       python run_seed.py
   ```

3. **Validation in pipeline**:
   ```bash
   # Verify seed data exists
   python -c "
   from app.config import get_settings
   from app.services.seed_service import ORG_TECHVENTURE_ID
   from sqlalchemy.ext.asyncio import create_async_engine
   import asyncio

   async def check():
       engine = create_async_engine(get_settings().database_url)
       async with engine.begin() as conn:
           result = await conn.execute(
               'SELECT COUNT(*) FROM organizations'
           )
           assert result.scalar() >= 1
   asyncio.run(check())
   "
   ```

---

### Workflow 4: Clean Database State (Reset)

**Purpose**: Remove all seed data and return to clean state for re-seeding.

**Steps**:

1. **CLI cleanup** (preserves schema)
   ```bash
   python run_seed.py --delete
   ```
   Removes all seed organizations, users, jobs, candidates, transcripts, evaluations, etc.

2. **Full reset** (destroys schema)
   ```bash
   # Downgrade to no migrations
   python -m alembic downgrade base
   # Re-apply all migrations
   python -m alembic upgrade head
   # Seed fresh
   python run_seed.py
   ```

3. **Docker full reset**
   ```bash
   docker-compose down -v  # Remove volumes
   docker-compose up -d    # Fresh containers
   # Then run migration + seed workflows
   ```

---

### Workflow 5: API-Based Seeding (Runtime)

**Purpose**: Seed database via HTTP API for testing or demo scenarios.

**Prerequisites**:
- API running and accessible
- User authenticated with admin role

**Steps**:

1. **Admin login** (get auth token)
   ```bash
   curl -X POST http://localhost:8100/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "email": "admin@example.com",
       "password": "admin_password"
     }'
   # Response includes access_token
   ```

2. **Trigger seed endpoint**
   ```bash
   curl -X POST http://localhost:8100/api/v1/admin/seed \
     -H "Authorization: Bearer ${ACCESS_TOKEN}" \
     -H "Content-Type: application/json"
   ```

3. **Response contains counts**:
   ```json
   {
     "message": "Seed data created successfully",
     "organizations_created": 1,
     "roles_created": 5,
     "users_created": 4,
     "jobs_created": 6,
     "candidates_created": 25,
     "transcripts_created": 25,
     "evaluations_created": 21,
     "human_reviews_created": 6,
     "comparison_runs_created": 36,
     "rankings_created": 6,
     "feedback_records_created": 64
   }
   ```

4. **Delete via API**
   ```bash
   curl -X DELETE http://localhost:8100/api/v1/admin/seed \
     -H "Authorization: Bearer ${ACCESS_TOKEN}"
   ```

---

### Workflow 6: Partial/Custom Seeding

**Purpose**: Seed only specific entity types for targeted testing.

**Implementation**: Modify `SeedService` usage in custom scripts

1. **Create custom seed script** (`scripts/custom_seed.py`):
   ```python
   import asyncio
   from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
   from sqlalchemy.orm import sessionmaker
   from app.config import get_settings
   from app.services.seed_service import SeedService

   async def seed_specific():
       settings = get_settings()
       engine = create_async_engine(settings.database_url)
       async_session = sessionmaker(engine, class_=AsyncSession)

       async with async_session() as session:
           seed_service = SeedService(session)
           
           # Only seed platform feature gates
           await seed_service.seed_platform_feature_gates()
           
           print("Partial seed complete")

   asyncio.run(seed_specific())
   ```

2. **Run custom seed**:
   ```bash
   python scripts/custom_seed.py
   ```

---

## Seed Data Architecture

### Data Dependencies

Seeding follows strict order to satisfy foreign keys:

```
Organizations
    ↓
Roles → Users → API Keys
    ↓
Jobs
    ↓
Candidates → Transcripts
    ↓
Evaluations
    ↓
Comparisons → Rankings
    ↓
Feedback
```

Each level depends on previous levels. The `SeedService` maintains this order automatically.

### Deterministic UUIDs

All IDs are generated deterministically from string seeds, ensuring:
- **Idempotency**: Running seed multiple times produces identical IDs
- **Predictability**: IDs known in advance for testing
- **No duplicates**: Same seed always produces same UUID

Example:
```python
candidate_id = deterministic_uuid(f"candidate-{job_id}-1")
# Always produces same UUID for same input
```

### Reference IDs

The default seed no longer creates reference job or candidate IDs.

---

## Troubleshooting

### Issue: "Database connection failed"

**Cause**: PostgreSQL not ready or credentials wrong

**Solution**:
```bash
# Check container status
docker-compose ps
# Wait for postgres health check
docker-compose logs postgres
# Verify credentials in .env
```

### Issue: "Constraint violation: duplicate key"

**Cause**: Seed data already exists from previous run

**Solution**:
```bash
# Option 1: Clean and re-seed
python run_seed.py --delete
python run_seed.py

# Option 2: Full database reset
docker-compose down -v
docker-compose up -d
python -m alembic upgrade head
python run_seed.py
```

### Issue: "Migration not applied"

**Cause**: Alembic stamp or version mismatch

**Solution**:
```bash
# Check migration status
python -m alembic current
python -m alembic history

# Manually reset to base (careful!)
python -m alembic downgrade base
python -m alembic upgrade head
```

### Issue: "Transaction timeout during seed"

**Cause**: Large seed operations, slow DB, or network latency

**Solution**:
```bash
# Increase statement timeout in PostgreSQL
# Or upgrade to faster hardware/network
# Or use partial seeding (Workflow 6)
```

---

## Performance Considerations

- **Full seed duration**: 30-120 seconds depending on system
- **Database size**: ~500MB after full seed
- **Network latency**: Significant impact in remote DB scenarios

**Optimization tips**:
- Use local PostgreSQL for development
- Run migrations + seed in parallel containers
- Consider partial seeding for UI-only testing
- Use pgBouncer for connection pooling

---

## Use Cases

| Scenario | Recommended Workflow | Notes |
|---|---|---|
| Local dev setup | Workflow 1 | Start fresh each day |
| Docker dev environment | Workflow 2 | In-container seeding |
| CI/CD pipeline | Workflow 3 | Automated, validated |
| Testing clean state | Workflow 4 | Between test runs |
| Demo/live scenario | Workflow 5 | Via API, runtime |
| Testing specific features | Workflow 6 | Partial seed for speed |
| Load testing | Workflow 1 + script | Can customize volumes |

---

## Implementation Notes

### SeedService Class

Located in [app/services/seed_service.py](app/services/seed_service.py)

**Public Methods**:
- `seed_platform_feature_gates() → int`: Upserts platform feature gates
- `cleanup_seed_data() → None`: Removes old TechVenture demo seed data

### Configuration

All seed data is defined as constants in `seed_service.py`:
- `SEED_JOBS_DATA`: 6 job definitions (5 active, 1 draft) with titles, descriptions, skills
- `CANDIDATES_BY_JOB`: 27 deterministic candidates across 6 jobs (4–5 per job)
- Organization/User/Role IDs: Fixed UUIDs for consistency
- Password hashes: Uses bcrypt

---

## Security Considerations

⚠️ **Important**: Seed credentials and data are for **development/test only**

- **Never run in production** without explicit review
- Seed credentials have simple, known passwords
- Seed data does not respect data classification or PII policies
- API endpoint requires admin role (protected)
- Always use separate test/prod databases

---

## See Also

- [SeedService Implementation](app/services/seed_service.py)
- [API Seed Endpoint](app/api/v1/admin/seed_data.py)
- [Alembic Migrations](alembic/versions/)
- [Development Setup](development-setup.md)
