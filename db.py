from sqlmodel import SQLModel, create_engine ,Session
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

# Retrieve database credentials safely
postgres_user = quote_plus(os.getenv("POSTGRES_USER", ""))
postgres_password = quote_plus(os.getenv("POSTGRES_PASSWORD", ""))
postgres_host = os.getenv("POSTGRES_HOST", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")  # Default to 5432 if None
postgres_db = os.getenv("POSTGRES_DB", "")

# Construct database URL
DATABASE_URL = f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/mydatabase"

# Create engine
engine = create_engine(DATABASE_URL, echo=True)  # Set echo=True for debugging

def get_sesion():
    with Session(engine)as session:
        yield session
        
def init_db():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    init_db()
