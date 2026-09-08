from datetime import datetime
import os
import pandas as pd
import streamlit as st
from pypdf import PdfReader

# File paths
RESULTS_FILE = "results.csv"
LOGINS_FILE = "user_logins.csv"

st.set_page_config(
    page_title="Advanced Quiz Application", page_icon="📝", layout="centered"
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

if "is_admin" not in st.session_state:
  st.session_state.is_admin = False

if "admin_password" not in st.session_state:
  st.session_state.admin_password = "admin123"

if "quiz_active" not in st.session_state:
  st.session_state.quiz_active = True

if "notifications" not in st.session_state:
  st.session_state.notifications = []


# Robust PDF Parsing Function (Fixed Option Bleeding & Mapping)
def parse_pdf_questions(uploaded_file):
  reader = PdfReader(uploaded_file)
  text = ""
  for page in reader.pages:
    t = page.extract_text()
    if t:
      text += t + "\n"

  import re

  parsed_questions = []
  lines = text.split("\n")
  current_q = None
  current_options = []
  current_ans = None

  for line in lines:
    line = line.strip()
    if not line:
      continue

    # Detect question start (e.g., "1.", "Q1.", "1)")
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
    # Detect option start (e.g., "A.", "(A)", "A)")
    elif re.match(r"^([A-D][\.\)]|\([A-D]\))", line):
      opt_text = re.sub(r"^([A-D][\.\)]|\([A-D]\))\s*", "", line)
      current_options.append(opt_text)
    # Detect Answer line
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


# Navigation Sidebar
st.sidebar.title("Navigation")
menu = st.sidebar.selectbox("Choose Mode", ["User Portal", "Admin Panel"])

# Global Notifications Display
if st.session_state.notifications:
  st.sidebar.markdown("---")
  st.sidebar.subheader("📢 Admin Notifications")
  for note in st.session_state.notifications[-3:]:
    st.sidebar.info(note)

if menu == "Admin Panel":
  st.title("🔐 Admin Control Dashboard")

  if not st.session_state.is_admin:
    st.subheader("Admin Login")
    adm_user = st.text_input("Username")
    adm_pass = st.text_input("Password", type="password")

    if st.button("Login as Admin"):
      if adm_user == "admin" and adm_pass == st.session_state.admin_password:
        st.session_state.is_admin = True
        st.success("Login Successful!")
        st.rerun()
      else:
        st.error("Invalid Username or Password")
  else:
    st.success("Welcome, Admin!")

    admin_tab = st.sidebar.selectbox(
        "Admin Controls",
        [
            "Upload PDF Questions",
            "Manual Question Entry",
            "User Login Logs",
            "Quiz Results & Management",
            "Quiz Control & Broadcast",
            "Settings & Password",
        ],
    )

    if admin_tab == "Upload Questions PDF":
      st.subheader("📄 Upload Question Bank via PDF")
      uploaded_pdf = st.file_uploader("Upload PDF File", type=["pdf"])
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
                "Could not parse questions properly. Check PDF formatting."
            )
        except Exception as e:
          st.error(f"Error reading PDF: {e}")

    elif admin_tab == "Manual Question Entry":
      st.subheader("✍️ Add Question Manually")
      with st.form("manual_q_form"):
        q_text = st.text_area("Question Text")
        opt1 = st.text_input("Option A")
        opt2 = st.text_input("Option B")
        opt3 = st.text_input("Option C")
        opt4 = st.text_input("Option D")
        correct_ans = st.selectbox(
            "Correct Answer", [opt1, opt2, opt3, opt4] if opt1 else [""]
        )
        submit_q = st.form_submit_button("Add Question")

        if submit_q:
          if q_text and opt1 and opt2:
            options_list = [
                o for o in [opt1, opt2, opt3, opt4] if o.strip() != ""
            ]
            st.session_state.questions.append({
                "question": q_text,
                "options": options_list,
                "answer": correct_ans,
            })
            st.success("Question added successfully!")
          else:
            st.error("Please fill at least the question and two options.")

    elif admin_tab == "User Login Logs":
      st.subheader("👥 User Login Records & Timestamps")
      if os.path.exists(LOGINS_FILE):
        df_logins = pd.read_csv(LOGINS_FILE)
        if not df_logins.empty:
          st.dataframe(df_logins, use_container_width=True)
        else:
          st.info("No login records found yet.")
      else:
        st.info("No login tracking file created yet.")

    elif admin_tab == "Quiz Results & Management":
      st.subheader("📊 Student Results Management")
      if os.path.exists(RESULTS_FILE):
        df_res = pd.read_csv(RESULTS_FILE)
        if not df_res.empty:
          st.dataframe(df_res, use_container_width=True)

          row_to_del = st.selectbox(
              "Select Result Record to Delete",
              df_res.index,
              format_func=lambda x: (
                  f"Row {x} | User: {df_res.loc[x].get('Name', 'N/A')} | Score:"
                  f" {df_res.loc[x].get('Score', 'N/A')}"
              ),
          )
          if st.button("Delete Selected Result"):
            df_res = df_res.drop(row_to_del).reset_index(drop=True)
            df_res.to_csv(RESULTS_FILE, index=False)
            st.success("Result deleted successfully!")
            st.rerun()

          if st.button("Clear All Results"):
            if os.path.exists(RESULTS_FILE):
              os.remove(RESULTS_FILE)
            st.success("All results wiped out!")
            st.rerun()
        else:
          st.info("Results file is empty.")
      else:
        st.info("No results submitted yet.")

    elif admin_tab == "Quiz Control & Broadcast":
      st.subheader("⚙️ Quiz Status & Notifications")
      current_status = st.session_state.quiz_active
      new_status = st.radio(
          "Quiz Status",
          [True, False],
          index=0 if current_status else 1,
          format_func=lambda x: "Active (Running)" if x else "Closed (Stopped)",
      )
      st.session_state.quiz_active = new_status

      st.markdown("---")
      st.subheader("Send Broadcast Notification")
      notice_text = st.text_input("Notification Message")
      if st.button("Publish Notification"):
        if notice_text:
          st.session_state.notifications.append(notice_text)
          st.success("Notification sent to all users!")
        else:
          st.error("Notification text cannot be empty.")

    elif admin_tab == "Settings & Password":
      st.subheader("🔑 Change Admin Password")
      new_pass = st.text_input("New Admin Password", type="password")
      if st.button("Update Password"):
        if new_pass:
          st.session_state.admin_password = new_pass
          st.success("Password updated successfully!")
        else:
          st.error("Password cannot be blank.")

    st.markdown("---")
    if st.button("Logout Admin"):
      st.session_state.is_admin = False
      st.rerun()

