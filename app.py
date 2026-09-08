import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Optional import for PDF processing
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

USERS_FILE = "users.csv"
RESULTS_FILE = "results.csv"
NOTICES_FILE = "notifications.csv"
CONFIG_FILE = "quiz_config.csv"
QUESTIONS_FILE = "questions.csv"

def load_users():
    if os.path.exists(USERS_FILE):
        return pd.read_csv(USERS_FILE, dtype=str)
    else:
        default_df = pd.DataFrame([{
            "username": "admin", 
            "password": "admin123", 
            "email": "admin@gmail.com", 
            "phone": "9999999999", 
            "role": "Admin"
        }])
        default_df.to_csv(USERS_FILE, index=False)
        return default_df

def save_user(username, password, email, phone, role="Participant"):
    df = load_users()
    if username in df["username"].values or email in df["email"].values:
        return False, "This username or email is already registered!"
    new_user = pd.DataFrame([{
        "username": username, 
        "password": password, 
        "email": email, 
        "phone": phone, 
        "role": role
    }])
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_csv(USERS_FILE, index=False)
    return True, "Registered successfully!"

def load_config():
    if os.path.exists(CONFIG_FILE):
        return pd.read_csv(CONFIG_FILE).iloc[0].to_dict()
    else:
        default_config = {"mode": "Unlimited Time (Elapsed Stopwatch)", "duration": 10}
        pd.DataFrame([default_config]).to_csv(CONFIG_FILE, index=False)
        return default_config

def save_config(mode, duration):
    cfg_df = pd.DataFrame([{"mode": mode, "duration": duration}])
    cfg_df.to_csv(CONFIG_FILE, index=False)

def load_questions():
    if os.path.exists(QUESTIONS_FILE):
        return pd.read_csv(QUESTIONS_FILE)
    else:
        return pd.DataFrame(columns=["question", "opt1", "opt2", "opt3", "opt4", "answer"])

def save_question(q, o1, o2, o3, o4, ans):
    df = load_questions()
    new_q = pd.DataFrame([{
        "question": q, "opt1": o1, "opt2": o2, "opt3": o3, "opt4": o4, "answer": ans
    }])
    df = pd.concat([df, new_q], ignore_index=True)
    df.to_csv(QUESTIONS_FILE, index=False)

st.set_page_config(page_title="Professional Quiz Portal", page_icon="🎓", layout="centered")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.email = ""

st.title("🎓 Online Quiz Portal")

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
    
    with tab1:
        st.subheader("Login to your account")
        login_id = st.text_input("Username or Email", key="l_id")
        login_pass = st.text_input("Password", type="password", key="l_pass")
        
        if st.button("Login"):
            df = load_users()
            user_row = df[(df["username"] == login_id) | (df["email"] == login_id)]
            
            if not user_row.empty and user_row.iloc[0]["password"] == login_pass:
                st.session_state.logged_in = True
                st.session_state.username = user_row.iloc[0]["username"]
                st.session_state.role = user_row.iloc[0]["role"]
                st.session_state.email = user_row.iloc[0]["email"]
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Incorrect username, email, or password!")

    with tab2:
        st.subheader("Register a new account")
        new_user = st.text_input("Choose Username", key="s_user")
        new_email = st.text_input("Email Address", key="s_email")
        new_phone = st.text_input("Mobile Number", key="s_phone")
        new_pass = st.text_input("Choose Password", type="password", key="s_pass")
        
        if st.button("Register"):
            if new_user and new_email and new_phone and new_pass:
                success, msg = save_user(new_user, new_pass, new_email, new_phone, role="Participant")
                if success:
                    st.success(msg + " Now go to the 'Login' tab to sign in.")
                else:
                    st.error(msg)
            else:
                st.warning("Please fill in all details.")

