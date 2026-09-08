import os
import pandas as pd
import streamlit as st
from pypdf import PdfReader

# File paths
RESULTS_FILE = "results.csv"

st.set_page_config(
    page_title="Quiz Application", page_icon="📝", layout="centered"
)

# Initialize session state for questions
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


# Improved PDF Parsing Function to fix option bleeding
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

  import re

  for line in lines:
    line = line.strip()
    if not line:
      continue

    # Detect new question pattern (e.g., "1.", "Q1.", "1)")
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


# Sidebar Navigation & Login
st.sidebar.title("Navigation & Login")
menu = st.sidebar.selectbox("Choose Mode", ["Quiz", "Admin Login"])

if menu == "Admin Login":
  st.subheader("Admin Login Panel")
  username = st.text_input("Username")
  password = st.text_input("Password", type="password")

  if st.button("Login"):
    if username == "admin" and password == "admin123":
      st.session_state["is_admin"] = True
      st.success("Logged in successfully as Admin!")
    else:
      st.error("Invalid Username or Password")

  if st.session_state.get("is_admin", False):
    st.markdown("---")
    st.subheader("Admin Dashboard")

    # PDF Upload Section
    st.markdown("### Upload Question Bank PDF")
    uploaded_pdf = st.file_uploader("Upload PDF file", type=["pdf"])
    if uploaded_pdf is not None:
      try:
        extracted_qs = parse_pdf_questions(uploaded_pdf)
        if extracted_qs:
          st.session_state.questions = extracted_qs
          st.success(
              f"Successfully loaded {len(extracted_qs)} questions from PDF!"
          )
        else:
          st.warning(
              "Could not parse questions properly. Please check the PDF format."
          )
      except Exception as e:
        st.error(f"Error parsing PDF: {e}")

    # Result Management & Deletion Feature
    st.markdown("---")
    st.subheader("Manage User Results (Delete Results)")
    if os.path.exists(RESULTS_FILE):
      df_results = pd.read_csv(RESULTS_FILE)
      if not df_results.empty:
        st.dataframe(df_results)

        # Select row to delete
        row_to_delete = st.selectbox(
            "Select Result Index to Delete",
            df_results.index,
            format_func=lambda x: (
                f"Row {x} | User: {df_results.loc[x].get('Name', 'N/A')} |"
                f" Score: {df_results.loc[x].get('Score', 'N/A')}"
            ),
        )
        if st.button("Delete Selected Result"):
          df_results = df_results.drop(row_to_delete).reset_index(drop=True)
          df_results.to_csv(RESULTS_FILE, index=False)
          st.success("Selected result deleted successfully!")
          st.rerun()
      else:
        st.info("No results found in CSV.")
    else:
      st.info("No result file exists yet.")

    if st.button("Logout Admin"):
      st.session_state["is_admin"] = False
      st.rerun()

else:
  # Quiz User Section
  st.title("Interactive Quiz Application")
  user_name = st.text_input("Enter Your Name:")

  if user_name:
    st.write(f"Welcome, **{user_name}**! Answer the following questions:")

    answers = {}
    for i, q in enumerate(st.session_state.questions):
      st.markdown(f"**Q{i+1}: {q['question']}**")
      # index=None ensures no option is auto-selected/pre-checked
      selected_opt = st.radio(
          f"Select option for Q{i+1}", q["options"], index=None, key=f"q_{i}"
      )
      answers[i] = selected_opt
      st.markdown("---")

    if st.button("Submit Quiz"):
      score = 0
      total = len(st.session_state.questions)
      for i, q in enumerate(st.session_state.questions):
        user_ans = answers.get(i)
        correct_ans = q["answer"]
        if user_ans and str(user_ans).strip().lower() == str(
            correct_ans
        ).strip().lower():
          score += 1

      st.success(f"Quiz Submitted! Your Score: {score} out of {total}")

      # Save results to CSV
      new_result = pd.DataFrame(
          [{"Name": user_name, "Score": f"{score}/{total}"}]
      )
      if os.path.exists(RESULTS_FILE):
        df_existing = pd.read_csv(RESULTS_FILE)
        df_updated = pd.concat([df_existing, new_result], ignore_index=True)
      else:
        df_updated = new_result
      df_updated.to_csv(RESULTS_FILE, index=False)
  else:
    st.info("Please enter your name above to start the quiz.")