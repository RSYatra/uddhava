import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

# Ensure project root (parent of this alembic directory) is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# This Alembic Config object gives access to values in alembic.ini
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.core.config import get_settings  # noqa: E402

# --- Dynamic database URL resolution ---
# We import SQLAlchemy models metadata so autogenerate can detect changes.
from app.db.models import Base  # noqa: E402

settings = get_settings()
DATABASE_URL = settings.get_database_url()

target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine, though an Engine
    is acceptable here as well. By skipping the Engine creation we don't even
    need a DBAPI to be available.
    """
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    engine = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
