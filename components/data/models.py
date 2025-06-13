from components.data.database import db_pool
import logging
from tables import DatabaseTableCreator
from config import db_config

logger = logging.getLogger(__name__)

def create_tables():

    try:

        creator = DatabaseTableCreator()
        creator.connect_postgresql(
            host=db_config.host,
            database=db_config.database,
            user=db_config.user,
            password=db_config.password,
            port=db_config.port
        )
        creator.create_tables()
        creator.close_connection()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise 