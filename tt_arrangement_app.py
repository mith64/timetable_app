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

# File paths - Using absolute paths to avoid conflicts
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
    """Create necessary directories if they don't exist"""
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
            # Default admin user
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
    """Check if file is locked by another process"""
    try:
        # Try to open file in append mode
        with open(filepath, 'a'):
            pass
        return False
    except (PermissionError, OSError):
        return True

# Force close any open handles to the file
def force_close_file(filepath):
    """Attempt to force close any open handles to the file"""
    try:
        import gc
        gc.collect()
        if os.path.exists(filepath):
            # Try to rename the file temporarily
            temp_name = filepath + ".temp"
            if os.path.exists(temp_name):
                os.remove(temp_name)
            os.rename(filepath, temp_name)
            os.rename(temp_name, filepath)
        return True
    except:
        return False

# Load timetable with proper error handling
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_timetable():
    """Load timetable with comprehensive error handling"""
    try:
        # Check if file exists
        if not os.path.exists(TIMETABLE_FILE):
            st.warning("No timetable file found. Creating sample data...")
            return create_sample_timetable()
        
        # Check if file is locked
        if is_file_locked(TIMETABLE_FILE):
            st.error("⚠️ Timetable file is locked by another process (like Excel)")
            st.info("Please close Excel if it's open, then refresh the page (F5)")
            # Return cached data if available
            if st.session_state.timetable_df is not None:
                return st.session_state.timetable_df
            return create_sample_timetable()
        
        # Try to read with different engines
        engines = ['openpyxl', 'xlrd', 'calamine']
        for engine in engines:
            try:
                df = pd.read_excel(TIMETABLE_FILE, engine=engine)
                if not df.empty:
                    st.session_state.timetable_df = df
                    return df
            except:
                continue
        
        # If all engines fail, try alternative method
        try:
            # Read as binary and save to temp file
            with open(TIMETABLE_FILE, 'rb') as f:
                data = f.read()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            
            df = pd.read_excel(tmp_path)
            os.unlink(tmp_path)
            st.session_state.timetable_df = df
            return df
        except Exception as e:
            st.error(f"Cannot read timetable file. Error: {e}")
            return create_sample_timetable()
            
    except PermissionError as e:
        st.error(f"🔒 Permission Denied: {e}")
        st.info("""
        **Solutions:**
        1. Close Excel if the file is open
        2. Run Streamlit as administrator
        3. Check file permissions
        4. Restart Streamlit server
        """)
        if st.session_state.timetable_df is not None:
            return st.session_state.timetable_df
        return create_sample_timetable()
    except Exception as e:
        st.error(f"Error loading timetable: {e}")
        if st.session_state.timetable_df is not None:
            return st.session_state.timetable_df
        return create_sample_timetable()

def create_sample_timetable():
    """Create sample timetable data"""
    sample_data = {
        'Day': ['Monday', 'Monday', 'Tuesday', 'Tuesday', 'Wednesday', 'Wednesday'],
        'Time': ['9:00-10:00', '10:00-11:00', '9:00-10:00', '10:00-11:00', '9:00-10:00', '10:00-11:00'],
        'Teacher': ['Dr. Smith', 'Prof. Johnson', 'Dr. Smith', 'Prof. Brown', 'Prof. Johnson', 'Dr. Smith'],
        'Subject': ['Mathematics', 'Physics', 'Mathematics', 'Chemistry', 'Physics', 'Mathematics'],
        'Class': ['10A', '10A', '10B', '10B', '10C', '10C'],
        'Designation': ['Math Teacher', 'Physics Teacher', 'Math Teacher', 'Chemistry Teacher', 'Physics Teacher', 'Math Teacher']
    }
    df = pd.DataFrame(sample_data)
    # Try to save it
    save_timetable(df)
    return df

