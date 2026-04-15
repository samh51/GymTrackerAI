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

# Connect directly to the Sheet via Hardcoded ID
SHEET_ID = "1HjD_5l2OV1HdQIY-VzD1qK6bqnzHBN36yz40fpStn2Q"
try:
    spreadsheet = client.open_by_key(SHEET_ID)
    db_log = spreadsheet.worksheet("WorkoutLog")
    db_library = spreadsheet.worksheet("ExerciseLibrary")
    db_cardio = spreadsheet.worksheet("CardioLog") # NEW CARDIO DB
except Exception as e:
    st.error(f"Critical Database Error: {e}")
    st.stop()
