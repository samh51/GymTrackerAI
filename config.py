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
    # Bypassing name search, opening by direct ID
    spreadsheet = client.open_by_key(SHEET_ID)
    db_log = spreadsheet.worksheet("WorkoutLog")
    db_library = spreadsheet.worksheet("ExerciseLibrary")
except gspread.exceptions.SpreadsheetNotFound:
    st.error("Critical Error: The hardcoded spreadsheet ID was not found. Check if the link is correct and accessible by the service account.")
    st.stop()
except gspread.exceptions.WorksheetNotFound:
    st.error("Critical Error: The spreadsheet was found, but the tabs are wrong. Make sure you have exactly two tabs named 'WorkoutLog' and 'ExerciseLibrary'.")
    st.stop()
