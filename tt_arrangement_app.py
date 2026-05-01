import streamlit as st
import pandas as pd
import hashlib
import json
import os
from datetime import datetime, timedelta

# File paths
USER_DB_FILE = "users.json"
TIMETABLE_FILE = "timetable.xlsx"
ARRANGEMENT_FILE = "arrangements.json"

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'role' not in st.session_state:
    st.session_state.role = None

# Hash password function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Load users from JSON file
def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'r') as f:
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

# Save users to JSON file
def save_users(users):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Load arrangements
def load_arrangements():
    if os.path.exists(ARRANGEMENT_FILE):
        with open(ARRANGEMENT_FILE, 'r') as f:
            return json.load(f)
    else:
        return {}

# Save arrangements
def save_arrangements(arrangements):
    with open(ARRANGEMENT_FILE, 'w') as f:
        json.dump(arrangements, f, indent=4)

# Load timetable from Excel
@st.cache_data
def load_timetable():
    try:
        if os.path.exists(TIMETABLE_FILE):
            df = pd.read_excel(TIMETABLE_FILE)
            return df
        else:
            # Create sample timetable
            sample_data = {
                'Day': ['Monday', 'Monday', 'Monday', 'Tuesday', 'Tuesday', 'Tuesday', 'Wednesday', 'Wednesday', 'Wednesday'],
                'Time': ['9:00-10:00', '10:00-11:00', '11:00-12:00', '9:00-10:00', '10:00-11:00', '11:00-12:00', '9:00-10:00', '10:00-11:00', '11:00-12:00'],
                'Teacher': ['Dr. Smith', 'Prof. Johnson', 'Dr. Williams', 'Dr. Smith', 'Prof. Brown', 'Dr. Williams', 'Prof. Johnson', 'Dr. Smith', 'Prof. Brown'],
                'Subject': ['Mathematics', 'Physics', 'Chemistry', 'Mathematics', 'English', 'Chemistry', 'Physics', 'Mathematics', 'English'],
                'Class': ['10A', '10A', '10A', '10B', '10B', '10B', '10C', '10C', '10C'],
                'Designation': ['Math Teacher', 'Physics Teacher', 'Chemistry Teacher', 'Math Teacher', 'English Teacher', 'Chemistry Teacher', 'Physics Teacher', 'Math Teacher', 'English Teacher']
            }
            sample_df = pd.DataFrame(sample_data)
            sample_df.to_excel(TIMETABLE_FILE, index=False)
            return sample_df
    except Exception as e:
        st.error(f"Error loading timetable: {e}")
        return pd.DataFrame()

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

# Get available teachers for arrangement
def get_available_teachers(df, current_day, current_time, exclude_teacher):
    """Find teachers who are free during a specific period"""
    # Get all teachers who are NOT teaching at that time
    busy_teachers = df[(df['Day'] == current_day) & (df['Time'] == current_time)]['Teacher'].tolist()
    all_teachers = df['Teacher'].unique()
    available = [t for t in all_teachers if t not in busy_teachers and t != exclude_teacher]
    return available

