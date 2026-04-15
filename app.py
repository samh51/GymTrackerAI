import streamlit as st
from datetime import datetime
import logic

st.set_page_config(page_title="Autonomous Gym Coach", layout="wide")
st.title("Systematic Hypertrophy Engine")

# --- STATE INITIALIZATION ---
if 'active_workout' not in st.session_state: st.session_state.active_workout = None
if 'exercise_status' not in st.session_state: st.session_state.exercise_status = {}
if 'staged_results' not in st.session_state: st.session_state.staged_results = []

tab_train, tab_cardio, tab_manage = st.tabs(["🏋️ Train", "🏃 Cardio", "⚙️ Manage Library"])

# --- TAB 1: DAILY TRAINING ---
with tab_train:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Condition")
        workout_env = st.selectbox("Environment", ["Gym", "Home", "Outdoor"])
        energy_level = st.select_slider("Energy", options=["Low", "Mid", "High"], value="Mid")
        duration = st.selectbox("Available Time", ["10 min", "30 min", "45 min", "1 h", "1.5 h", "2 h"], index=3)
        
        if st.button("Generate Optimal Workout"):
            with st.spinner("Analyzing history and constructing protocol..."):
                plan = logic.suggest_workout(workout_env, energy_level, duration)
                if plan:
                    st.session_state.active_workout = plan
                    st.session_state.staged_results = []
                    # Initialize status for all exercises to 'pending'
                    st.session_state.exercise_status = {idx: 'pending' for idx in range(len(plan['exercises']))}
                else:
                    st.error("AI failed to generate a plan.")

with col2:
        if st.session_state.active_workout:
            plan = st.session_state.active_workout
            split_name = plan.get('recommended_split', 'Unknown Split')
            
            st.info(plan.get('intro_summary', ''))
            st.subheader(f"Protocol: {split_name}")
            st.caption(f"🧠 **Rationale:** {plan.get('rationale', '')}")
            st.divider()
            
            all_completed = True
            
            for idx, t in enumerate(plan.get('exercises', [])):
                status = st.session_state.exercise_status.get(idx, 'pending')
                is_new = t.get('is_new_suggestion', False)
                manual_swap_key = f"manual_swap_{idx}"
                
                if status == 'pending':
                    all_completed = False
                    
                    # --- MANUAL SWAP UI ---
                    if st.session_state.get(manual_swap_key, False):
                        st.markdown(f"#### 🔄 Swapping out: {t['exercise']}")
                        available_options = logic.get_env_exercises(workout_env)
                        
                        if available_options:
                            new_ex_choice = st.selectbox("Select your new exercise:", available_options, key=f"sel_{idx}")
                            c_btn1, c_btn2 = st.columns(2)
                            if c_btn1.button("✅ Confirm Swap", key=f"conf_{idx}"):
                                new_details = logic.get_exercise_details(new_ex_choice)
                                if new_details:
                                    st.session_state.active_workout['exercises'][idx] = new_details
                                    st.session_state[manual_swap_key] = False
                                    st.toast("Fantastic choice! Exercise updated!")
                                    st.rerun()
                            if c_btn2.button("❌ Cancel", key=f"canc_{idx}"):
                                st.session_state[manual_swap_key] = False
                                st.rerun()
                        else:
                            st.error("No other exercises found in your library for this environment!")
                            if st.button("Cancel", key=f"canc_empty_{idx}"):
                                st.session_state[manual_swap_key] = False
                                st.rerun()
                        st.divider()
                        continue # Skip rendering the rest of the normal UI while swapping
                    
                    # --- NORMAL EXERCISE UI ---
                    if is_new: 
                        st.warning(f"💡 **AI Suggestion:** {t['exercise']} (Not in Library)")
                    else: 
                        st.markdown(f"#### {t['exercise']}")
                    
                    st.write(f"**Target:** {t.get('target_reps', '8-10')} @ **{t.get('target_weight_kg', 0)} kg**")
                    
                    c1, c2, c3 = st.columns(3)
                    a_weight = c1.number_input(f"Weight", value=float(t.get('target_weight_kg', 0)), key=f"aw_{idx}")
                    a_reps = c2.text_input(f"Reps", key=f"ar_{idx}")
                    feedback = c3.selectbox("Feedback", [
                        "Achieved: A lot of energy left", 
                        "Achieved: Medium energy left", 
                        "Achieved: No energy left (Failure)", 
                        "Not Achieved: Almost got it", 
                        "Not Achieved: Missed by a lot"
                    ], key=f"f_{idx}")
                    
                    accept_new = st.checkbox("Save to Library", value=True, key=f"acc_{idx}") if is_new else False
                    
                    # The 4 Dynamic Buttons!
                    bc1, bc2, bc3, bc4 = st.columns(4)
                    
                    if bc1.button("✅ Log", key=f"log_{idx}", type="primary"):
                        st.session_state.staged_results.append({
                            "exercise": t['exercise'], "t_weight": t.get('target_weight_kg', 0), "t_reps": t.get('target_reps', ''),
                            "a_weight": a_weight, "a_reps": a_reps, "feedback": feedback,
                            "is_new": is_new, "accept_new": accept_new, "muscle": t.get('primary_muscle', 'Unknown')
                        })
                        st.session_state.exercise_status[idx] = 'logged'
                        st.toast("Awesome job! Execution logged. Keep that momentum going!")
                        st.rerun()
                        
                    if bc2.button("⏭️ Skip", key=f"skip_{idx}"):
                        st.session_state.exercise_status[idx] = 'skipped'
                        st.toast("Exercise skipped. You'll get it next time!")
                        st.rerun()
                        
                    if bc3.button("🔀 Auto-Change", key=f"auto_{idx}"):
                        alt_ex = logic.get_auto_alternative(t['exercise'], workout_env, t.get('primary_muscle', 'Unknown'))
                        if alt_ex:
                            st.session_state.active_workout['exercises'][idx] = alt_ex
                            st.toast("Swapped! Let's crush this new movement!")
                            st.rerun()
                        else:
                            st.toast("No alternatives found in the library for this muscle/environment!")
                            
                    if bc4.button("🔍 Select Other", key=f"man_{idx}"):
                        st.session_state[manual_swap_key] = True
                        st.rerun()
                        
                    st.divider()
                
                elif status == 'logged':
                    st.success(f"✅ {t['exercise']} - Logged brilliantly!")
                elif status == 'skipped':
                    st.error(f"⏭️ {t['exercise']} - Skipped")
                
                elif status == 'logged':
                    st.success(f"✅ {t['exercise']} - Logged brilliantly!")
                elif status == 'skipped':
                    st.error(f"⏭️ {t['exercise']} - Skipped")

            # Finalize Batch
            if all_completed and len(st.session_state.exercise_status) > 0:
                st.subheader("Session Complete! Amazing effort!")
                if st.button("Commit Data to Database", type="primary"):
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    with st.spinner("Processing your wonderful progress..."):
                        final_results = []
                        for r in st.session_state.staged_results:
                            if r['is_new'] and r['accept_new']:
                                logic.add_exercise(r['exercise'], r['muscle'], workout_env, r['a_weight'], r['t_reps'])
                            final_results.append(r)
                            
                        if final_results:
                            logic.log_and_update(date_str, workout_env, split_name, final_results)
                            
                    st.success("Data secured and progression calculated! You are one step closer to your goals!")
                    st.session_state.active_workout = None
                    st.session_state.exercise_status = {}
                    st.session_state.staged_results = []
                    st.rerun()

