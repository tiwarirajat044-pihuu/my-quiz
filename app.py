from datetime import datetime
import os
import pandas as pd
import re
from pypdf import PdfReader
import streamlit as st

# File Paths
USERS_FILE = "users_db.csv"
RESULTS_FILE = "results.csv"
LOGINS_FILE = "user_logins.csv"

st.set_page_config(
    page_title="🚀 Ultimate Pro Quiz Hub", page_icon="🎯", layout="wide"
)

# Custom Styling & Motivational UI Enhancements
st.markdown(
    """
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 10px; }
    .stButton>button:hover { background: linear-gradient(135deg, #764ba2 0%, #667eea 100%); color: white; }
    .metric-card { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session States
if "questions" not in st.session_state:
  st.session_state.questions = [
      {
          "passage": "",
          "question": "What is the capital of India?",
          "options": ["Mumbai", "New Delhi", "Kolkata", "Chennai"],
          "answer": "New Delhi",
      }
  ]

if "quiz_active" not in st.session_state:
  st.session_state.quiz_active = True

if "quiz_mode" not in st.session_state:
  st.session_state.quiz_mode = (
      "Strict Time Limit"  # Options: 'Strict Time Limit', 'Unlimited Time'
  )

if "time_limit_mins" not in st.session_state:
  st.session_state.time_limit_mins = 10

if "notifications" not in st.session_state:
  st.session_state.notifications = [
      "🌟 Welcome to the Ultimate Quiz Portal! Stay focused and give your best!"
  ]

if "results_declared" not in st.session_state:
  st.session_state.results_declared = False

if "admin_username" not in st.session_state:
  st.session_state.admin_username = "admin"

if "admin_password" not in st.session_state:
  st.session_state.admin_password = "admin123"


# Robust PDF Parser (Extracts Passage, Questions, Options, & Hidden Answers)
def parse_pdf_questions(uploaded_file):
  reader = PdfReader(uploaded_file)
  text = ""
  for page in reader.pages:
    t = page.extract_text()
    if t:
      text += t + "\n"

  parsed_questions = []
  lines = text.split("\n")
  current_passage = ""
  current_q = None
  current_options = []
  current_ans = None

  for line in lines:
    line_str = line.strip()
    if not line_str:
      continue

    # Detect passage/reading comprehension blocks if explicitly marked or long block
    if line_str.lower().startswith("passage:") or line_str.lower().startswith(
        "read the passage"
    ):
      current_passage = line_str
      continue

    # Detect question pattern (e.g., "1.", "Q1.", "1)")
    if re.match(r"^(\d+[\.\)]|Q\d+[\.\)])", line_str):
      if current_q and len(current_options) >= 2:
        parsed_questions.append({
            "passage": current_passage,
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
      current_q = re.sub(r"^(\d+[\.\)]|Q\d+[\.\)])\s*", "", line_str)
      current_options = []
      current_ans = None
    elif re.match(r"^([A-D][\.\)]|\([A-D]\))", line_str):
      opt_text = re.sub(r"^([A-D][\.\)]|\([A-D]\))\s*", "", line_str)
      current_options.append(opt_text)
    elif line_str.lower().startswith("ans") or line_str.lower().startswith(
        "correct"
    ):
      ans_part = re.sub(
          r"^(ans|answer|correct\s*answer)[\:\-\s]*",
          "",
          line_str,
          flags=re.IGNORECASE,
      ).strip()
      current_ans = ans_part
    else:
      if current_q and not current_options:
        current_q += " " + line_str
      elif current_options:
        current_options[-1] += " " + line_str
      elif not current_q:
        current_passage += "\n" + line_str

  if current_q and len(current_options) >= 2:
    parsed_questions.append({
        "passage": current_passage,
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


# Database Helpers for Users
def load_users():
  if os.path.exists(USERS_FILE):
    return pd.read_csv(USERS_FILE)
  return pd.DataFrame(columns=["Identifier", "Password", "CreatedAt", "LastLogin"])


def save_new_user(identifier, password):
  df = load_users()
  now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  new_row = pd.DataFrame([{
      "Identifier": identifier,
      "Password": password,
      "CreatedAt": now_str,
      "LastLogin": now_str,
  }])
  df = pd.concat([df, new_row], ignore_index=True)
  df.to_csv(USERS_FILE, index=False)


def update_last_login(identifier):
  if os.path.exists(USERS_FILE):
    df = load_users()
    if identifier in df["Identifier"].values:
      df.loc[df["Identifier"] == identifier, "LastLogin"] = (
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      )
      df.to_csv(USERS_FILE, index=False)


# ==========================================
# AUTHENTICATION & LANDING PAGE PORTAL
# ==========================================
if "logged_in_user" not in st.session_state:
  st.session_state.logged_in_user = None
  st.session_state.is_admin = False

if st.session_state.logged_in_user is None:
  st.title("🌟 Welcome to the Ultimate Quiz Hub 🚀")
  st.markdown(
      "***'Success is no accident. It is hard work, perseverance, learning, and"
      " most of all, love of what you are doing.'*** 💪"
  )
  st.markdown("---")

  col1, col2 = st.columns([1, 1], gap="large")

  with col1:
    st.subheader("🔐 Login to Portal")
    login_input = st.text_input(
        "Enter Username, Email ID, or Mobile Number", key="login_id"
    )
    login_pwd = st.text_input("Enter Password", type="password", key="login_pass")

    if st.button("🚀 Login Now"):
      # Check Admin
      if (
          login_input.strip() == st.session_state.admin_username
          and login_pwd == st.session_state.admin_password
      ):
        st.session_state.logged_in_user = st.session_state.admin_username
        st.session_state.is_admin = True
        update_last_login(st.session_state.admin_username)

        # Log entry
        pd.DataFrame([{
            "Identity": "Admin",
            "Type": "Admin Login",
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }]).to_csv(
            LOGINS_FILE,
            mode="a",
            header=not os.path.exists(LOGINS_FILE),
            index=False,
        )
        st.success("🎉 Admin Logged In Successfully!")
        st.rerun()
      else:
        users_df = load_users()
        match = users_df[
            (users_df["Identifier"] == login_input)
            & (users_df["Password"] == login_pwd)
        ]
        if not match.empty:
          st.session_state.logged_in_user = login_input
          st.session_state.is_admin = False
          update_last_login(login_input)

          # Log login timestamp
          pd.DataFrame([{
              "Identity": login_input,
              "Type": "Participant Login",
              "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          }]).to_csv(
              LOGINS_FILE,
              mode="a",
              header=not os.path.exists(LOGINS_FILE),
              index=False,
          )
          st.success(f"Welcome back, {login_input}! 🎯")
          st.rerun()
        else:
          st.error(
              "❌ Invalid credentials or account does not exist. Please check"
              " your details."
          )

  with col2:
    st.subheader("📝 Create New Account")
    reg_input = st.text_input(
        "Choose Username, Email ID, or Mobile Number", key="reg_id"
    )
    reg_pwd = st.text_input("Create Password", type="password", key="reg_pass")

    if st.button("✨ Register & Join"):
      if reg_input.strip() and reg_pwd.strip():
        df_users = load_users()
        if (
            not df_users.empty
            and reg_input.strip() in df_users["Identifier"].values
        ):
          st.warning(
              "⚠️ This identity is already registered. Please login directly!"
          )
        else:
          save_new_user(reg_input.strip(), reg_pwd.strip())
          st.session_state.logged_in_user = reg_input.strip()
          st.session_state.is_admin = False

          # Log registration & first login
          pd.DataFrame([{
              "Identity": reg_input.strip(),
              "Type": "New Registration",
              "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          }]).to_csv(
              LOGINS_FILE,
              mode="a",
              header=not os.path.exists(LOGINS_FILE),
              index=False,
          )
          st.success("🎉 Account created successfully! Welcome aboard!")
          st.rerun()
      else:
        st.error("Please fill in both fields correctly.")

else:
  # ==========================================
  # ADMIN DASHBOARD PORTAL
  # ==========================================
  if st.session_state.is_admin:
    st.title("🔐 Admin Ultimate Control Dashboard")
    st.sidebar.markdown(f"👤 Logged in as: **Admin**")

    if st.sidebar.button("🚪 Logout Admin"):
      st.session_state.logged_in_user = None
      st.session_state.is_admin = False
      st.rerun()

    # Clean sequential horizontal options / tabs for admin
    adm_tab1, adm_tab2, adm_tab3, adm_tab4, adm_tab5 = st.tabs([
        "👥 User Records & Logs",
        "📚 Question Bank Management",
        "⚙️ Quiz Control & Timers",
        "📊 Results & Leaderboard",
        "🔑 Admin Settings",
    ])

    with adm_tab1:
      st.subheader("📋 Registered Users & Login Timestamps")
      if os.path.exists(USERS_FILE):
        df_u = load_users()
        st.dataframe(df_u, use_container_width=True)
      else:
        st.info("No user records found.")

      st.markdown("### Recent Login Activity Logs")
      if os.path.exists(LOGINS_FILE):
        df_l = pd.read_csv(LOGINS_FILE)
        st.dataframe(df_l, use_container_width=True)
      else:
        st.info("No login tracking logs available yet.")

    with adm_tab2:
      st.subheader("📚 Question Bank Creation & Upload")
      q_method = st.radio(
          "Choose Question Input Method:",
          ["Upload PDF Question Bank", "Type Questions Manually"],
      )

      if q_method == "Upload PDF Question Bank":
        uploaded_pdf = st.file_uploader(
            "Upload Quiz PDF (Answers remain hidden from users automatically)",
            type=["pdf"],
        )
        if uploaded_pdf is not None:
          try:
            extracted_qs = parse_pdf_questions(uploaded_pdf)
            if extracted_qs:
              st.session_state.questions = extracted_qs
              st.success(
                  f"✅ Successfully extracted {len(extracted_qs)} questions from"
                  " PDF!"
              )
            else:
              st.warning(
                  "⚠️ Could not parse properly. Check document formatting."
              )
          except Exception as e:
            st.error(f"Error parsing PDF: {e}")
      else:
        with st.form("manual_q_form"):
          passage_text = st.text_area(
              "Optional Reading Passage / Paragraph (if applicable)"
          )
          q_txt = st.text_area("Question Text")
          opt_a = st.text_input("Option A")
          opt_b = st.text_input("Option B")
          opt_c = st.text_input("Option C")
          opt_d = st.text_input("Option D")
          correct_answer = st.selectbox(
              "Correct Answer Option Text",
              [opt_a, opt_b, opt_c, opt_d] if opt_a else [""],
          )
          add_btn = st.form_submit_button("Add Question to Bank")

          if add_btn:
            if q_txt and opt_a and opt_b:
              valid_opts = [
                  x for x in [opt_a, opt_b, opt_c, opt_d] if x.strip() != ""
              ]
              st.session_state.questions.append({
                  "passage": passage_text,
                  "question": q_txt,
                  "options": valid_opts,
                  "answer": correct_answer,
              })
              st.success("✅ Question added successfully!")
            else:
              st.error("Please provide at least the question and two options.")

      st.markdown("---")
      st.write("### 🔍 Current Loaded Questions Preview:")
      for idx, item in enumerate(st.session_state.questions):
        with st.expander(f"Q{idx+1}: {item['question']}"):
          if item.get("passage"):
            st.info(f"**Passage:** {item['passage']}")
          st.write(f"**Options:** {item['options']}")
          st.write(f"**Correct Answer (Hidden from user):** `{item['answer']}`")

    with adm_tab3:
      st.subheader("⚙️ Quiz Controls, Timers & Notifications")

      # Quiz Live status toggle
      active_toggle = st.radio(
          "Quiz Live Status",
          [True, False],
          index=0 if st.session_state.quiz_active else 1,
          format_func=lambda x: (
              "🟢 Active (Quiz Running)" if x else "🔴 Closed (Quiz Paused)"
          ),
      )
      st.session_state.quiz_active = active_toggle

      st.markdown("---")
      # Timer Mode Control
      st.markdown("### ⏱️ Select Quiz Timer Mode")
      mode_choice = st.radio(
          "Timer Mode",
          ["Strict Time Limit", "Unlimited Time"],
          index=(
              0
              if st.session_state.quiz_mode == "Strict Time Limit"
              else 1
          ),
      )
      st.session_state.quiz_mode = mode_choice

      if mode_choice == "Strict Time Limit":
        st.session_state.time_limit_mins = st.number_input(
            "Set Total Time Limit (in minutes)",
            min_value=1,
            max_value=120,
            value=st.session_state.time_limit_mins,
        )
        st.info(
            f"⏳ Strict mode active: Users have {st.session_state.time_limit_mins}"
            " minutes to complete."
        )
      else:
        st.info(
            "⏱️ Unlimited mode active: Stopwatch will track elapsed time for"
            " each user."
        )

      st.markdown("---")
      st.subheader("📢 Broadcast Notification & Notice Board")
      notice_msg = st.text_input("Enter notification message for participants")
      if st.button("Publish Broadcast Notice"):
        if notice_msg.strip():
          st.session_state.notifications.append(notice_msg.strip())
          st.success("✅ Notification published successfully!")
        else:
          st.error("Notice cannot be empty.")

    with adm_tab4:
      st.subheader("📊 Quiz Results, Leaderboard & Result Declaration")

      # Result declaration switch
      dec_status = st.checkbox(
          "📢 Declare Results Officially to All Users",
          value=st.session_state.results_declared,
      )
      st.session_state.results_declared = dec_status
      if dec_status:
        st.success("Results are now declared and visible on user dashboards!")
      else:
        st.warning(
            "Results are currently hidden from users until officially"
            " declared."
        )

      st.markdown("---")
      if os.path.exists(RESULTS_FILE):
        df_res = pd.read_csv(RESULTS_FILE)
        if not df_res.empty:
          st.dataframe(df_res, use_container_width=True)

          # Option to delete specific rows or wipe out
          row_to_del = st.selectbox(
              "Select record row to delete",
              df_res.index,
              format_func=lambda x: (
                  f"Row {x} | User: {df_res.loc[x].get('Name', 'N/A')} | Score:"
                  f" {df_res.loc[x].get('Score', 'N/A')}"
              ),
          )
          if st.button("Delete Selected Result Record"):
            df_res = df_res.drop(row_to_del).reset_index(drop=True)
            df_res.to_csv(RESULTS_FILE, index=False)
            st.success("Record deleted successfully!")
            st.rerun()

          if st.button("Clear All Results Data"):
            if os.path.exists(RESULTS_FILE):
              os.remove(RESULTS_FILE)
            st.success("All results cleared!")
            st.rerun()
        else:
          st.info("No submissions recorded yet.")
      else:
        st.info("No result file generated yet.")

    with adm_tab5:
      st.subheader("🔑 Change Admin Credentials")
      new_adm_user = st.text_input(
          "New Admin Username", value=st.session_state.admin_username
      )
      new_adm_pwd = st.text_input(
          "New Admin Password", type="password", value=""
      )

      if st.button("Update Admin Credentials"):
        if new_adm_user.strip():
          st.session_state.admin_username = new_adm_user.strip()
        if new_adm_pwd.strip():
          st.session_state.admin_password = new_adm_pwd.strip()
        st.success("✅ Admin credentials updated successfully!")

  # ==========================================
  # PARTICIPANT / STUDENT QUIZ PORTAL
  # ==========================================
  else:
    current_user = st.session_state.logged_in_user
    st.title(f"📝 Welcome to the Quiz Portal, {current_user}!")

    # Sidebar details & Notifications
    st.sidebar.markdown(f"👤 User: **{current_user}**")
    if st.sidebar.button("🚪 Logout"):
      st.session_state.logged_in_user = None
      st.rerun()

    if st.session_state.notifications:
      st.sidebar.markdown("---")
      st.sidebar.subheader("📢 Live Notifications")
      for note in st.session_state.notifications[-3:]:
        st.sidebar.info(note)

    # Check if quiz is active
    if not st.session_state.quiz_active:
      st.warning(
          "⏳ The quiz is currently paused/closed by the admin. Please wait"
          " until the host starts it!"
      )
    else:
      # Check if results declared, user can view leaderboard
      if st.session_state.results_declared:
        st.balloons()
        st.success("🎉 Official Quiz Results Have Been Declared!")
        if os.path.exists(RESULTS_FILE):
          df_leaderboard = pd.read_csv(RESULTS_FILE)
          st.subheader("🏆 Leaderboard")
          st.dataframe(df_leaderboard, use_container_width=True)
        st.markdown("---")

      st.write(
          "✨ *Read the questions carefully. Answers will be evaluated"
          " automatically upon final submission.* ✨"
      )

      # Main Layout: Left side question palette / timer info, Right side questions
      main_col, side_col = st.columns([3, 1], gap="medium")

      with side_col:
        st.markdown("### 📊 Exam Dashboard")
        st.markdown(
            f"<div class='metric-card'>"
            f"<b>Timer Mode:</b><br>{st.session_state.quiz_mode}"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.write("")
        st.markdown(
            f"<div class='metric-card'>"
            f"<b>Total Questions:</b><br>{len(st.session_state.questions)}"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.write(
            "📌 **Tip:** Make sure to answer all questions before clicking Final"
            " Submit."
        )

      with main_col:
        user_answers = {}

        # Render questions with support for passages on the left if available
        for i, q in enumerate(st.session_state.questions):
          st.markdown(f"---")
          if q.get("passage"):
            # Layout for passage-based questions: 2 columns (Passage on left, Question on right)
            p_col, q_col = st.columns([1, 1], gap="medium")
            with p_col:
              st.markdown(
                  "**📖 Reading Passage:**"
              )  # Use HTML/Markdown cleanly
              st.info(q["passage"])
            with q_col:
              st.markdown(f"**Q{i+1}: {q['question']}**")
              selected_opt = st.radio(
                  f"Select option for Q{i+1}",
                  q["options"],
                  index=None,
                  key=f"ans_{i}",
              )
              user_answers[i] = selected_opt
          else:
            # Standard question layout
            st.markdown(f"**Q{i+1}: {q['question']}**")
            selected_opt = st.radio(
                f"Select option for Q{i+1}",
                q["options"],
                index=None,
                key=f"ans_{i}",
            )
            user_answers[i] = selected_opt

        st.markdown("---")
        if st.button("🚀 Final Submit Quiz"):
          # Validate all questions attempted
          unattempted = any(
              user_answers.get(i) is None
              for i in range(len(st.session_state.questions))
          )
          if unattempted:
            st.warning(
                "⚠️ Please answer all questions before making the final"
                " submission!"
            )
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
                f"🎉 Quiz Submitted Successfully! Your Score: {score} out of"
                f" {total}"
            )

            # Save result entry
            sub_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            res_entry = pd.DataFrame([{
                "Name": current_user,
                "Score": f"{score}/{total}",
                "SubmittedAt": sub_time,
            }])

            if os.path.exists(RESULTS_FILE):
              df_ex = pd.read_csv(RESULTS_FILE)
              df_up = pd.concat([df_ex, res_entry], ignore_index=True)
            else:
              df_up = res_entry
            df_up.to_csv(RESULTS_FILE, index=False)

            st.info(
                "⏳ Your submission has been recorded. Wait for the admin to"
                " declare the official results and leaderboard!"
            )