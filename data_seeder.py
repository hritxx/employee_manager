import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import logging
from datetime import datetime
import os
from typing import Dict, List, Optional


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseSeeder:
    def __init__(self, db_config: Dict[str, str]):

        self.db_config = db_config
        self.conn = None
        self.cursor = None

    def connect(self):

        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor()
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):

        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")

    def execute_query(self, query: str, params=None):

        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Query execution failed: {e}")
            raise

    def check_table_constraints(self, table_name: str):

        query = """
        SELECT 
            conname as constraint_name,
            contype as constraint_type,
            array_agg(attname ORDER BY attnum) as columns
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_attribute att ON att.attrelid = con.conrelid 
            AND att.attnum = ANY(con.conkey)
        WHERE rel.relname = %s
        GROUP BY conname, contype
        """
        try:
            self.cursor.execute(query, (table_name,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.warning(f"Could not check constraints for {table_name}: {e}")
            return []

    def bulk_insert_safe(self, table: str, columns: List[str], data: List[tuple],
                        primary_key_columns: Optional[List[str]] = None):

        if not data:
            logger.warning(f"No data to insert into {table}")
            return


        constraints = self.check_table_constraints(table)
        logger.info(f"Found constraints for {table}: {constraints}")


        unique_constraints = [c for c in constraints if c[1] == 'u'] 
        primary_constraints = [c for c in constraints if c[1] == 'p']  


        base_query = f"INSERT INTO {table} ({','.join(columns)}) VALUES %s"


        if table == 'employee_exit':

            conflict_cols = ['employee_code']
            update_cols = ['exit_date', 'last_working_date', 'exit_reason', 'exit_comments']
            conflict_action = f"ON CONFLICT (employee_code) DO UPDATE SET " + \
                            ", ".join(f"{col} = EXCLUDED.{col}" for col in update_cols)
            query = f"{base_query} {conflict_action}"
        elif table == 'attendance':

            conflict_cols = ['employee_code', 'attendance_date']
            update_cols = ['clock_in_time', 'clock_out_time', 'attendance_type']
            conflict_action = f"ON CONFLICT (employee_code, attendance_date) DO UPDATE SET " + \
                            ", ".join(f"{col} = EXCLUDED.{col}" for col in update_cols)
            query = f"{base_query} {conflict_action}"
        elif table == 'timesheet':

            conflict_cols = ['employee_code', 'project_id', 'work_date']
            update_cols = ['hours_worked', 'task_description']
            conflict_action = f"ON CONFLICT (employee_code, project_id, work_date) DO UPDATE SET " + \
                            ", ".join(f"{col} = EXCLUDED.{col}" for col in update_cols)
            query = f"{base_query} {conflict_action}"
        elif primary_constraints:

            pk_columns = primary_constraints[0][2] 
            conflict_clause = f"ON CONFLICT ({','.join(pk_columns)}) DO NOTHING"
            query = f"{base_query} {conflict_clause}"
        elif unique_constraints:
            unique_columns = unique_constraints[0][2]
            conflict_clause = f"ON CONFLICT ({','.join(unique_columns)}) DO NOTHING"
            query = f"{base_query} {conflict_clause}"
        elif primary_key_columns:
            conflict_clause = f"ON CONFLICT ({','.join(primary_key_columns)}) DO NOTHING"
            query = f"{base_query} {conflict_clause}"
        else:
            query = base_query

        try:
            execute_values(self.cursor, query, data, template=None, page_size=1000)
            self.conn.commit()
            logger.info(f"Successfully processed {len(data)} records for {table}")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Bulk insert failed for {table}: {e}")
            self._try_individual_inserts(table, columns, data)

    def _try_individual_inserts(self, table: str, columns: List[str], data: List[tuple]):
        logger.info(f"Attempting individual inserts for {table}")
        success_count = 0
        failure_count = 0

        insert_query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join(['%s'] * len(columns))})"

        for record in data:
            try:
                self.cursor.execute(insert_query, record)
                self.conn.commit()
                success_count += 1
            except Exception as e:
                self.conn.rollback()
                failure_count += 1
                if failure_count <= 5:
                    logger.warning(f"Failed to insert record {record[:2]}...: {e}")

        logger.info(f"Individual inserts completed: {success_count} success, {failure_count} failures")

    def seed_departments_and_designations(self, df_emp: pd.DataFrame):
        logger.info("Seeding departments and designations...")

        departments = df_emp[['Department', 'Business Unit', 'Parent Department']].drop_duplicates()
        dept_data = []
        for _, row in departments.iterrows():
            dept_data.append((
                row['Department'],
                row['Business Unit'],
                row['Parent Department'] if pd.notna(row['Parent Department']) else None,
                'Active'
            ))


        self.bulk_insert_safe('department',
                            ['department_name', 'business_unit', 'parent_department', 'status'],
                            dept_data)


        designations = df_emp['Designation'].unique()
        desig_data = [(desig, 'Mid', 'Active') for desig in designations if pd.notna(desig)]

        self.bulk_insert_safe('designation',
                            ['designation_name', 'level', 'status'],
                            desig_data)

    def get_reference_mappings(self):
        
        self.cursor.execute("SELECT department_id, department_name FROM department")
        dept_mapping = {name: dept_id for dept_id, name in self.cursor.fetchall()}


        self.cursor.execute("SELECT designation_id, designation_name FROM designation")
        desig_mapping = {name: desig_id for desig_id, name in self.cursor.fetchall()}

        return dept_mapping, desig_mapping

    def parse_date(self, date_str: str) -> datetime.date:

        if pd.isna(date_str):
            return None
            
        formats = ['%d-%m-%Y', '%Y-%m-%d']  
        
        for fmt in formats:
            try:
                return pd.to_datetime(date_str, format=fmt).date()
            except ValueError:
                continue
                

        try:
            return pd.to_datetime(date_str).date()
        except Exception as e:
            logger.error(f"Failed to parse date {date_str}: {e}")
            return None

    def seed_employees(self, df_emp: pd.DataFrame, dept_mapping: Dict, desig_mapping: Dict):
        logger.info("Seeding employees...")

        emp_data = []
        personal_data = []
        financial_data = []


        used_aadhaar = {}  
        used_pan = {}  

        for _, row in df_emp.iterrows():

            emp_data.append((
                row['Employee Code'],
                row['Employee Name'],
                row['Email'] if pd.notna(row['Email']) else None,
                row['Mobile Number'] if pd.notna(row['Mobile Number']) else None,
                self.parse_date(row['Date Of Joining']),
                row['Employee Type'],
                row['Grade'] if pd.notna(row['Grade']) else None,
                row['Status'],
                dept_mapping.get(row['Department']),
                row['Department'],  
                desig_mapping.get(row['Designation']),
                None,  
                0.0,  
                0.0   
            ))


            aadhaar = str(row['Aadhaar Number']) if pd.notna(row['Aadhaar Number']) else None
            if aadhaar:
                if aadhaar in used_aadhaar:

                    base = aadhaar[:-1]
                    last_digit = int(aadhaar[-1])
                    new_last_digit = (last_digit + 1) % 10
                    aadhaar = f"{base}{new_last_digit}"
                    while aadhaar in used_aadhaar.values():
                        new_last_digit = (new_last_digit + 1) % 10
                        aadhaar = f"{base}{new_last_digit}"
                used_aadhaar[str(row['Aadhaar Number'])] = aadhaar


            pan = str(row['PAN Number']) if pd.notna(row['PAN Number']) else None
            if pan:
                if pan in used_pan:

                    base = pan[:-1]
                    last_char = pan[-1]

                    if last_char.isdigit():
                        new_last_char = str((int(last_char) + 1) % 10)
                    else:

                        new_last_char = chr((ord(last_char.upper()) - ord('A') + 1) % 26 + ord('A'))
                    pan = f"{base}{new_last_char}"
                    while pan in used_pan.values():
                        if new_last_char.isdigit():
                            new_last_char = str((int(new_last_char) + 1) % 10)
                        else:
                            new_last_char = chr((ord(new_last_char) - ord('A') + 1) % 26 + ord('A'))
                        pan = f"{base}{new_last_char}"
                used_pan[str(row['PAN Number'])] = pan


            personal_data.append((
                row['Employee Code'],
                row['Gender'] if pd.notna(row['Gender']) else None,
                self.parse_date(row['Date Of Birth']),
                row['Marital Status'] if pd.notna(row['Marital Status']) else None,
                row['Present Address'] if pd.notna(row['Present Address']) else None,
                row['Permanent Address'] if pd.notna(row['Permanent Address']) else None,
                pan,
                aadhaar
            ))


            financial_data.append((
                row['Employee Code'],
                row['Bank Name'] if pd.notna(row['Bank Name']) else None,
                row['Account Number'] if pd.notna(row['Account Number']) else None,
                row['IFSC Code'] if pd.notna(row['IFSC Code']) else None
            ))


        self.bulk_insert_safe('employee',
                            ['employee_code', 'employee_name', 'email', 'mobile_number',
                             'date_of_joining', 'employee_type', 'grade', 'status',
                             'department_id', 'department_name', 'designation_id', 'primary_manager_id',
                             'past_experience', 'current_experience'],
                            emp_data,
                            primary_key_columns=['employee_code'])

        self.bulk_insert_safe('employee_personal',
                            ['employee_code', 'gender', 'date_of_birth', 'marital_status',
                             'present_address', 'permanent_address', 'pan_number', 'aadhaar_number'],
                            personal_data,
                            primary_key_columns=['employee_code'])

        self.bulk_insert_safe('employee_financial',
                            ['employee_code', 'bank_name', 'account_number', 'ifsc_code'],
                            financial_data,
                            primary_key_columns=['employee_code'])

    def seed_work_profiles(self, df_work: pd.DataFrame, dept_mapping: Dict, desig_mapping: Dict):

        logger.info("Processing work profiles...")

        for _, row in df_work.iterrows():

            update_query = """
                UPDATE employee 
                SET department_id = COALESCE(%s, department_id),
                    department_name = COALESCE(%s, department_name),
                    designation_id = COALESCE(%s, designation_id)
                WHERE employee_code = %s
            """

            dept_id = dept_mapping.get(row['Assigned Department']) if pd.notna(row['Assigned Department']) else None
            dept_name = row['Assigned Department'] if pd.notna(row['Assigned Department']) else None
            desig_id = desig_mapping.get(row['Designation']) if pd.notna(row['Designation']) else None

            try:
                self.execute_query(update_query, (dept_id, dept_name, desig_id, row['Employee Code']))
            except Exception as e:
                logger.warning(f"Failed to update work profile for {row['Employee Code']}: {e}")

    def update_experience_data(self, df_exp: pd.DataFrame):

        logger.info("Updating employee experience data...")

        for _, row in df_exp.iterrows():
            update_query = """
                UPDATE employee 
                SET current_experience = %s,
                    past_experience = %s
                WHERE employee_code = %s
            """
            try:
                self.execute_query(update_query, (
                    float(row['Current Experience']),
                    float(row['Past Experience']),
                    row['Employee Code']
                ))
            except Exception as e:
                logger.warning(f"Failed to update experience for {row['Employee Code']}: {e}")

    def seed_employee_exits(self, df_exit: pd.DataFrame):

        logger.info("Seeding employee exits...")

        exit_data = []
        for _, row in df_exit.iterrows():
            exit_data.append((
                row['Employee Code'],
                pd.to_datetime(row['Exit Date']).date(),
                pd.to_datetime(row['Expected Resignation Date']).date(),
                'Resignation',  
                f"Employee {row['Employee Name']} resigned"
            ))

        self.bulk_insert_safe('employee_exit',
                            ['employee_code', 'exit_date', 'last_working_date',
                             'exit_reason', 'exit_comments'],
                            exit_data,
                            primary_key_columns=['employee_code'])


        for _, row in df_exit.iterrows():
            try:
                update_query = "UPDATE employee SET status = 'Inactive' WHERE employee_code = %s"
                self.execute_query(update_query, (row['Employee Code'],))
            except Exception as e:
                logger.warning(f"Failed to update status for exited employee {row['Employee Code']}: {e}")

    def seed_projects(self, df_timesheet: pd.DataFrame):
        logger.info("Seeding projects...")


        project_query = """
            SELECT project_id, project_name
            FROM project
            WHERE status = 'Active'
        """
        self.cursor.execute(project_query)
        existing_projects = {pid: name for pid, name in self.cursor.fetchall()}


        project_data = []
        for project_id in df_timesheet['project_id'].unique():
            if project_id not in existing_projects:
                project_data.append((
                    project_id,
                    f"Project {project_id}", 
                    'Default Client', 
                    'Active',
                    datetime.now().date(), 
                    None  
                ))

        if project_data:
            self.bulk_insert_safe('project',
                                ['project_id', 'project_name', 'client_name', 'status',
                                 'start_date', 'end_date'],
                                project_data,
                                primary_key_columns=['project_id'])

    def seed_attendance(self, df_attendance: pd.DataFrame):
        logger.info("Seeding attendance data...")

        attendance_data = []
        for _, row in df_attendance.iterrows():
            try:
                attendance_data.append((
                    pd.to_datetime(row['Date']).date(),
                    row['Employee Code'],
                    pd.to_datetime(row['Clock-In Time'], format='%H:%M:%S').time(),
                    pd.to_datetime(row['Clock-Out Time'], format='%H:%M:%S').time(),
                    'Present'
                ))
            except Exception as e:
                logger.warning(f"Failed to parse attendance record: {e}")
                continue

        self.bulk_insert_safe('attendance',
                            ['attendance_date', 'employee_code', 'clock_in_time',
                             'clock_out_time', 'attendance_type'],
                            attendance_data,
                            primary_key_columns=['employee_code', 'attendance_date'])

    def seed_timesheets(self, df_timesheet: pd.DataFrame):
        logger.info("Seeding timesheet data...")

        timesheet_data = []
        for _, row in df_timesheet.iterrows():
            try:
                timesheet_data.append((
                    pd.to_datetime(row['work_date']).date(),
                    row['employee_code'],
                    row['project_id'],
                    float(row['hours_worked']),
                    row['task_description'] if pd.notna(row['task_description']) else None
                ))
            except Exception as e:
                logger.warning(f"Failed to parse timesheet record: {e}")
                continue

        self.bulk_insert_safe('timesheet',
                            ['work_date', 'employee_code', 'project_id', 'hours_worked',
                             'task_description'],
                            timesheet_data,
                            primary_key_columns=['employee_code', 'project_id', 'work_date'])

    def seed_project_allocations(self, df_allocations: pd.DataFrame):

        logger.info("Seeding project allocations...")

        allocation_data = []
        for _, row in df_allocations.iterrows():
            try:
                allocation_data.append((
                    row['employee_code'],
                    row['project_id'],
                    float(row['allocation_percentage']) if pd.notna(row['allocation_percentage']) else 100.0,
                    pd.to_datetime(row['effective_from']).date(),
                    pd.to_datetime(row['effective_to']).date() if pd.notna(row['effective_to']) else None,
                    'Active',
                    row['created_by'] if pd.notna(row['created_by']) else None,
                    row['change_reason'] if pd.notna(row['change_reason']) else None
                ))
            except Exception as e:
                logger.warning(f"Failed to parse project allocation record: {e}")
                continue

        self.bulk_insert_safe('project_allocation',
                            ['employee_code', 'project_id', 'allocation_percentage',
                             'effective_from', 'effective_to', 'status', 'created_by',
                             'change_reason'],
                            allocation_data)

    def seed_database(self, csv_files: Dict[str, str], clean_existing: bool = False,
                 tables_to_clean: List[str] = None):

        try:
            logger.info(f"Starting database seeding with files: {list(csv_files.keys())}")
            
            if clean_existing:
                self.clean_existing_data(tables_to_clean)


            if 'employee_master' in csv_files and csv_files['employee_master'] is not None:
                df_emp = csv_files['employee_master']
                if isinstance(df_emp, str):  
                    logger.info(f"Reading employee_master from file: {df_emp}")
                    df_emp = pd.read_csv(df_emp)
                logger.info(f"Processing {len(df_emp)} employee records")
                self.seed_departments_and_designations(df_emp)


            dept_mapping, desig_mapping = self.get_reference_mappings()
            logger.info(f"Found {len(dept_mapping)} departments and {len(desig_mapping)} designations")


            if 'employee_master' in csv_files and csv_files['employee_master'] is not None:
                logger.info("Seeding employee data...")
                self.seed_employees(df_emp, dept_mapping, desig_mapping)


            if 'work_profile' in csv_files and csv_files['work_profile'] is not None:
                df_work = csv_files['work_profile']
                if isinstance(df_work, str):
                    logger.info(f"Reading work_profile from file: {df_work}")
                    df_work = pd.read_csv(df_work)
                logger.info(f"Processing {len(df_work)} work profiles")
                self.seed_work_profiles(df_work, dept_mapping, desig_mapping)


            if 'experience_report' in csv_files and csv_files['experience_report'] is not None:
                df_exp = csv_files['experience_report']
                if isinstance(df_exp, str):
                    logger.info(f"Reading experience_report from file: {df_exp}")
                    df_exp = pd.read_csv(df_exp)
                logger.info(f"Processing {len(df_exp)} experience records")
                self.update_experience_data(df_exp)


            if 'employee_exit' in csv_files and csv_files['employee_exit'] is not None:
                df_exit = csv_files['employee_exit']
                if isinstance(df_exit, str):
                    logger.info(f"Reading employee_exit from file: {df_exit}")
                    df_exit = pd.read_csv(df_exit)
                logger.info(f"Processing {len(df_exit)} exit records")
                self.seed_employee_exits(df_exit)


            if 'timesheet_report' in csv_files and csv_files['timesheet_report'] is not None:
                df_timesheet = csv_files['timesheet_report']
                if isinstance(df_timesheet, str):
                    logger.info(f"Reading timesheet_report from file: {df_timesheet}")
                    df_timesheet = pd.read_csv(df_timesheet)
                logger.info(f"Processing {len(df_timesheet)} timesheet records")
                self.seed_projects(df_timesheet)


            if 'project_allocations' in csv_files and csv_files['project_allocations'] is not None:
                df_allocations = csv_files['project_allocations']
                if isinstance(df_allocations, str):
                    logger.info(f"Reading project_allocations from file: {df_allocations}")
                    df_allocations = pd.read_csv(df_allocations)
                logger.info(f"Processing {len(df_allocations)} allocation records")
                self.seed_project_allocations(df_allocations)


            if 'resource_utilization' in csv_files and csv_files['resource_utilization'] is not None:
                df_utilization = csv_files['resource_utilization']
                if isinstance(df_utilization, str):
                    logger.info(f"Reading resource_utilization from file: {df_utilization}")
                    df_utilization = pd.read_csv(df_utilization)
                logger.info(f"Processing {len(df_utilization)} resource utilization records")
                self.seed_resource_utilization(df_utilization)


            if 'attendance_report' in csv_files and csv_files['attendance_report'] is not None:
                df_attendance = csv_files['attendance_report']
                if isinstance(df_attendance, str):
                    logger.info(f"Reading attendance_report from file: {df_attendance}")
                    df_attendance = pd.read_csv(df_attendance)
                logger.info(f"Processing {len(df_attendance)} attendance records")
                self.seed_attendance(df_attendance)


            if 'timesheet_report' in csv_files and csv_files['timesheet_report'] is not None:
                logger.info(f"Processing {len(df_timesheet)} timesheet entries")
                self.seed_timesheets(df_timesheet)
                
            if 'resource_utilization' in csv_files and csv_files['resource_utilization'] is not None:
                logger.info(f"Processing {len(df_utilization)} resource utilization entries")
                self.seed_resource_utilization(df_utilization)

            logger.info("Database seeding completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error seeding database: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        
    def seed_resource_utilization(self, df_utilization: pd.DataFrame):

        logger.info("Seeding resource utilization data...")

        utilization_data = []
        for _, row in df_utilization.iterrows():
            try:
                utilization_data.append((
                    row['project_id'],
                    pd.to_datetime(row['week_start_date']).date(),
                    float(row['estimated_hours']) if pd.notna(row['estimated_hours']) else 0.0
                ))
            except Exception as e:
                logger.warning(f"Failed to parse resource utilization record: {e}")
                continue

        self.bulk_insert_safe('resource_utilization',
                            ['project_id', 'week_start_date', 'estimated_hours'],
                            utilization_data,
                            primary_key_columns=['project_id', 'week_start_date'])

def main():

    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'dbname': os.getenv('DB_NAME', 'your_database'),
        'user': os.getenv('DB_USER', 'your_user'),
        'password': os.getenv('DB_PASSWORD', 'your_password')
    }


    csv_files = {
        'employee_master': 'employee_master.csv',
        'employee_exit': 'employee_exit_report.csv',
        'experience_report': 'experience_report.csv',
        'work_profile': 'employee_work_profile.csv',
        'attendance_report': 'attendance_report_daily.csv',
        'timesheet_report': 'timesheet_report_clean.csv',
        'project_allocations': 'project_allocations.csv',
        'resource_utilization': 'resource_utilization.csv'  
    }


    for file_type, file_path in csv_files.items():
        if not os.path.exists(file_path):
            logger.warning(f"CSV file {file_path} not found. Skipping {file_type} data.")
            csv_files[file_type] = None


    csv_files = {k: v for k, v in csv_files.items() if v is not None}

    if not csv_files:
        logger.error("No CSV files found. Please ensure CSV files are in the current directory.")
        return


    seeder = DatabaseSeeder(db_config)
    try:
        seeder.connect()
        seeder.seed_database(csv_files)
    finally:
        seeder.disconnect()


if __name__ == "__main__":
    main()