# --- TAB 2: CARDIO ---
with tab_cardio:
    st.subheader("Cardiovascular Conditioning")
    with st.form("cardio_form"):
        c_date = st.date_input("Date", datetime.today())
        c_type = st.selectbox("Modality", ["Running", "Cycling", "Swimming", "Rowing"])
        c_dist = st.number_input("Distance (km)", min_value=0.0, step=0.1)
        c_time = st.number_input("Time (minutes)", min_value=0, step=1)
        if st.form_submit_button("Log Cardio"):
            logic.log_cardio(c_date.strftime("%Y-%m-%d"), c_type, c_dist, c_time)
            st.success("Cardio logged.")

# --- TAB 3: MANAGE LIBRARY ---
with tab_manage:
    df_lib = logic.get_library()
    st.dataframe(df_lib, use_container_width=True)
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Add New Exercise**")
        n_name = st.text_input("Name")
        n_muscle = st.selectbox("Primary Muscle", ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core"])
        n_envs = st.multiselect("Environments", ["Gym", "Home", "Outdoor"])
        n_weight = st.number_input("Starting Weight (kg)", min_value=0.0, step=2.5)
        n_reps = st.text_input("Target Reps (e.g., 3x8-10)")
        if st.button("Add to Library"):
            if n_envs:
                logic.add_exercise(n_name, n_muscle, ", ".join(n_envs), n_weight, n_reps)
                st.success("Added!")
            else: st.error("Select an environment.")
    with c2:
        st.write("**Delete Exercise**")
        if not df_lib.empty:
            del_target = st.selectbox("Select to delete", df_lib['ExerciseName'].tolist())
            if st.button("Delete"):
                logic.delete_exercise(del_target)
                st.error(f"Deleted {del_target}.")
