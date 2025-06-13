import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from components.pages.employee_master import show_employee_master_report
import plotly.express as px
import plotly.graph_objects as go

def create_project_document_report(project_data, project_info, weekly_hours_data, title):

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        textColor=colors.HexColor('#1f4e79'),
        alignment=1  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=12,
        textColor=colors.HexColor('#2c5aa0')
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        spaceBefore=12,
        spaceAfter=8,
        textColor=colors.HexColor('#4472c4')
    )
    
    # Title
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 12))
    
    # Date and basic info
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Project Overview Section
    if not project_info.empty:
        elements.append(Paragraph("PROJECT OVERVIEW", heading_style))
        
        proj_info = project_info.iloc[0]
        overview_text = f"""
        <b>Project Name:</b> {proj_info.get('project_name', 'N/A')}<br/>
        <b>Project ID:</b> {proj_info.get('project_id', 'N/A')}<br/>
        <b>Client:</b> {proj_info.get('client_name', 'N/A')}<br/>
        <b>Status:</b> {proj_info.get('status', 'N/A')}<br/>
        <b>Start Date:</b> {proj_info.get('start_date', 'N/A')}<br/>
        <b>End Date:</b> {proj_info.get('end_date', 'N/A') if proj_info.get('end_date') else 'Ongoing'}<br/>
        """
        elements.append(Paragraph(overview_text, styles['Normal']))
        elements.append(Spacer(1, 16))
    
    # Project Manager Section
    if not project_data.empty:
        managers = project_data[project_data['employee_type'].str.contains('Manager|Lead', case=False, na=False)]
        if not managers.empty:
            elements.append(Paragraph("PROJECT MANAGEMENT", heading_style))
            # Get unique manager (in case of duplicates)
            manager = managers.drop_duplicates('employee_code').iloc[0]
            manager_text = f"""
            <b>Project Manager:</b> {manager['employee_name']} ({manager['employee_code']})<br/>
            <b>Department:</b> {manager.get('department_name', 'N/A')}<br/>
            <b>Designation:</b> {manager.get('designation_name', 'N/A')}<br/>
            """
            elements.append(Paragraph(manager_text, styles['Normal']))
            elements.append(Spacer(1, 16))
    
    # Team Composition Section
    if not project_data.empty:
        elements.append(Paragraph("TEAM COMPOSITION & ALLOCATION HISTORY", heading_style))
        

        unique_employees = project_data['employee_code'].unique()
        
        for emp_code in unique_employees:
            emp_data = project_data[project_data['employee_code'] == emp_code]
            emp_info = emp_data.iloc[0] 
            
            elements.append(Paragraph(f"{emp_info['employee_name']} ({emp_code})", subheading_style))
            

            emp_details = f"""
            <b>Designation:</b> {emp_info.get('designation_name', 'N/A')}<br/>
            <b>Department:</b> {emp_info.get('department_name', 'N/A')}<br/>
            <b>Employee Type:</b> {emp_info.get('employee_type', 'N/A')}<br/>
            <b>Total Experience:</b> {emp_info.get('total_experience', 'N/A')} years<br/>
            """
            elements.append(Paragraph(emp_details, styles['Normal']))
            elements.append(Spacer(1, 8))
            

            allocation_columns = ['effective_from', 'effective_to', 'allocation_percentage', 'allocation_status', 'change_reason']
            unique_allocations = emp_data[allocation_columns].drop_duplicates()
            
            if len(unique_allocations) > 0:
                elements.append(Paragraph("<b>Allocation History:</b>", styles['Normal']))
                
                for _, allocation in unique_allocations.iterrows():

                    duration_text = f"From {allocation['effective_from']}"
                    if pd.notna(allocation['effective_to']) and allocation['effective_to']:
                        duration_text += f" to {allocation['effective_to']}"
                    else:
                        duration_text += " (Current)"
                    

                    alloc_text = f"""
                    • <b>Period:</b> {duration_text}<br/>
                      <b>Allocation:</b> {allocation['allocation_percentage']}%<br/>
                      <b>Status:</b> {allocation['allocation_status']}<br/>
                    """
                    

                    if pd.notna(allocation.get('change_reason')) and allocation.get('change_reason'):
                        alloc_text += f"      <b>Reason:</b> {allocation['change_reason']}<br/>"
                    
                    elements.append(Paragraph(alloc_text, styles['Normal']))
            
            elements.append(Spacer(1, 12))
    

    if not weekly_hours_data.empty:
        elements.append(Paragraph("WEEKLY HOURS ANALYSIS", heading_style))
        

        unique_hour_employees = weekly_hours_data['employee_code'].unique()
        
        for emp_code in unique_hour_employees:
            emp_hours = weekly_hours_data[weekly_hours_data['employee_code'] == emp_code]
            emp_name = emp_hours.iloc[0]['employee_name']
            
            elements.append(Paragraph(f"{emp_name} ({emp_code}) - Weekly Hours Breakdown", subheading_style))
            

            emp_hours = emp_hours.copy()
            emp_hours['work_date'] = pd.to_datetime(emp_hours['work_date'])
            

            emp_hours['week_start'] = emp_hours['work_date'] - pd.to_timedelta(emp_hours['work_date'].dt.dayofweek, unit='d')
            
            weekly_summary = emp_hours.groupby('week_start').agg({
                'hours_worked': 'sum',
                'work_date': 'count'
            }).rename(columns={'work_date': 'days_worked'}).sort_index()
            

            for week_start, week_data in weekly_summary.iterrows():
                week_end = week_start + timedelta(days=6)
                avg_hours_per_day = week_data['hours_worked'] / week_data['days_worked'] if week_data['days_worked'] > 0 else 0
                
                week_text = f"""
                <b>Week of {week_start.strftime('%B %d, %Y')}:</b><br/>
                • Total Hours: {week_data['hours_worked']:.1f}<br/>
                • Days Worked: {week_data['days_worked']}<br/>
                • Average Hours/Day: {avg_hours_per_day:.1f}<br/>
                """
                elements.append(Paragraph(week_text, styles['Normal']))
            

            emp_hours['month'] = emp_hours['work_date'].dt.to_period('M')
            monthly_summary = emp_hours.groupby('month')['hours_worked'].sum().sort_index()
            
            if not monthly_summary.empty:
                elements.append(Paragraph("<b>Monthly Summary:</b>", styles['Normal']))
                for month, total_hours in monthly_summary.items():
                    month_text = f"• {month.strftime('%B %Y')}: {total_hours:.1f} hours"
                    elements.append(Paragraph(month_text, styles['Normal']))
            
            elements.append(Spacer(1, 16))
    

    if not project_data.empty:
        elements.append(Paragraph("PROJECT STATISTICS", heading_style))
        

        total_employees = project_data['employee_code'].nunique()
        current_employees = project_data[project_data['allocation_status'] == 'Active']['employee_code'].nunique()
        

        active_allocations = project_data[project_data['allocation_status'] == 'Active']
        if not active_allocations.empty:

            latest_allocations = active_allocations.sort_values('effective_from').groupby('employee_code').tail(1)
            avg_allocation = latest_allocations['allocation_percentage'].mean()
        else:
            avg_allocation = 0
        
        stats_text = f"""
        <b>Total Team Members (Ever):</b> {total_employees}<br/>
        <b>Current Active Members:</b> {current_employees}<br/>
        <b>Average Current Allocation:</b> {avg_allocation:.1f}%<br/>
        """
        
        if not weekly_hours_data.empty:
            total_hours = weekly_hours_data['hours_worked'].sum()
            

            weekly_hours_data_copy = weekly_hours_data.copy()
            weekly_hours_data_copy['work_date'] = pd.to_datetime(weekly_hours_data_copy['work_date'])
            weekly_hours_data_copy['week'] = weekly_hours_data_copy['work_date'].dt.isocalendar().week
            weekly_hours_data_copy['year'] = weekly_hours_data_copy['work_date'].dt.year
            
            weekly_totals = weekly_hours_data_copy.groupby(['employee_code', 'year', 'week'])['hours_worked'].sum()
            avg_weekly_hours = weekly_totals.mean() if not weekly_totals.empty else 0
            
            stats_text += f"""
            <b>Total Hours Logged:</b> {total_hours:.1f} hours<br/>
            <b>Average Weekly Hours per Employee:</b> {avg_weekly_hours:.1f} hours<br/>
            """
        
        elements.append(Paragraph(stats_text, styles['Normal']))
        elements.append(Spacer(1, 16))
    

    elements.append(Paragraph("SUMMARY", heading_style))
    summary_text = """
    This report provides a comprehensive overview of the project including team composition, 
    allocation history, and work hours analysis. All data is presented chronologically and 
    represents the current state of project assignments and historical changes.
    """
    elements.append(Paragraph(summary_text, styles['Normal']))
    

    doc.build(elements)
    buffer.seek(0)
    return buffer
