# SQLAlchemy Storage Manager

This project uses SQLAlchemy as the database ORM for managing all persistent data.

## Overview

The storage system consists of:
- **SQLAlchemy Base** (`app/db/base.py`) - Declarative base class
- **SQLAlchemy Models** (`app/db/models.py`) - Database table definitions
- **StorageManager** (`app/plugins/storage.py`) - Complete storage solution including:
  - Database engine and session management
  - Connection pooling
  - High-level CRUD operations
  - Database provisioning
- **Alembic Migrations** (`alembic/`) - Database schema versioning

## Database Models

### Core Tables

1. **LogEntry** - DID log entries
   - Primary key: `scid`
   - Fields: did, domain, namespace, identifier, logs, deactivated
   - Indexes: did, domain, namespace, identifier

2. **Resource** - Attested resources
   - Primary key: `resource_id`
   - Fields: scid, did, resource_type, resource_name, content, metadata, proof
   - Indexes: scid, did, resource_type

3. **WitnessFile** - Witness proofs
   - Primary key: `scid`
   - Fields: witness_proofs

4. **WhoisPresentation** - WHOIS presentations
   - Primary key: `scid`
   - Fields: presentation

5. **Task** - Background tasks
   - Primary key: `task_id`
   - Fields: task_type, status, progress, message
   - Indexes: task_type, status

6. **Policy** - Server policies
   - Primary key: `policy_id`
   - Fields: version, witness, watcher, portability, prerotation, endorsement, policy_data

7. **Registry** - Registries (e.g., known witnesses)
   - Primary key: `registry_id`
   - Fields: registry_type, registry_data, meta

### Test Tables

8. **TestLogEntry** - Test log entries (for load testing)
9. **TestResource** - Test resources (for load testing)

## StorageManager Architecture

The `StorageManager` class is the central component that:

1. **Owns the Database Connection** - Creates and manages the SQLAlchemy engine
2. **Provides Session Factory** - Creates database sessions with proper pooling
3. **Implements Singleton Pattern** - Ensures single engine instance across the app
4. **Offers High-Level CRUD** - Convenient methods for all database operations
5. **Handles Provisioning** - Database schema creation and reset (like AskarStorage)

```python
from app.plugins.storage import StorageManager

# Get singleton instance
storage = StorageManager()

# Access engine (if needed)
engine = storage.engine

# Get session factory (if needed)
SessionLocal = storage.SessionLocal

# Get a session
with storage.get_session() as session:
    result = session.query(Model).all()

# Or use high-level methods (recommended)
log_entry = storage.get_log_entry("scid-123")
```

## Database Configuration

### Environment Variables

```bash
# PostgreSQL
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_SERVER_NAME=localhost
POSTGRES_SERVER_PORT=5432

# Or use SQLite (default)
# No configuration needed, uses sqlite://app.db
```

### Supported Databases

- **SQLite** (default) - Good for development
- **PostgreSQL** - Recommended for production

## Usage

### Provisioning Pattern (Askar-Compatible)

The StorageManager follows the same provisioning pattern as AskarStorage:

```python
import asyncio
from app.plugins.storage import StorageManager

# Provision database (create tables)
storage = StorageManager()
asyncio.run(storage.provision())

# Provision with recreate (drops all tables first - useful for tests)
asyncio.run(storage.provision(recreate=True))
```

### Initialize Database

**Using the provision method (recommended):**

```python
import asyncio
from app.plugins.storage import StorageManager

storage = StorageManager()
asyncio.run(storage.provision())
```

**Using init_db (synchronous wrapper):**

```python
from app.plugins.storage import StorageManager

storage = StorageManager()
storage.init_db()  # Creates all tables
```

**Using the CLI:**

```bash
# Create tables
uv run python init_db.py

# Drop and recreate all tables
uv run python init_db.py --recreate
```

### Server Startup

The StorageManager is automatically provisioned on server startup in `main.py`:

```python
class StartupBackgroundTasks(threading.Thread):
    def run(self):
        asyncio.run(AskarStorage().provision())
        asyncio.run(StorageManager().provision())  # ← Automatic provisioning
        asyncio.run(TaskManager(...).set_policies())
```

