import streamlit as st
from datetime import datetime
import logic

st.set_page_config(page_title="AI Hypertrophy Engine", layout="wide")

# --- STATE MANAGEMENT ---
if 'templates' not in st.session_state:
    st.session_state.templates = {
        "Push Day A": ["Bench Press", "Incline Dumbbell Press", "Overhead Press", "Tricep Extensions"],
        "Pull Day A": ["Barbell Rows", "Pull-ups", "Face Pulls", "Bicep Curls"],
        "Leg Day A": ["Squats", "Romanian Deadlifts", "Leg Press", "Calf Raises"]
    }

st.title("Systematic Hypertrophy Engine")

# --- UI: TEMPLATE MANAGER ---
with st.expander("🛠️ Manage Workout Templates"):
    new_template_name = st.text_input("New Template Name")
    new_template_exercises = st.text_input("Exercises (comma separated)")
    if st.button("Add/Update Template"):
        if new_template_name and new_template_exercises:
            ex_list = [e.strip() for e in new_template_exercises.split(",")]
            st.session_state.templates[new_template_name] = ex_list
            st.success(f"Saved {new_template_name}!")

st.divider()

# --- UI: DAILY EXECUTION ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Today's Parameters")
    selected_routine = st.selectbox("Select Routine", list(st.session_state.templates.keys()))
    workout_type = st.selectbox("Environment", ["Gym", "Home", "Outdoor"])
    energy_level = st.select_slider("Current Energy", options=["Low", "Mid", "High"], value="Mid")
    
    if st.button("Calculate Targets"):
        st.session_state.active_workout = []
        exercises = st.session_state.templates[selected_routine]
        
        with st.spinner("Analyzing past data in a single batch..."):
            batch_history = []
            for ex in exercises:
                past_data = logic.get_last_performance(ex)
                batch_history.append({"exercise": ex, "history": past_data})
            
            batched_targets = logic.calculate_progression_batch(batch_history, energy_level)
            
            if batched_targets:
                for target in batched_targets:
                    st.session_state.active_workout.append({
                        "exercise": target["exercise"],
                        "targets": target
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
                        logic.log_exercise_to_db(date_str, workout_type, res['exercise'], res['t_weight'], res['t_reps'], res['a_weight'], res['a_reps'], res['feedback'])
                st.success("Data secured. Progression locked in.")
                del st.session_state.active_workout
