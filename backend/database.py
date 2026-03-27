import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from pathlib import Path


def _normalize_database_url(raw_url: str | None) -> str | None:
    if raw_url is None:
        return None
    url = raw_url.strip()
    if (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
        url = url[1:-1].strip()
    if url.startswith("postgres://"):
        # SQLAlchemy expects postgresql://
        url = "postgresql://" + url[len("postgres://") :]
    return url


def _masked_url_for_error(url: str) -> str:
    scheme = url.split("://", 1)[0] if "://" in url else "invalid"
    return f"{scheme}://*** (len={len(url)})"


DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL"))

# fallback to SQLITE for local
if not DATABASE_URL:
    DATA_DIR = Path(__file__).resolve().parent.parent / "data"
    DATA_DIR.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite:///{DATA_DIR}/railvision.db"

try:
    if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgresql+"):
        engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require"})
    else:
        engine = create_engine(DATABASE_URL)
except Exception as exc:
    raise RuntimeError(
        f"Invalid DATABASE_URL format: {_masked_url_for_error(DATABASE_URL)}. "
        "Check for accidental quotes/whitespace or malformed URL."
    ) from exc
    
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