# Suggest arrangement
def suggest_arrangement(df, absent_teacher, day, time_period):
    """Suggest a teacher to cover for absent teacher"""
    # Get the subject and class of absent teacher
    absent_class = df[(df['Day'] == day) & 
                      (df['Time'] == time_period) & 
                      (df['Teacher'] == absent_teacher)]
    
    if absent_class.empty:
        return None, None, None
    
    subject = absent_class.iloc[0]['Subject']
    class_name = absent_class.iloc[0]['Class']
    
    # Find teachers who can teach this subject
    qualified_teachers = df[df['Subject'] == subject]['Teacher'].unique()
    
    # Find available teachers among qualified ones
    available_teachers = get_available_teachers(df, day, time_period, absent_teacher)
    
    # Prioritize qualified teachers
    for teacher in qualified_teachers:
        if teacher in available_teachers:
            return teacher, subject, class_name
    
    # If no qualified teacher available, suggest any available teacher
    if available_teachers:
        return available_teachers[0], subject, class_name
    
    return None, subject, class_name

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
    
    # Upload Timetable Tab
    with tab3:
        st.subheader("Upload Timetable")
        st.info("Excel file should have columns: Day, Time, Teacher, Subject, Class, Designation")
        
        uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls'])
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                required_cols = ['Day', 'Time', 'Teacher', 'Subject', 'Class', 'Designation']
                if all(col in df.columns for col in required_cols):
                    df.to_excel(TIMETABLE_FILE, index=False)
                    st.success("Timetable uploaded successfully!")
                    st.dataframe(df)
                    st.cache_data.clear()
                else:
                    st.error(f"Missing columns. Required: {required_cols}")
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    # Arrangement Management Tab
    with tab4:
        st.subheader("📋 Teacher Absence & Arrangement Management")
        
        df = load_timetable()
        if df.empty:
            st.warning("Please upload timetable first")
            return
        
        # Get unique values
        days = df['Day'].unique()
        time_periods = df['Time'].unique()
        teachers = df['Teacher'].unique()
        
        # Section 1: Report Absence
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
            
            if st.form_submit_button("Report Absence & Get Arrangement Suggestion"):
                suggested_teacher, subject, class_name = suggest_arrangement(df, absent_teacher, absence_day, absence_time)
                
                if suggested_teacher:
                    st.success(f"✅ Arrangement Suggested!")
                    st.info(f"""
                    **Details:**
                    - **Absent Teacher:** {absent_teacher}
                    - **Class:** {class_name}
                    - **Subject:** {subject}
                    - **Time:** {absence_day}, {absence_time}
                    - **Suggested Replacement:** {suggested_teacher}
                    """)
                    
                    # Save arrangement
                    arrangements = load_arrangements()
                    arrangement_key = f"{absence_day}_{absence_time}_{class_name}"
                    arrangements[arrangement_key] = {
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
                    
                    # Option to confirm arrangement
                    if st.button("Confirm Arrangement"):
                        arrangements[arrangement_key]["status"] = "confirmed"
                        save_arrangements(arrangements)
                        st.success(f"Arrangement confirmed! {suggested_teacher} will cover for {absent_teacher}")
                else:
                    st.error("❌ No available teachers found for arrangement!")
                    st.warning("Please check if any teacher is free during this period")
        
        # Section 2: Current Arrangements
        st.subheader("2️⃣ Current Arrangements")
        arrangements = load_arrangements()
        
        if arrangements:
            # Filter arrangements for today
            arrangements_df = pd.DataFrame.from_dict(arrangements, orient='index')
            st.dataframe(arrangements_df)
            
            # Option to mark arrangement as completed
            st.subheader("Mark Arrangement as Completed")
            arrangement_to_complete = st.selectbox("Select arrangement to complete", 
                                                  list(arrangements.keys()))
            if st.button("Mark as Completed"):
                arrangements[arrangement_to_complete]["status"] = "completed"
                save_arrangements(arrangements)
                st.success("Arrangement marked as completed!")
                st.rerun()
        else:
            st.info("No active arrangements")

# User dashboard
def user_dashboard():
    st.header(f"👋 Welcome, {st.session_state.name}!")
    st.write(f"**Designation:** {st.session_state.designation}")
    
    # Load timetable
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
        st.info(f"No timetable entries found for your designation: {st.session_state.designation}")
    
    # Show arrangement periods assigned to user
    st.subheader("🔄 Your Arrangement Assignments")
    arrangements = load_arrangements()
    
    if arrangements:
        user_arrangements = []
        for key, value in arrangements.items():
            if value.get('replacement_teacher') == st.session_state.name or value.get('replacement_teacher') == st.session_state.designation:
                if value.get('status') not in ['completed']:
                    user_arrangements.append(value)
        
        if user_arrangements:
            for arr in user_arrangements:
                with st.container():
                    st.info(f"""
                    **📌 Arrangement Assignment**
                    - **Date/Day:** {arr.get('day', 'N/A')}, {arr.get('time', 'N/A')}
                    - **Class:** {arr.get('class', 'N/A')}
                    - **Subject:** {arr.get('subject', 'N/A')}
                    - **Covering For:** {arr.get('absent_teacher', 'N/A')}
                    - **Status:** {arr.get('status', 'N/A')}
                    """)
        else:
            st.info("No active arrangement assignments")
    else:
        st.info("No arrangement periods assigned")
    
    # View all arrangements (for admin users)
    if st.session_state.role == 'admin':
        st.subheader("📊 All Arrangements")
        if arrangements:
            arrangements_df = pd.DataFrame.from_dict(arrangements, orient='index')
            st.dataframe(arrangements_df, use_container_width=True)
        else:
            st.info("No arrangements recorded")

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
        .stApp {
            background-color: #f5f5f5;
        }
        .stButton > button {
            width: 100%;
        }
        .css-1aumxhk {
            background-color: #ffffff;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Title
    st.title("📚 Timetable Management System with Smart Arrangement")
    
    # Login/Logout logic
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
        # Sidebar with user info and logout
        with st.sidebar:
            st.write(f"**Logged in as:** {st.session_state.name}")
            st.write(f"**Username:** {st.session_state.username}")
            st.write(f"**Role:** {st.session_state.role}")
            st.markdown("---")
            
            if st.button("🚪 Logout"):
                logout()
            
            st.markdown("---")
            st.caption(f"Login Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Main content based on role
        if st.session_state.role == 'admin':
            admin_panel()
            user_dashboard()
        else:
            user_dashboard()

if __name__ == "__main__":
    main()