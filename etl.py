"""
ETL Pipeline for HR Management System
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from psycopg2.extras import execute_values

from config import etl_config, app_config, FILE_SCHEMAS, DATA_TYPE_RULES, db_config
from components.data.database import db_pool
from components.data.models import create_tables
from data_seeder import DatabaseSeeder

logger = logging.getLogger(__name__)

class ETLPipeline:
    """Coordinates the ETL process"""

    def __init__(self):
        self.seeder = DatabaseSeeder({
            'host': db_config.host,
            'database': db_config.database,
            'user': db_config.user,
            'password': db_config.password,
            'port': db_config.port
        })
        self.upload_id: Optional[int] = None

    def process_files(self, files: Dict[str, Path]) -> Tuple[bool, str, Dict]:
        """Process uploaded files through the ETL pipeline"""
        try:
            # Connect to database
            self.seeder.connect()

            # Log upload start
            logger.info(f"Starting ETL process with files: {[f.name for f in files.values()]}")
            
            # Read all CSV files
            df_dict = {}
            for file_type, file_path in files.items():
                logger.info(f"Reading {file_type} from {file_path}")
                df_dict[file_type] = pd.read_csv(file_path)
                logger.info(f"Successfully read {len(df_dict[file_type])} rows from {file_path}")

            # Use DatabaseSeeder to load data
            success = self.seeder.seed_database(
                {
                    'employee_master': df_dict.get('employee_master'),
                    'employee_exit': df_dict.get('employee_exit'),
                    'experience_report': df_dict.get('experience_report'),
                    'work_profile': df_dict.get('work_profile'),
                    'attendance_report': df_dict.get('attendance_report'),
                    'timesheet_report': df_dict.get('timesheet_report'),
                    'project_allocations': df_dict.get('project_allocations'),
                    'resource_utilization': df_dict.get('resource_utilization')  # Add the new DataFrame
                },
                clean_existing=False  # Don't clean existing data
            )

            # Close database connection
            self.seeder.disconnect()

            if success:
                return True, "Data loaded successfully", {
                    'stage': 'complete',
                    'extracted_files': len(df_dict),
                    'validation_errors': {}
                }
            else:
                return False, "Data loading failed", {
                    'stage': 'load',
                    'validation_errors': {}
                }

        except Exception as e:
            error_message = f"Pipeline execution failed: {str(e)}"
            logger.error(error_message)
            return False, error_message, {'stage': 'pipeline_error'} 