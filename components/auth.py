import streamlit as st
import os
import hashlib
from typing import Optional

class AuthManager:
    """Handles authentication for the Streamlit app"""
    
    def __init__(self):
        self.valid_username = os.getenv('APP_USERNAME')
        self.valid_password = os.getenv('APP_PASSWORD')
        
        # Optional: Use hashed passwords for better security
        self.valid_password_hash = os.getenv('APP_PASSWORD_HASH')
        
    def hash_password(self, password: str) -> str:
        """Create SHA-256 hash of password"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_credentials(self, username: str, password: str) -> bool:
        """Verify username and password against environment variables"""
        if not self.valid_username or not (self.valid_password or self.valid_password_hash):
            st.error("Authentication credentials not configured. Please check environment variables.")
            return False
        
        # Check username
        if username != self.valid_username:
            return False
        
        # Check password (plain text or hashed)
        if self.valid_password_hash:
            # Use hashed password verification
            return self.hash_password(password) == self.valid_password_hash
        else:
            # Use plain text password verification
            return password == self.valid_password
    
    def login_form(self) -> bool:
        """Display login form and handle authentication"""
        st.markdown("# 🔐 Employee Reports Dashboard")
        st.markdown("### Please log in to access the system")
        
        # Create login form
        with st.form("login_form"):
            st.markdown("#### Login Credentials")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                login_button = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if login_button:
                if not username or not password:
                    st.error("⚠️ Please enter both username and password")
                    return False
                
                if self.verify_credentials(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("✅ Login successful! Redirecting...")
                    st.rerun()
                    return True
                else:
                    st.error("❌ Invalid username or password")
                    return False
        
        # Add some styling and information
        st.markdown("---")
        st.markdown("##### 📝 Note:")
        st.info("Contact your system administrator if you need access credentials.")
        
        return False
    
    def logout(self):
        """Handle user logout"""
        st.session_state.authenticated = False
        if 'username' in st.session_state:
            del st.session_state.username
        st.rerun()
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return st.session_state.get('authenticated', False)
    
    def get_current_user(self) -> Optional[str]:
        """Get current logged-in username"""
        return st.session_state.get('username', None)
    
    def require_auth(self) -> bool:
        """Decorator-like function to require authentication"""
        if not self.is_authenticated():
            return self.login_form()
        return True