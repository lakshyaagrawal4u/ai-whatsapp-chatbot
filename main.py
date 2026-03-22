from flask import Flask, request
import os
from dotenv import load_dotenv
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("ClinicData").sheet1

# Flask app
app = Flask(__name__)

# User state storage
user_state = {}
user_data = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    user_msg = request.values.get("Body", "").lower()
    user_number = request.values.get("From")

    # Initialize user
    if user_number not in user_state:
        user_state[user_number] = None
        user_data[user_number] = {}

    # 🔥 FIXED REPLIES
    if "fee" in user_msg:
        return respond("Doctor consultation fee ₹500 hai.")

    if "timing" in user_msg:
        return respond("Clinic timing: 10 AM - 6 PM")

    if "doctor" in user_msg:
        return respond("Doctor: Dr. Sharma (General Physician)")

    if "treatment" in user_msg or "problem" in user_msg:
        return respond("Hum fever, cold, skin problems, general checkup ka ilaj karte hain.")

    # 🟢 APPOINTMENT FLOW
    if "appointment" in user_msg:
        user_state[user_number] = "name"
        return respond("Appointment ke liye apna naam batayein.")

    if user_state[user_number] == "name":
        user_data[user_number]["name"] = user_msg
        user_state[user_number] = "date"
        return respond("Date batayein (e.g., 20 March).")

    if user_state[user_number] == "date":
        user_data[user_number]["date"] = user_msg
        user_state[user_number] = "time"
        return respond("Time batayein (e.g., 5 PM).")

    if user_state[user_number] == "time":
        user_data[user_number]["time"] = user_msg
        user_state[user_number] = "problem"
        return respond("Apni problem short me batayein.")

    if user_state[user_number] == "problem":
        user_data[user_number]["problem"] = user_msg

        # Save to Google Sheet
        sheet.append_row([
            user_data[user_number]["name"],
            user_number,
            user_data[user_number]["date"],
            user_data[user_number]["time"],
            user_data[user_number]["problem"]
        ])

        user_state[user_number] = None
        return respond("✅ Appointment booked! Clinic me time par aa jayein.")

    # 🤖 GEMINI AI RESPONSE
    prompt = f"""
    You are a clinic assistant chatbot.

    Clinic Details:
    - Doctor: Dr. Sharma
    - Fees: ₹500
    - Timing: 10 AM - 6 PM
    - Services: Fever, Cold, Skin problems, General checkup

    Rules:
    - Do NOT give serious medical advice
    - Suggest visiting clinic
    - Be polite

    User: {user_msg}
    """

    ai_response = model.generate_content(prompt)
    return respond(ai_response.text)


# Twilio response format
def respond(message):
    return f"<Response><Message>{message}</Message></Response>"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)