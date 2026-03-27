import os
import shlex
from urllib.parse import quote, urlencode
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
    if url.startswith("postgresql:") and not url.startswith("postgresql://"):
        url = "postgresql://" + url[len("postgresql:") :].lstrip("/")
    if "://" not in url and "=" in url:
        # Accept libpq-style DSN: host=... port=... user=... password=... dbname=...
        parts: dict[str, str] = {}
        for token in shlex.split(url):
            if "=" not in token:
                continue
            k, v = token.split("=", 1)
            if k:
                parts[k.strip()] = v.strip()
        host = parts.get("host")
        dbname = parts.get("dbname") or parts.get("database")
        user = parts.get("user")
        password = parts.get("password", "")
        if host and dbname and user:
            port = parts.get("port")
            netloc = host if not port else f"{host}:{port}"
            auth = f"{quote(user, safe='')}:{quote(password, safe='')}@"
            query_params = {
                k: v
                for k, v in parts.items()
                if k not in {"host", "port", "dbname", "database", "user", "password"}
            }
            query = f"?{urlencode(query_params)}" if query_params else ""
            url = f"postgresql://{auth}{netloc}/{dbname}{query}"
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
