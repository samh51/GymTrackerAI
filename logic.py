import pandas as pd
import json
import streamlit as st
from config import db_log, db_library, ai_model

# --- EXERCISE LIBRARY MANAGEMENT ---
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

def update_library_targets(updates):
    """Updates the master library with new targets calculated by AI after a workout."""
    df = get_library()
    
    if df.empty:
        return

    # Enforce strict data types to prevent Pandas crashes
    df['CurrentWeightKG'] = pd.to_numeric(df['CurrentWeightKG'], errors='coerce').fillna(0.0).astype(float)
    df['CurrentReps'] = df['CurrentReps'].astype(str)
    
    for update in updates:
        idx = df.index[df['ExerciseName'] == update['exercise']].tolist()
        if idx:
            # Sanitize AI output
            try:
                safe_weight = float(update['new_weight'])
            except (ValueError, TypeError, KeyError):
                safe_weight = df.loc[idx[0], 'CurrentWeightKG'] 
                
            safe_reps = str(update.get('new_reps', df.loc[idx[0], 'CurrentReps']))
            
            df.loc[idx[0], 'CurrentWeightKG'] = safe_weight
            df.loc[idx[0], 'CurrentReps'] = safe_reps
    
    db_library.clear()
    db_library.update([df.columns.values.tolist()] + df.values.tolist())

# --- AI WORKOUT GENERATION ---
def suggest_workout(environment, energy_level, duration):
    """AI analyzes history, determines the split, and suggests exercises."""
    history = pd.DataFrame(db_log.get_all_records())
    library = get_library()
    
    library['Environment'] = library['Environment'].fillna("")
    mask = library['Environment'].str.contains(environment, case=False) | library['Environment'].str.contains("Any", case=False)
    available_ex = library[mask].to_dict('records')
    
    recent_history = history.tail(30).to_string() if not history.empty else "No previous history."

    prompt = f"""
    You are an elite sports scientist creating an optimal hypertrophy workout.
    Environment: {environment}
    Energy Level: {energy_level}
    Time Available: {duration}
    
    Recent Workout History:
    {recent_history}
    
    Available Exercises in Library:
    {available_ex}
    
    Task:
    1. Analyze the history to determine which muscle groups are most recovered. 
    2. Based on that recovery, DECLARE a specific workout split for today (e.g., "Push", "Pull", "Legs", "Upper Body", "Lower Body", "Full Body").
    3. Select exercises to fit the {duration} timeframe (10m: 1-2, 30m: 3-4, 1h+: 4-6).
    4. If the library lacks exercises for the chosen split/environment, invent new ones.
    
    Output strictly as a JSON object. NO markdown formatting.
    Format EXACTLY like this:
    {{
      "recommended_split": "Name of the Split",
      "rationale": "One short sentence explaining why.",
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
    
    response = ai_model.generate_content(prompt)
    try:
        return json.loads(response.text.replace('```json', '').replace('```', '').strip())
    except Exception:
        return None

# --- AI PROGRESSION EVALUATION ---
def calculate_next_targets(completed_workout):
    """AI analyzes performance and calculates targets for the NEXT time."""
    prompt = f"""
    Evaluate this completed workout and calculate progressive overload for the NEXT session.
    
    Workout Data:
    {completed_workout}
    
    Rules for next session's targets:
    - Feedback "A lot of energy left": Aggressive weight increase (+2.5 to 5kg).
    - Feedback "Medium energy left": Slight weight increase (+1 to 2.5kg) or rep increase.
    - Feedback "No energy left" / "Failure": Maintain weight.
    - Feedback "Not Achieved": Decrease weight slightly.
    
    Output strictly as JSON array:
    [
      {{"exercise": "Name", "new_weight": 82.5, "new_reps": "8-10"}}
    ]
    """
    response = ai_model.generate_content(prompt)
    try:
        return json.loads(response.text.replace('```json', '').replace('```', '').strip())
    except Exception:
        return []

def log_and_update(date, env, split_name, results_to_log):
    """Logs the workout with the explicitly defined split name."""
    # 1. Log to history
    for res in results_to_log:
        db_log.append_row([date, env, split_name, res['exercise'], res['t_weight'], res['t_reps'], res['a_weight'], res['a_reps'], res['feedback']])
    
    # 2. Let AI calculate next week's targets based on today's feedback
    new_targets = calculate_next_targets(results_to_log)
    
    # 3. Update the master library
    if new_targets:
        update_library_targets(new_targets)
