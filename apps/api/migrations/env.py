"""
Alembic environment configuration.
Imports Base from models so autogenerate detects all tables.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.models.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", "+psycopg"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits SQL to stdout."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


from sqlalchemy import engine_from_config, pool, create_engine, text
from sqlalchemy.engine.url import make_url

def create_database_if_not_exists(url: str) -> None:
    parsed_url = make_url(url)
    db_name = parsed_url.database
    
    # Conectar a la bd 'postgres' por defecto para checar/crear
    postgres_url = parsed_url.set(database="postgres")
    
    engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"))
            if not result.scalar():
                print(f"✅ Creando base de datos: {db_name}")
                conn.execute(text(f"CREATE DATABASE {db_name}"))
    except Exception as e:
        print(f"⚠️ No se pudo verificar/crear la BD automáticamente: {e}")

def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to the database."""
    url = config.get_main_option("sqlalchemy.url")
    create_database_if_not_exists(url)
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
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