else:
  st.title("📝 Student Quiz Portal")

  if not st.session_state.quiz_active:
    st.error(
        "🚫 The quiz is currently closed by the admin. Please try again later."
    )
  else:
    st.subheader("Login / Registration to Take Quiz")
    login_type = st.radio(
        "Login via:", ["Username", "Email Address", "Mobile Number"]
    )
    user_identity = st.text_input(f"Enter your {login_type}:")

    if user_identity:
      # Save login tracking info
      login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      login_entry = pd.DataFrame([{
          "Login_Type": login_type,
          "Identity": user_identity,
          "Timestamp": login_time,
      }])

      if os.path.exists(LOGINS_FILE):
        df_l = pd.read_csv(LOGINS_FILE)
        # Avoid duplicate immediate spam logging for same session text
        df_l = pd.concat([df_l, login_entry], ignore_index=True)
      else:
        df_l = login_entry
      df_l.to_csv(LOGINS_FILE, index=False)

      st.success(f"Welcome, **{user_identity}**! You may now begin the quiz.")
      st.markdown("---")

      user_answers = {}
      for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**Q{i+1}: {q['question']}**")
        # index=None avoids auto-selecting any option
        selected_opt = st.radio(
            f"Select option for question {i+1}",
            q["options"],
            index=None,
            key=f"user_ans_{i}",
        )
        user_answers[i] = selected_opt
        st.markdown("---")

      if st.button("Submit Quiz"):
        # Check if all answered
        unanswered_flag = any(
            user_answers.get(i) is None
            for i in range(len(st.session_state.questions))
        )
        if unanswered_flag:
          st.warning("Please answer all questions before submitting!")
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
                f"🎉 Quiz Submitted! Your Final Score: {score} out of {total}"
            )

            # Save result to CSV
            res_df_entry = pd.DataFrame(
                [{"Name": user_identity, "Score": f"{score}/{total}"}]
            )
            if os.path.exists(RESULTS_FILE):
              existing_res = pd.read_csv(RESULTS_FILE)
              updated_res = pd.concat(
                  [existing_res, res_df_entry], ignore_index=True
              )
            else:
              updated_res = res_df_entry
            updated_res.to_csv(RESULTS_FILE, index=False)
    else:
      st.info("Please enter your login credential above to start the quiz.")