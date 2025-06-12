import streamlit as st
import psycopg2
import pandas as pd
import google.generativeai as genai
from typing import List, Dict
import json
import os
from datetime import datetime
import re

class TaskSummarizer:
    def __init__(self):
        """Initialize the task summarizer with environment variables"""
        # Get API key from environment
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not gemini_api_key:
            st.error("GEMINI_API_KEY not found in environment variables")
            return
            
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Database configuration from environment variables
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'postgres'),
            'user': os.getenv('DB_USER', 'hr_admin'),
            'password': os.getenv('DB_PASSWORD'),
            'port': os.getenv('DB_PORT', '5432')
        }
        
    def get_database_connection(self):
        """Create database connection"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            st.error(f"Database connection error: {str(e)}")
            return None
    
    def fetch_employee_timesheet_data(self, employee_code: str) -> Dict:
        """Fetch all timesheet data for a given employee grouped by project"""
        conn = self.get_database_connection()
        if not conn:
            return {}
        
        try:
            query = """
            SELECT 
                t.project_id,
                p.project_name,
                p.client_name,
                t.task_description,
                t.hours_worked,
                t.work_date,
                SUM(t.hours_worked) OVER (PARTITION BY t.project_id) as total_project_hours
            FROM timesheet t
            LEFT JOIN project p ON t.project_id = p.project_id
            WHERE t.employee_code = %s 
                AND t.task_description IS NOT NULL 
                AND t.task_description != ''
            ORDER BY t.project_id, t.work_date DESC
            """
            
            df = pd.read_sql_query(query, conn, params=[employee_code])
            conn.close()
            
            if df.empty:
                return {}
            
            # Group by project
            projects_data = {}
            for project_id, group in df.groupby('project_id'):
                project_info = {
                    'project_name': group.iloc[0]['project_name'],
                    'client_name': group.iloc[0]['client_name'],
                    'total_hours': group.iloc[0]['total_project_hours'],
                    'tasks': []
                }
                
                for _, row in group.iterrows():
                    project_info['tasks'].append({
                        'description': row['task_description'],
                        'hours': row['hours_worked'],
                        'date': row['work_date']
                    })
                
                projects_data[project_id] = project_info
            
            return projects_data
        
        except Exception as e:
            st.error(f"Error fetching timesheet data: {str(e)}")
            if conn:
                conn.close()
            return {}
    
    def summarize_project_tasks_with_gemini(self, project_data: Dict) -> str:
        """Summarize tasks for a specific project using Gemini API"""
        if not project_data or not project_data.get('tasks'):
            return "No tasks found for this project."
        
        # Prepare tasks text
        tasks_text = []
        for task in project_data['tasks']:
            tasks_text.append(f"- {task['description']} ({task['hours']} hours on {task['date']})")
        
        all_tasks = "\n".join(tasks_text)
        total_hours = project_data['total_hours']
        project_name = project_data.get('project_name', 'Unknown Project')
        client_name = project_data.get('client_name', 'Unknown Client')
        
        prompt = f"""
        Summarize the following tasks for a project. Provide a concise summary that highlights:
        1. Main activities and work areas
        2. Key deliverables or outcomes
        3. Types of work performed
        4. Overall contribution to the project

        Project: {project_name}
        Client: {client_name}
        Total Hours: {total_hours}

        Tasks:
        {all_tasks}

        Provide a clear, professional summary in 1 paragraph:
        """
        
        try:
            response = self.model.generate_content(prompt)
            summary = response.text.strip()
            return summary
            
        except Exception as e:
            st.error(f"Error generating summary with Gemini: {str(e)}")
            return f"Error generating summary: {str(e)}"
    
    def get_employee_summary_stats(self, employee_code: str) -> Dict:
        """Get employee summary statistics"""
        conn = self.get_database_connection()
        if not conn:
            return {}
        
        try:
            query = """
            SELECT 
                e.employee_code,
                e.employee_name,
                d.department_name,
                des.designation_name,
                COUNT(DISTINCT t.project_id) as total_projects,
                SUM(t.hours_worked) as total_hours,
                COUNT(t.timesheet_id) as total_entries,
                MIN(t.work_date) as first_entry,
                MAX(t.work_date) as last_entry,
                COUNT(DISTINCT t.task_description) as unique_tasks
            FROM employee e
            LEFT JOIN timesheet t ON e.employee_code = t.employee_code
            LEFT JOIN department d ON e.department_id = d.department_id
            LEFT JOIN designation des ON e.designation_id = des.designation_id
            WHERE e.employee_code = %s
            GROUP BY e.employee_code, e.employee_name, d.department_name, des.designation_name
            """
            
            df = pd.read_sql_query(query, conn, params=[employee_code])
            conn.close()
            
            if df.empty:
                return {}
            
            return df.iloc[0].to_dict()
            
        except Exception as e:
            st.error(f"Error fetching employee stats: {str(e)}")
            if conn:
                conn.close()
            return {}
    
    def get_all_employees(self) -> List[str]:
        """Get list of all employees who have timesheet entries"""
        conn = self.get_database_connection()
        if not conn:
            return []
        
        try:
            query = """
            SELECT DISTINCT e.employee_code, e.employee_name
            FROM employee e
            INNER JOIN timesheet t ON e.employee_code = t.employee_code
            ORDER BY e.employee_name
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Return list of formatted strings: "CODE - Name"
            return [f"{row['employee_code']} - {row['employee_name']}" for _, row in df.iterrows()]
        
        except Exception as e:
            st.error(f"Error fetching employees: {str(e)}")
            if conn:
                conn.close()
            return []

