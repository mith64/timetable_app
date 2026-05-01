import streamlit as st
import pandas as pd
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
import time
import gc
import sys

# Try to import openpyxl with error handling
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    st.warning("⚠️ openpyxl not installed. Please run: pip install openpyxl")

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DB_FILE = os.path.join(BASE_DIR, "users.json")
TIMETABLE_FILE = os.path.join(BASE_DIR, "timetable.xlsx")
ARRANGEMENT_FILE = os.path.join(BASE_DIR, "arrangements.json")
BACKUP_FOLDER = os.path.join(BASE_DIR, "backups")

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'role' not in st.session_state:
    st.session_state.role = None
if 'timetable_df' not in st.session_state:
    st.session_state.timetable_df = None

# Create necessary directories
def create_directories():
    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER, exist_ok=True)

create_directories()

# Hash password function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Load users from JSON file
def load_users():
    try:
        if os.path.exists(USER_DB_FILE):
            with open(USER_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            default_users = {
                "admin": {
                    "password": hash_password("admin123"),
                    "name": "Administrator",
                    "designation": "Admin",
                    "role": "admin"
                }
            }
            save_users(default_users)
            return default_users
    except Exception as e:
        st.error(f"Error loading users: {e}")
        return {"admin": {"password": hash_password("admin123"), "name": "Admin", "designation": "Admin", "role": "admin"}}

# Save users to JSON file
def save_users(users):
    try:
        with open(USER_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4)
    except Exception as e:
        st.error(f"Error saving users: {e}")

# Load arrangements
def load_arrangements():
    try:
        if os.path.exists(ARRANGEMENT_FILE):
            with open(ARRANGEMENT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {}
    except Exception as e:
        st.error(f"Error loading arrangements: {e}")
        return {}

# Save arrangements
def save_arrangements(arrangements):
    try:
        with open(ARRANGEMENT_FILE, 'w', encoding='utf-8') as f:
            json.dump(arrangements, f, indent=4)
    except Exception as e:
        st.error(f"Error saving arrangements: {e}")

# Check if file is locked
def is_file_locked(filepath):
    try:
        with open(filepath, 'a'):
            pass
        return False
    except (PermissionError, OSError):
        return True

# Load timetable with multiple engine support
@st.cache_data(ttl=300)
def load_timetable():
    """Load timetable with multiple fallback methods"""
    
    # First check if openpyxl is available
    if not OPENPYXL_AVAILABLE:
        st.error("❌ openpyxl package is not installed!")
        st.info("Please run this command in your terminal:\n```bash\npip install openpyxl\n```")
        return create_sample_timetable()
    
    try:
        if not os.path.exists(TIMETABLE_FILE):
            st.warning("No timetable file found. Creating sample data...")
            return create_sample_timetable()
        
        if is_file_locked(TIMETABLE_FILE):
            st.error("⚠️ Timetable file is locked by another process")
            if st.session_state.timetable_df is not None:
                return st.session_state.timetable_df
            return create_sample_timetable()
        
        # Try different engines
        engines_to_try = ['openpyxl', 'xlrd', 'calamine']
        
        for engine in engines_to_try:
            try:
                df = pd.read_excel(TIMETABLE_FILE, engine=engine)
                if not df.empty:
                    st.session_state.timetable_df = df
                    return df
            except Exception as e:
                continue
        
        # If all engines fail, try alternative method with temp file
        try:
            with open(TIMETABLE_FILE, 'rb') as f:
                data = f.read()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            
            df = pd.read_excel(tmp_path, engine='openpyxl')
            os.unlink(tmp_path)
            st.session_state.timetable_df = df
            return df
        except Exception as e:
            st.error(f"Failed to read file: {e}")
            return create_sample_timetable()
            
    except Exception as e:
        st.error(f"Error loading timetable: {e}")
        if st.session_state.timetable_df is not None:
            return st.session_state.timetable_df
        return create_sample_timetable()

def create_sample_timetable():
    """Create sample timetable data"""
    sample_data = {
        'Day': ['Monday', 'Monday', 'Tuesday', 'Tuesday', 'Wednesday', 'Wednesday', 'Thursday', 'Thursday', 'Friday', 'Friday', 'Saturday', 'Saturday'],
        'Time': ['9:00-10:00', '10:00-11:00', '9:00-10:00', '10:00-11:00', '9:00-10:00', '10:00-11:00', '9:00-10:00', '10:00-11:00', '9:00-10:00', '10:00-11:00', '9:00-10:00', '10:00-11:00'],
        'Teacher': ['Dr. Smith', 'Prof. Johnson', 'Dr. Smith', 'Prof. Brown', 'Prof. Johnson', 'Dr. Smith', 'Prof. Brown', 'Prof. Johnson', 'Dr. Smith', 'Prof. Brown', 'Dr. Smith', 'Prof. Johnson'],
        'Subject': ['Mathematics', 'Physics', 'Mathematics', 'Chemistry', 'Physics', 'Mathematics', 'Chemistry', 'Biology', 'Mathematics', 'Physics', 'Mathematics', 'Computer Science'],
        'Class': ['10A', '10A', '10B', '10B', '10C', '10C', '10A', '10A', '10B', '10B', '10C', '10C'],
        'Designation': ['Math Teacher', 'Physics Teacher', 'Math Teacher', 'Chemistry Teacher', 'Physics Teacher', 'Math Teacher', 'Chemistry Teacher', 'Biology Teacher', 'Math Teacher', 'Physics Teacher', 'Math Teacher', 'CS Teacher']
    }
    df = pd.DataFrame(sample_data)
    save_timetable(df)
    return df

def save_timetable(df):
    """Save timetable with retry logic"""
    if not OPENPYXL_AVAILABLE:
        st.error("Cannot save: openpyxl not installed")
        return False
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            gc.collect()
            
            if os.path.exists(TIMETABLE_FILE) and is_file_locked(TIMETABLE_FILE):
                time.sleep(1)
                continue
            
            # Save to temp file first
            temp_file = TIMETABLE_FILE + ".tmp"
            df.to_excel(temp_file, index=False, engine='openpyxl')
            
            # Replace original
            if os.path.exists(TIMETABLE_FILE):
                os.remove(TIMETABLE_FILE)
            os.rename(temp_file, TIMETABLE_FILE)
            
            st.session_state.timetable_df = df
            st.cache_data.clear()
            return True
            
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"Failed to save: {e}")
            time.sleep(1)
    
    return False

def delete_timetable_file():
    """Delete the timetable file safely"""
    try:
        if os.path.exists(TIMETABLE_FILE):
            if is_file_locked(TIMETABLE_FILE):
                st.error("Cannot delete: File is locked")
                return False
            
            backup_name = os.path.join(BACKUP_FOLDER, f"deleted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            shutil.copy2(TIMETABLE_FILE, backup_name)
            
            os.remove(TIMETABLE_FILE)
            st.success(f"File deleted. Backup saved")
            st.cache_data.clear()
            return True
    except Exception as e:
        st.error(f"Error deleting file: {e}")
        return False

# Login function
def login(username, password):
    users = load_users()
    if username in users and users[username]['password'] == hash_password(password):
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = users[username]['role']
        st.session_state.name = users[username]['name']
        st.session_state.designation = users[username]['designation']
        return True
    return False

# Logout function
def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.name = None
    st.session_state.designation = None
    st.rerun()

# Check and install packages
def check_packages():
    """Check if required packages are installed"""
    missing_packages = []
    
    try:
        import openpyxl
    except ImportError:
        missing_packages.append("openpyxl")
    
    try:
        import pandas
    except ImportError:
        missing_packages.append("pandas")
    
    if missing_packages:
        st.error(f"❌ Missing packages: {', '.join(missing_packages)}")
        st.info(f"""
        Please install missing packages by running:
        ```bash
        pip install {' '.join(missing_packages)}