def save_timetable(df):
    """Save timetable with retry logic"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            # Force close any open handles
            gc.collect()
            
            # Check if file is locked
            if os.path.exists(TIMETABLE_FILE) and is_file_locked(TIMETABLE_FILE):
                st.warning(f"File is locked (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            
            # Method 1: Direct save with temp file
            temp_file = TIMETABLE_FILE + ".tmp"
            df.to_excel(temp_file, index=False, engine='openpyxl')
            
            # Replace original with temp
            if os.path.exists(TIMETABLE_FILE):
                os.remove(TIMETABLE_FILE)
            os.rename(temp_file, TIMETABLE_FILE)
            
            st.session_state.timetable_df = df
            st.cache_data.clear()
            return True
            
        except PermissionError as e:
            st.warning(f"Permission error on attempt {attempt + 1}: {e}")
            time.sleep(retry_delay)
        except Exception as e:
            st.error(f"Save error: {e}")
            time.sleep(retry_delay)
    
    st.error("Failed to save timetable after multiple attempts")
    return False

def delete_timetable_file():
    """Delete the timetable file safely"""
    try:
        if os.path.exists(TIMETABLE_FILE):
            if is_file_locked(TIMETABLE_FILE):
                st.error("Cannot delete: File is locked")
                return False
            
            # Create backup before deletion
            backup_name = os.path.join(BACKUP_FOLDER, f"deleted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            shutil.copy2(TIMETABLE_FILE, backup_name)
            
            os.remove(TIMETABLE_FILE)
            st.success(f"File deleted. Backup saved: {backup_name}")
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

# Admin panel
def admin_panel():
    st.header("👑 Admin Panel")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Create User", "Manage Users", "Upload Timetable", "Arrangement Management"])
    
    # Create User Tab
    with tab1:
        st.subheader("Create New User")
        with st.form("create_user_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_name = st.text_input("Full Name")
            new_designation = st.text_input("Designation")
            new_role = st.selectbox("Role", ["user", "admin"])
            
            if st.form_submit_button("Create User"):
                if new_username and new_password and new_name and new_designation:
                    users = load_users()
                    if new_username not in users:
                        users[new_username] = {
                            "password": hash_password(new_password),
                            "name": new_name,
                            "designation": new_designation,
                            "role": new_role
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
        
        if user_list:
            for username in user_list:
                with st.expander(f"User: {username}"):
                    st.write(f"**Name:** {users[username]['name']}")
                    st.write(f"**Designation:** {users[username]['designation']}")
                    st.write(f"**Role:** {users[username]['role']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Delete {username}", key=f"del_{username}"):
                            del users[username]
                            save_users(users)
                            st.success(f"User {username} deleted!")
                            st.rerun()
                    with col2:
                        if st.button(f"Reset Password {username}", key=f"reset_{username}"):
                            new_pass = "password123"
                            users[username]['password'] = hash_password(new_pass)
                            save_users(users)
                            st.success(f"Password reset to '{new_pass}' for {username}")
        else:
            st.info("No users found except admin")
    
    # Upload Timetable Tab - Fixed version
    with tab3:
        st.subheader("Upload Timetable")
        
        # Show current status
        col1, col2 = st.columns(2)
        with col1:
            if os.path.exists(TIMETABLE_FILE):
                st.success(f"✅ Current file: {os.path.basename(TIMETABLE_FILE)}")
                file_size = os.path.getsize(TIMETABLE_FILE)
                st.caption(f"Size: {file_size} bytes")
            else:
                st.warning("⚠️ No timetable file exists")
        
        with col2:
            if st.button("🗑️ Delete Current Timetable", type="secondary"):
                if delete_timetable_file():
                    st.rerun()
        
        st.markdown("---")
        
        # File upload section
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
                # Read the uploaded file
                df = pd.read_excel(uploaded_file, engine='openpyxl')
                
                # Check required columns
                required_cols = ['Day', 'Time', 'Teacher', 'Subject', 'Class', 'Designation']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    st.error(f"❌ Missing columns: {missing_cols}")
                else:
                    # Show preview
                    st.subheader("Preview of uploaded data:")
                    st.dataframe(df.head())
                    
                    # Confirm upload
                    confirm = st.button("✅ Upload and Replace Current Timetable", type="primary")
                    
                    if confirm:
                        # Force close any open file handles
                        gc.collect()
                        time.sleep(0.5)
                        
                        # Save the new timetable
                        if save_timetable(df):
                            st.success("✨ Timetable uploaded successfully!")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Failed to save timetable. Please check if the file is not open in Excel.")
                            
            except Exception as e:
                st.error(f"Error reading file: {e}")
                st.info("""
                **Troubleshooting:**
                1. Make sure the file is not open in Excel
                2. Check if the file is a valid Excel file
                3. Try saving the file again from Excel
                4. Close and reopen Streamlit
                """)
    
    # Arrangement Management Tab
    with tab4:
        st.subheader("📋 Teacher Absence & Arrangement Management")
        
        df = load_timetable()
        if df.empty:
            st.warning("Please upload timetable first")
            return
        
        days = df['Day'].unique()
        time_periods = df['Time'].unique()
        teachers = df['Teacher'].unique()
        
        st.subheader("1️⃣ Report Teacher Absence")
        with st.form("absence_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                absent_teacher = st.selectbox("Absent Teacher", teachers)
            with col2:
                absence_day = st.selectbox("Day of Absence", days)
            with col3:
                absence_time = st.selectbox("Time Period", time_periods)
            
            reason = st.text_area("Reason for Absence (Optional)")
            
            if st.form_submit_button("Report Absence"):
                # Find arrangement suggestion
                absent_class = df[(df['Day'] == absence_day) & 
                                 (df['Time'] == absence_time) & 
                                 (df['Teacher'] == absent_teacher)]
                
                if not absent_class.empty:
                    subject = absent_class.iloc[0]['Subject']
                    class_name = absent_class.iloc[0]['Class']
                    
                    # Find available teacher
                    busy_teachers = df[(df['Day'] == absence_day) & (df['Time'] == absence_time)]['Teacher'].tolist()
                    all_teachers = df['Teacher'].unique()
                    available = [t for t in all_teachers if t not in busy_teachers and t != absent_teacher]
                    
                    if available:
                        suggested_teacher = available[0]
                        st.success(f"✅ Suggested replacement: {suggested_teacher}")
                        st.info(f"Class: {class_name}, Subject: {subject}")
                        
                        # Save arrangement
                        arrangements = load_arrangements()
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

# User dashboard
def user_dashboard():
    st.header(f"👋 Welcome, {st.session_state.name}!")
    st.write(f"**Designation:** {st.session_state.designation}")
    
    df = load_timetable()
    
    if df.empty:
        st.warning("No timetable available. Please contact admin.")
        return
    
    # Show personal timetable
    st.subheader("📅 Your Timetable")
    user_timetable = df[df['Designation'].str.lower() == st.session_state.designation.lower()]
    
    if not user_timetable.empty:
        st.dataframe(user_timetable[['Day', 'Time', 'Subject', 'Class']], use_container_width=True)
    else:
        st.info(f"No timetable entries found for your designation")
    
    # Show arrangements
    st.subheader("🔄 Your Arrangement Assignments")
    arrangements = load_arrangements()
    
    if arrangements:
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
    
    # Custom CSS
    st.markdown("""
        <style>
        .stAlert {
            border-radius: 10px;
        }
        .stButton button {
            border-radius: 5px;
        }
        </style>
    """, unsafe_allow_html=True)
    
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
