# Employee Reports Dashboard

A comprehensive web application for managing employee data, generating reports, and running analytics using Streamlit, PostgreSQL, and AI integration.

![Employee Reports Dashboard]()

## 📋 Overview

Employee Reports Dashboard is a powerful tool designed to streamline employee data management, generate insightful reports, and provide AI-assisted data analysis. The application helps HR teams and managers to efficiently manage employee records, track performance, summarize tasks, and generate custom reports.

## ✨ Features

- **User Authentication**: Secure login system to protect sensitive employee data
- **File Upload**: Import employee data from various file formats
- **Predefined Reports**: Ready-to-use reports for common HR analytics
- **Custom Queries**: Run custom SQL queries against your employee database
- **AI Query Assistant**: Use natural language to query your database with Gemini AI integration
- **Tasks Summarizer**: AI-powered tool to summarize employee tasks and activities
- **Standard Reports**: Generate standardized reports for compliance and regular reviews
- **Activity Logging**: Track all system activities for audit purposes

## 🔐 Authentication System

The application implements a robust authentication system to protect sensitive employee data:

- **Session-based authentication**: Secure user sessions managed through Streamlit's session state
- **Credential verification**: Username and password verification against stored credentials
- **Password hashing**: Optional SHA-256 password hashing for enhanced security
- **Environment variables**: Authentication credentials stored securely in environment variables
- **Configurable credentials**: Easy configuration through `.env` file or system environment variables
- **Login form**: User-friendly interface with validation and error handling
- **Session management**: Automatic session tracking and timeout functionality
- **Logout capability**: Secure session termination when users log out
- **Authentication state**: Persistent authentication state during user session

To set up authentication:

1. Configure credentials in your `.env` file:

   ```
   APP_USERNAME=your_username
   APP_PASSWORD=your_password
   # Or use a hashed password for better security
   # APP_PASSWORD_HASH=your_hashed_password
   ```

2. For production, consider using password hashing:
   ```python
   import hashlib
   hashed_password = hashlib.sha256("your_password".encode()).hexdigest()
   # Then set APP_PASSWORD_HASH to this value in your .env file
   ```

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Gemini API key (for AI features)

### Setup Instructions

1. Clone the repository:

   ```bash
   git clone https://github.com/hritxx/employee_manager.git
   cd employee_manager
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory with the following variables:

   ```
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=employee_db
   DB_USER=postgres
   DB_PASSWORD=your_password

   # API Keys
   GEMINI_API_KEY=your_gemini_api_key
   ```

5. Initialize the database:
   ```bash
   python -m scripts.init_db
   ```

## 🚀 Usage

1. Start the application:

   ```bash
   streamlit run app.py
   ```

2. Open your browser and navigate to `http://localhost:8501`

3. Log in with your credentials

4. Navigate through the tabs to access different features:
   - 📂 File Upload: Import employee data files
   - 📊 Predefined Reports: Access ready-made analytical reports
   - 🔍 Custom Queries: Write and execute custom SQL queries
   - 🤖 AI Query Assistant: Use natural language to query your data
   - 🤖 Tasks Summarizer: Get AI-generated summaries of employee tasks
   - 📋 Standard Reports: Generate compliance and periodic reports
   - 🧾 Logs: View system activity logs

## 📊 Application Components

### Authentication System

The application uses a custom authentication system managed by the `AuthManager` class to secure data and functionalities. This class handles login verification, session management, and access control throughout the application.

### Data Management

- PostgreSQL database for structured data storage
- ETL pipeline for data processing and transformation
- File upload functionality supporting various formats

### Reporting System

- Predefined reports for common HR needs
- Custom query interface for advanced users
- Standard reports for compliance and documentation

### AI Integration

- Natural language query processing using Gemini AI
- Task summarization and analysis tools

## 🔧 Configuration

The application uses three main configuration files:

- `app_config`: General application settings
- `etl_config`: Data processing pipeline configuration
- `db_config`: Database connection settings

## 💻 Technologies Used

- **Backend**: Python, SQLAlchemy
- **Frontend**: Streamlit
- **Database**: PostgreSQL
- **AI Integration**: Google Gemini API
- **Data Processing**: Pandas, custom ETL pipeline
- **Authentication**: Custom session-based auth with optional password hashing

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add some amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Contact

For questions or support, please contact the development team at [hriteekroy1869@gmail.com](mailto:hriteekroy1869@gmail.com).

---

© 2025 Employee Reports Dashboard | All Rights Reserved
# employee_manager
