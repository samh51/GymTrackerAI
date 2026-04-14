import streamlit as st
from datetime import datetime
import logic

st.set_page_config(page_title="Autonomous Gym Coach", layout="wide")

st.title("Systematic Hypertrophy Engine")

# Create UI Tabs
tab_train, tab_manage = st.tabs(["🏋️ Train", "⚙️ Manage Exercises"])

# --- TAB 1: DAILY TRAINING ---
with tab_train:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Condition")
        workout_env = st.selectbox("Environment", ["Gym", "Home", "Outdoor"])
        energy_level = st.select_slider("Energy", options=["Low", "Mid", "High"], value="Mid")
        
        if st.button("Generate Optimal Workout"):
            with st.spinner("Analyzing fatigue & selecting exercises..."):
                plan = logic.suggest_workout(workout_env, energy_level)
                if plan:
                    st.session_state.active_workout = plan
                else:
                    st.error("AI failed to generate a plan. Check your library.")

    with col2:
        if 'active_workout' in st.session_state and st.session_state.active_workout:
            st.subheader("Today's Protocol")
            
            with st.form("execution_form"):
                results_to_log = []
                
                for idx, t in enumerate(st.session_state.active_workout):
                    st.markdown(f"#### {t['exercise']}")
                    st.info(f"**Target:** {t.get('target_reps', '8-10')} @ **{t.get('target_weight_kg', 0)} kg**")
                    
                    c1, c2, c3 = st.columns(3)
                    a_weight = c1.number_input(f"Actual Weight", value=float(t.get('target_weight_kg', 0)), key=f"aw_{idx}")
                    a_reps = c2.text_input(f"Actual Reps", key=f"ar_{idx}")
                    feedback = c3.selectbox("Feedback (RIR)", [
                        "Achieved: A lot of energy left", "Achieved: Medium energy left", 
                        "Achieved: No energy left (Failure)", "Not Achieved: Almost got it", 
                        "Not Achieved: Missed by a lot"
                    ], key=f"f_{idx}")
                    
                    results_to_log.append({
                        "exercise": t['exercise'], "t_weight": t.get('target_weight_kg', 0), "t_reps": t.get('target_reps', ''),
                        "a_weight": a_weight, "a_reps": a_reps, "feedback": feedback
                    })
                    st.divider()
                    
                if st.form_submit_button("Log & Calculate Next Targets"):
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    with st.spinner("Logging data and calculating next week's progression..."):
                        logic.log_and_update(date_str, workout_env, results_to_log)
                    st.success("Workout Secured. Library Updated.")
                    del st.session_state.active_workout

# --- TAB 2: MANAGE EXERCISE LIBRARY ---
with tab_manage:
    st.subheader("Exercise Library")
    
    # Display current library
    df_lib = logic.get_library()
    st.dataframe(df_lib, use_container_width=True)
    
    st.divider()
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("**Add New Exercise**")
        n_name = st.text_input("Name (e.g., Bench Press)")
        n_muscle = st.selectbox("Primary Muscle", ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core"])
        
        # Replaced selectbox with multiselect
        n_envs = st.multiselect("Environments (Select all that apply)", ["Gym", "Home", "Outdoor"])
        
        n_weight = st.number_input("Starting Weight (kg)", min_value=0.0, step=2.5)
        n_reps = st.text_input("Target Reps (e.g., 3x8-10)")
        
        if st.button("Add to Library"):
            if not n_envs:
                st.error("You must select at least one environment.")
            else:
                # Convert the list ["Gym", "Home"] into a string "Gym, Home"
                env_string = ", ".join(n_envs)
                logic.add_exercise(n_name, n_muscle, env_string, n_weight, n_reps)
                st.success("Added! Refresh page to see.")
            
    with c2:
        st.write("**Delete Exercise**")
        if not df_lib.empty:
            del_target = st.selectbox("Select to delete", df_lib['ExerciseName'].tolist())
            if st.button("Delete"):
                logic.delete_exercise(del_target)
                st.error(f"Deleted {del_target}. Refresh page.")
