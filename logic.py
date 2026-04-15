from google.api_core.exceptions import ResourceExhausted

import pandas as pd
import json
from datetime import datetime, timedelta
import streamlit as st
from config import db_log, db_library, db_cardio, ai_model

# --- DATABASE OPERATIONS ---
def get_library():
    data = db_library.get_all_records()
    return pd.DataFrame(data)

def add_exercise(name, muscle, environment, start_weight, start_reps):
    db_library.append_row([name, muscle, environment, start_weight, start_reps])

def delete_exercise(name):
    df = get_library()
    df = df[df['ExerciseName'] != name]
    db_library.clear()
    db_library.update([df.columns.values.tolist()] + df.values.tolist())
    
import random

def get_auto_alternative(current_name, environment, primary_muscle):
    """Finds a random alternative exercise for the same muscle and environment."""
    df = get_library()
    if df.empty: return None
    
    df['Environment'] = df['Environment'].fillna("")
    mask_env = df['Environment'].str.contains(environment, case=False) | df['Environment'].str.contains("Any", case=False)
    mask_not_current = df['ExerciseName'] != current_name
    
    # Try to match the exact muscle group first
    if primary_muscle and primary_muscle != 'Unknown':
        mask_muscle = df['TargetMuscle'].str.contains(primary_muscle, case=False)
        available = df[mask_env & mask_muscle & mask_not_current]
    else:
        available = pd.DataFrame()
        
    # Fallback: Just grab ANY other exercise for that environment if we can't match the muscle
    if available.empty:
        available = df[mask_env & mask_not_current]
        
    if available.empty: return None
    
    chosen = available.sample(1).iloc[0]
    return {
        "exercise": chosen['ExerciseName'],
        "target_weight_kg": chosen['CurrentWeightKG'],
        "target_reps": chosen['CurrentReps'],
        "is_new_suggestion": False,
        "primary_muscle": chosen['TargetMuscle']
    }

def get_env_exercises(environment):
    """Gets a list of all exercise names available in the current environment."""
    df = get_library()
    if df.empty: return []
    df['Environment'] = df['Environment'].fillna("")
    mask_env = df['Environment'].str.contains(environment, case=False) | df['Environment'].str.contains("Any", case=False)
    return df[mask_env]['ExerciseName'].tolist()

def get_exercise_details(name):
    """Fetches the specific target weight and reps for a manually selected exercise."""
    df = get_library()
    ex = df[df['ExerciseName'] == name]
    if ex.empty: return None
    chosen = ex.iloc[0]
    return {
        "exercise": chosen['ExerciseName'],
        "target_weight_kg": chosen['CurrentWeightKG'],
        "target_reps": chosen['CurrentReps'],
        "is_new_suggestion": False,
        "primary_muscle": chosen['TargetMuscle']
    }
def log_cardio(date, c_type, distance, time):
    db_cardio.append_row([date, c_type, distance, time])

def get_7_day_history():
    """Fetches and formats the last 7 days of workouts."""
    df = pd.DataFrame(db_log.get_all_records())
    if df.empty:
        return "No history in the last 7 days."
    
    # Sanitize headers: force everything to lowercase to prevent KeyErrors
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    if 'date' not in df.columns:
        return "Database error: 'date' column missing."
    
    # Filter for last 7 days
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_df = df[df['date'] >= seven_days_ago].copy()
    
    if recent_df.empty:
        return "No workouts logged in the last 7 days."
        
    recent_df['datestr'] = recent_df['date'].dt.strftime('%Y-%m-%d')
    summary = recent_df.groupby(['datestr', 'split'])['exercise'].apply(list).reset_index()
    return summary.to_string()

def update_library_targets(updates):
    df = get_library()
    if df.empty: return

    df['CurrentWeightKG'] = pd.to_numeric(df['CurrentWeightKG'], errors='coerce').fillna(0.0).astype(float)
    df['CurrentReps'] = df['CurrentReps'].astype(str)
    
    for update in updates:
        idx = df.index[df['ExerciseName'] == update['exercise']].tolist()
        if idx:
            try: safe_weight = float(update['new_weight'])
            except: safe_weight = df.loc[idx[0], 'CurrentWeightKG'] 
            safe_reps = str(update.get('new_reps', df.loc[idx[0], 'CurrentReps']))
            df.loc[idx[0], 'CurrentWeightKG'] = safe_weight
            df.loc[idx[0], 'CurrentReps'] = safe_reps
    
    db_library.clear()
    db_library.update([df.columns.values.tolist()] + df.values.tolist())

# --- AI ENGINES ---
def suggest_workout(environment, energy_level, duration):
    library = get_library()
    library['Environment'] = library['Environment'].fillna("")
    mask = library['Environment'].str.contains(environment, case=False) | library['Environment'].str.contains("Any", case=False)
    available_ex = library[mask].to_dict('records')
    
    seven_day_summary = get_7_day_history()

    prompt = f"""
    You are an elite, motivational sports scientist. Always Happy and encouriging. 
    Environment: {environment} | Energy: {energy_level} | Time: {duration}
    
    7-Day History (Oldest to Newest):
    {seven_day_summary}
    
    Available Library: {available_ex}
    
    Task:
    1. Write an "intro_summary": A motivational, analytical 1-2 sentence recap of the 7-day history. Follow it with a harsh, stoic reality-check about discipline.
    2. DECLARE a workout split based on what needs recovery.
    3. Select exercises to fit the time limit. Invent new ones if the library is empty.
    
    Output strictly as JSON:
    {{
      "intro_summary": "Your recap and harsh truth here.",
      "recommended_split": "Name of the Split",
      "rationale": "Why this split.",
      "exercises": [
        {{
          "exercise": "Exercise Name", 
          "target_weight_kg": 20, 
          "target_reps": "3x8-10", 
          "is_new_suggestion": false,
          "primary_muscle": "Back"
        }}
      ]
    }}
    """
    try:
        response = ai_model.generate_content(prompt)
        return json.loads(response.text.replace('```json', '').replace('```', '').strip())
    except ResourceExhausted:
        st.error("Whoops! We are moving too fast for the AI! 🚀 The API just needs a 60-second breather. Grab some water and click Generate again in a minute!")
        return None
    except Exception as e:
        st.error(f"Oh no, a little hiccup occurred: {e} - Let's try that again!")
        return None

def calculate_next_targets(completed_workout):
    prompt = f"""Evaluate this and calculate progressive overload for NEXT time: {completed_workout}
    Rules: 'A lot of energy' = +2.5 to 5kg. 'Medium' = +1 to 2.5kg. 'Failure' = maintain. 'Not Achieved' = decrease slightly.
    Output strictly as JSON array: [{{"exercise": "Name", "new_weight": 82.5, "new_reps": "8-10"}}]"""
    response = ai_model.generate_content(prompt)
    try: return json.loads(response.text.replace('```json', '').replace('```', '').strip())
    except: return []

def log_and_update(date, env, split_name, results_to_log):
    for res in results_to_log:
        db_log.append_row([date, env, split_name, res['exercise'], res['t_weight'], res['t_reps'], res['a_weight'], res['a_reps'], res['feedback']])
    new_targets = calculate_next_targets(results_to_log)
    if new_targets: update_library_targets(new_targets)
