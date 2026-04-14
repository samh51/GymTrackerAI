import pandas as pd
import json
import streamlit as st
from config import db_sheet, ai_model

def get_last_performance(exercise_name):
    """Fetches only the most recent data for a specific exercise."""
    data = db_sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or 'exercise' not in df.columns:
        return None
    
    ex_df = df[df['exercise'] == exercise_name]
    if ex_df.empty:
        return None
    
    return ex_df.iloc[-1].to_dict()

def calculate_progression_batch(exercises_history, current_energy):
    """Sends all exercises in one single API call to avoid rate limits."""
    history_context = ""
    for item in exercises_history:
        ex = item['exercise']
        past = item['history']
        if not past:
            history_context += f"- {ex}: First time performing. Needs baseline.\n"
        else:
            history_context += f"- {ex}: Last weight: {past.get('a_weight')}kg, Reps: {past.get('a_reps')}, Feedback: '{past.get('feedback')}'\n"

    prompt = f"""
    You are an elite sports scientist calculating progressive overload.
    User's Current Energy Level Today: {current_energy}
    
    Here is the history for today's routine:
    {history_context}
    
    Rules for progression:
    - If feedback was "A lot of energy left", aggressively increase weight (2.5 - 5kg).
    - If feedback was "Medium energy left", slightly increase weight (1 - 2.5kg) OR increase reps.
    - If feedback was "No energy left" or "Not Achieved", maintain or slightly decrease weight.
    
    Output strictly as a JSON array of objects with NO markdown.
    Format EXACTLY like this:
    [
      {{"exercise": "Exercise Name 1", "target_weight_kg": 82.5, "target_sets": 3, "target_reps": "8-10", "rationale": "Brief reason"}},
      {{"exercise": "Exercise Name 2", "target_weight_kg": 40, "target_sets": 3, "target_reps": "10-12", "rationale": "Brief reason"}}
    ]
    """
    
    response = ai_model.generate_content(prompt)
    response_text = response.text.replace('```json', '').replace('```', '').strip()
    
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return []

def log_exercise_to_db(date, w_type, exercise, t_weight, t_reps, a_weight, a_reps, feedback):
    """Writes a single row to Google Sheets."""
    row = [date, w_type, exercise, t_weight, t_reps, a_weight, a_reps, feedback]
    db_sheet.append_row(row)
