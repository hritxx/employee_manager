import streamlit as st
from pathlib import Path
import pandas as pd
import logging
from datetime import datetime
import os
from dotenv import load_dotenv
from components.pages.summary_reports import render_summary_reports
from components.pages.query_assistant import render_ai_query_assistant
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from components.pages.tasks_summariser import task_summarizer
from components.pages.custom_queries import render_custom_queries
from components.pages.file_upload import render_file_upload
from components.pages.report import render_standard_reports
from components.auth import AuthManager 
from components.pages.activity_log_view import render_activity_logs

load_dotenv()


auth_manager = AuthManager()


GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')


DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')


encoded_password = quote_plus(DB_PASSWORD)
DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)


from config import app_config, etl_config, db_config


st.set_page_config(
    page_title=app_config.title,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


logger = logging.getLogger(__name__)

from components.data.database import db_pool
from etl import ETLPipeline
from components.data.models import create_tables


def get_available_tables():
    try:
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
        """
        result = pd.read_sql(query, engine)
        return result['table_name'].tolist()
    except Exception as e:
        st.error(f"Error getting tables: {e}")
        return []


def initialize_database():

    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        st.error("Failed to initialize database tables. Please check the logs.")

def render_authenticated_app():

    initialize_database()
    

    logger.info("Database Configuration:")
    logger.info(f"Host: {db_config.host}")
    logger.info(f"Database: {db_config.database}")
    logger.info(f"User: {db_config.user}")
    logger.info(f"Port: {db_config.port}")
    

    with st.sidebar:
        st.markdown("---")
        st.markdown(f"👤 **Logged in as:** {auth_manager.get_current_user()}")
        if st.button("🚪 Logout", use_container_width=True):
            auth_manager.logout()
    

    st.title("Employee Reports Dashboard")

    tabs = st.tabs([
        "📂 File Upload", 
        "📊 Predefined Reports", 
        "🔍 Custom Queries", 
        "🤖 AI Query Assistant",
        "🤖 Tasks Summariser",
        "📋 Standard Reports",
        "🧾 Logs"
    ])
    
    with tabs[0]:
        render_file_upload(db_pool)

    with tabs[1]:
        render_summary_reports()
    
    with tabs[2]:
        render_custom_queries(engine)
    
    with tabs[3]:
        render_ai_query_assistant(engine, get_available_tables, GEMINI_API_KEY)

    with tabs[4]:
        task_summarizer()   

    with tabs[5]:
        render_standard_reports(engine, db_pool)
        
    with tabs[6]:
        render_activity_logs(engine)
    

def main():

    if not auth_manager.require_auth():
        return 
    

    render_authenticated_app()

if __name__ == "__main__":
    main()