### CRUD Operations

#### Log Entries

```python
from app.plugins.storage import StorageManager

storage = StorageManager()

# Create
log_entry = storage.create_log_entry(
    scid="abc123",
    did="did:webvh:example.com:namespace:identifier",
    domain="example.com",
    namespace="namespace",
    identifier="identifier",
    logs=[{"versionId": "1", "state": {...}}],
    deactivated=False
)

# Read
log_entry = storage.get_log_entry("abc123")
all_logs = storage.get_log_entries()
filtered = storage.get_log_entries(filters={"namespace": "namespace"})

# Update
updated = storage.update_log_entry(
    "abc123",
    logs=[{"versionId": "2", "state": {...}}],
    deactivated=True
)

# Delete
success = storage.delete_log_entry("abc123")
```

#### Resources

```python
# Create
resource = storage.create_resource(
    resource_id="res123",
    scid="abc123",
    did="did:webvh:example.com:namespace:identifier",
    resource_type="anonCredsSchema",
    resource_name="TestSchema",
    content={"attrNames": ["name", "age"]},
    metadata={"version": "1.0"},
    proof={"type": "DataIntegrityProof", ...}
)

# Read
resource = storage.get_resource("res123")
resources = storage.get_resources(filters={"scid": "abc123"})

# Update
updated = storage.update_resource(
    "res123",
    content={"attrNames": ["name", "age", "email"]}
)

# Delete
success = storage.delete_resource("res123")
```

#### Tasks

```python
# Create
task = storage.create_task(
    task_id="task123",
    task_type="load_test",
    status="started",
    progress={"completed": 0},
    message="Starting..."
)

# Read
task = storage.get_task("task123")
tasks = storage.get_tasks(filters={"status": "started"})

# Update
updated = storage.update_task(
    "task123",
    status="completed",
    progress={"completed": 100}
)

# Delete
success = storage.delete_task("task123")
```

#### Policies

```python
# Create or Update
policy = storage.create_or_update_policy(
    "active",
    {
        "version": "1.0",
        "witness": True,
        "portability": False,
        "prerotation": True,
        "endorsement": False
    }
)

# Read
policy = storage.get_policy("active")
```

#### Registries

```python
# Create or Update
registry = storage.create_or_update_registry(
    "knownWitnesses",
    "witness",
    {"registry": {"did:key:z6Mk...": {"name": "Witness 1"}}},
    meta={"created": "2025-01-01", "updated": "2025-01-01"}
)

# Read
registry = storage.get_registry("knownWitnesses")
```

#### Witness Files

```python
# Create or Update
witness_file = storage.create_or_update_witness_file(
    "abc123",
    [{"proofValue": "...", "verificationMethod": "..."}]
)

# Read
witness_file = storage.get_witness_file("abc123")
```

#### WHOIS Presentations

```python
# Create or Update
whois = storage.create_or_update_whois(
    "abc123",
    {"@context": [...], "type": "VerifiablePresentation", ...}
)

# Read
whois = storage.get_whois("abc123")
```

### Advanced: Direct Session Access

For complex queries, you can access the session directly:

```python
from app.db import SessionLocal, LogEntry

with SessionLocal() as session:
    # Complex query example
    active_logs = session.query(LogEntry).filter(
        LogEntry.deactivated == False,
        LogEntry.domain == "example.com"
    ).order_by(LogEntry.created_at.desc()).limit(10).all()
```

## Migrations with Alembic

### Create a New Migration

```bash
# Auto-generate migration based on model changes
uv run alembic revision --autogenerate -m "Add new column"

# Or create empty migration
uv run alembic revision -m "Custom migration"
```

### Apply Migrations

```bash
# Upgrade to latest
uv run alembic upgrade head

# Upgrade to specific revision
uv run alembic upgrade abc123

# Downgrade one version
uv run alembic downgrade -1

# See current version
uv run alembic current

# See migration history
uv run alembic history
```

### Initial Migration

To create the initial database migration:

```bash
uv run alembic revision --autogenerate -m "Initial migration"
uv run alembic upgrade head
```

## Performance Tips

