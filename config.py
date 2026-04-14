import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai

# --- AI CONFIGURATION ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# Using the fast, rate-limit friendly model
ai_model = genai.GenerativeModel('gemini-2.5-flash')

# --- DATABASE CONFIGURATION ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = dict(st.secrets["gcp_service_account"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Connect to the Sheet
SHEET_NAME = "GymTrackerAI"
try:
    db_sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1HjD_5l2OV1HdQIY-VzD1qK6bqnzHBN36yz40fpStn2Q/edit?gid=883371807#gid=883371807").sheet1
    db_log = spreadsheet.worksheet("WorkoutLog")
    db_library = spreadsheet.worksheet("ExerciseLibrary")
except gspread.exceptions.SpreadsheetNotFound:
    st.error(f"Critical Error: Database '{SHEET_NAME}' not found or not shared with Service Account.")
    st.stop()
except gspread.exceptions.WorksheetNotFound:
    st.error("Critical Error: Make sure you have tabs named 'WorkoutLog' and 'ExerciseLibrary'.")
    st.stop()
