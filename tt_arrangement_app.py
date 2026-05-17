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
from collections import defaultdict, Counter
import numpy as np

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
CLASSROOM_FILE = os.path.join(BASE_DIR, "classrooms.json")

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
if 'editing_mode' not in st.session_state:
    st.session_state.editing_mode = False
if 'edit_df' not in st.session_state:
    st.session_state.edit_df = None

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

# Load classrooms
def load_classrooms():
    """Load classroom data"""
    try:
        if os.path.exists(CLASSROOM_FILE):
            with open(CLASSROOM_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    return json.loads(content)
                else:
                    return {}
        else:
            save_classrooms({})
            return {}
    except json.JSONDecodeError:
        save_classrooms({})
        return {}
    except Exception as e:
        st.error(f"Error loading classrooms: {e}")
        return {}

def save_classrooms(classrooms):
    """Save classroom data"""
    try:
        if classrooms is None:
            classrooms = {}
        with open(CLASSROOM_FILE, 'w', encoding='utf-8') as f:
            json.dump(classrooms, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving classrooms: {e}")
        return False

# Load arrangements
def load_arrangements():
    """Load arrangements with proper error handling"""
    try:
        if os.path.exists(ARRANGEMENT_FILE):
            with open(ARRANGEMENT_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    return json.loads(content)
                else:
                    return {}
        else:
            save_arrangements({})
            return {}
    except json.JSONDecodeError:
        st.warning("Arrangements file was corrupted. Creating new one...")
        save_arrangements({})
        return {}
    except Exception as e:
        st.error(f"Error loading arrangements: {e}")
        return {}

# Save arrangements
def save_arrangements(arrangements):
    """Save arrangements with error handling"""
    try:
        if arrangements is None:
            arrangements = {}
        with open(ARRANGEMENT_FILE, 'w', encoding='utf-8') as f:
            json.dump(arrangements, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving arrangements: {e}")
        return False

# Load timetable
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
        
        try:
            df = pd.read_excel(TIMETABLE_FILE, engine='openpyxl')
            if not df.empty:
                st.session_state.timetable_df = df
                return df
        except Exception as e:
            st.warning(f"Could not read with openpyxl: {e}")
            
        try:
            df = pd.read_excel(TIMETABLE_FILE)
            if not df.empty:
                st.session_state.timetable_df = df
                return df
        except Exception as e:
            st.warning(f"Could not read with default engine: {e}")
            
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
        
        try:
            df.to_excel(TIMETABLE_FILE, index=False, engine='openpyxl')
            st.session_state.timetable_df = df
            st.cache_data.clear()
            return True
        except Exception as e1:
            st.warning(f"Direct save failed: {e1}")
            
            try:
                df.to_excel(TIMETABLE_FILE, index=False, engine='xlsxwriter')
                st.session_state.timetable_df = df
                st.cache_data.clear()
                return True
            except Exception as e2:
                st.warning(f"Alternative engine failed: {e2}")
                
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

# ============ PREDICTION SYSTEM ============

def get_teacher_availability(df, day, time_slot, exclude_teacher=None):
    """Get available teachers for a given time slot"""
    busy_teachers = df[(df['Day'] == day) & (df['Time'] == time_slot)]['Teacher'].tolist()
    all_teachers = df['Teacher'].unique()
    
    available = []
    for teacher in all_teachers:
        if teacher not in busy_teachers and teacher != exclude_teacher:
            # Check if teacher has any duties at this time
            teacher_duties = df[(df['Day'] == day) & (df['Time'] == time_slot) & (df['Teacher'] == teacher)]
            if teacher_duties.empty:
                available.append(teacher)
    
    return available

def calculate_teacher_load(df, teacher):
    """Calculate weekly load for a teacher"""
    return len(df[df['Teacher'] == teacher])

def get_teacher_vacant_periods(df, teacher, day):
    """Get all vacant periods for a teacher on a specific day"""
    teacher_schedule = df[(df['Teacher'] == teacher) & (df['Day'] == day)]
    teacher_times = set(teacher_schedule['Time'].tolist())
    all_times = set(df[df['Day'] == day]['Time'].unique())
    
    vacant_periods = all_times - teacher_times
    return list(vacant_periods)

def predict_best_replacement(df, absent_teacher, day, time_slot, class_name, subject):
    """PREDICTION ALGORITHM: Find best replacement teacher based on multiple criteria"""
    
    # Get all teachers who can teach this subject (based on designation)
    subject_teachers = df[df['Subject'] == subject]['Teacher'].unique()
    
    # Get busy teachers at this time
    busy_teachers = df[(df['Day'] == day) & (df['Time'] == time_slot)]['Teacher'].tolist()
    
    # Get teachers on duty at this time
    on_duty = df[(df['Day'] == day) & (df['Time'] == time_slot) & (df['Designation'].str.contains('Duty', case=False, na=False))]['Teacher'].tolist()
    
    candidates = []
    
    for teacher in subject_teachers:
        # Condition 1: Teacher is present (not absent)
        if teacher == absent_teacher:
            continue
        
        # Condition 2: Teacher is vacant in this period
        if teacher in busy_teachers:
            continue
        
        # Condition 3: Teacher has no duty at this time
        if teacher in on_duty:
            continue
        
        # Calculate priority score
        score = 0
        
        # Lower current load is better
        load = calculate_teacher_load(df, teacher)
        score += (100 - load)  # Less load = higher score
        
        # Check if teacher has consecutive free periods (for serial classes)
        vacant_periods = get_teacher_vacant_periods(df, teacher, day)
        if len(vacant_periods) >= 2:  # Can handle 2+ classes serially
            score += 30
        
        # Teacher who handled this class before gets bonus
        if len(df[(df['Teacher'] == teacher) & (df['Class'] == class_name)]) > 0:
            score += 20
        
        candidates.append((teacher, score))
    
    # Sort by score (highest first)
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    if candidates:
        return candidates[0][0]
    else:
        # Fallback: Any available teacher
        all_available = get_teacher_availability(df, day, time_slot, absent_teacher)
        return all_available[0] if all_available else None

def check_crisis_mode(df, arrangements):
    """Check if absent teacher count exceeds 40%"""
    total_teachers = len(df['Teacher'].unique())
    
    # Count unique absent teachers in last 7 days
    recent_absences = set()
    for key, value in arrangements.items():
        if 'status' in value and value['status'] == 'pending':
            recent_absences.add(value.get('absent_teacher'))
    
    absent_count = len(recent_absences)
    
    if total_teachers > 0 and (absent_count / total_teachers) >= 0.4:
        return True, absent_count, total_teachers
    return False, absent_count, total_teachers

def get_serial_class_recommendations(df, day, time_slot, available_teacher):
    """Get recommendations for serial classes (3-4 classes in a row)"""
    
    # Find all classes at this time that need coverage
    classes_at_time = df[(df['Day'] == day) & (df['Time'] == time_slot)]
    
    # Check if teacher can take multiple consecutive classes
    vacant_periods = get_teacher_vacant_periods(df, available_teacher, day)
    
    serial_recommendations = []
    
    # Find next time slots
    all_times = sorted(df['Time'].unique())
    current_index = all_times.index(time_slot) if time_slot in all_times else -1
    
    if current_index != -1:
        consecutive_slots = []
        for i in range(current_index, min(current_index + 4, len(all_times))):
            if all_times[i] in vacant_periods:
                consecutive_slots.append(all_times[i])
            else:
                break
        
        if len(consecutive_slots) >= 2:
            for slot in consecutive_slots:
                classes_to_cover = df[(df['Day'] == day) & (df['Time'] == slot)]
                for _, row in classes_to_cover.iterrows():
                    serial_recommendations.append({
                        'time': slot,
                        'class': row['Class'],
                        'subject': row['Subject']
                    })
    
    return serial_recommendations

# ============ ONLINE TIMETABLE EDITOR ============

def edit_timetable_online():
    """Inline editor for timetable"""
    st.subheader("✏️ Online Timetable Editor")
    
    df = load_timetable()
    
    if df.empty:
        st.warning("No timetable data available. Please upload or create a new one.")
        return
    
    # Edit mode toggle
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("✏️ Enable Edit Mode", type="primary" if not st.session_state.editing_mode else "secondary"):
            st.session_state.editing_mode = True
            st.session_state.edit_df = df.copy()
            st.rerun()
    
    with col2:
        if st.button("📥 Export Excel"):
            if save_timetable(df):
                st.success("Timetable exported successfully!")
    
    with col3:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()
    
    if st.session_state.editing_mode:
        st.info("📝 Edit Mode Active - Click on any cell to edit, then click 'Save Changes'")
        
        # Create editable dataframe
        edited_df = st.data_editor(
            st.session_state.edit_df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Day": st.column_config.SelectboxColumn(
                    "Day",
                    options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    required=True
                ),
                "Time": st.column_config.TextColumn("Time", required=True),
                "Teacher": st.column_config.TextColumn("Teacher", required=True),
                "Subject": st.column_config.TextColumn("Subject", required=True),
                "Class": st.column_config.TextColumn("Class", required=True),
                "Designation": st.column_config.TextColumn("Designation", required=True)
            }
        )
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("💾 Save Changes", type="primary"):
                if save_timetable(edited_df):
                    st.success("Timetable saved successfully!")
                    st.session_state.editing_mode = False
                    st.session_state.edit_df = None
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to save timetable")
        
        with col2:
            if st.button("❌ Cancel Editing"):
                st.session_state.editing_mode = False
                st.session_state.edit_df = None
                st.rerun()
        
        with col3:
            if st.button("➕ Add New Row"):
                new_row = pd.DataFrame([{
                    'Day': 'Monday',
                    'Time': '11:00-12:00',
                    'Teacher': 'New Teacher',
                    'Subject': 'New Subject',
                    'Class': 'New Class',
                    'Designation': 'New Designation'
                }])
                st.session_state.edit_df = pd.concat([st.session_state.edit_df, new_row], ignore_index=True)
                st.rerun()
        
        with col4:
            if st.button("🗑️ Delete Last Row"):
                if len(st.session_state.edit_df) > 0:
                    st.session_state.edit_df = st.session_state.edit_df.iloc[:-1]
                    st.rerun()
    
    else:
        # Display mode
        st.dataframe(df, use_container_width=True)
        
        # Summary statistics
        st.subheader("📊 Timetable Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Classes", len(df))
        with col2:
            st.metric("Unique Teachers", len(df['Teacher'].unique()))
        with col3:
            st.metric("Unique Subjects", len(df['Subject'].unique()))
        with col4:
            st.metric("Unique Classes", len(df['Class'].unique()))

# ============ CLASSROOM MANAGEMENT UI ============

def classroom_management():
    """Complete classroom management interface"""
    st.subheader("🏫 Classroom Management")
    
    classrooms = load_classrooms()
    
    # Tabs for different operations
    tab1, tab2, tab3 = st.tabs(["📋 View Classrooms", "➕ Add/Edit Classroom", "🗑️ Delete Classroom"])
    
    # View Classrooms
    with tab1:
        if classrooms:
            # Display as cards
            for room_id, room_data in classrooms.items():
                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.markdown(f"**🏠 {room_data.get('name', room_id)}**")
                    with col2:
                        st.markdown(f"Capacity: {room_data.get('capacity', 'N/A')} students")
                    with col3:
                        st.markdown(f"Floor: {room_data.get('floor', 'N/A')}")
                    
                    if room_data.get('equipment'):
                        st.caption(f"🛠️ Equipment: {', '.join(room_data['equipment'])}")
                    
                    if room_data.get('current_class'):
                        st.info(f"📚 Current Class: {room_data['current_class']}")
                    
                    st.markdown("---")
        else:
            st.info("No classrooms added yet. Use 'Add Classroom' tab to add.")
    
    # Add/Edit Classroom
    with tab2:
        st.subheader("Add/Edit Classroom")
        
        operation = st.radio("Select Operation", ["Add New Classroom", "Edit Existing Classroom"])
        
        if operation == "Edit Existing Classroom" and classrooms:
            selected_room = st.selectbox("Select Classroom to Edit", list(classrooms.keys()))
            room_data = classrooms.get(selected_room, {})
        else:
            selected_room = None
            room_data = {}
        
        with st.form("classroom_form"):
            room_name = st.text_input("Classroom Name/Room Number", value=room_data.get('name', '') if room_data else '')
            capacity = st.number_input("Capacity (Number of Students)", min_value=1, value=room_data.get('capacity', 30) if room_data else 30)
            floor = st.number_input("Floor Level", min_value=0, max_value=10, value=room_data.get('floor', 1) if room_data else 1)
            
            equipment = st.multiselect(
                "Equipment Available",
                options=["Projector", "Smart Board", "AC", "Computers", "WiFi", "Whiteboard", "Speakers", "Microphone"],
                default=room_data.get('equipment', []) if room_data else []
            )
            
            current_class = st.text_input("Currently Assigned Class (Optional)", value=room_data.get('current_class', '') if room_data else '')
            
            submitted = st.form_submit_button("Save Classroom")
            
            if submitted:
                if room_name:
                    room_id = room_name.replace(" ", "_").lower()
                    classrooms[room_id] = {
                        "name": room_name,
                        "capacity": capacity,
                        "floor": floor,
                        "equipment": equipment,
                        "current_class": current_class,
                        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    save_classrooms(classrooms)
                    st.success(f"Classroom '{room_name}' saved successfully!")
                    st.rerun()
                else:
                    st.error("Please enter classroom name")
    
    # Delete Classroom
    with tab3:
        if classrooms:
            st.subheader("Delete Classroom")
            room_to_delete = st.selectbox("Select Classroom to Delete", list(classrooms.keys()))
            
            if st.button("🗑️ Delete Classroom", type="secondary"):
                confirm = st.checkbox("I confirm deletion of this classroom")
                if confirm:
                    del classrooms[room_to_delete]
                    save_classrooms(classrooms)
                    st.success(f"Classroom deleted successfully!")
                    st.rerun()
        else:
            st.info("No classrooms to delete")

# ============ IMPROVED ARRANGEMENT SYSTEM ============

def arrangement_management():
    """Enhanced arrangement management with prediction"""
    st.subheader("📋 Teacher Absence & Intelligent Arrangement System")
    
    df = load_timetable()
    if df.empty:
        st.warning("Please upload timetable first")
        return
    
    arrangements = load_arrangements()
    if arrangements is None:
        arrangements = {}
    
    # Check crisis mode
    crisis_mode, absent_count, total_teachers = check_crisis_mode(df, arrangements)
    
    if crisis_mode:
        st.error(f"⚠️ **CRISIS MODE ACTIVATED!** {absent_count}/{total_teachers} teachers absent ({int(absent_count/total_teachers*100)}%)")
        st.warning("Using Serial Class Prediction System - Teachers will be assigned 3-4 consecutive classes")
    
    days = df['Day'].unique() if not df.empty else []
    time_periods = df['Time'].unique() if not df.empty else []
    teachers = df['Teacher'].unique() if not df.empty else []
    
    # Absence Reporting
    st.subheader("1️⃣ Report Teacher Absence (With Prediction)")
    with st.form("absence_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            absent_teacher = st.selectbox("Absent Teacher", teachers.tolist())
        with col2:
            absence_day = st.selectbox("Day of Absence", days.tolist())
        with col3:
            absence_time = st.selectbox("Time Period", time_periods.tolist())
        
        reason = st.text_area("Reason for Absence")
        
        if st.form_submit_button("Report Absence & Get Prediction"):
            try:
                absent_class = df[(df['Day'] == absence_day) & 
                                 (df['Time'] == absence_time) & 
                                 (df['Teacher'] == absent_teacher)]
                
                if not absent_class.empty:
                    subject = absent_class.iloc[0]['Subject']
                    class_name = absent_class.iloc[0]['Class']
                    
                    # Use prediction algorithm
                    if crisis_mode:
                        # Crisis mode: Find teacher who can take multiple classes
                        available_teacher = predict_best_replacement(df, absent_teacher, absence_day, absence_time, class_name, subject)
                        
                        if available_teacher:
                            # Get serial class recommendations
                            serial_classes = get_serial_class_recommendations(df, absence_day, absence_time, available_teacher)
                            
                            st.success(f"✅ **Predicted Replacement (Crisis Mode):** {available_teacher}")
                            st.info(f"📚 Class: {class_name} | Subject: {subject}")
                            
                            if serial_classes:
                                st.warning("🔄 **Serial Class Assignment Available:**")
                                for sc in serial_classes:
                                    st.markdown(f"- {sc['time']}: {sc['class']} - {sc['subject']}")
                            
                            # Save arrangement with crisis flag
                            key = f"{absence_day}_{absence_time}_{class_name}"
                            arrangements[key] = {
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "absent_teacher": absent_teacher,
                                "replacement_teacher": available_teacher,
                                "class": class_name,
                                "subject": subject,
                                "day": absence_day,
                                "time": absence_time,
                                "reason": reason,
                                "status": "assigned",
                                "crisis_mode": crisis_mode,
                                "serial_classes": serial_classes
                            }
                            save_arrangements(arrangements)
                        else:
                            st.error("❌ No available teachers found")
                    else:
                        # Normal mode: Find best replacement
                        best_replacement = predict_best_replacement(df, absent_teacher, absence_day, absence_time, class_name, subject)
                        
                        if best_replacement:
                            st.success(f"✅ **Intelligent Prediction:** {best_replacement}")
                            st.info(f"📚 Class: {class_name} | Subject: {subject}")
                            
                            # Show teacher's vacant periods
                            vacant_periods = get_teacher_vacant_periods(df, best_replacement, absence_day)
                            if vacant_periods:
                                st.caption(f"🕐 {best_replacement}'s vacant periods on {absence_day}: {', '.join(vacant_periods)}")
                            
                            # Save arrangement
                            key = f"{absence_day}_{absence_time}_{class_name}"
                            arrangements[key] = {
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "absent_teacher": absent_teacher,
                                "replacement_teacher": best_replacement,
                                "class": class_name,
                                "subject": subject,
                                "day": absence_day,
                                "time": absence_time,
                                "reason": reason,
                                "status": "assigned",
                                "crisis_mode": False
                            }
                            save_arrangements(arrangements)
                        else:
                            st.error("❌ No suitable replacement found")
                else:
                    st.error("No class found for this teacher at specified time")
            except Exception as e:
                st.error(f"Error in prediction: {e}")
    
    # Display arrangements
    st.subheader("2️⃣ Current Arrangements")
    if arrangements and len(arrangements) > 0:
        for key, value in list(arrangements.items()):
            with st.expander(f"📅 {value.get('day', 'N/A')} - {value.get('time', 'N/A')} - {value.get('class', 'N/A')}"):
                st.write(f"**Absent Teacher:** {value.get('absent_teacher', 'N/A')}")
                st.write(f"**Replacement:** {value.get('replacement_teacher', 'N/A')}")
                st.write(f"**Subject:** {value.get('subject', 'N/A')}")
                st.write(f"**Status:** {value.get('status', 'N/A')}")
                if value.get('crisis_mode'):
                    st.warning("⚠️ Crisis Mode Assignment")
                if value.get('serial_classes'):
                    st.write("**Serial Classes:**")
                    for sc in value['serial_classes']:
                        st.write(f"  - {sc['time']}: {sc['class']}")
                
                if st.button(f"Mark Complete", key=f"complete_{key}"):
                    value['status'] = 'completed'
                    save_arrangements(arrangements)
                    st.rerun()
                
                if st.button(f"Delete", key=f"del_{key}"):
                    del arrangements[key]
                    save_arrangements(arrangements)
                    st.rerun()
    else:
        st.info("No pending arrangements")

# ============ REST OF THE FUNCTIONS (login, password, etc.) ============

def change_password(username, old_password, new_password, confirm_password):
    """Change user password with validation"""
    users = load_users()
    
    if username not in users:
        return False, "User not found"
    
    if users[username]['password'] != hash_password(old_password):
        return False, "Current password is incorrect"
    
    if old_password == new_password:
        return False, "New password cannot be the same as current password"
    
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long"
    
    if new_password != confirm_password:
        return False, "New passwords do not match"
    
    users[username]['password'] = hash_password(new_password)
    users[username]['first_login'] = False
    users[username]['password_last_changed'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    save_users(users)
    return True, "Password changed successfully!"

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

def login(username, password):
    users = load_users()
    if username in users and users[username]['password'] == hash_password(password):
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = users[username]['role']
        st.session_state.name = users[username]['name']
        st.session_state.designation = users[username]['designation']
        
        if users[username].get('first_login', False) and username == 'admin':
            st.session_state.show_password_change = True
        else:
            st.session_state.show_password_change = False
        
        return True
    return False

def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.name = None
    st.session_state.designation = None
    st.session_state.show_password_change = False
    st.session_state.password_changed = False
    st.session_state.editing_mode = False
    st.rerun()

def admin_panel():
    st.header("👑 Admin Panel")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Create User", "Manage Users", "Upload Timetable", 
        "Online Editor", "Classroom Management", "Arrangements"
    ])
    
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
                        with st.popover(f"Reset Password for {username}"):
                            new_pass = st.text_input(f"New password for {username}", type="password", key=f"reset_pass_{username}")
                            if st.button(f"Confirm Reset", key=f"confirm_reset_{username}"):
                                if new_pass and len(new_pass) >= 6:
                                    success, message = reset_user_password(username, new_pass)
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)
                                else:
                                    st.error("Password must be at least 6 characters")
        else:
            st.info("No users found except admin")
    
    with tab3:
        st.subheader("Upload Timetable (Excel)")
        uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls'])
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                required_cols = ['Day', 'Time', 'Teacher', 'Subject', 'Class', 'Designation']
                if all(col in df.columns for col in required_cols):
                    if save_timetable(df):
                        st.success("Timetable uploaded successfully!")
                        st.rerun()
                else:
                    st.error(f"Missing columns. Required: {required_cols}")
            except Exception as e:
                st.error(f"Error: {e}")
    
    with tab4:
        edit_timetable_online()
    
    with tab5:
        classroom_management()
    
    with tab6:
        arrangement_management()

def user_dashboard():
    st.header(f"👋 Welcome, {st.session_state.name}!")
    st.write(f"**Designation:** {st.session_state.designation}")
    
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
                with st.expander(f"📌 {arr.get('day')} - {arr.get('time')}"):
                    st.write(f"**Class:** {arr.get('class')}")
                    st.write(f"**Subject:** {arr.get('subject')}")
                    st.write(f"**Covering for:** {arr.get('absent_teacher')}")
                    if arr.get('crisis_mode'):
                        st.warning("⚠️ Crisis Mode - Multiple classes may be assigned")
        else:
            st.info("No active arrangements")

def main():
    st.set_page_config(
        page_title="Timetable Management System with AI Prediction",
        page_icon="📚",
        layout="wide"
    )
    
    st.title("📚 Intelligent Timetable Management System")
    st.caption("Powered by AI Prediction & Classroom Management")
    
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
        if st.session_state.show_password_change and not st.session_state.password_changed:
            password_change_form()
        else:
            with st.sidebar:
                st.write(f"**Logged in as:** {st.session_state.name}")
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
