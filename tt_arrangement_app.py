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

# Try to import openpyxl with error handling
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

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
if 'password_changed' not in st.session_state:
    st.session_state.password_changed = False
if 'show_password_change' not in st.session_state:
    st.session_state.show_password_change = False

# Create necessary directories
def create_directories():
    """Create necessary directories if they don't exist"""
    try:
        if not os.path.exists(BACKUP_FOLDER):
            os.makedirs(BACKUP_FOLDER, exist_ok=True)
    except Exception as e:
        st.error(f"Error creating directories: {e}")

create_directories()

# Hash password function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Load users from JSON file
def load_users():
    """Load users with proper error handling"""
    try:
        if os.path.exists(USER_DB_FILE):
            with open(USER_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Default admin user with flag for first login
            default_users = {
                "admin": {
                    "password": hash_password("admin123"),
                    "name": "Administrator",
                    "designation": "Admin",
                    "role": "admin",
                    "first_login": True,
                    "password_last_changed": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            save_users(default_users)
            return default_users
    except json.JSONDecodeError:
        st.error("Users file is corrupted. Creating new one...")
        default_users = {
            "admin": {
                "password": hash_password("admin123"),
                "name": "Administrator",
                "designation": "Admin",
                "role": "admin",
                "first_login": True,
                "password_last_changed": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        save_users(default_users)
        return default_users
    except Exception as e:
        st.error(f"Error loading users: {e}")
        return {"admin": {"password": hash_password("admin123"), "name": "Admin", "designation": "Admin", "role": "admin", "first_login": True}}

# Save users to JSON file
def save_users(users):
    """Save users with error handling"""
    try:
        with open(USER_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving users: {e}")
        return False

# Load arrangements - FIXED VERSION
def load_arrangements():
    """Load arrangements with proper error handling"""
    try:
        if os.path.exists(ARRANGEMENT_FILE):
            with open(ARRANGEMENT_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():  # Check if file is not empty
                    return json.loads(content)
                else:
                    return {}
        else:
            # Create empty arrangements file
            save_arrangements({})
            return {}
    except json.JSONDecodeError:
        st.warning("Arrangements file was corrupted. Creating new one...")
        save_arrangements({})
        return {}
    except Exception as e:
        st.error(f"Error loading arrangements: {e}")
        return {}

# Save arrangements - FIXED VERSION
def save_arrangements(arrangements):
    """Save arrangements with error handling"""
    try:
        # Ensure arrangements is a dictionary
        if arrangements is None:
            arrangements = {}
        
        with open(ARRANGEMENT_FILE, 'w', encoding='utf-8') as f:
            json.dump(arrangements, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving arrangements: {e}")
        return False

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
    
    if not OPENPYXL_AVAILABLE:
        st.error("❌ openpyxl package is not installed!")
        return create_sample_timetable()
    
    try:
        if not os.path.exists(TIMETABLE_FILE):
            st.warning("No timetable file found. Creating sample data...")
            return create_sample_timetable()
        
        # Try to read with openpyxl
        try:
            df = pd.read_excel(TIMETABLE_FILE, engine='openpyxl')
            if not df.empty:
                st.session_state.timetable_df = df
                return df
        except Exception as e:
            st.warning(f"Could not read with openpyxl: {e}")
            
        # Try alternative method without engine specification
        try:
            df = pd.read_excel(TIMETABLE_FILE)
            if not df.empty:
                st.session_state.timetable_df = df
                return df
        except Exception as e:
            st.warning(f"Could not read with default engine: {e}")
            
        # If all fail, create sample
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
    """Save timetable with simplified approach"""
    
    if not OPENPYXL_AVAILABLE:
        st.error("Cannot save: openpyxl not installed")
        return False
    
    try:
        gc.collect()
        time.sleep(0.5)
        
        # Method 1: Direct save with explicit engine
        try:
            df.to_excel(TIMETABLE_FILE, index=False, engine='openpyxl')
            st.session_state.timetable_df = df
            st.cache_data.clear()
            return True
        except Exception as e1:
            st.warning(f"Direct save failed: {e1}")
            
            # Method 2: Save with xlsxwriter (alternative)
            try:
                df.to_excel(TIMETABLE_FILE, index=False, engine='xlsxwriter')
                st.session_state.timetable_df = df
                st.cache_data.clear()
                return True
            except Exception as e2:
                st.warning(f"Alternative engine failed: {e2}")
                
                # Method 3: Use temporary file with proper extension
                try:
                    temp_file = tempfile.NamedTemporaryFile(
                        delete=False, 
                        suffix='.xlsx',
                        mode='wb'
                    )
                    temp_file.close()
                    
                    df.to_excel(temp_file.name, index=False, engine='openpyxl')
                    
                    if os.path.exists(TIMETABLE_FILE):
                        os.remove(TIMETABLE_FILE)
                    shutil.copy2(temp_file.name, TIMETABLE_FILE)
                    os.unlink(temp_file.name)
                    
                    st.session_state.timetable_df = df
                    st.cache_data.clear()
                    return True
                except Exception as e3:
                    st.error(f"All save methods failed. Last error: {e3}")
                    return False
                    
    except Exception as e:
        st.error(f"Unexpected error saving: {e}")
        return False

def delete_timetable_file():
    """Delete the timetable file safely"""
    try:
        if os.path.exists(TIMETABLE_FILE):
            backup_name = os.path.join(BACKUP_FOLDER, f"deleted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            shutil.copy2(TIMETABLE_FILE, backup_name)
            os.remove(TIMETABLE_FILE)
            st.success(f"File deleted. Backup saved")
            st.cache_data.clear()
            return True
    except Exception as e:
        st.error(f"Error deleting file: {e}")
        return False

# Change password function
def change_password(username, old_password, new_password, confirm_password):
    """Change user password with validation"""
    users = load_users()
    
    if username not in users:
        return False, "User not found"
    
    # Verify old password
    if users[username]['password'] != hash_password(old_password):
        return False, "Current password is incorrect"
    
    # Check if new password is same as old
    if old_password == new_password:
        return False, "New password cannot be the same as current password"
    
    # Check password length
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long"
    
    # Check if passwords match
    if new_password != confirm_password:
        return False, "New passwords do not match"
    
    # Update password
    users[username]['password'] = hash_password(new_password)
    users[username]['first_login'] = False
    users[username]['password_last_changed'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    save_users(users)
    return True, "Password changed successfully!"

# Reset user password (admin only)
def reset_user_password(username, new_password):
    """Admin function to reset user password"""
    users = load_users()
    
    if username not in users:
        return False, "User not found"
    
    if len(new_password) < 6:
        return False, "Password must be at least 6 characters long"
    
    users[username]['password'] = hash_password(new_password)
    users[username]['first_login'] = False
    users[username]['password_last_changed'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    save_users(users)
    return True, f"Password reset for {username} successfully!"

# Password change form
def password_change_form():
    """Display password change form"""
    st.markdown("---")
    st.subheader("🔐 Change Password")
    st.warning("⚠️ For security reasons, please change your default password")
    
    with st.form("change_password_form"):
        old_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password", 
                                     help="Password must be at least 6 characters long")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Change Password", type="primary")
        with col2:
            skip = st.form_submit_button("Remind Me Later")
    
    if submit:
        if old_password and new_password and confirm_password:
            success, message = change_password(
                st.session_state.username, 
                old_password, 
                new_password, 
                confirm_password
            )
            if success:
                st.success(message)
                st.session_state.password_changed = True
                st.session_state.show_password_change = False
                st.balloons()
                time.sleep(1)
                st.rerun()
            else:
                st.error(message)
        else:
            st.error("Please fill all fields")
    
    if skip:
        st.session_state.show_password_change = False
        st.rerun()

# Login function with first login check
def login(username, password):
    users = load_users()
    if username in users and users[username]['password'] == hash_password(password):
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = users[username]['role']
        st.session_state.name = users[username]['name']
        st.session_state.designation = users[username]['designation']
        
        # Check if first login and user is admin
        if users[username].get('first_login', False) and username == 'admin':
            st.session_state.show_password_change = True
        else:
            st.session_state.show_password_change = False
        
        return True
    return False

# Logout function
def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.name = None
    st.session_state.designation = None
    st.session_state.show_password_change = False
    st.session_state.password_changed = False
    st.rerun()

# Admin panel
def admin_panel():
    st.header("👑 Admin Panel")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Create User", "Manage Users", "Upload Timetable", "Arrangement Management", "Security Settings"])
    
    # Create User Tab
    with tab1:
        st.subheader("Create New User")
        with st.form("create_user_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password", help="Minimum 6 characters")
            new_name = st.text_input("Full Name")
            new_designation = st.text_input("Designation")
            new_role = st.selectbox("Role", ["user", "admin"])
            
            if st.form_submit_button("Create User"):
                if new_username and new_password and new_name and new_designation:
                    if len(new_password) < 6:
                        st.error("Password must be at least 6 characters long!")
                    else:
                        users = load_users()
                        if new_username not in users:
                            users[new_username] = {
                                "password": hash_password(new_password),
                                "name": new_name,
                                "designation": new_designation,
                                "role": new_role,
                                "first_login": False,
                                "password_last_changed": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            save_users(users)
                            st.success(f"User {new_username} created successfully!")
                            st.rerun()
                        else:
                            st.error("Username already exists!")
                else:
                    st.error("Please fill all fields!")
    
    # Manage Users Tab
    with tab2:
        st.subheader("Manage Users")
        users = load_users()
        user_list = [u for u in users.keys() if u != 'admin']
        
        # Admin password change section
        with st.expander("🔐 Change Your Admin Password", expanded=False):
            st.write("Change your own admin password")
            with st.form("admin_change_password"):
                old_pass = st.text_input("Current Password", type="password")
                new_pass = st.text_input("New Password", type="password", help="Minimum 6 characters")
                confirm_pass = st.text_input("Confirm New Password", type="password")
                
                if st.form_submit_button("Update My Password", type="primary"):
                    if old_pass and new_pass and confirm_pass:
                        success, message = change_password("admin", old_pass, new_pass, confirm_pass)
                        if success:
                            st.success(message)
                            st.info("Please login again with your new password")
                            time.sleep(2)
                            logout()
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill all fields")
        
        st.markdown("---")
        st.subheader("User List")
        
        if user_list:
            for username in user_list:
                with st.expander(f"User: {username}"):
                    st.write(f"**Name:** {users[username]['name']}")
                    st.write(f"**Designation:** {users[username]['designation']}")
                    st.write(f"**Role:** {users[username]['role']}")
                    st.write(f"**Password Last Changed:** {users[username].get('password_last_changed', 'Never')}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"Delete {username}", key=f"del_{username}"):
                            del users[username]
                            save_users(users)
                            st.success(f"User {username} deleted!")
                            st.rerun()
                    with col2:
                        # Password reset for user
                        with st.popover(f"Reset Password for {username}"):
                            new_pass = st.text_input(f"New password for {username}", type="password", key=f"reset_pass_{username}")
                            if st.button(f"Confirm Reset", key=f"confirm_reset_{username}"):
                                if new_pass and len(new_pass) >= 6:
                                    success, message = reset_user_password(username, new_pass)
                                    if success:
                                        st.success(message)
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error(message)
                                else:
                                    st.error("Password must be at least 6 characters")
                    with col3:
                        st.caption(f"Created: {users[username].get('created_date', 'N/A')}")
        else:
            st.info("No users found except admin")
    
    # Upload Timetable Tab
    with tab3:
        st.subheader("Upload Timetable")
        
        if not OPENPYXL_AVAILABLE:
            st.error("❌ openpyxl is not installed!")
            st.code("pip install openpyxl", language="bash")
            return
        
        col1, col2 = st.columns(2)
        with col1:
            if os.path.exists(TIMETABLE_FILE):
                st.success(f"✅ Current timetable exists")
            else:
                st.warning("⚠️ No timetable file exists")
        
        with col2:
            if st.button("🗑️ Delete Current Timetable", type="secondary"):
                if delete_timetable_file():
                    st.rerun()
        
        st.markdown("---")
        
        st.info("""
        **📋 Required Excel columns:**
        - Day (Monday, Tuesday, etc.)
        - Time (9:00-10:00 format)
        - Teacher (Teacher's name)
        - Subject (Subject name)
        - Class (Class name)
        - Designation (Math Teacher, etc.)
        """)
        
        uploaded_file = st.file_uploader(
            "Choose Excel file", 
            type=['xlsx', 'xls'],
            help="Upload a new timetable file"
        )
        
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file, engine='openpyxl')
                
                required_cols = ['Day', 'Time', 'Teacher', 'Subject', 'Class', 'Designation']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    st.error(f"❌ Missing columns: {missing_cols}")
                else:
                    st.subheader("Preview of uploaded data:")
                    st.dataframe(df.head())
                    
                    if st.button("✅ Upload and Replace Current Timetable", type="primary"):
                        with st.spinner("Saving timetable..."):
                            if save_timetable(df):
                                st.success("✨ Timetable uploaded successfully!")
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Failed to save timetable")
                            
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    # Arrangement Management Tab - FIXED VERSION
    with tab4:
        st.subheader("📋 Teacher Absence & Arrangement Management")
        
        df = load_timetable()
        if df.empty:
            st.warning("Please upload timetable first")
            return
        
        # Safe loading of arrangements
        arrangements = load_arrangements()
        if arrangements is None:
            arrangements = {}
        
        days = df['Day'].unique() if not df.empty else []
        time_periods = df['Time'].unique() if not df.empty else []
        teachers = df['Teacher'].unique() if not df.empty else []
        
        if len(days) == 0 or len(time_periods) == 0 or len(teachers) == 0:
            st.warning("Timetable data is incomplete. Please check the timetable file.")
            return
        
        st.subheader("1️⃣ Report Teacher Absence")
        with st.form("absence_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                absent_teacher = st.selectbox("Absent Teacher", teachers.tolist() if hasattr(teachers, 'tolist') else list(teachers))
            with col2:
                absence_day = st.selectbox("Day of Absence", days.tolist() if hasattr(days, 'tolist') else list(days))
            with col3:
                absence_time = st.selectbox("Time Period", time_periods.tolist() if hasattr(time_periods, 'tolist') else list(time_periods))
            
            reason = st.text_area("Reason for Absence (Optional)")
            
            if st.form_submit_button("Report Absence"):
                try:
                    absent_class = df[(df['Day'] == absence_day) & 
                                     (df['Time'] == absence_time) & 
                                     (df['Teacher'] == absent_teacher)]
                    
                    if not absent_class.empty:
                        subject = absent_class.iloc[0]['Subject']
                        class_name = absent_class.iloc[0]['Class']
                        
                        busy_teachers = df[(df['Day'] == absence_day) & (df['Time'] == absence_time)]['Teacher'].tolist()
                        all_teachers = df['Teacher'].unique()
                        available = [t for t in all_teachers if t not in busy_teachers and t != absent_teacher]
                        
                        if available:
                            suggested_teacher = available[0]
                            st.success(f"✅ Suggested replacement: {suggested_teacher}")
                            st.info(f"Class: {class_name}, Subject: {subject}")
                            
                            # Save arrangement
                            arrangements = load_arrangements()
                            if arrangements is None:
                                arrangements = {}
                            
                            key = f"{absence_day}_{absence_time}_{class_name}"
                            arrangements[key] = {
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "absent_teacher": absent_teacher,
                                "replacement_teacher": suggested_teacher,
                                "class": class_name,
                                "subject": subject,
                                "day": absence_day,
                                "time": absence_time,
                                "reason": reason,
                                "status": "pending"
                            }
                            save_arrangements(arrangements)
                        else:
                            st.error("❌ No available teachers found")
                    else:
                        st.error("No class found for this teacher at specified time")
                except Exception as e:
                    st.error(f"Error reporting absence: {e}")
        
        # Display existing arrangements
        st.subheader("2️⃣ Existing Arrangements")
        arrangements = load_arrangements()
        if arrangements and len(arrangements) > 0:
            for key, value in list(arrangements.items())[:5]:  # Show last 5
                with st.expander(f"Arrangement: {value.get('day', 'N/A')} - {value.get('class', 'N/A')}"):
                    st.write(f"**Absent Teacher:** {value.get('absent_teacher', 'N/A')}")
                    st.write(f"**Replacement:** {value.get('replacement_teacher', 'N/A')}")
                    st.write(f"**Status:** {value.get('status', 'N/A')}")
                    st.write(f"**Date:** {value.get('date', 'N/A')}")
        else:
            st.info("No arrangements found")
    
    # Security Settings Tab
    with tab5:
        st.subheader("🔒 Security Settings")
        
        # Display current security info
        users = load_users()
        admin_info = users.get('admin', {})
        
        st.info(f"""
        **Security Information:**
        - **Last Password Change:** {admin_info.get('password_last_changed', 'Never')}
        - **First Login Completed:** {'✅ Yes' if not admin_info.get('first_login', True) else '⚠️ No (Default password still active)'}
        - **Total Users:** {len([u for u in users.keys() if u != 'admin'])}
        """)
        
        st.markdown("---")
        
        # Password policy settings
        st.subheader("📋 Password Policy")
        st.markdown("""
        - Minimum password length: **6 characters**
        - Password cannot be same as current password
        - Admin must change default password on first login
        - Users can change their password anytime
        """)
        
        # Option to force password change for all users
        if st.button("🔐 Force All Users to Change Password on Next Login", type="secondary"):
            users = load_users()
            for username in users:
                if username != 'admin':
                    users[username]['first_login'] = True
            save_users(users)
            st.success("All users will be required to change password on next login")

# User dashboard
def user_dashboard():
    st.header(f"👋 Welcome, {st.session_state.name}!")
    st.write(f"**Designation:** {st.session_state.designation}")
    
    # Add password change option in sidebar for users
    with st.sidebar:
        st.markdown("---")
        with st.expander("🔐 Change Password", expanded=False):
            with st.form("user_change_password"):
                old_pass = st.text_input("Current Password", type="password")
                new_pass = st.text_input("New Password", type="password", help="Minimum 6 characters")
                confirm_pass = st.text_input("Confirm New Password", type="password")
                
                if st.form_submit_button("Update Password"):
                    if old_pass and new_pass and confirm_pass:
                        success, message = change_password(st.session_state.username, old_pass, new_pass, confirm_pass)
                        if success:
                            st.success(message)
                            st.info("Please login again with your new password")
                            time.sleep(2)
                            logout()
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill all fields")
    
    df = load_timetable()
    
    if df.empty:
        st.warning("No timetable available. Please contact admin.")
        return
    
    st.subheader("📅 Your Timetable")
    user_timetable = df[df['Designation'].str.lower() == st.session_state.designation.lower()]
    
    if not user_timetable.empty:
        st.dataframe(user_timetable[['Day', 'Time', 'Subject', 'Class']], use_container_width=True)
    else:
        st.info(f"No timetable entries found")
    
    st.subheader("🔄 Your Arrangement Assignments")
    arrangements = load_arrangements()
    
    if arrangements and len(arrangements) > 0:
        user_arrangements = []
        for key, value in arrangements.items():
            if value.get('replacement_teacher') == st.session_state.name:
                if value.get('status') != 'completed':
                    user_arrangements.append(value)
        
        if user_arrangements:
            for arr in user_arrangements:
                st.info(f"""
                **📌 Assignment**
                - **Day/Time:** {arr.get('day')}, {arr.get('time')}
                - **Class:** {arr.get('class')}
                - **Subject:** {arr.get('subject')}
                - **Covering for:** {arr.get('absent_teacher')}
                """)
        else:
            st.info("No active arrangements")

# Main app
def main():
    st.set_page_config(
        page_title="Timetable Management System",
        page_icon="📚",
        layout="wide"
    )
    
    st.title("📚 Timetable Management System")
    
    if not st.session_state.logged_in:
        st.subheader("Login")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                
                if submit:
                    if login(username, password):
                        st.success(f"Welcome {st.session_state.name}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password!")
            
            st.markdown("---")
            st.caption("Demo Credentials:")
            st.caption("Admin: admin / admin123")
            st.caption("*Note: Admin will be prompted to change password on first login*")
    else:
        # Check if password change is required
        if st.session_state.show_password_change and not st.session_state.password_changed:
            password_change_form()
        else:
            with st.sidebar:
                st.write(f"**Logged in as:** {st.session_state.name}")
                st.write(f"**Username:** {st.session_state.username}")
                st.write(f"**Role:** {st.session_state.role}")
                st.markdown("---")
                
                if st.button("🚪 Logout"):
                    logout()
                
                st.markdown("---")
                st.caption(f"Login Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            if st.session_state.role == 'admin':
                admin_panel()
                user_dashboard()
            else:
                user_dashboard()

if __name__ == "__main__":
    main()
