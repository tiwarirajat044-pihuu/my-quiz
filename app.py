import os
import pandas as pd
import streamlit as st
from pypdf import PdfReader

RESULTS_FILE = "results.csv"

st.set_page_config(
    page_title="Complete Quiz Application", page_icon="📚", layout="centered"
)

# Initialize Session States
if "questions" not in st.session_state:
  st.session_state.questions = [
      {
          "question": "What is the capital of India?",
          "options": ["Mumbai", "New Delhi", "Kolkata", "Chennai"],
          "answer": "New Delhi",
      },
      {
          "question": "Which language is used for Streamlit?",
          "options": ["Python", "Java", "C++", "JavaScript"],
          "answer": "Python",
      },
  ]

if "is_admin" not in st.session_state:
  st.session_state.is_admin = False

if "admin_password" not in st.session_state:
  st.session_state.admin_password = "admin123"


# Robust PDF Parsing Function (Fixed bleeding & mapping)
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

    # Check for question start (e.g. "1.", "Q1.", "1)")
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
    # Check for option start (e.g. "A.", "(A)", "A)")
    elif re.match(r"^([A-D][\.\)]|\([A-D]\))", line):
      opt_text = re.sub(r"^([A-D][\.\)]|\([A-D]\))\s*", "", line)
      current_options.append(opt_text)
    # Check for Answer
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
menu = st.sidebar.selectbox("Select Mode", ["Take Quiz", "Admin Panel"])

if menu == "Admin Panel":
  st.title("🔐 Admin Control Panel")

  if not st.session_state.is_admin:
    st.subheader("Please Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
      if username == "admin" and password == st.session_state.admin_password:
        st.session_state.is_admin = True
        st.success("Login Successful!")
        st.rerun()
      else:
        st.error("Invalid Username or Password")
  else:
    st.success("Logged in as Admin")

    # Admin Tabs/Sections for full control
    admin_tab = st.sidebar.radio(
        "Admin Menu",
        [
            "Upload Questions (PDF)",
            "View Results",
            "Manage Questions",
            "Settings",
        ],
    )

    if admin_tab == "Upload Questions (PDF)":
      st.subheader("📄 Upload Question Bank via PDF")
      uploaded_pdf = st.file_uploader("Choose a PDF file", type=["pdf"])
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
                "Could not parse questions. Please check PDF formatting."
            )
        except Exception as e:
          st.error(f"Error reading PDF: {e}")

    elif admin_tab == "View Results":
      st.subheader("📊 User Quiz Results")
      if os.path.exists(RESULTS_FILE):
        df = pd.read_csv(RESULTS_FILE)
        if not df.empty:
          st.dataframe(df, use_container_width=True)

          # Delete options
          st.markdown("### Delete Results")
          del_option = st.radio(
              "Delete Mode", ["Delete Specific Row", "Clear All Results"]
          )

          if del_option == "Delete Specific Row":
            row_idx = st.selectbox(
                "Select Row Index to Delete",
                df.index,
                format_func=lambda x: (
                    f"Row {x} - User: {df.loc[x].get('Name', 'N/A')} | Score:"
                    f" {df.loc[x].get('Score', 'N/A')}"
                ),
            )
            if st.button("Delete Selected Result"):
              df = df.drop(row_idx).reset_index(drop=True)
              df.to_csv(RESULTS_FILE, index=False)
              st.success("Selected result deleted successfully!")
              st.rerun()
          else:
            if st.button("Clear All Results Data"):
              if os.path.exists(RESULTS_FILE):
                os.remove(RESULTS_FILE)
              st.success("All results cleared successfully!")
              st.rerun()
        else:
          st.info("No result records found.")
      else:
        st.info("Results file does not exist yet.")

    elif admin_tab == "Manage Questions":
      st.subheader("📋 Currently Loaded Questions")
      for i, q in enumerate(st.session_state.questions):
        with st.expander(f"Q{i+1}: {q['question']}"):
          st.write(f"**Options:** {q['options']}")
          st.write(f"**Correct Answer:** {q['answer']}")

    elif admin_tab == "Settings":
      st.subheader("⚙️ Admin Settings")
      new_pass = st.text_input("New Admin Password", type="password")
      if st.button("Update Password"):
        if new_pass:
          st.session_state.admin_password = new_pass
          st.success("Admin password updated successfully!")
        else:
          st.error("Password cannot be empty.")

    st.markdown("---")
    if st.button("Logout Admin"):
      st.session_state.is_admin = False
      st.rerun()

else:
  # User Quiz Section
  st.title("📝 Interactive Quiz Application")
  user_name = st.text_input("Enter Your Full Name to Start:")

  if user_name:
    st.write(
        f"Welcome, **{user_name}**! Please answer all the questions below:"
    )

    user_answers = {}
    for i, q in enumerate(st.session_state.questions):
      st.markdown(f"**Q{i+1}: {q['question']}**")
      # index=None ensures no option is auto-selected
      selected = st.radio(
          f"Choose option for Q{i+1}",
          q["options"],
          index=None,
          key=f"user_q_{i}",
      )
      user_answers[i] = selected
      st.markdown("---")

    if st.button("Submit Quiz"):
      score = 0
      total = len(st.session_state.questions)
      unanswered = False

      for i, q in enumerate(st.session_state.questions):
        if user_answers.get(i) is None:
          unanswered = True

      if unanswered:
        st.warning("Please answer all questions before submitting the quiz!")
      else:
        for i, q in enumerate(st.session_state.questions):
          u_ans = user_answers.get(i)
          c_ans = q["answer"]
          if u_ans and str(u_ans).strip().lower() == str(c_ans).strip().lower():
            score += 1

        st.success(
            f"🎉 Quiz Submitted Successfully! Your Score: {score} out of {total}"
        )

        # Save to CSV
        new_entry = pd.DataFrame(
            [{"Name": user_name, "Score": f"{score}/{total}"}]
        )
        if os.path.exists(RESULTS_FILE):
          df_existing = pd.read_csv(RESULTS_FILE)
          df_updated = pd.concat([df_existing, new_entry], ignore_index=True)
        else:
          df_updated = new_entry
        df_updated.to_csv(RESULTS_FILE, index=False)
  else:
    st.info("👆 Please enter your name above to begin the quiz.")