def render_standard_reports(engine=None, db_pool=None):

    st.header("Standard Reports")
    

    report_tabs = st.tabs(["📁 Project Master", "👥 Employee Master"])
    

    with report_tabs[0]:
        show_project_master_report(engine, db_pool)
    

    with report_tabs[1]:
        show_employee_master_report(engine, db_pool)

def show_project_master_report(engine=None, db_pool=None):
    st.subheader("Project Master Report")

    

    try:
        projects_df = run_query("SELECT project_id, project_name, client_name, status FROM project ORDER BY project_name", engine, db_pool)
        
        if not projects_df.empty:
            project_options = ["Select a Project"] + [f"{row['project_name']} ({row['project_id']})" for _, row in projects_df.iterrows()]
            selected_project = st.selectbox("Choose Project", project_options, key="project_master_selector")
            
            if selected_project != "Select a Project":

                project_id = selected_project.split("(")[-1].rstrip(")")
                project_name = selected_project.split(" (")[0]
                

                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("📅 From Date", value=datetime.now() - timedelta(days=90), key="proj_start_date")
                with col2:
                    end_date = st.date_input("📅 To Date", value=datetime.now(), key="proj_end_date")
                

                project_info = get_project_info(project_id, engine, db_pool)
                project_data = get_project_allocation_history(project_id, engine, db_pool)
                weekly_hours_data = get_project_weekly_hours(project_id, start_date, end_date, engine, db_pool)
                
                if not project_data.empty:

                    st.markdown("### Project Overview")
                    if not project_info.empty:
                        proj_info = project_info.iloc[0]
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Project Status", proj_info.get('status', 'N/A'))
                        with col2:
                            st.metric(" Client", proj_info.get('client_name', 'N/A'))
                        with col3:
                            duration = "Ongoing"
                            if proj_info.get('start_date') and proj_info.get('end_date'):
                                start = pd.to_datetime(proj_info['start_date'])
                                end = pd.to_datetime(proj_info['end_date'])
                                duration = f"{(end - start).days} days"
                            st.metric("Duration", duration)
                    

                    st.markdown("### 👥 Team Summary")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        total_members = project_data['employee_code'].nunique()
                        st.metric("Total Members", total_members)
                    with col2:
                        avg_allocation = project_data[project_data['allocation_status'] == 'Active']['allocation_percentage'].mean()
                        st.metric("Avg Allocation", f"{avg_allocation:.1f}%")


                    

                    st.markdown("###  Team Composition & History")
                    

                    current_employees = project_data[
                        (project_data['allocation_status'] == 'Active') & 
                        (project_data['effective_to'].isna())
                    ]['employee_code'].unique()
                    
                    past_employees = project_data[
                        ~project_data['employee_code'].isin(current_employees)
                    ]['employee_code'].unique()
                    

                    project_data_clean = project_data.drop_duplicates(
                        subset=['employee_code', 'effective_from', 'effective_to', 'allocation_percentage']
                    ).sort_values(['employee_code', 'effective_from'])
                    

                    if len(current_employees) > 0:
                        st.markdown("####  **Current Team Members**")
                        
                        for emp_code in current_employees:
                            emp_data = project_data_clean[project_data_clean['employee_code'] == emp_code]
                            emp_info = emp_data.iloc[0]
                            

                            current_allocation = emp_data[
                                (emp_data['allocation_status'] == 'Active') & 
                                (emp_data['effective_to'].isna())
                            ]
                            
                            current_alloc_pct = current_allocation['allocation_percentage'].iloc[0] if not current_allocation.empty else 0
                            
                            with st.expander(f"👤 {emp_info['employee_name']} ({emp_code}) - **{current_alloc_pct}% allocated**"):
                                col1, col2 = st.columns([2, 1])
                                
                                with col1:
                                    st.markdown(f"""
                                    **Personal Details:**
                                    - **Designation:** {emp_info.get('designation_name', 'N/A')}
                                    - **Department:** {emp_info.get('department_name', 'N/A')}
                                    - **Employee Type:** {emp_info.get('employee_type', 'N/A')}
                                    - **Total Experience:** {emp_info.get('total_experience', 'N/A')} years
                                    
                                    **Allocation History:**
                                    """)
                                    
                                    for _, allocation in emp_data.iterrows():
                                        duration_text = f"From {allocation['effective_from']}"
                                        if pd.notna(allocation['effective_to']):
                                            duration_text += f" to {allocation['effective_to']}"
                                            days = (pd.to_datetime(allocation['effective_to']) - pd.to_datetime(allocation['effective_from'])).days
                                            duration_text += f" ({days} days)"
                                            status_icon = "🔴"
                                        else:
                                            duration_text += " (Current)"
                                            days = (datetime.now().date() - pd.to_datetime(allocation['effective_from']).date()).days
                                            duration_text += f" ({days} days so far)"
                                            status_icon = "🟢"
                                        
                                        st.markdown(f"""
                                        {status_icon} **Period:** {duration_text}  
                                        &nbsp;&nbsp;&nbsp;&nbsp;**Allocation:** {allocation['allocation_percentage']}%  
                                        &nbsp;&nbsp;&nbsp;&nbsp;**Status:** {allocation['allocation_status']}""")
                                        if allocation.get('change_reason'):
                                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**Reason:** {allocation['change_reason']}")
                                        st.markdown("")
                                
                                with col2:

                                    emp_hours = weekly_hours_data[weekly_hours_data['employee_code'] == emp_code]
                                    if not emp_hours.empty:
                                        st.markdown("**Recent Hours Summary:**")
                                        

                                        emp_hours['week'] = pd.to_datetime(emp_hours['work_date']).dt.isocalendar().week
                                        emp_hours['year'] = pd.to_datetime(emp_hours['work_date']).dt.year
                                        weekly_summary = emp_hours.groupby(['year', 'week']).agg({
                                            'hours_worked': 'sum',
                                            'work_date': 'count'
                                        }).rename(columns={'work_date': 'days_worked'}).tail(4)
                                        
                                        total_hours = emp_hours['hours_worked'].sum()
                                        st.metric("Total Hours", f"{total_hours:.1f}h")
                                        
                                        for (year, week), week_data in weekly_summary.iterrows():
                                            st.markdown(f"""
                                            **Week {week}, {year}:**  
                                            Hours: {week_data['hours_worked']:.1f}h | Days: {week_data['days_worked']} | Avg: {week_data['hours_worked']/week_data['days_worked']:.1f}h/day
                                            """)
                                    else:
                                        st.markdown("*No timesheet data available*")
                    

                    if len(past_employees) > 0:
                        st.markdown("####  **Past Team Members**")
                        
                        for emp_code in past_employees:
                            emp_data = project_data_clean[project_data_clean['employee_code'] == emp_code]
                            emp_info = emp_data.iloc[0]
                            

                            total_days = 0
                            for _, allocation in emp_data.iterrows():
                                if pd.notna(allocation['effective_to']):
                                    days = (pd.to_datetime(allocation['effective_to']) - pd.to_datetime(allocation['effective_from'])).days
                                    total_days += days
                            
                            with st.expander(f"👤 {emp_info['employee_name']} ({emp_code}) - **Worked {total_days} days**"):
                                col1, col2 = st.columns([2, 1])
                                
                                with col1:
                                    st.markdown(f"""
                                    **Personal Details:**
                                    - **Designation:** {emp_info.get('designation_name', 'N/A')}
                                    - **Department:** {emp_info.get('department_name', 'N/A')}
                                    - **Employee Type:** {emp_info.get('employee_type', 'N/A')}
                                    - **Total Experience:** {emp_info.get('total_experience', 'N/A')} years
                                    
                                    ** Historical Allocation:**
                                    """)
                                    
                                    for _, allocation in emp_data.iterrows():
                                        if pd.notna(allocation['effective_to']):
                                            duration_text = f"From {allocation['effective_from']} to {allocation['effective_to']}"
                                            days = (pd.to_datetime(allocation['effective_to']) - pd.to_datetime(allocation['effective_from'])).days
                                            duration_text += f" ({days} days)"
                                            
                                            st.markdown(f"""
                                            🔴 **Period:** {duration_text}  
                                            &nbsp;&nbsp;&nbsp;&nbsp;**Allocation:** {allocation['allocation_percentage']}%  
                                            &nbsp;&nbsp;&nbsp;&nbsp;**Status:** {allocation['allocation_status']}""")
                                            if allocation.get('change_reason'):
                                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**Reason:** {allocation['change_reason']}")
                                            st.markdown("")
                                
                                with col2:

                                    emp_hours = weekly_hours_data[weekly_hours_data['employee_code'] == emp_code]
                                    if not emp_hours.empty:
                                        st.markdown("**Historical Hours:**")
                                        total_hours = emp_hours['hours_worked'].sum()
                                        avg_hours_per_day = emp_hours['hours_worked'].mean()
                                        
                                        st.metric("Total Hours", f"{total_hours:.1f}h")
                                        st.metric("Avg Hours/Day", f"{avg_hours_per_day:.1f}h")
                                    else:
                                        st.markdown("*No timesheet data available*")
                    

                    if not weekly_hours_data.empty:
                        st.markdown("###  Hours Analysis")
                        

                        weekly_chart_data = weekly_hours_data.copy()
                        weekly_chart_data['week_start'] = pd.to_datetime(weekly_chart_data['work_date']) - pd.to_timedelta(pd.to_datetime(weekly_chart_data['work_date']).dt.dayofweek, unit='d')
                        weekly_totals = weekly_chart_data.groupby(['week_start', 'employee_name'])['hours_worked'].sum().reset_index()
                        
                        fig = px.bar(weekly_totals, x='week_start', y='hours_worked', color='employee_name',
                                   title='Weekly Hours by Employee', labels={'week_start': 'Week', 'hours_worked': 'Hours'})
                        st.plotly_chart(fig, use_container_width=True)
                    

                    st.markdown("### Download Report")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(" Generate Document Report", key="gen_proj_doc_report"):
                            try:
                                pdf_buffer = create_project_document_report(
                                    project_data, project_info, weekly_hours_data,
                                    f"Project Master Report - {project_name}"
                                )
                                st.download_button(
                                    label=" Download PDF Report",
                                    data=pdf_buffer,
                                    file_name=f"project_report_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                    mime="application/pdf",
                                    key="download_proj_doc_pdf"
                                )
                                
                            except Exception as e:
                                st.error(f"Error generating report: {str(e)}")
                    
                    with col2:

                        combined_data = project_data.merge(
                            weekly_hours_data.groupby('employee_code').agg({
                                'hours_worked': 'sum'
                            }).reset_index(),
                            on='employee_code', how='left'
                        )
                        
                        csv = combined_data.to_csv(index=False)
                        st.download_button(
                            label="Download Raw Data (CSV)",
                            data=csv,
                            file_name=f"project_data_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key="download_proj_raw_csv"
                        )
                
                else:
                    st.warning("⚠️ No allocation data found for this project.")
        else:
            st.warning("⚠️ No projects found in the database.")
            
    except Exception as e:
        st.error(f" Error loading projects: {str(e)}")