def task_summarizer():
    """Tab 5: Employee Task Summarizer"""
    
    st.header("Employee Task Summarizer")
    
    
    # Check for required environment variables
    required_vars = ['GEMINI_API_KEY', 'DB_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        st.info("Please set the following environment variables:")
        for var in missing_vars:
            st.code(f"export {var}=your_value_here")
        return
    
    # Initialize the task summarizer
    try:
        summarizer = TaskSummarizer()
        if not hasattr(summarizer, 'model'):
            return  # Error already shown in __init__
    except Exception as e:
        st.error(f"Error initializing Task Summarizer: {str(e)}")
        return
    
    # Create columns for layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # st.subheader("Employee Selection")
        
        # # Database connection test - using container instead of expander
        # st.markdown("#### Database Connection")
        # if st.button("Test Database Connection", key="test_db_conn"):
        #     conn = summarizer.get_database_connection()
        #     if conn:
        #         st.success(" Database connected successfully!")
        #         conn.close()
        #     else:
        #         st.error(" Database connection failed!")
        
        st.divider()
        
        # Get all employees
        employees = summarizer.get_all_employees()
        
        if not employees:
            st.error("No employees found with timesheet entries or connection error.")
            return
        
        # Employee selection
        selected_employee_display = st.selectbox(
            "Select Employee:",
            options=employees,
            help="Choose an employee to summarize their project tasks",
            key="employee_select_tab5"
        )
        
        # Extract employee code from display string
        selected_employee = selected_employee_display.split(' - ')[0] if selected_employee_display else None
        
        # Model selection
        model_options = {
            'gemini-1.5-flash': 'Gemini 1.5 Flash (Fast & Efficient)',
            'gemini-1.5-flash-002': 'Gemini 1.5 Flash-002 (Latest)',
        }
        
        selected_model = st.selectbox(
            "Select AI Model:",
            options=list(model_options.keys()),
            format_func=lambda x: model_options[x],
            help="Choose the Gemini model for task summarization",
            key="model_select_tab5"
        )
        
        # Summarize tasks button
        if st.button(" Summarize Tasks", use_container_width=True, key="summarize_btn"):
            if selected_employee:
                with st.spinner("Analyzing timesheet data and generating summaries..."):
                    # Update model based on selection
                    summarizer.model = genai.GenerativeModel(selected_model)
                    
                    # Store results in session state with tab-specific keys
                    st.session_state.tab5_current_employee = selected_employee
                    st.session_state.tab5_employee_stats = summarizer.get_employee_summary_stats(selected_employee)
                    st.session_state.tab5_projects_data = summarizer.fetch_employee_timesheet_data(selected_employee)
                    
                    # Generate summaries for each project
                    st.session_state.tab5_project_summaries = {}
                    for project_id, project_data in st.session_state.tab5_projects_data.items():
                        st.session_state.tab5_project_summaries[project_id] = summarizer.summarize_project_tasks_with_gemini(project_data)
                    
                    st.session_state.tab5_summary_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.tab5_model_used = selected_model
                    
                    st.success("Task summaries generated successfully!")
    
    with col2:
        st.subheader("Task Summary Results")
        
        # Display results if available
        if hasattr(st.session_state, 'tab5_current_employee') and st.session_state.tab5_current_employee:
            
            # Employee info
            if st.session_state.tab5_employee_stats:
                stats = st.session_state.tab5_employee_stats
                
                # Employee information
                st.info(f"**{stats.get('employee_name', 'Unknown')}** ({st.session_state.tab5_current_employee})")
                
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.write(f"**Department:** {stats.get('department_name', 'N/A')}")
                with col_info2:
                    st.write(f"**Designation:** {stats.get('designation_name', 'N/A')}")
                
                # Employee statistics
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    st.metric("Total Hours", f"{stats.get('total_hours', 0) or 0:.1f}")
                with col_b:
                    st.metric("Projects", stats.get('total_projects', 0) or 0)
                with col_c:
                    st.metric("Entries", stats.get('total_entries', 0) or 0)

                
                st.divider()
                
                # Project summaries section
                if st.session_state.tab5_projects_data and st.session_state.tab5_project_summaries:
                    
                    # Add project selection if multiple projects
                    project_ids = list(st.session_state.tab5_projects_data.keys())
                    if len(project_ids) > 1:
                        st.markdown("#### Project Selection")
                        project_options = {}
                        for pid in project_ids:
                            pdata = st.session_state.tab5_projects_data[pid]
                            project_options[pid] = f"{pdata.get('project_name', pid)} ({pdata.get('total_hours', 0):.1f}h)"
                        
                        selected_projects = st.multiselect(
                            "Select projects to display:",
                            options=project_ids,
                            default=project_ids,
                            format_func=lambda x: project_options[x],
                            key="project_selector"
                        )
                    else:
                        selected_projects = project_ids
                    
                    st.markdown("####  Project Summaries")
                    
                    for project_id in selected_projects:
                        project_data = st.session_state.tab5_projects_data[project_id]
                        
                        # Project header
                        st.markdown(f"### {project_data.get('project_name', project_id)}")
                        
                        # Project details in a container
                        container = st.container()
                        with container:
                            col_x, col_y = st.columns(2)
                            with col_x:
                                st.write(f"**Project ID:** {project_id}")
                                st.write(f"**Client:** {project_data.get('client_name', 'N/A')}")
                            with col_y:
                                st.write(f"**Total Hours:** {project_data.get('total_hours', 0):.1f}")
                                st.write(f"**Number of Tasks:** {len(project_data.get('tasks', []))}")
                            
                            # AI-generated summary
                            st.markdown("**AI Summary:**")
                            summary = st.session_state.tab5_project_summaries.get(project_id, "No summary available")
                            st.markdown(f"> {summary}")
                            
                            # Show detailed tasks using toggle
                            show_details = st.toggle(
                                f"Show Detailed Tasks",
                                key=f"show_tasks_{project_id}",
                                help=f"Toggle to show/hide detailed task breakdown for {project_data.get('project_name', project_id)}"
                            )
                            
                            if show_details:
                                st.markdown("** Detailed Tasks:**")
                                tasks_df = pd.DataFrame(project_data.get('tasks', []))
                                if not tasks_df.empty:
                                    # Sort by date (most recent first)
                                    tasks_df = tasks_df.sort_values('date', ascending=False)
                                    st.dataframe(
                                        tasks_df,
                                        use_container_width=True,
                                        hide_index=True,
                                        column_config={
                                            "description": "Task Description",
                                            "hours": st.column_config.NumberColumn("Hours", format="%.2f"),
                                            "date": st.column_config.DateColumn("Date")
                                        }
                                    )
                                else:
                                    st.write("No tasks found.")
                        
                        st.divider()
                    
                    # Download options
                    st.markdown("#### Download Reports")
                    
                    col_dl1, col_dl2 = st.columns(2)
                    
                    with col_dl1:
                        # Create summary report
                        summary_report = {
                            "employee_code": st.session_state.tab5_current_employee,
                            "employee_info": st.session_state.tab5_employee_stats,
                            "generation_date": st.session_state.tab5_summary_time,
                            "model_used": st.session_state.get('tab5_model_used', 'gemini-1.5-flash'),
                            "project_summaries": []
                        }
                        
                        for project_id, project_data in st.session_state.tab5_projects_data.items():
                            project_summary = {
                                "project_id": project_id,
                                "project_name": project_data.get('project_name'),
                                "client_name": project_data.get('client_name'),
                                "total_hours": project_data.get('total_hours'),
                                "task_count": len(project_data.get('tasks', [])),
                                "ai_summary": st.session_state.tab5_project_summaries.get(project_id, ""),
                                "detailed_tasks": project_data.get('tasks', [])
                            }
                            summary_report["project_summaries"].append(project_summary)
                        
                        st.download_button(
                            label=" Download JSON Report",
                            data=json.dumps(summary_report, indent=2, default=str),
                            file_name=f"{st.session_state.tab5_current_employee}_task_summary.json",
                            mime="application/json",
                            key="download_json_tab5"
                        )
                    
                    with col_dl2:
                        # Create text summary
                        text_summary = f"TASK SUMMARY REPORT\n"
                        text_summary += f"Employee: {stats.get('employee_name', 'Unknown')} ({st.session_state.tab5_current_employee})\n"
                        text_summary += f"Department: {stats.get('department_name', 'N/A')}\n"
                        text_summary += f"Generated: {st.session_state.tab5_summary_time}\n"
                        text_summary += f"="*50 + "\n\n"
                        
                        for project_id, project_data in st.session_state.tab5_projects_data.items():
                            text_summary += f"PROJECT: {project_data.get('project_name', project_id)}\n"
                            text_summary += f"Client: {project_data.get('client_name', 'N/A')}\n"
                            text_summary += f"Total Hours: {project_data.get('total_hours', 0):.1f}\n"
                            text_summary += f"Tasks: {len(project_data.get('tasks', []))}\n\n"
                            text_summary += "SUMMARY:\n"
                            text_summary += st.session_state.tab5_project_summaries.get(project_id, "No summary available")
                            text_summary += "\n\n" + "-"*40 + "\n\n"
                        
                        st.download_button(
                            label="Download TXT Report",
                            data=text_summary,
                            file_name=f"{st.session_state.tab5_current_employee}_task_summary.txt",
                            mime="text/plain",
                            key="download_txt_tab5"
                        )
                    
                else:
                    st.warning("No timesheet data found for this employee.")
                
                # Generation info
                model_info = st.session_state.get('tab5_model_used', 'gemini-1.5-flash')
                st.caption(f"Last generated: {st.session_state.tab5_summary_time} | Model: {model_info}")
            
            else:
                st.error("Employee not found in database.")
        
        else:
            st.info("👈 Select an employee and click 'Summarize Tasks' to see results.")

# For standalone testing
if __name__ == "__main__":
    st.set_page_config(
        page_title="Task Summarizer Tab",
        page_icon="📋",
        layout="wide"
    )
    task_summarizer()