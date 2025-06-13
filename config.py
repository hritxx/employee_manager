
import os
from pathlib import Path
from typing import Dict
from dataclasses import dataclass
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

@dataclass
class DatabaseConfig:
    host: str = os.getenv('DB_HOST')
    port: int = int(os.getenv('DB_PORT'))
    database: str = os.getenv('DB_NAME')
    user: str = os.getenv('DB_USER')
    password: str = os.getenv('DB_PASSWORD')

@dataclass
class ETLConfig:
    batch_size: int = 1000
    max_workers: int = 4
    timeout_seconds: int = 300
    required_files: Dict[str, str] = None

    def __post_init__(self):
        self.required_files = {
            'employee_master': 'employee_master.csv',
            'employee_exit': 'employee_exit_report.csv',
            'experience_report': 'experience_report.csv',
            'work_profile': 'employee_work_profile.csv',
            'attendance_report': 'attendance_report_daily.csv',
            'timesheet_report': 'timesheet_report_clean.csv',
            'project_allocations': 'project_allocations.csv',
            'resource_utilization': 'resource_utilization.csv'
        }

@dataclass
class AppConfig:
    title: str = "HR Management System"
    description: str = "Enterprise ETL Pipeline for HR Data Management"
    version: str = "1.0.0"
    debug: bool = bool(os.getenv('APP_DEBUG', True))
    upload_folder: Path = Path("uploads")
    log_folder: Path = Path("logs")

    def __post_init__(self):
        self.upload_folder.mkdir(exist_ok=True)
        self.log_folder.mkdir(exist_ok=True)


db_config = DatabaseConfig()
etl_config = ETLConfig()
app_config = AppConfig()


FILE_SCHEMAS = {
    'employee_master': {
        'required_columns': [
            'Employee Code', 'Employee Name', 'Email', 'Date Of Joining',
            'Employee Type', 'Department', 'Designation'
        ],
        'optional_columns': [
            'Mobile Number', 'Grade', 'Business Unit', 'Parent Department',
            'Status', 'Gender', 'Date Of Birth', 'Marital Status',
            'Present Address', 'Permanent Address', 'PAN Number', 'Aadhaar Number',
            'Bank Name', 'Account Number', 'IFSC Code'
        ]
    },
    'employee_exit': {
        'required_columns': [
            'Employee Code', 'Exit Date', 'Expected Resignation Date'
        ],
        'optional_columns': [
            'Exit Reason', 'Exit Comments', 'Notice Period', 'Last Working Date'
        ]
    },
    'experience_report': {
        'required_columns': [
            'Employee Code', 'Employee Name', 'Business Unit', 'Department',
            'Designation', 'Date Of Joining', 'Current Experience',
            'Past Experience', 'Total Experience'
        ],
        'optional_columns': []
    },
    'work_profile': {
        'required_columns': [
            'Employee Code', 'Employee Name', 'Business Unit', 'Parent Designation',
            'Assigned Department', 'Designation', 'Office Location Name'
        ],
        'optional_columns': []
    },
    'attendance_report': {
        'required_columns': [
            'Date', 'Employee Code', 'Employee Name', 'Clock-In Time', 'Clock-Out Time'
        ],
        'optional_columns': [
            'Total Hours'
        ]
    },
    'timesheet_report': {
        'required_columns': [
            'timesheet_id', 'work_date', 'employee_code', 'project_id', 'hours_worked'
        ],
        'optional_columns': [
            'task_description', 'allocation_id'
        ]
    },
    'project_allocations': {
        'required_columns': [
            'allocation_id', 'employee_code', 'project_id', 'allocation_percentage',
            'effective_from', 'effective_to', 'status'
        ],
        'optional_columns': [
            'created_by', 'change_reason'
        ]
    },
    'resource_utiliszation': {
        'required_columns': [
            'project_id','week_start_date', 'week_end_date', 'working_hours',
        ],
        'optional_columns': []
    }
}


DATA_TYPE_RULES = {
    'Employee Code': str,
    'Email': str,
    'Date Of Joining': 'date',
    'Date Of Birth': 'date',
    'Exit Date': 'date',
    'Expected Resignation Date': 'date',
    'Last Working Date': 'date',
    'Start Date': 'date',
    'End Date': 'date',
    'Date': 'date',
    'Total Experience': float,
    'Relevant Experience': float,
    'Allocation Percentage': float,
    'Hours Worked': float,
    'Billable Hours': float,
    'Working Hours': float,
    'Overtime': float
} 