from dataclasses import dataclass
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class PostgresConnection:
    user: str
    password: str
    host: str
    port: int
    database: str

    @property
    def is_localhost(self) -> bool:
        return self.host in {"localhost", "127.0.0.1", "::1"}


def parse_database_url(database_url: str) -> PostgresConnection:
    normalized = database_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    normalized = normalized.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError(f"Unsupported database URL scheme: {parsed.scheme}")
    database = (parsed.path or "").lstrip("/").split("?")[0]
    if not database:
        raise ValueError("DATABASE_URL missing database name")
    user = unquote(parsed.username or "postgres")
    password = unquote(parsed.password or "")
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    return PostgresConnection(user=user, password=password, host=host, port=port, database=database)
