import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger("core.db")


def get_connection():
    logger.debug("Opening database connection")
    return psycopg2.connect(settings.database_url, cursor_factory=RealDictCursor)
