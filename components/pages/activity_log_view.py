import streamlit as st
import pandas as pd
import json
from datetime import datetime
from typing import Dict, Any

from components.utils.activity_logger import get_logger

def render_activity_logs(engine=None):
    logger = get_logger(engine)
    

    logs = logger.get_logs(limit=50)
    
    if not logs.empty:

        display_df = logs.copy()
        

        if 'timestamp' in display_df.columns:
            display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        

        columns_to_display = ['log_id', 'event_type', 'description', 'user', 'timestamp']
        columns_to_display = [col for col in columns_to_display if col in display_df.columns]
        
        if columns_to_display:
            result_df = display_df[columns_to_display]
            column_names = {
                'log_id': 'Log ID', 
                'event_type': 'Activity Type', 
                'description': 'Description', 
                'user': 'User', 
                'timestamp': 'Timestamp'
            }
            result_df = result_df.rename(columns={k: v for k, v in column_names.items() if k in result_df.columns})
            

            st.dataframe(result_df, use_container_width=True)
    else:
        st.info("No logs found") 