def run_query(query, engine=None, db_pool=None):

    try:
        if engine:
            df = pd.read_sql(query, engine)
        elif db_pool:

            df = pd.read_sql(query, db_pool)
        else:

            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Database query error: {str(e)}")
        return pd.DataFrame()

def get_project_info(project_id, engine=None, db_pool=None):

    query = f"""
    SELECT project_id, project_name, client_name, status, start_date, end_date
    FROM project 
    WHERE project_id = '{project_id}'
    """
    return run_query(query, engine, db_pool)

def get_project_allocation_history(project_id, engine=None, db_pool=None):

    query = f"""
    SELECT 
        pa.allocation_id,
        pa.employee_code,
        e.employee_name,
        e.employee_type,
        e.total_experience,
        d.department_name,
        des.designation_name,
        pa.project_id,
        p.project_name,
        pa.allocation_percentage,
        pa.effective_from,
        pa.effective_to,
        pa.status as allocation_status,
        pa.change_reason,
        pa.created_at
    FROM project_allocation pa
    JOIN employee e ON pa.employee_code = e.employee_code
    JOIN project p ON pa.project_id = p.project_id
    LEFT JOIN department d ON e.department_id = d.department_id
    LEFT JOIN designation des ON e.designation_id = des.designation_id
    WHERE pa.project_id = '{project_id}'
    ORDER BY e.employee_name, pa.effective_from DESC
    """
    return run_query(query, engine, db_pool)

def get_project_weekly_hours(project_id, start_date, end_date, engine=None, db_pool=None):

    query = f"""
    SELECT 
        t.employee_code,
        e.employee_name,
        t.work_date,
        t.hours_worked,
        t.task_description,
        t.project_id
    FROM timesheet t
    JOIN employee e ON t.employee_code = e.employee_code
    WHERE t.project_id = '{project_id}'
    AND t.work_date BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY t.employee_code, t.work_date
    """
    return run_query(query, engine, db_pool)