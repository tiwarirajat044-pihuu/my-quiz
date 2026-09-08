from datetime import datetime
import os
import pandas as pd
import re
from pypdf import PdfReader
import streamlit as st

# File paths for data storage
USERS_FILE = "users_db.csv"
RESULTS_FILE = "results.csv"
LOGINS_FILE = "user_logins.csv"

st.set_page_config(
    page_title="🚀 Ultimate Interactive Quiz Hub", page_icon="🎯", layout="centered"
)

# Custom styling & motivational background touch
st.markdown(
    """
    <style>
    .main { background-color: #f4f6f9; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; background-color: #ff4b4b; color: white; }
    .stButton>button:hover { background-color: #e03e3e; color: white; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session States
if "questions" not in st.session_state:
  st.session_state.questions = [
      {
          "question": "What is the capital of India?",
          "options": ["Mumbai", "New Delhi", "Kolkata", "Chennai"],
          "answer": "New Delhi",
      }
  ]

if "quiz_active" not in st.session_state:
  st.session_state.quiz_active = True

if "notifications" not in st.session_state:
  st.session_state.notifications = [
      "Welcome to the Quiz Hub! Stay tuned for active quizzes. 🌟"
  ]

if "admin_password" not in st.session_state:
  st.session_state.admin_password = "admin123"


# Robust PDF Parsing Function (Fixes option bleeding & mapping)
def parse_pdf_questions(uploaded_file):
  reader = PdfReader(uploaded_file)
  text = ""
  for page in reader.pages:
    t = page.extract_text()
    if t:
      text += t + "\n"

  parsed_questions = []
  lines = text.split("\n")
  current_q = None
  current_options = []
  current_ans = None

  for line in lines:
    line = line.strip()
    if not line:
      continue

    # Detect question pattern (e.g., "1.", "Q1.", "1)")
    if re.match(r"^(\d+[\.\)]|Q\d+[\.\)])", line):
      if current_q and len(current_options) >= 2:
        parsed_questions.append({
            "question": current_q,
            "options": current_options,
            "answer": (
                current_ans
                if current_ans
                else current_options[0]
                if current_options
                else ""
            ),
        })
      current_q = re.sub(r"^(\d+[\.\)]|Q\d+[\.\)])\s*", "", line)
      current_options = []
      current_ans = None
    elif re.match(r"^([A-D][\.\)]|\([A-D]\))", line):
      opt_text = re.sub(r"^([A-D][\.\)]|\([A-D]\))\s*", "", line)
      current_options.append(opt_text)
    elif line.lower().startswith("ans") or line.lower().startswith("correct"):
      ans_part = re.sub(
          r"^(ans|answer|correct\s*answer)[\:\-\s]*", "", line, flags=re.IGNORECASE
      ).strip()
      current_ans = ans_part
    else:
      if current_q and not current_options:
        current_q += " " + line
      elif current_options:
        current_options[-1] += " " + line

  if current_q and len(current_options) >= 2:
    parsed_questions.append({
        "question": current_q,
        "options": current_options,
        "answer": (
            current_ans
            if current_ans
            else current_options[0]
            if current_options
            else ""
        ),
    })

  return parsed_questions


# Load or initialize users database
def load_users():
  if os.path.exists(USERS_FILE):
    return pd.read_csv(USERS_FILE)
  return pd.DataFrame(columns=["Identifier", "Password"])


def save_user(identifier, password):
  df = load_users()
  new_row = pd.DataFrame([{"Identifier": identifier, "Password": password}])
  df = pd.concat([df, new_row], ignore_index=True)
  df.to_csv(USERS_FILE, index=False)


# Main App Authentication Gate (Unified Portal)
if "logged_in_user" not in st.session_state:
  st.session_state.logged_in_user = None
  st.session_state.is_admin = False

if st.session_state.logged_in_user is None:
  st.title("🎯 Welcome to Quiz Hub")
  st.write(
      "✨ *Log in or create your account to begin your learning journey!* ✨"
  )

  auth_tab1, auth_tab2 = st.tabs(["🔑 Login", "📝 Create Account (Sign Up)"])

  with auth_tab1:
    st.subheader("Existing User / Admin Login")
    login_id = st.text_input("Username, Email ID, or Mobile Number", key="l_id")
    login_pass = st.text_input("Password", type="password", key="l_pass")

    if st.button("Login Now"):
      # Check if Admin
      if (
          login_id.strip().lower() == "admin"
          and login_pass == st.session_state.admin_password
      ):
        st.session_state.logged_in_user = "Admin"
        st.session_state.is_admin = True
        # Log admin login
        login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pd.DataFrame([{
            "Identity": "Admin",
            "Type": "Admin Login",
            "Timestamp": login_time,
        }]).to_csv(
            LOGINS_FILE,
            mode="a",
            header=not os.path.exists(LOGINS_FILE),
            index=False,
        )
        st.success("Admin Logged in successfully! Redirecting...")
        st.rerun()
      else:
        # Check regular user database
        users_df = load_users()
        match = users_df[
            (users_df["Identifier"] == login_id)
            & (users_df["Password"] == login_pass)
        ]
        if not match.empty:
          st.session_state.logged_in_user = login_id
          st.session_state.is_admin = False
          # Log user entry
          login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          pd.DataFrame([{
              "Identity": login_id,
              "Type": "Participant Login",
              "Timestamp": login_time,
          }]).to_csv(
              LOGINS_FILE,
              mode="a",
              header=not os.path.exists(LOGINS_FILE),
              index=False,
          )
          st.success(f"Welcome back, {login_id}!")
          st.rerun()
        else:
          st.error("❌ Invalid credentials or user does not exist.")

  with auth_tab2:
    st.subheader("New User Registration")
    reg_id = st.text_input(
        "Enter Username, Email ID, or Mobile Number", key="r_id"
    )
    reg_pass = st.text_input("Create Password", type="password", key="r_pass")

    if st.button("Register & Login"):
      if reg_id.strip() and reg_pass.strip():
        users_df = load_users()
        if not users_df.empty and reg_id in users_df["Identifier"].values:
          st.warning(
              "⚠️ This identity is already registered. Please log in directly."
          )
        else:
          save_user(reg_id, reg_pass)
          st.session_state.logged_in_user = reg_id
          st.session_state.is_admin = False
          # Log registration & login
          login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          pd.DataFrame([{
              "Identity": reg_id,
              "Type": "New User Registration",
              "Timestamp": login_time,
          }]).to_csv(
              LOGINS_FILE,
              mode="a",
              header=not os.path.exists(LOGINS_FILE),
              index=False,
          )
          st.success("Account created successfully! Welcome!")
          st.rerun()
      else:
        st.error("Please fill in both fields.")

else:
  # ==========================================
  # ADMIN PANEL DASHBOARD (Clean Tab-Based UI)
  # ==========================================
  if st.session_state.is_admin:
    st.title("🔐 Admin Control Dashboard")
    st.sidebar.write(f"Logged in as: **Admin**")

    if st.sidebar.button("🚪 Logout"):
      st.session_state.logged_in_user = None
      st.session_state.is_admin = False
      st.rerun()

    # Organized side-by-side / sequential tabs for admin control
    admin_tab1, admin_tab2, admin_tab3, admin_tab4, admin_tab5 = st.tabs([
        "👥 User Logs",
        "📚 Question Bank",
        "⚙️ Quiz Control & Notice",
        "📊 Results & Leaderboard",
        "🔑 Settings",
    ])

    with admin_tab1:
      st.subheader("📋 User Login Timestamps & Details")
      if os.path.exists(LOGINS_FILE):
        df_logins = pd.read_csv(LOGINS_FILE)
        if not df_logins.empty:
          st.dataframe(df_logins, use_container_width=True)
        else:
          st.info("No login records found yet.")
      else:
        st.info("No logs file created yet.")

    with admin_tab2:
      st.subheader("📝 Add Questions (PDF Upload or Manual Entry)")
      sub_choice = st.radio(
          "Choose Method", ["Upload PDF Question Bank", "Type Questions Manually"]
      )

      if sub_choice == "Upload PDF Question Bank":
        uploaded_pdf = st.file_uploader("Upload PDF file", type=["pdf"])
        if uploaded_pdf is not None:
          try:
            extracted = parse_pdf_questions(uploaded_pdf)
            if extracted:
              st.session_state.questions = extracted
              st.success(
                  f"Successfully loaded {len(extracted)} questions from PDF!"
              )
            else:
              st.warning(
                  "Could not parse questions properly. Check PDF format."
              )
          except Exception as e:
            st.error(f"Error parsing PDF: {e}")
      else:
        with st.form("manual_entry_form"):
          q_text = st.text_area("Question Text")
          o1 = st.text_input("Option A")
          o2 = st.text_input("Option B")
          o3 = st.text_input("Option C")
          o4 = st.text_input("Option D")
          ans = st.selectbox(
              "Select Correct Answer option text",
              [o1, o2, o3, o4] if o1 else [""],
          )
          submitted = st.form_submit_button("Save Question")
          if submitted:
            if q_text and o1 and o2:
              opts = [x for x in [o1, o2, o3, o4] if x.strip() != ""]
              st.session_state.questions.append({
                  "question": q_text,
                  "options": opts,
                  "answer": ans,
              })
              st.success("Question added successfully!")
            else:
              st.error("Please provide at least a question and two options.")

      st.markdown("---")
      st.write("### Current Active Questions Preview:")
      for idx, q_item in enumerate(st.session_state.questions):
        st.markdown(
            f"**Q{idx+1}: {q_item['question']}** (Ans: `{q_item['answer']}`)"
        )

    with admin_tab3:
      st.subheader("⚙️ Quiz Status & Notifications")
      # Start/Stop Quiz toggle
      quiz_status = st.radio(
          "Quiz Live Status",
          [True, False],
          index=0 if st.session_state.quiz_active else 1,
          format_func=lambda x: (
              "🟢 Active (Quiz Running)" if x else "🔴 Closed (Quiz Stopped)"
          ),
      )
      st.session_state.quiz_active = quiz_status

      st.markdown("---")
      st.subheader("📢 Broadcast Notification to Participants")
      new_notice = st.text_input("Type notification message here...")
      if st.button("Publish Notification"):
        if new_notice:
          st.session_state.notifications.append(new_notice)
          st.success("Notification broadcasted successfully!")
        else:
          st.error("Message cannot be empty.")

    with admin_tab4:
      st.subheader("📊 Student Results & Leaderboard")
      if os.path.exists(RESULTS_FILE):
        res_df = pd.read_csv(RESULTS_FILE)
        if not res_df.empty:
          # Show leaderboard sorted or itemized
          st.dataframe(res_df, use_container_width=True)

          # Delete option for admin
          del_row = st.selectbox(
              "Select result record to delete",
              res_df.index,
              format_func=lambda x: (
                  f"Row {x} | User: {res_df.loc[x].get('Name', 'N/A')} | Score:"
                  f" {res_df.loc[x].get('Score', 'N/A')}"
              ),
          )
          if st.button("Delete Selected Result"):
            res_df = res_df.drop(del_row).reset_index(drop=True)
            res_df.to_csv(RESULTS_FILE, index=False)
            st.success("Result deleted!")
            st.rerun()

          if st.button("Clear All Results"):
            if os.path.exists(RESULTS_FILE):
              os.remove(RESULTS_FILE)
            st.success("All results wiped out!")
            st.rerun()
        else:
          st.info("No quiz submissions found yet.")
      else:
        st.info("No results file generated yet.")

    with admin_tab5:
      st.subheader("🔑 Admin Settings")
      new_password = st.text_input("New Admin Password", type="password")
      if st.button("Update Admin Password"):
        if new_password.strip():
          st.session_state.admin_password = new_password
          st.success("Admin password updated successfully!")
        else:
          st.error("Password cannot be empty.")

  # ==========================================
  # PARTICIPANT / STUDENT PORTAL
  # ==========================================
  else:
    user_identity = st.session_state.logged_in_user
    st.title(f"📝 Welcome, {user_identity}!")

    # Sidebar notifications view for users
    st.sidebar.write(f"Logged in as: **{user_identity}**")
    if st.sidebar.button("🚪 Logout"):
      st.session_state.logged_in_user = None
      st.rerun()

    if st.session_state.notifications:
      st.sidebar.markdown("---")
      st.sidebar.subheader("📢 Admin Notifications")
      for note in st.session_state.notifications[-3:]:
        st.sidebar.info(note)

    # Check if quiz is active
    if not st.session_state.quiz_active:
      st.warning(
          "⏳ The quiz is currently closed by the admin. Please wait for the"
          " host to start it!"
      )
    else:
      st.write("🌟 *Read the questions carefully and select your answers.* 🌟")
      st.markdown("---")

      user_answers = {}
      for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**Q{i+1}: {q['question']}**")
        # index=None ensures no option is pre-checked/auto-selected
        selected_option = st.radio(
            f"Select choice for Q{i+1}",
            q["options"],
            index=None,
            key=f"user_q_{i}",
        )
        user_answers[i] = selected_option
        st.markdown("---")

      if st.button("🚀 Submit Quiz"):
        # Check if any question is unattempted
        unanswered = any(
            user_answers.get(i) is None
            for i in range(len(st.session_state.questions))
        )
        if unanswered:
          st.warning("⚠️ Please answer all questions before submitting!")
        else:
          score = 0
          total = len(st.session_state.questions)
          for i, q in enumerate(st.session_state.questions):
            u_ans = user_answers.get(i)
            c_ans = q["answer"]
            if (
                u_ans
                and str(u_ans).strip().lower() == str(c_ans).strip().lower()
            ):
              score += 1

          st.success(
              f"🎉 Quiz Submitted Successfully! Your Score: {score} out of {total}"
          )

          # Save results
          result_entry = pd.DataFrame(
              [{"Name": user_identity, "Score": f"{score}/{total}"}]
          )
          if os.path.exists(RESULTS_FILE):
            existing_results = pd.read_csv(RESULTS_FILE)
            updated_results = pd.concat(
                [existing_results, result_entry], ignore_index=True
            )
          else:
            updated_results = result_entry
          updated_results.to_csv(RESULTS_FILE, index=False)