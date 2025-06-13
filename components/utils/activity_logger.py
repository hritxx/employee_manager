import logging
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, 
    Text, DateTime, ForeignKey, select, desc, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import pandas as pd
import os
from dotenv import load_dotenv


load_dotenv()


logger = logging.getLogger(__name__)


Base = declarative_base()


class SystemLog(Base):

    __tablename__ = 'system_logs'
    
    log_id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)
    user = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    
    def __repr__(self):
        return f"<SystemLog(log_id={self.log_id}, event_type='{self.event_type}', timestamp='{self.timestamp}')>"


class ActivityLogger:

    
    def __init__(self, engine=None):
      
        try:
            if engine is None:

                db_host = os.getenv('DB_HOST', 'localhost')
                db_port = os.getenv('DB_PORT', '5432')
                db_name = os.getenv('DB_NAME', 'employee_management_db')
                db_user = os.getenv('DB_USER', 'hr_admin')
                db_password = os.getenv('DB_PASSWORD', '')
                
                db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
                self.engine = create_engine(db_url, pool_size=5, max_overflow=10)
            else:
                self.engine = engine
                
            self.Session = sessionmaker(bind=self.engine)
            
            self.create_logs_table()
        except Exception as e:
            logger.error(f"Failed to initialize ActivityLogger: {e}")
            self.engine = None
            self.Session = None
        
    def create_logs_table(self):
        try:
            Base.metadata.create_all(self.engine, tables=[SystemLog.__table__])
            logger.info("System logs table created or already exists")
        except Exception as e:
            logger.error(f"Error creating system logs table: {e}")
    
    def log_event(self, event_type: str, description: str, user: Optional[str] = None, 
                  details: Optional[Dict[str, Any]] = None) -> bool:

        try:
            if self.Session is None:
                logger.error("Cannot log event: Session is not initialized")
                return False
                
            details_str = None
            if details:
                import json
                details_str = json.dumps(details)
            

            log_entry = SystemLog(
                event_type=event_type,
                user=user,
                description=description,
                details=details_str,
                timestamp=datetime.now()
            )
            

            with self.Session() as session:
                session.add(log_entry)
                session.commit()
                
            logger.info(f"Logged event: {event_type} - {description}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging event: {e}")
            return False
    
    def log_file_upload(self, filename: str, file_type: str, user: Optional[str] = None, 
                        status: str = "SUCCESS", details: Optional[Dict[str, Any]] = None) -> bool:
        
        description = f"File upload: {filename} ({file_type}) - {status}"
        return self.log_event("FILE_UPLOAD", description, user, details)
    
    def log_file_processing(self, filename: str, records_processed: int, 
                           records_success: int, records_failed: int,
                           user: Optional[str] = None) -> bool:
    
        description = f"File processed: {filename}"
        details = {
            "records_processed": records_processed,
            "records_success": records_success,
            "records_failed": records_failed
        }
        return self.log_event("FILE_PROCESSING", description, user, details)
    
    def log_query(self, query_text: str, user: Optional[str] = None, 
                 query_type: str = "CUSTOM", status: str = "SUCCESS") -> bool:
        
        if len(query_text) > 500:
            query_text_short = query_text[:500] + "..."
        else:
            query_text_short = query_text
            
        description = f"{query_type} query executed: {query_text_short}"
        details = {
            "query": query_text,
            "status": status
        }
        return self.log_event("QUERY", description, user, details)
    
    def log_ai_query(self, user_query: str, generated_sql: str, 
                    user: Optional[str] = None, status: str = "SUCCESS") -> bool:
       
        description = f"AI Query: {user_query[:100]}..."
        details = {
            "user_query": user_query,
            "generated_sql": generated_sql,
            "status": status
        }
        return self.log_event("AI_QUERY", description, user, details)
    
    def get_logs(self, event_type: Optional[str] = None, 
                limit: int = 100, offset: int = 0) -> pd.DataFrame:
        try:
            if self.Session is None:
                logger.error("Cannot get logs: Session is not initialized")
                return pd.DataFrame()
                
            with self.Session() as session:
                query = select(SystemLog).order_by(desc(SystemLog.timestamp))
                

                if event_type:
                    query = query.where(SystemLog.event_type == event_type)
                

                query = query.limit(limit).offset(offset)
                

                result = session.execute(query).scalars().all()
                

                logs_data = []
                for log in result:
                    log_dict = {
                        "log_id": log.log_id,
                        "event_type": log.event_type,
                        "user": log.user,
                        "description": log.description,
                        "details": log.details,
                        "timestamp": log.timestamp
                    }
                    logs_data.append(log_dict)
                

                return pd.DataFrame(logs_data)
                
        except Exception as e:
            logger.error(f"Error retrieving logs: {e}")
            return pd.DataFrame()
    
    def get_log_stats(self) -> Dict[str, Any]:
      
        try:
            with self.Session() as session:

                total_count = session.query(func.count(SystemLog.log_id)).scalar()
                

                event_counts_query = (
                    session.query(
                        SystemLog.event_type,
                        func.count(SystemLog.log_id).label('count')
                    )
                    .group_by(SystemLog.event_type)
                    .order_by(desc('count'))
                )
                event_counts = {row[0]: row[1] for row in event_counts_query}
                

                daily_counts_query = (
                    session.query(
                        func.date_trunc('day', SystemLog.timestamp).label('day'),
                        func.count(SystemLog.log_id).label('count')
                    )
                    .group_by('day')
                    .order_by(desc('day'))
                    .limit(7)
                )
                daily_counts = {str(row[0].date()): row[1] for row in daily_counts_query}
                
                return {
                    "total_count": total_count,
                    "event_counts": event_counts,
                    "daily_counts": daily_counts
                }
                
        except Exception as e:
            logger.error(f"Error retrieving log statistics: {e}")
            return {
                "total_count": 0,
                "event_counts": {},
                "daily_counts": {}
            }



_activity_logger = None

def get_logger(engine=None):

    global _activity_logger
    if _activity_logger is None:
        _activity_logger = ActivityLogger(engine)
    return _activity_logger 