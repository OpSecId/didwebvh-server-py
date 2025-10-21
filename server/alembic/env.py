from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import settings first
import os
from dotenv import load_dotenv

basedir = Path(__file__).resolve().parents[1]
load_dotenv(os.path.join(basedir, ".env"))

# Get DATABASE_URL directly from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://app.db")

# Import Base and models directly without triggering app/__init__.py
import importlib.util

# Load Base
spec = importlib.util.spec_from_file_location("base", basedir / "app" / "db" / "base.py")
base_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_module)
Base = base_module.Base

# Load models to register them with Base
spec = importlib.util.spec_from_file_location("models", basedir / "app" / "db" / "models.py")
models_module = importlib.util.module_from_spec(spec)
sys.modules['app.db.base'] = base_module  # Make it available for models.py import
spec.loader.exec_module(models_module)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override the sqlalchemy.url with our DATABASE_URL
config.set_main_option('sqlalchemy.url', DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
