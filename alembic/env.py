from logging.config import fileConfig
from sqlalchemy import create_engine
from alembic import context
from sqlmodel import SQLModel

# Importa i tuoi modelli SQLModel per generare le migrazioni
from app_models import *  # Assicurati che contenga tutti i modelli

# Carica la configurazione di Alembic
config = context.config

# Configura il logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Usa SQLModel per ottenere i metadati
target_metadata = SQLModel.metadata

# Legge la stringa di connessione dal file alembic.ini
DATABASE_URL = config.get_main_option("sqlalchemy.url")

# Crea manualmente il motore del database
engine = create_engine(DATABASE_URL, pool_recycle=3600)

def run_migrations_offline() -> None:
    """Esegui le migrazioni in modalità offline."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Esegui le migrazioni in modalità online."""
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