### Indexes

The models include indexes on frequently queried fields:
- `scid`, `did`, `domain`, `namespace`, `identifier` on LogEntry
- `scid`, `did`, `resource_type` on Resource
- `task_type`, `status` on Task

### Batch Operations

For bulk inserts, use SQLAlchemy's bulk operations:

```python
from app.db import SessionLocal, LogEntry

with SessionLocal() as session:
    session.bulk_insert_mappings(LogEntry, [
        {"scid": "1", "did": "...", ...},
        {"scid": "2", "did": "...", ...},
    ])
    session.commit()
```

### Connection Pooling

Connection pooling is configured in `app/db/session.py`:
- **SQLite**: Uses StaticPool
- **PostgreSQL**: Pool size of 10, max overflow of 20

## Testing

### Test Database

For testing, use a separate database:

```bash
export DATABASE_URL="sqlite:///test.db"
```

### Test Fixtures (Pytest)

The project includes pytest fixtures that follow the same pattern as Askar tests:

```python
# tests/conftest.py provides these fixtures:

@pytest.mark.asyncio
async def test_example(storage_manager):
    """storage_manager fixture provisions with recreate=True."""
    log_entry = storage_manager.create_log_entry(...)
    assert log_entry.scid == "test-scid"

@pytest.mark.asyncio
async def test_with_both(dual_storage):
    """Test with both StorageManager and AskarStorage."""
    storage = dual_storage["storage"]
    askar = dual_storage["askar"]
    # Both are provisioned with clean slate
```

### Manual Test Provisioning

```python
import asyncio
from app.plugins.storage import StorageManager

async def setup_test_db():
    storage = StorageManager()
    # Drop all tables and recreate (clean slate)
    await storage.provision(recreate=True)
    return storage

# In your test
storage = asyncio.run(setup_test_db())
```

### Load Testing

The system includes dedicated test tables for load testing:

```python
# Create test data
test_entry = storage.create_test_log_entry(
    "test-scid-1",
    [{"test": "data"}],
    {"namespace": "loadtest"}
)

# Clean up test data
storage.delete_test_log_entry("test-scid-1")
```

## Troubleshooting

### Migration Conflicts

If you encounter migration conflicts:

```bash
# Reset migrations (WARNING: drops all data)
uv run alembic downgrade base
uv run alembic upgrade head
```

### Database Locked (SQLite)

If using SQLite and getting "database locked" errors:
- Use PostgreSQL for concurrent access
- Ensure all sessions are properly closed
- Consider using WAL mode:

```python
# In session.py
engine = create_engine(
    "sqlite:///app.db",
    connect_args={"check_same_thread": False, "timeout": 30},
    execution_options={"isolation_level": "AUTOCOMMIT"}
)
```

### Slow Queries

Enable query logging to identify slow queries:

```python
# In session.py
engine = create_engine(
    DATABASE_URL,
    echo=True  # Logs all SQL queries
)
```

## Migration from Askar

If migrating from Askar storage to SQLAlchemy:

1. Export data from Askar
2. Initialize SQLAlchemy database
3. Import data using StorageManager methods
4. Update code to use new StorageManager

Example migration script:

```python
from app.plugins.askar import AskarStorage
from app.plugins.storage import StorageManager

async def migrate():
    askar = AskarStorage()
    storage = StorageManager()
    
    # Initialize new database
    storage.init_db()
    
    # Migrate log entries
    entries = await askar.get_category_entries("logEntries")
    for entry in entries:
        storage.create_log_entry(
            scid=entry.name,
            did=entry.value_json["did"],
            domain=entry.tags["domain"],
            namespace=entry.tags["namespace"],
            identifier=entry.tags["identifier"],
            logs=entry.value_json["logs"]
        )
```

## Best Practices

1. **Always use context managers** for sessions
2. **Close sessions** properly to avoid connection leaks
3. **Use transactions** for multiple related operations
4. **Add indexes** for frequently queried fields
5. **Use migrations** for schema changes
6. **Test migrations** before applying to production
7. **Back up data** before major migrations
8. **Monitor connection pool** usage in production

## Additional Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Don't_Do_This)

