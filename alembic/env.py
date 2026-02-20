"""Alembic environment for CryoDash.

This env.py uses the application's `DATABASE_URL` and the SQLAlchemy
`Base.metadata` to autogenerate migrations.
"""

import logging
from logging.config import fileConfig

from sqlalchemy import create_engine

from alembic import context  # type: ignore[attr-defined]

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# Import application configuration and metadata
from cryodash.config import DATABASE_URL  # noqa: E402
from cryodash.database import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation we don't
    even need a DBAPI to be available.
    """
    url = DATABASE_URL
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection with the context.
    """
    connectable = create_engine(DATABASE_URL)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
