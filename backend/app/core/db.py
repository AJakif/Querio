import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import settings


class ConnectionFactory:
    def __init__(self, dsn: str | None = None):
        self._dsn = dsn or settings.database_url

    def __call__(self):
        return psycopg2.connect(self._dsn, cursor_factory=RealDictCursor)


get_connection = ConnectionFactory()
