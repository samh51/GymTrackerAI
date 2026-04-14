import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import pandas as pd
import json
from datetime import datetime

# --- CONFIGURATION & AUTH ---
st.set_page_config(page_title="AI Hypertrophy Engine", layout="wide")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = dict(st.secrets["gcp_service_account"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# We now need the main data sheet. (You should also create a 'Templates' sheet later to save these permanently)
SHEET_NAME = "WorkoutData"
try:
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1HjD_5l2OV1HdQIY-VzD1qK6bqnzHBN36yz40fpStn2Q/edit?usp=sharing").sheet1
except gspread.exceptions.SpreadsheetNotFound:
    st.error(f"Please create a Google Sheet named '{"GymTrackerAI"}'.")
    st.stop()

# --- STATE MANAGEMENT FOR TEMPLATES ---
# For this prototype, we store templates in session state. 
# Long term, these should be saved to another tab in your Google Sheet.
if 'templates' not in st.session_state:
    st.session_state.templates = {
        "Push Day A": ["Bench Press", "Incline Dumbbell Press", "Overhead Press", "Tricep Extensions"],
        "Pull Day A": ["Barbell Rows", "Pull-ups", "Face Pulls", "Bicep Curls"],
        "Leg Day A": ["Squats", "Romanian Deadlifts", "Leg Press", "Calf Raises"]
    }

# --- HELPER FUNCTIONS ---
def get_last_performance(exercise_name):
    """Fetches only the most recent data for a specific exercise to save tokens and improve AI accuracy."""
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or 'exercise' not in df.columns:
        return None
    
    # Filter for the specific exercise and get the last entry
    ex_df = df[df['exercise'] == exercise_name]
    if ex_df.empty:
        return None
    
    return ex_df.iloc[-1].to_dict()

def calculate_progression(exercise, last_performance, current_energy):
    """Uses AI strictly to calculate progressive overload for one exercise."""
    
    if not last_performance:
        history_context = "This is the first time performing this exercise. Suggest a baseline starting weight and rep range (e.g., 3 sets of 8-12) for a beginner/intermediate."
    else:
        history_context = f"""
        Last performance data:
        - Weight Used: {last_performance.get('a_weight', 'Unknown')} kg
        - Reps Achieved: {last_performance.get('a_reps', 'Unknown')}
        - User Feedback (RIR equivalent): '{last_performance.get('feedback', 'None')}'
        """

    prompt = f"""
    You are an elite sports scientist calculating progressive overload for hypertrophy.
    Exercise: {exercise}
    User's Current Energy Level Today: {current_energy}
    
    {history_context}
    
    Rules for progression:
    - If feedback was "A lot of energy left", aggressively increase weight (2.5 - 5kg).
    - If feedback was "Medium energy left", slightly increase weight (1 - 2.5kg) OR increase rep target.
    - If feedback was "No energy left" or "Not Achieved", maintain or slightly decrease weight.
    - Adjust expectations based on today's energy level.
    
    Output strictly as valid JSON with NO markdown formatting.
    Format: {{"target_weight_kg": 82.5, "target_sets": 3, "target_reps": "8-10", "rationale": "Brief 1-sentence explanation"}}
    """
    
    response = model.generate_content(prompt)
    response_text = response.text.replace('```json', '').replace('```', '').strip()
    
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {"target_weight_kg": 0, "target_sets": 3, "target_reps": "8-12", "rationale": "AI parsing error. Defaulting to baseline."}

def log_exercise(date, w_type, exercise, t_weight, t_reps, a_weight, a_reps, feedback):
    row = [date, w_type, exercise, t_weight, t_reps, a_weight, a_reps, feedback]
    sheet.append_row(row)

# --- UI LAYOUT ---
st.title("Systematic Hypertrophy Engine")

# TEMPLATE MANAGER
with st.expander("🛠️ Manage Workout Templates"):
    st.write("Define your locked-in routines here.")
    new_template_name = st.text_input("New Template Name")
    new_template_exercises = st.text_input("Exercises (comma separated)")
    if st.button("Add/Update Template"):
        if new_template_name and new_template_exercises:
            ex_list = [e.strip() for e in new_template_exercises.split(",")]
            st.session_state.templates[new_template_name] = ex_list
            st.success(f"Saved {new_template_name}!")

st.divider()

# DAILY EXECUTION
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Today's Parameters")
    selected_routine = st.selectbox("Select Routine", list(st.session_state.templates.keys()))
    workout_type = st.selectbox("Environment", ["Gym", "Home", "Outdoor"])
    energy_level = st.select_slider("Current Energy", options=["Low", "Mid", "High"], value="Mid")
    
    if st.button("Calculate Targets"):
        st.session_state.active_workout = []
        exercises = st.session_state.templates[selected_routine]
        
        with st.spinner("Analyzing past data and calculating optimal progression..."):
            for ex in exercises:
                past_data = get_last_performance(ex)
                target_data = calculate_progression(ex, past_data, energy_level)
                
                st.session_state.active_workout.append({
                    "exercise": ex,
                    "targets": target_data
                })

with col2:
    if 'active_workout' in st.session_state and st.session_state.active_workout:
        st.subheader(f"Executing: {selected_routine}")
        
        with st.form("execution_form"):
            results_to_log = []
            
            for idx, item in enumerate(st.session_state.active_workout):
                ex_name = item['exercise']
                t = item['targets']
                
                st.markdown(f"#### {ex_name}")
                st.info(f"**Target:** {t.get('target_sets', 3)} sets x {t.get('target_reps', '8-10')} @ **{t.get('target_weight_kg', 0)} kg**")
                st.caption(f"*AI Rationale: {t.get('rationale', 'N/A')}*")
                
                c1, c2, c3 = st.columns(3)
                a_weight = c1.number_input(f"Actual Weight (kg)", value=float(t.get('target_weight_kg', 0)), key=f"aw_{idx}")
                a_reps = c2.text_input(f"Actual Reps", key=f"ar_{idx}")
                
                feedback = c3.selectbox("Feedback (RIR)", [
                    "Achieved: A lot of energy left", "Achieved: Medium energy left", 
                    "Achieved: No energy left (Failure)", "Not Achieved: Almost got it", 
                    "Not Achieved: Missed by a lot"
                ], key=f"f_{idx}")
                
                results_to_log.append({
                    "exercise": ex_name, "t_weight": t.get('target_weight_kg', 0), "t_reps": t.get('target_reps', ''),
                    "a_weight": a_weight, "a_reps": a_reps, "feedback": feedback
                })
                st.divider()
                
            if st.form_submit_button("Log Workout"):
                date_str = datetime.now().strftime("%Y-%m-%d")
                with st.spinner("Writing to database..."):
                    for res in results_to_log:
                        log_exercise(date_str, workout_type, res['exercise'], res['t_weight'], res['t_reps'], res['a_weight'], res['a_reps'], res['feedback'])
                st.success("Data secured. Progression locked in.")
                del st.session_state.active_workout
