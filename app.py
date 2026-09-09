from datetime import datetime, timedelta
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
    page_title="🚀 Ultimate Pro Quiz Portal", page_icon="🎯", layout="wide"
)

# Custom Styling & Motivational UI Enhancements (Colorful & Cute Theme)
st.markdown(
    """
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { border-radius: 10px; font-weight: bold; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 8px 16px; }
    .stButton>button:hover { background: linear-gradient(135deg, #764ba2 0%, #667eea 100%); color: white; }
    .metric-card { background: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); text-align: center; }
    .motivational-banner { background: linear-gradient(90deg, #ff9966 0%, #ff5e62 100%); padding: 15px; border-radius: 12px; color: white; text-align: center; font-size: 18px; font-weight: bold; margin-bottom: 20px; }
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
      "Strict Time Limit"  # 'Strict Time Limit' or 'Unlimited Time'
  )

if "time_limit_mins" not in st.session_state:
  st.session_state.time_limit_mins = 15

if "start_time" not in st.session_state:
  st.session_state.start_time = datetime.now()

if "end_time" not in st.session_state:
  st.session_state.end_time = datetime.now() + timedelta(hours=1)

if "results_declared" not in st.session_state:
  st.session_state.results_declared = False

if "admin_username" not in st.session_state:
  st.session_state.admin_username = "admin"

if "admin_password" not in st.session_state:
  st.session_state.admin_password = "admin123"

if "current_q_idx" not in st.session_state:
  st.session_state.current_q_idx = 0

if "user_answers" not in st.session_state:
  st.session_state.user_answers = {}


# Advanced PDF Parser with Answer Key Scanning & Passage Support
def parse_pdf_questions(uploaded_file):
  reader = PdfReader(uploaded_file)
  text = ""
  for page in reader.pages:
    t = page.extract_text()
    if t:
      text += t + "\n"

  parsed_questions = []
  answer_key_dict = {}

  # Check if there is an Answer Key section at the end
  if "answer key" in text.lower() or "answers:" in text.lower():
    parts = re.split(r"(answer\s*key|answers:)", text, flags=re.IGNORECASE)
    main_text = parts[0]
    key_text = "".join(parts[1:])
    # Extract answers like "1. A" or "1) B" or "Q1: C"
    key_matches = re.findall(
        r"(\d+)[\.\)]\s*([A-Da-d])", key_text, flags=re.IGNORECASE
    )
    for q_num, ans_opt in key_matches:
      answer_key_dict[int(q_num)] = ans_opt.upper()
  else:
    main_text = text

  lines = main_text.split("\n")
  current_passage = ""
  current_q = None
  current_options = []
  current_ans = None
  q_counter = 1

  for line in lines:
    line_str = line.strip()
    if not line_str:
      continue

    if line_str.lower().startswith("passage:") or line_str.lower().startswith(
        "read the passage"
    ):
      current_passage = line_str
      continue

    # Detect Question
    if re.match(r"^(\d+[\.\)]|Q\d+[\.\)])", line_str):
      if current_q and len(current_options) >= 2:
        # Determine correct answer (from background key dict if available, else inline/default)
        final_ans = current_ans
        if q_counter in answer_key_dict:
          opt_map = {"A": 0, "B": 1, "C": 2, "D": 3}
          idx = opt_map.get(answer_key_dict[q_counter], 0)
          if idx < len(current_options):
            final_ans = current_options[idx]

        parsed_questions.append({
            "passage": current_passage,
            "question": current_q,
            "options": current_options,
            "answer": (
                final_ans
                if final_ans
                else current_options[0]
                if current_options
                else ""
            ),
        })
        q_counter += 1

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
    final_ans = current_ans
    if q_counter in answer_key_dict:
      opt_map = {"A": 0, "B": 1, "C": 2, "D": 3}
      idx = opt_map.get(answer_key_dict[q_counter], 0)
      if idx < len(current_options):
        final_ans = current_options[idx]

    parsed_questions.append({
        "passage": current_passage,
        "question": current_q,
        "options": current_options,
        "answer": (
            final_ans
            if final_ans
            else current_options[0]
            if current_options
            else ""
        ),
    })

  return parsed_questions


# User Database Management
def load_users():
  if os.path.exists(USERS_FILE):
    return pd.read_csv(USERS_FILE)
  return pd.DataFrame(
      columns=["Identifier", "Password", "CreatedAt", "LastLogin"]
  )


def save_user(identifier, password):
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


def update_user_login(identifier):
  if os.path.exists(USERS_FILE):
    df = load_users()
    if identifier in df["Identifier"].values:
      df.loc[df["Identifier"] == identifier, "LastLogin"] = (
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      )
      df.to_csv(USERS_FILE, index=False)


# ==========================================
# UNIFIED AUTHENTICATION & LANDING PAGE PORTAL
# ==========================================
if "logged_in_user" not in st.session_state:
  st.session_state.logged_in_user = None
  st.session_state.is_admin = False

if st.session_state.logged_in_user is None:
  st.title("🌟 Welcome to the Ultimate Pro Quiz Hub 🚀")
  st.markdown(
      "<div class='motivational-banner'>"
      "💡 'Education is the passport to the future, for tomorrow belongs to"
      " those who prepare for it today!' 🎯"
      "</div>",
      unsafe_allow_html=True,
  )

  auth_tab1, auth_tab2 = st.tabs(["🔑 Login Portal", "📝 Create Account"])

  with auth_tab1:
    st.subheader("Login to Your Account (Admin or Participant)")
    l_id = st.text_input(
        "Enter Username, Email, or Mobile Number", key="login_id_input"
    )
    l_pwd = st.text_input("Enter Password", type="password", key="login_pwd_input")

    if st.button("🚀 Login"):
      if (
          l_id.strip() == st.session_state.admin_username
          and l_pwd == st.session_state.admin_password
      ):
        st.session_state.logged_in_user = st.session_state.admin_username
        st.session_state.is_admin = True
        update_user_login(st.session_state.admin_username)

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
        df_u = load_users()
        match = df_u[(df_u["Identifier"] == l_id) & (df_u["Password"] == l_pwd)]
        if not match.empty:
          st.session_state.logged_in_user = l_id
          st.session_state.is_admin = False
          update_user_login(l_id)

          pd.DataFrame([{
              "Identity": l_id,
              "Type": "Participant Login",
              "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          }]).to_csv(
              LOGINS_FILE,
              mode="a",
              header=not os.path.exists(LOGINS_FILE),
              index=False,
          )
          st.success(f"🎉 Welcome back, {l_id}!")
          st.rerun()
        else:
          st.error(
              "❌ Invalid credentials or user not found. Please register first."
          )

  with auth_tab2:
    st.subheader("Create a New Account")
    r_id = st.text_input(
        "Choose Username, Email, or Mobile Number", key="reg_id_input"
    )
    r_pwd = st.text_input("Create Password", type="password", key="reg_pwd_input")

    if st.button("✨ Register Now"):
      if r_id.strip() and r_pwd.strip():
        df_u = load_users()
        if not df_u.empty and r_id.strip() in df_u["Identifier"].values:
          st.warning("⚠️ This identity is already registered. Please login!")
        else:
          save_user(r_id.strip(), r_pwd.strip())
          st.session_state.logged_in_user = r_id.strip()
          st.session_state.is_admin = False

          pd.DataFrame([{
              "Identity": r_id.strip(),
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
        st.error("Please fill in both fields.")

else:
  # ==========================================
  # ADMIN DASHBOARD PORTAL
  # ==========================================
  if st.session_state.is_admin:
    st.title("🔐 Admin Control Dashboard")
    st.sidebar.markdown(f"👤 Logged in as: **Admin**")

    if st.sidebar.button("🚪 Logout"):
      st.session_state.logged_in_user = None
      st.session_state.is_admin = False
      st.rerun()

    # Admin Tabs as requested
    adm_t1, adm_t2, adm_t3, adm_t4, adm_t5 = st.tabs([
        "📋 User Records & Logs",
        "📚 Question Bank & PDF",
        "⚙️ Quiz Control & Timers",
        "📊 Results & Declaration",
        "🔑 Admin Settings",
    ])

    with adm_t1:
      st.subheader("👥 User Registration & Login Activity Logs")
      if os.path.exists(USERS_FILE):
        st.write("**Registered Users Database:**")
        st.dataframe(load_users(), use_container_width=True)
      else:
        st.info("No users registered yet.")

      if os.path.exists(LOGINS_FILE):
        st.write("**Detailed Login Timestamps:**")
        st.dataframe(pd.read_csv(LOGINS_FILE), use_container_width=True)

    with adm_t2:
      st.subheader("📚 Question Bank: Upload PDF or Add Manually")
      upload_method = st.radio(
          "Select Method", ["Upload PDF Question Bank", "Type Questions Manually"]
      )

      if upload_method == "Upload PDF Question Bank":
        pdf_file = st.file_uploader(
            "Upload Quiz PDF (Answers at the end will be auto-scanned and saved"
            " in background)",
            type=["pdf"],
        )
        if pdf_file is not None:
          try:
            parsed_qs = parse_pdf_questions(pdf_file)
            if parsed_qs:
              st.session_state.questions = parsed_qs
              st.success(
                  f"✅ Successfully scanned and loaded {len(parsed_qs)} questions"
                  " from PDF!"
              )
            else:
              st.warning(
                  "⚠️ Could not parse properly. Check PDF text formatting."
              )
          except Exception as e:
            st.error(f"Error parsing PDF: {e}")

        # Instant Start Test trigger option right after PDF upload as requested
        if st.button("🚀 Start Test Now (Live)"):
          st.session_state.quiz_active = True
          st.success("🔥 Test is now LIVE for all participants!")
      else:
        with st.form("manual_entry"):
          pass_txt = st.text_area("Passage / Paragraph (Optional)")
          q_str = st.text_area("Question Text")
          o_a = st.text_input("Option A")
          o_b = st.text_input("Option B")
          o_c = st.text_input("Option C")
          o_d = st.text_input("Option D")
          correct_o = st.selectbox(
              "Correct Answer Option Text", [o_a, o_b, o_c, o_d] if o_a else [""]
          )
          submitted_q = st.form_submit_button("Add Question")

          if submitted_q:
            if q_str and o_a and o_b:
              opts = [x for x in [o_a, o_b, o_c, o_d] if x.strip() != ""]
              st.session_state.questions.append({
                  "passage": pass_txt,
                  "question": q_str,
                  "options": opts,
                  "answer": correct_o,
              })
              st.success("✅ Question added successfully!")
            else:
              st.error("Please fill in question and options.")

      st.markdown("---")
      st.write("### 🔍 Loaded Questions Preview:")
      for idx, q_item in enumerate(st.session_state.questions):
        with st.expander(f"Q{idx+1}: {q_item['question']}"):
          if q_item.get("passage"):
            st.info(f"**Passage:** {q_item['passage']}")
          st.write(f"**Options:** {q_item['options']}")
          st.write(
              f"**Correct Answer (Background Saved):** `{q_item['answer']}`"
          )

    with adm_t3:
      st.subheader("⚙️ Quiz Control, Timers & Scheduling")

      # Live status
      q_status = st.radio(
          "Quiz Active Status",
          [True, False],
          index=0 if st.session_state.quiz_active else 1,
          format_func=lambda x: (
              "🟢 Active (Quiz Running)" if x else "🔴 Paused / Closed"
          ),
      )
      st.session_state.quiz_active = q_status

      st.markdown("---")
      st.markdown("### ⏱️ Timer Configuration")
      timer_sel = st.radio(
          "Timer Mode",
          ["Strict Time Limit", "Unlimited Time"],
          index=(
              0
              if st.session_state.quiz_mode == "Strict Time Limit"
              else 1
          ),
      )
      st.session_state.quiz_mode = timer_sel

      if timer_sel == "Strict Time Limit":
        st.session_state.time_limit_mins = st.number_input(
            "Test Duration (Minutes)",
            min_value=1,
            max_value=300,
            value=st.session_state.time_limit_mins,
        )

      st.markdown("### 📅 Automatic Test Schedule")
      col_s1, col_s2 = st.columns(2)
      with col_s1:
        start_d = st.date_input(
            "Test Start Date", st.session_state.start_time.date()
        )
        start_t = st.time_input(
            "Test Start Time", st.session_state.start_time.time()
        )
        st.session_state.start_time = datetime.combine(start_d, start_t)
      with col_s2:
        end_d = st.date_input("Test End Date", st.session_state.end_time.date())
        end_t = st.time_input("Test End Time", st.session_state.end_time.time())
        st.session_state.end_time = datetime.combine(end_d, end_t)

      st.info(
          f"📅 Scheduled: From {st.session_state.start_time} to"
          f" {st.session_state.end_time}"
      )

    with adm_t4:
      st.subheader("📊 Results, Leaderboard & Test Actions")

      col_r1, col_r2 = st.columns(2)
      with col_r1:
        if st.button("📢 Declare Results Officially"):
          st.session_state.results_declared = True
          st.success(
              "🎉 Results declared successfully! Visible to all participants."
          )
      with col_r2:
        if st.button("❌ Cancel / Reset Test Data"):
          st.session_state.results_declared = False
          if os.path.exists(RESULTS_FILE):
            os.remove(RESULTS_FILE)
          st.warning("⚠️ Test results cleared and test reset.")
          st.rerun()

      st.markdown("---")
      if os.path.exists(RESULTS_FILE):
        df_res = pd.read_csv(RESULTS_FILE)
        if not df_res.empty:
          st.dataframe(df_res, use_container_width=True)
        else:
          st.info("No student submissions yet.")
      else:
        st.info("No result records found.")

    with adm_t5:
      st.subheader("🔑 Admin Settings (Change Username & Password)")
      new_adm_user = st.text_input(
          "New Admin Username", value=st.session_state.admin_username
      )
      new_adm_pwd = st.text_input(
          "New Admin Password", type="password", value=""
      )

      if st.button("Update Credentials"):
        if new_adm_user.strip():
          st.session_state.admin_username = new_adm_user.strip()
        if new_adm_pwd.strip():
          st.session_state.admin_password = new_adm_pwd.strip()
        st.success("✅ Admin credentials updated successfully!")

  # ==========================================
  # PARTICIPANT / STUDENT PORTAL
  # ==========================================
  else:
    current_user = st.session_state.logged_in_user
    st.sidebar.markdown(f"👤 User: **{current_user}**")
    if st.sidebar.button("🚪 Logout"):
      st.session_state.logged_in_user = None
      st.rerun()

    # Participant Navigation Tabs
    p_tab1, p_tab2, p_tab3 = st.tabs(
        ["📝 Test Questions", "📊 Your Analysis & Result", "⚙️ Profile Settings"]
    )

    with p_tab1:
      st.title(f"📝 Quiz Examination Portal - {current_user}")

      # Check Schedule / Active Status
      now_time = datetime.now()
      if (
          not st.session_state.quiz_active
          or now_time < st.session_state.start_time
          or now_time > st.session_state.end_time
      ):
        st.warning(
            "⏳ **Test is currently NOT LIVE.**\n- Scheduled Start:"
            f" {st.session_state.start_time}\n- Scheduled End:"
            f" {st.session_state.end_time}\nPlease wait for the scheduled"
            " window!"
        )
      else:
        st.markdown(
            "✨ *Read questions carefully. Correct = +1 mark, Incorrect = -0.25"
            " negative marking.* ✨"
        )
        st.markdown("---")

        total_q = len(st.session_state.questions)
        q_idx = st.session_state.current_q_idx

        # Layout: Main quiz area on left, Question Palette Grid on right
        quiz_col, palette_col = st.columns([3, 1], gap="medium")

        with palette_col:
          st.markdown("### 🗂️ Question Palette")
          st.write(
              "🟢 *Attempted* | 🔴 *Skipped/Unattempted* Click to jump:"
          )

          # Grid of question buttons
          cols_grid = st.columns(4)
          for i in range(total_q):
            col_target = cols_grid[i % 4]
            is_answered = (
                i in st.session_state.user_answers
                and st.session_state.user_answers[i] is not None
            )
            btn_color = "🟢" if is_answered else "🔴"
            if col_target.button(f"{btn_color} {i+1}", key=f"pal_{i}"):
              st.session_state.current_q_idx = i
              st.rerun()

        with quiz_col:
          current_question_data = st.session_state.questions[q_idx]

          # Passage layout support (Passage on left of question or top)
          if current_question_data.get("passage"):
            st.info(f"**📖 Passage:**\n{current_question_data['passage']}")

          st.markdown(
              f"### Question {q_idx + 1} of {total_q}\n**"
              f"{current_question_data['question']}**"
          )

          # Radio button with index=None so nothing is pre-selected
          prev_ans = st.session_state.user_answers.get(q_idx, None)
          try:
            default_idx = (
                current_question_data["options"].index(prev_ans)
                if prev_ans in current_question_data["options"]
                else None
            )
          except:
            default_idx = None

          selected_opt = st.radio(
              "Select your option:",
              current_question_data["options"],
              index=default_idx,
              key=f"radio_q_{q_idx}",
          )

          # Save current answer into session state
          st.session_state.user_answers[q_idx] = selected_opt

          st.markdown("---")
          nav_c1, nav_c2, nav_c3 = st.columns(3)
          with nav_c1:
            if q_idx > 0 and st.button("⬅️ Previous"):
              st.session_state.current_q_idx -= 1
              st.rerun()
          with nav_c2:
            if q_idx < total_q - 1 and st.button("Save & Next ➡️"):
              st.session_state.current_q_idx += 1
              st.rerun()
          with nav_c3:
            if st.button("🚀 Final Submit Test"):
              # Calculate Score with Negative Marking (+1 / -0.25)
              score = 0.0
              correct_count = 0
              incorrect_count = 0
              unattempted_count = 0

              for i, q in enumerate(st.session_state.questions):
                u_ans = st.session_state.user_answers.get(i)
                if u_ans is None:
                  unattempted_count += 1
                elif (
                    str(u_ans).strip().lower()
                    == str(q["answer"]).strip().lower()
                ):
                  score += 1.0
                  correct_count += 1
                else:
                  score -= 0.25
                  incorrect_count += 1

              st.success(
                  f"🎉 Test Submitted Successfully!\n- Correct: {correct_count}"
                  f" (+{float(correct_count)*1.0})\n- Incorrect:"
                  f" {incorrect_count} (-{float(incorrect_count)*0.25})\n- Final"
                  f" Score: **{score} / {total_q}**"
              )

              # Save to results CSV
              sub_t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
              res_df_row = pd.DataFrame([{
                  "Name": current_user,
                  "Score": score,
                  "Details": (
                      f"Correct:{correct_count}, Incorrect:{incorrect_count}"
                  ),
                  "SubmittedAt": sub_t,
              }])

              if os.path.exists(RESULTS_FILE):
                df_ex = pd.read_csv(RESULTS_FILE)
                df_up = pd.concat([df_ex, res_df_row], ignore_index=True)
              else:
                df_up = res_df_row
              df_up.to_csv(RESULTS_FILE, index=False)

              st.info(
                  "⏳ Results recorded. Check 'Your Analysis & Result' tab once"
                  " admin declares results!"
              )

    with p_tab2:
      st.subheader("📊 Your Analysis, Score & Leaderboard Rank")
      if st.session_state.results_declared:
        st.balloons()
        st.success("🎉 Official Results Have Been Declared by Admin!")
        if os.path.exists(RESULTS_FILE):
          df_leader = pd.read_csv(RESULTS_FILE)
          # Sort by score descending
          if "Score" in df_leader.columns:
            df_leader = df_leader.sort_values(by="Score", ascending=False)
          st.dataframe(df_leader, use_container_width=True)

          # Find current user rank
          user_records = df_leader[df_leader["Name"] == current_user]
          if not user_records.empty:
            user_score = user_records.iloc[0]["Score"]
            st.info(
                f"🎯 **Your Score:** {user_score} | Check your standing in the"
                " leaderboard above!"
            )
        else:
          st.info("No result data available.")
      else:
        st.warning(
            "⏳ Results are not yet declared by the admin. Please check back"
            " later!"
        )

    with p_tab3:
      st.subheader("⚙️ Profile Settings (Change Username)")
      new_uname = st.text_input("New Username", value=current_user)
      if st.button("Update Username"):
        if new_uname.strip() and new_uname != current_user:
          # Update users db
          if os.path.exists(USERS_FILE):
            df_u = load_users()
            df_u.loc[df_u["Identifier"] == current_user, "Identifier"] = (
                new_uname.strip()
            )
            df_u.to_csv(USERS_FILE, index=False)
          st.session_state.logged_in_user = new_uname.strip()
          st.success("✅ Username updated successfully!")
          st.rerun()
        else:
          st.error("Please enter a valid unique username.")