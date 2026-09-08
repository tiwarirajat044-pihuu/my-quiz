import streamlit as st
import pandas as pd
import time

# --- SETUP & DATABASE MOCK ---
if 'users' not in st.session_state:
    st.session_state.users = {'admin': 'admin_pass', 'user1': 'pass1', 'user2': 'pass2'}
if 'roles' not in st.session_state:
    st.session_state.roles = {'admin': 'Admin', 'user1': 'Participant', 'user2': 'Participant'}
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'quiz_schedule' not in st.session_state:
    st.session_state.quiz_schedule = ""
if 'results_published' not in st.session_state:
    st.session_state.results_published = False
if 'scores' not in st.session_state:
    st.session_state.scores = {}

# Mock Quiz Data 
quiz_data = [
    {"q": "What is the capital of India?", "options": ["Delhi", "Mumbai", "Kolkata", "Chennai"], "answer": "Delhi"},
    {"q": "What is 5 + 7?", "options": ["10", "11", "12", "13"], "answer": "12"}
]

# --- LOGIN SYSTEM ---
def login():
    st.title("🔐 Quiz Portal Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in st.session_state.users and st.session_state.users[username] == password:
            st.session_state.current_user = username
            st.rerun()
        else:
            st.error("Invalid Credentials!")

# --- ADMIN DASHBOARD ---
def admin_dashboard():
    st.title(f"👑 Admin Dashboard - Welcome {st.session_state.current_user}")
    
    st.header("1. Schedule & Notify")
    schedule_text = st.text_input("Set a notification (e.g., 'Quiz tomorrow at 5 PM')")
    if st.button("Set Notification"):
        st.session_state.quiz_schedule = schedule_text
        st.success("Notification updated for all users!")

    st.header("2. Manage Access (Role Control)")
    new_user = st.text_input("Add New Username")
    new_pass = st.text_input("New User Password")
    role = st.selectbox("Assign Role", ["Participant", "Host"])
    if st.button("Add User"):
        st.session_state.users[new_user] = new_pass
        st.session_state.roles[new_user] = role
        st.success(f"User {new_user} added as {role}!")

    st.header("3. Upload Quiz (PDF/CSV)")
    uploaded_file = st.file_uploader("Upload Question Bank", type=['pdf', 'csv'])
    if uploaded_file:
        st.info("File uploaded successfully.")

    st.header("4. Result Control")
    if st.button("Declare Results Publicly" if not st.session_state.results_published else "Hide Results"):
        st.session_state.results_published = not st.session_state.results_published
        st.success("Result visibility changed!")

# --- QUIZ INTERFACE ---
def take_quiz():
    st.title("📝 Live Quiz")
    
    if st.session_state.quiz_schedule:
        st.info(f"📢 Notification: {st.session_state.quiz_schedule}")

    if 'q_index' not in st.session_state:
        st.session_state.q_index = 0
        st.session_state.user_answers = {}
        st.session_state.quiz_started = False

    if not st.session_state.quiz_started:
        if st.button("Start Quiz"):
            st.session_state.quiz_started = True
            st.session_state.start_time = time.time()
            st.rerun()
    else:
        time_limit_per_question = 30 
        elapsed_time = time.time() - st.session_state.start_time
        time_left = max(0, time_limit_per_question - int(elapsed_time))
        
        st.warning(f"⏳ Time Left: {time_left} seconds")

        if time_left == 0:
            st.error("Time is up for this question!")
            time.sleep(2) 
            st.session_state.q_index += 1
            st.session_state.start_time = time.time()
            st.rerun()

        if st.session_state.q_index < len(quiz_data):
            current_q = quiz_data[st.session_state.q_index]
            st.subheader(f"Q{st.session_state.q_index + 1}: {current_q['q']}")
            
            choice = st.radio("Options", current_q['options'], index=None, key=f"radio_{st.session_state.q_index}")
            
            if st.button("Next Question"):
                st.session_state.user_answers[st.session_state.q_index] = choice
                st.session_state.q_index += 1
                st.session_state.start_time = time.time() 
                st.rerun()
        else:
            st.success("Quiz Completed! Awaiting Admin to declare results.")
            score = 0
            for i, q in enumerate(quiz_data):
                if st.session_state.user_answers.get(i) == q['answer']:
                    score += 1
            st.session_state.scores[st.session_state.current_user] = score

# --- RESULTS DASHBOARD ---
def show_results():
    st.title("🏆 Leaderboard")
    if st.session_state.results_published:
        if st.session_state.scores:
            df = pd.DataFrame(list(st.session_state.scores.items()), columns=['User', 'Score'])
            df = df.sort_values(by='Score', ascending=False).reset_index(drop=True)
            df.index = df.index + 1
            st.table(df)
        else:
            st.write("No one has taken the quiz yet.")
    else:
        st.warning("The Admin has not declared the results yet.")

# --- MAIN APP ROUTING ---
if st.session_state.current_user is None:
    login()
else:
    st.sidebar.write(f"Logged in as: **{st.session_state.current_user}**")
    role = st.session_state.roles[st.session_state.current_user]
    st.sidebar.write(f"Role: **{role}**")
    
    if st.sidebar.button("Logout"):
        st.session_state.current_user = None
        st.rerun()

    menu = ["Quiz", "Results"]
    if role == 'Admin' or role == 'Host':
        menu.insert(0, "Admin Dashboard")

    choice = st.sidebar.radio("Navigate", menu)

    if choice == "Admin Dashboard":
        admin_dashboard()
    elif choice == "Quiz":
        take_quiz()
    elif choice == "Results":
        show_results()