else:
    st.sidebar.write(f"👤 Welcome, **{st.session_state.username}**")
    st.sidebar.write(f"Role: **{st.session_state.role}**")
    
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.rerun()

    if st.session_state.role == "Admin":
        st.header("👑 Admin Control Panel (Host)")
        
        admin_tab1, admin_tab2, admin_tab3, admin_tab4, admin_tab5, admin_tab6 = st.tabs([
            "📊 Results & Export", 
            "👥 Users", 
            "❓ Add Questions / PDF Upload",
            "📢 Notifications", 
            "⏱️ Timer Settings",
            "⚙️ Admin Settings"
        ])
        
        with admin_tab1:
            st.subheader("Student Results & Export")
            if os.path.exists(RESULTS_FILE):
                res_df = pd.read_csv(RESULTS_FILE)
                st.dataframe(res_df, use_container_width=True)
                
                csv_data = res_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Results as CSV",
                    data=csv_data,
                    file_name="quiz_results.csv",
                    mime="text/csv"
                )
            else:
                st.info("No student has submitted the test yet.")

        with admin_tab2:
            st.subheader("List of all registered users:")
            st.dataframe(load_users(), use_container_width=True)

        with admin_tab3:
            st.subheader("Add Questions: Manual Entry or PDF Upload")
            
            input_method = st.radio("Choose Question Input Method", ["Manual Entry", "Upload PDF Question Bank"])
            
            if input_method == "Manual Entry":
                q_text = st.text_input("Question Text")
                o1 = st.text_input("Option A")
                o2 = st.text_input("Option B")
                o3 = st.text_input("Option C")
                o4 = st.text_input("Option D")
                correct_ans = st.selectbox("Correct Option", [o1, o2, o3, o4] if (o1 and o2) else ["Option A", "Option B", "Option C", "Option D"])
                
                if st.button("Add Question"):
                    if q_text and o1 and o2:
                        save_question(q_text, o1, o2, o3, o4, correct_ans)
                        st.success("Question added successfully!")
                    else:
                        st.warning("Please fill question and at least two options.")
            
            else:
                st.write("Upload a PDF containing questions. (Ensure text is selectable in PDF)")
                uploaded_pdf = st.file_uploader("Upload Question PDF", type=["pdf"])
                
                if uploaded_pdf is not None and PdfReader is not None:
                    if st.button("Extract and Save Questions from PDF"):
                        try:
                            reader = PdfReader(uploaded_pdf)
                            extracted_text = ""
                            for page in reader.pages:
                                extracted_text += page.extract_text() + "\n"
                            
                            # Simple line-by-line parsing mockup or saving text chunk as questions
                            lines = [line.strip() for line in extracted_text.split("\n") if line.strip()]
                            count = 0
                            # Basic parser logic: grouping lines into questions
                            i = 0
                            while i < len(lines) - 5:
                                q = lines[i]
                                opt_a = lines[i+1]
                                opt_b = lines[i+2]
                                opt_c = lines[i+3] if i+3 < len(lines) else ""
                                opt_d = lines[i+4] if i+4 < len(lines) else ""
                                ans = opt_a # default first option as answer if not specified
                                save_question(q, opt_a, opt_b, opt_c, opt_d, ans)
                                count += 1
                                i += 5
                            
                            st.success(f"Successfully extracted and added sample questions from PDF!")
                        except Exception as e:
                            st.error(f"Error parsing PDF: {e}")
                elif PdfReader is None:
                    st.error("pypdf library is missing. Please make sure requirements include pypdf.")

            st.write("---")
            st.subheader("Existing Questions in Database:")
            q_df = load_questions()
            if not q_df.empty:
                st.dataframe(q_df, use_container_width=True)
                if st.button("Clear All Questions"):
                    if os.path.exists(QUESTIONS_FILE):
                        os.remove(QUESTIONS_FILE)
                        st.success("Question bank cleared!")
                        st.rerun()
            else:
                st.write("No questions added yet.")

        with admin_tab4:
            st.subheader("Send notification / announcement to all students")
            notice_text = st.text_area("Write notice here:")
            if st.button("📢 Broadcast Notice"):
                if notice_text:
                    new_notice = pd.DataFrame([{
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": notice_text
                    }])
                    if os.path.exists(NOTICES_FILE):
                        n_df = pd.read_csv(NOTICES_FILE)
                        new_notice = pd.concat([n_df, new_notice], ignore_index=True)
                    new_notice.to_csv(NOTICES_FILE, index=False)
                    st.success("Notice broadcasted successfully!")
                else:
                    st.warning("Please do not send an empty notice.")

        with admin_tab5:
            st.subheader("Configure Quiz Timer Mode")
            current_cfg = load_config()
            
            timer_mode = st.selectbox(
                "Select Quiz Timer Type", 
                ["Unlimited Time (Elapsed Stopwatch)", "Timed Quiz (With Strict Limit)"],
                index=0 if "Unlimited" in current_cfg["mode"] else 1
            )
            
            time_limit = st.number_input(
                "Set Time Limit in Minutes", 
                min_value=1, 
                max_value=180, 
                value=int(current_cfg["duration"])
            )
            
            if st.button("Save Timer Configuration"):
                save_config(timer_mode, time_limit)
                st.success("Quiz timer settings updated successfully!")

        with admin_tab6:
            st.subheader("Change admin credentials")
            new_adm_user = st.text_input("New Admin Username", value=st.session_state.username)
            new_adm_pass = st.text_input("New Admin Password", type="password")
            
            if st.button("Update Credentials"):
                df = load_users()
                df.loc[df["username"] == st.session_state.username, "username"] = new_adm_user
                if new_adm_pass:
                    df.loc[df["username"] == new_adm_user, "password"] = new_adm_pass
                df.to_csv(USERS_FILE, index=False)
                st.session_state.username = new_adm_user
                st.success("Admin details updated successfully! Please login again.")

    else:
        st.header("🎯 Student Quiz & Dashboard")
        
        config = load_config()
        
        part_tab1, part_tab2, part_tab3 = st.tabs([
            "🔔 Notifications", 
            "✍️ Take Quiz", 
            "🏆 My Results & Leaderboard"
        ])
        
        with part_tab1:
            st.subheader("Important Announcements:")
            if os.path.exists(NOTICES_FILE):
                n_df = pd.read_csv(NOTICES_FILE)
                for index, row in n_df.iterrows():
                    st.info(f"🕒 **{row['time']}**\n\n{row['message']}")
            else:
                st.write("No new notifications right now.")

        with part_tab2:
            st.subheader("Quiz Test Panel")
            st.info(f"📌 **Quiz Mode:** {config['mode']}")
            if "Timed" in config["mode"]:
                st.warning(f"⏳ **Time Limit:** {config['duration']} Minutes")
            else:
                st.write("⏱️ **Timer Type:** Unlimited time with elapsed time tracking.")

            q_df = load_questions()
            if q_df.empty:
                st.info("No questions have been uploaded by the admin yet.")
            else:
                user_answers = {}
                for idx, row in q_df.iterrows():
                    st.write(f"**Q{idx+1}: {row['question']}**")
                    opts = [row['opt1'], row['opt2']]
                    if pd.notna(row['opt3']) and row['opt3'] != "":
                        opts.append(row['opt3'])
                    if pd.notna(row['opt4']) and row['opt4'] != "":
                        opts.append(row['opt4'])
                    
                    user_answers[idx] = st.radio(f"Select answer for Q{idx+1}", opts, key=f"q_{idx}")
                    st.write("---")
                
                if st.button("📤 Submit Quiz"):
                    score = 0
                    total_q = len(q_df)
                    for idx, row in q_df.iterrows():
                        if user_answers.get(idx) == row['answer']:
                            score += 1
                    
                    result_data = pd.DataFrame([{
                        "username": st.session_state.username,
                        "email": st.session_state.email,
                        "score": f"{score}/{total_q}",
                        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    
                    if os.path.exists(RESULTS_FILE):
                        existing = pd.read_csv(RESULTS_FILE)
                        existing = existing[existing["username"] != st.session_state.username]
                        result_data = pd.concat([existing, result_data], ignore_index=True)
                    
                    result_data.to_csv(RESULTS_FILE, index=False)
                    st.success(f"Quiz submitted successfully! Your Score: {score}/{total_q}")

        with part_tab3:
            st.subheader("Your Submission Status:")
            if os.path.exists(RESULTS_FILE):
                res_df = pd.read_csv(RESULTS_FILE)
                my_res = res_df[res_df["username"] == st.session_state.username]
                if not my_res.empty:
                    st.dataframe(my_res, use_container_width=True)
                else:
                    st.write("You haven't submitted any test yet.")
                
                st.write("---")
                st.subheader("🏆 Global Leaderboard")
                st.dataframe(res_df.sort_values(by="score", ascending=False), use_container_width=True)
            else:
                st.write("No data available.")