import pandas as pd
import json
from config import db_log, db_library, ai_model

# --- EXERCISE LIBRARY MANAGEMENT ---
def get_library():
    data = db_library.get_all_records()
    return pd.DataFrame(data)

def add_exercise(name, muscle, environment, start_weight, start_reps):
    db_library.append_row([name, muscle, environment, start_weight, start_reps])

def delete_exercise(name):
    # gspread is clunky with deletions. We pull, filter, clear, and rewrite.
    df = get_library()
    df = df[df['ExerciseName'] != name]
    db_library.clear()
    db_library.update([df.columns.values.tolist()] + df.values.tolist())

def update_library_targets(updates):
    """Updates the master library with new targets calculated by AI after a workout."""
    df = get_library()
    for update in updates:
        idx = df.index[df['ExerciseName'] == update['exercise']].tolist()
        if idx:
            df.loc[idx[0], 'CurrentWeightKG'] = update['new_weight']
            df.loc[idx[0], 'CurrentReps'] = update['new_reps']
    
    db_library.clear()
    db_library.update([df.columns.values.tolist()] + df.values.tolist())

# --- AI WORKOUT GENERATION ---
def suggest_workout(environment, energy_level, duration):
    """AI analyzes history, time, and selects exercises from the library."""
    history = pd.DataFrame(db_log.get_all_records())
    library = get_library()
    
    library['Environment'] = library['Environment'].fillna("")
    mask = library['Environment'].str.contains(environment, case=False) | library['Environment'].str.contains("Any", case=False)
    available_ex = library[mask].to_dict('records')
    
    recent_history = history.tail(30).to_string() if not history.empty else "No previous history."

    prompt = f"""
    You are an elite sports scientist. Create an optimal hypertrophy workout for today.
    Environment: {environment}
    Energy Level: {energy_level}
    Time Available: {duration}
    
    Recent Workout History:
    {recent_history}
    
    Available Exercises in Library:
    {available_ex}
    
    Task:
    1. Analyze the history to determine which muscle groups are most recovered.
    2. Select exercises from the Available Library that fit the timeframe. 
       - CRITICAL TIME RULES:
       - If 10 min: Select ONLY 1 or 2 exercises max. High intensity.
       - If 30-45 min: Select 3-4 exercises.
       - If 1h+: Select 4-6 exercises.
    3. Output the selection as a strict JSON array.
    
    Format:
    [
      {{"exercise": "Exact Name from Library", "target_weight_kg": CurrentWeightKG_from_library, "target_reps": "CurrentReps_from_library"}}
    ]
    """
    
    response = ai_model.generate_content(prompt)
    try:
        return json.loads(response.text.replace('```json', '').replace('```', '').strip())
    except Exception:
        return []

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

def log_and_update(date, env, results_to_log):
    # 1. Log to history
    for res in results_to_log:
        db_log.append_row([date, env, "Auto-Split", res['exercise'], res['t_weight'], res['t_reps'], res['a_weight'], res['a_reps'], res['feedback']])
    
    # 2. Let AI calculate next week's targets based on today's feedback
    new_targets = calculate_next_targets(results_to_log)
    
    # 3. Update the master library
    if new_targets:
        update_library_targets(new_targets)
