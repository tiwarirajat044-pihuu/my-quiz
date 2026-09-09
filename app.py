import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime
from pypdf import PdfReader

# ==========================================
# ⚙️ SYSTEM & FILE CONFIGURATION
# ==========================================
st.set_page_config(page_title="🚀 Pro Quiz Hub (Master Edition)", page_icon="🏆", layout="wide")

DB_USERS = "db_users.csv"
DB_LOGINS = "db_logins.csv"
DB_TESTS = "db_tests.json"
DB_RESULTS = "db_results.json"

# ==========================================
# 🎨 ULTRA-PREMIUM CSS & UI STYLING
# ==========================================
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stButton>button { border-radius: 8px; font-weight: bold; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border: none; padding: 10px 20px; transition: 0.3s; width: 100%;}
    .stButton>button:hover { background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%); transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
    .btn-red>button { background: linear-gradient(135deg, #ff0844 0%, #ffb199 100%); }
    .btn-green>button { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .metric-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); text-align: center; border-bottom: 4px solid #4facfe;}
    .motive-banner { background: linear-gradient(90deg, #f6d365 0%, #fda085 100%); padding: 15px; border-radius: 12px; color: #333; text-align: center; font-size: 20px; font-weight: 800; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 25px;}
    .passage-box { background: #fff; padding: 20px; border-radius: 10px; border-left: 5px solid #ff0844; box-shadow: 0 2px 10px rgba(0,0,0,0.05); font-size: 16px; line-height: 1.6;}
    .question-box { font-size: 22px; font-weight: bold; color: #2c3e50; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🛠️ DATABASE HANDLERS (JSON & CSV)
# ==========================================
def init_dbs():
    if not os.path.exists(DB_USERS): pd.DataFrame(columns=["Username", "Password", "CreatedAt", "LastLogin"]).to_csv(DB_USERS, index=False)
    if not os.path.exists(DB_LOGINS): pd.DataFrame(columns=["Username", "Timestamp"]).to_csv(DB_LOGINS, index=False)
    if not os.path.exists(DB_TESTS):
        with open(DB_TESTS, 'w') as f: json.dump({}, f)
    if not os.path.exists(DB_RESULTS):
        with open(DB_RESULTS, 'w') as f: json.dump({}, f)

init_dbs()

def load_json(filepath):
    with open(filepath, 'r') as f: return json.load(f)

def save_json(filepath, data):
    with open(filepath, 'w') as f: json.dump(data, f, indent=4)

def log_user_activity(username, pwd, is_new=False):
    df_users = pd.read_csv(DB_USERS)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if is_new:
        new_row = pd.DataFrame([{"Username": username, "Password": pwd, "CreatedAt": now_str, "LastLogin": now_str}])
        df_users = pd.concat([df_users, new_row], ignore_index=True)
    else:
        df_users.loc[df_users["Username"] == username, "LastLogin"] = now_str
    df_users.to_csv(DB_USERS, index=False)
    
    df_logs = pd.read_csv(DB_LOGINS)
    pd.concat([df_logs, pd.DataFrame([{"Username": username, "Timestamp": now_str}])], ignore_index=True).to_csv(DB_LOGINS, index=False)

# ==========================================
# 🧠 ADVANCED PDF PARSER (FIXED SEQUENTIAL NUMBERING)
# ==========================================
def extract_questions_from_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = "".join([page.extract_text() + "\n" for page in reader.pages if page.extract_text()])
    
    parsed = []
    lines = text.split("\n")
    cur_passage, cur_q, cur_opts, cur_ans = "", None, [], None
    
    for line in lines:
        line_s = line.strip()
        if not line_s: continue
        
        if line_s.lower().startswith("passage:") or line_s.lower().startswith("read the passage"):
            cur_passage = line_s
            continue
            
        # Regex to catch ANY starting number (1., Q1., 9), 10-) and STRIP IT OUT to maintain our own perfect sequence
        q_match = re.match(r"^([Qq]?\s*\d+\s*[\.\)\-])", line_s)
        if q_match:
            if cur_q and len(cur_opts) >= 2:
                parsed.append({"passage": cur_passage, "question": cur_q, "options": cur_opts, "answer": cur_ans if cur_ans else cur_opts[0]})
            # Strip the random number, save pure question text
            cur_q = line_s[q_match.end():].strip()
            cur_opts, cur_ans = [], None
        elif re.match(r"^([A-D][\.\)]|\([A-D]\))", line_s, flags=re.IGNORECASE):
            cur_opts.append(re.sub(r"^([A-D][\.\)]|\([A-D]\))\s*", "", line_s, flags=re.IGNORECASE))
        elif line_s.lower().startswith("ans") or line_s.lower().startswith("correct"):
            cur_ans = re.sub(r"^(ans|answer|correct\s*answer)[\:\-\s]*", "", line_s, flags=re.IGNORECASE).strip()
        else:
            if cur_q and not cur_opts: cur_q += " " + line_s
            elif cur_opts: cur_opts[-1] += " " + line_s
            elif not cur_q: cur_passage += "\n" + line_s

    if cur_q and len(cur_opts) >= 2:
        parsed.append({"passage": cur_passage, "question": cur_q, "options": cur_opts, "answer": cur_ans if cur_ans else cur_opts[0]})
    return parsed

# ==========================================
# 🔐 SESSION INITIALIZATION
# ==========================================
if "user" not in st.session_state: st.session_state.user = None
if "is_admin" not in st.session_state: st.session_state.is_admin = False
if "admin_creds" not in st.session_state: st.session_state.admin_creds = {"user": "admin", "pass": "admin123"}
if "active_test_view" not in st.session_state: st.session_state.active_test_view = None

# ==========================================
# 🚪 UNIFIED LOGIN / REGISTRATION
# ==========================================
if not st.session_state.user:
    st.markdown("<div class='motive-banner'>🔥 Welcome to the Ultimate Pro Quiz Portal! Prove your mettle! 🚀</div>", unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["🔐 Login", "📝 Create Account"])
    with t1:
        st.subheader("Login to Your Dashboard")
        l_user = st.text_input("Username / Email / Phone", key="l_u")
        l_pass = st.text_input("Password", type="password", key="l_p")
        if st.button("🚀 Login"):
            if l_user == st.session_state.admin_creds["user"] and l_pass == st.session_state.admin_creds["pass"]:
                st.session_state.user, st.session_state.is_admin = "Admin", True
                log_user_activity("Admin", l_pass)
                st.rerun()
            else:
                df = pd.read_csv(DB_USERS)
                match = df[(df["Username"] == l_user) & (df["Password"] == l_pass)]
                if not match.empty:
                    st.session_state.user, st.session_state.is_admin = l_user, False
                    log_user_activity(l_user, l_pass)
                    st.rerun()
                else: st.error("❌ Invalid Credentials!")
                
    with t2:
        st.subheader("Join the Elite Learners")
        r_user = st.text_input("Choose Username / Email", key="r_u")
        r_pass = st.text_input("Create Password", type="password", key="r_p")
        if st.button("✨ Register Account"):
            df = pd.read_csv(DB_USERS)
            if r_user in df["Username"].values: st.warning("⚠️ User already exists!")
            elif r_user and r_pass:
                log_user_activity(r_user, r_pass, is_new=True)
                st.session_state.user, st.session_state.is_admin = r_user, False
                st.rerun()
            else: st.error("Fields cannot be empty.")

# ==========================================
# 👑 ADMIN DASHBOARD
# ==========================================
elif st.session_state.is_admin:
    st.title("👑 Ultimate Admin Command Center")
    st.sidebar.markdown("### 👨‍💻 Admin Panel")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.user = None
        st.rerun()

    tests_db = load_json(DB_TESTS)
    results_db = load_json(DB_RESULTS)

    tab_u, tab_qb, tab_sch, tab_res, tab_set = st.tabs([
        "👥 User Logs & Records", "📚 Question Bank (PDF/Manual)", "⚙️ Test Schedule & Control", "📊 Results Declaration & Delete", "🔑 Settings"
    ])

    # --- TAB 1: User Logs & DELETE USER ---
    with tab_u:
        st.subheader("📋 Participant Master Records")
        df_users = pd.read_csv(DB_USERS)
        st.dataframe(df_users, use_container_width=True)
        
        st.markdown("### ❌ Delete a User Account")
        del_user = st.selectbox("Select User to Delete", ["Select..."] + df_users["Username"].tolist())
        if st.button("🗑️ Permanently Delete User"):
            if del_user != "Select...":
                df_users = df_users[df_users["Username"] != del_user]
                df_users.to_csv(DB_USERS, index=False)
                st.success(f"User '{del_user}' has been permanently deleted!")
                st.rerun()

        st.markdown("---")
        st.subheader("🕒 Live Login Activity")
        st.dataframe(pd.read_csv(DB_LOGINS).tail(20), use_container_width=True)

    # --- TAB 2: Question Bank (PDF/Upload) & Quick Start ---
    with tab_qb:
        st.subheader("📝 Create New Test / Question Bank")
        test_name = st.text_input("Enter Unique Test Name (Required first)")
        
        up_mode = st.radio("Input Method", ["Upload PDF Question Bank", "Manual Entry"])
        if up_mode == "Upload PDF Question Bank":
            pdf_file = st.file_uploader("Upload PDF (Answers will auto-scan & hide)", type=["pdf"])
            if pdf_file and test_name:
                extracted = extract_questions_from_pdf(pdf_file)
                if extracted:
                    st.success(f"✅ Extracted {len(extracted)} questions seamlessly in Sequence!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🚀 Save & Start Test LIVE Now"):
                            tests_db[test_name] = {
                                "status": "Live", "mode": "Unlimited", "duration": 0,
                                "questions": extracted, "declared": False
                            }
                            save_json(DB_TESTS, tests_db)
                            st.success("🔥 Test is now LIVE for all users!")
                            st.rerun()
                    with col2:
                        if st.button("⏸️ Save as Draft / Paused"):
                            tests_db[test_name] = {
                                "status": "Paused", "mode": "Unlimited", "duration": 0,
                                "questions": extracted, "declared": False
                            }
                            save_json(DB_TESTS, tests_db)
                            st.info("Test saved but paused. You can schedule it later.")
                            st.rerun()

    # --- TAB 3: Test Schedule & Control ---
    with tab_sch:
        st.subheader("⚙️ Control Panel for Existing Tests")
        if not tests_db: st.info("No tests available. Upload in Question Bank first.")
        else:
            sel_test = st.selectbox("Select Test to Configure", list(tests_db.keys()))
            tdat = tests_db[sel_test]
            
            st.markdown(f"**Current Status:** `{tdat['status']}` | **Mode:** `{tdat['mode']}`")
            
            c1, c2, c3 = st.columns(3)
            if c1.button("🟢 Make LIVE"): tdat['status'] = "Live"; save_json(DB_TESTS, tests_db); st.rerun()
            if c2.button("🔴 Pause Test"): tdat['status'] = "Paused"; save_json(DB_TESTS, tests_db); st.rerun()
            if c3.button("📅 Schedule Later"): tdat['status'] = "Scheduled"; save_json(DB_TESTS, tests_db); st.rerun()

            st.markdown("### ⏱️ Timer Configuration")
            t_mode = st.radio("Select Timer Type", ["Strict Time Limit", "Unlimited Time"], index=0 if tdat['mode']=="Strict" else 1)
            t_dur = st.number_input("Time Limit (Minutes)", value=tdat.get('duration', 30))
            if st.button("Update Timer Settings"):
                tdat['mode'] = "Strict" if "Strict" in t_mode else "Unlimited"
                tdat['duration'] = t_dur
                save_json(DB_TESTS, tests_db)
                st.success("Timer Updated!")

    # --- TAB 4: Results Declaration & DELETE RESULTS ---
    with tab_res:
        st.subheader("📊 Declare Results & Manage Participant Data")
        if not tests_db: st.info("No tests available.")
        else:
            sel_test_res = st.selectbox("Select Test for Analytics", list(tests_db.keys()), key="res_sel")
            t_data = tests_db[sel_test_res]
            
            c1, c2 = st.columns(2)
            if c1.button(f"📢 Officially Declare Results for '{sel_test_res}'"):
                t_data['declared'] = True
                save_json(DB_TESTS, tests_db)
                st.success("Results Declared Successfully! Users can now see Leaderboard.")
            if c2.button(f"❌ Cancel & Wipe ALL Results for '{sel_test_res}'", type="primary"):
                t_data['declared'] = False
                if sel_test_res in results_db: del results_db[sel_test_res]
                save_json(DB_TESTS, tests_db)
                save_json(DB_RESULTS, results_db)
                st.error("All Results wiped completely!")

            st.markdown("### 👨‍🎓 Live Participant Actions")
            if sel_test_res in results_db and results_db[sel_test_res]:
                res_list = []
                for u, udata in results_db[sel_test_res].items():
                    res_list.append({
                        "Student": u,
                        "Status": udata['status'],
                        "Score": f"{udata.get('score', 0)} / {len(t_data['questions'])}",
                        "Skipped Qs": len(udata.get('skipped', [])),
                        "Time Taken (s)": round(udata.get('time_taken_sec', 0), 1)
                    })
                st.dataframe(pd.DataFrame(res_list).sort_values(by="Score", ascending=False), use_container_width=True)

                st.markdown("### 🗑️ Delete Specific Student's Result")
                del_stud_res = st.selectbox("Select Student Result to Delete", ["Select..."] + list(results_db[sel_test_res].keys()))
                if st.button("Delete Result Record"):
                    if del_stud_res != "Select...":
                        del results_db[sel_test_res][del_stud_res]
                        save_json(DB_RESULTS, results_db)
                        st.success(f"Result for {del_stud_res} deleted successfully!")
                        st.rerun()
            else: st.info("No participant data yet.")

    # --- TAB 5: Admin Settings ---
    with tab_set:
        st.subheader("🔑 Update Admin Credentials")
        n_user = st.text_input("New Username", value=st.session_state.admin_creds['user'])
        n_pass = st.text_input("New Password", type="password")
        if st.button("Save New Credentials"):
            st.session_state.admin_creds['user'] = n_user
            if n_pass: st.session_state.admin_creds['pass'] = n_pass
            st.success("Updated Successfully!")

# ==========================================
# 🎓 PARTICIPANT / STUDENT PORTAL
# ==========================================
else:
    tests_db = load_json(DB_TESTS)
    results_db = load_json(DB_RESULTS)
    user = st.session_state.user

    if st.session_state.active_test_view:
        t_name = st.session_state.active_test_view
        t_data = tests_db[t_name]
        q_list = t_data['questions']
        
        if "progress" not in st.session_state:
            if t_name in results_db and user in results_db[t_name]:
                st.session_state.progress = results_db[t_name][user]
            else:
                st.session_state.progress = {
                    "answers": {}, "skipped": [], "status": "In Progress", 
                    "start_time": datetime.now().timestamp(), "score": 0
                }
        
        if "q_idx" not in st.session_state: st.session_state.q_idx = 0
        
        prog = st.session_state.progress
        curr_q = q_list[st.session_state.q_idx]

        st.markdown(f"<h2 style='text-align: center; color: #4facfe;'>📝 Live Test: {t_name}</h2>", unsafe_allow_html=True)
        
        head1, head2 = st.columns([3,1])
        with head1: st.info(f"**Mode:** {t_data['mode']} | Negative Marking: -0.25 | Correct: +1")
        with head2:
            elapsed = int(datetime.now().timestamp() - prog['start_time'])
            if t_data['mode'] == "Strict":
                rem = max((t_data['duration'] * 60) - elapsed, 0)
                st.error(f"⏳ **Time Left: {rem//60}m {rem%60}s**")
                if rem == 0: st.warning("TIME UP! Please Final Submit.")
            else:
                st.success(f"⏱️ **Elapsed: {elapsed//60}m {elapsed%60}s**")

        st.markdown("---")
        
        main_col, pal_col = st.columns([3, 1], gap="large")
        
        with pal_col:
            st.markdown("### 🗂️ Question Palette")
            st.markdown("🟢 Answered | 🔴 Skipped | ⚪ Pending")
            grid_cols = st.columns(4)
            for i in range(len(q_list)):
                idx_str = str(i)
                color = "⚪"
                if idx_str in prog['answers']: color = "🟢"
                elif i in prog['skipped']: color = "🔴"
                
                if grid_cols[i % 4].button(f"{color} {i+1}", key=f"grid_{i}"):
                    st.session_state.q_idx = i
                    st.rerun()

        with main_col:
            if curr_q.get("passage"):
                st.markdown("<div class='passage-box'>", unsafe_allow_html=True)
                st.markdown(f"**📖 Reading Comprehension:**\n\n{curr_q['passage']}")
                st.markdown("</div><br>", unsafe_allow_html=True)
            
            # PERFECT SEQUENTIAL NUMBERING FOR UI (Q1, Q2, Q3...)
            st.markdown(f"<div class='question-box'>Q{st.session_state.q_idx + 1}: {curr_q['question']}</div>", unsafe_allow_html=True)
            
            prev_ans = prog['answers'].get(str(st.session_state.q_idx), None)
            idx_default = curr_q['options'].index(prev_ans) if prev_ans in curr_q['options'] else None
            
            sel_opt = st.radio("Select Answer:", curr_q['options'], index=idx_default, key=f"radio_{st.session_state.q_idx}")

            st.markdown("<br><hr>", unsafe_allow_html=True)
            b1, b2, b3, b4 = st.columns(4)
            
            if b1.button("✅ Submit & Next"):
                if sel_opt: prog['answers'][str(st.session_state.q_idx)] = sel_opt
                if st.session_state.q_idx in prog['skipped']: prog['skipped'].remove(st.session_state.q_idx)
                if st.session_state.q_idx < len(q_list) - 1: st.session_state.q_idx += 1
                st.rerun()
                
            if b2.button("⏩ Skip Question"):
                if st.session_state.q_idx not in prog['skipped']: prog['skipped'].append(st.session_state.q_idx)
                if str(st.session_state.q_idx) in prog['answers']: del prog['answers'][str(st.session_state.q_idx)]
                if st.session_state.q_idx < len(q_list) - 1: st.session_state.q_idx += 1
                st.rerun()
                
            if b3.button("🚪 Leave (Save for Later)"):
                prog['status'] = "Incomplete"
                prog['time_taken_sec'] = datetime.now().timestamp() - prog['start_time']
                if t_name not in results_db: results_db[t_name] = {}
                results_db[t_name][user] = prog
                save_json(DB_RESULTS, results_db)
                st.session_state.active_test_view = None
                del st.session_state.progress
                del st.session_state.q_idx
                st.rerun()
                
            with b4:
                st.markdown("<div class='btn-red'>", unsafe_allow_html=True)
                if st.button("🏁 FINAL SUBMIT"):
                    if sel_opt: prog['answers'][str(st.session_state.q_idx)] = sel_opt
                    
                    score = 0.0
                    for i, q in enumerate(q_list):
                        ans = prog['answers'].get(str(i))
                        if ans:
                            if str(ans).strip().lower() == str(q['answer']).strip().lower(): score += 1.0
                            else: score -= 0.25
                            
                    prog['score'] = score
                    prog['status'] = "Completed"
                    prog['time_taken_sec'] = datetime.now().timestamp() - prog['start_time']
                    
                    if t_name not in results_db: results_db[t_name] = {}
                    results_db[t_name][user] = prog
                    save_json(DB_RESULTS, results_db)
                    
                    st.session_state.active_test_view = None
                    del st.session_state.progress
                    del st.session_state.q_idx
                    st.success("🎉 Test Submitted Successfully! Wait for admin to declare results.")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.title(f"🎓 Student Dashboard: {user}")
        
        col_lg, col_ref = st.columns([8,2])
        with col_lg: 
            if st.button("🚪 Logout"):
                st.session_state.user = None
                st.rerun()
        with col_ref:
            # LIVE SYNC BUTTON: One click to fetch admin updates without logout!
            if st.button("🔄 Refresh / Sync Data"):
                st.rerun()
            
        pt1, pt2, pt3 = st.tabs(["📝 Available Tests", "🏆 Leaderboard & Analytics", "⚙️ Profile Settings"])
        
        with pt1:
            st.markdown("<div class='motive-banner'>📖 'Do something today that your future self will thank you for.'</div>", unsafe_allow_html=True)
            has_tests = False
            for t_name, t_data in tests_db.items():
                if t_data['status'] in ["Live", "Scheduled"]:
                    has_tests = True
                    st.markdown(f"<div class='metric-card'><h3>{t_name}</h3>", unsafe_allow_html=True)
                    st.write(f"**Status:** {t_data['status']} | **Mode:** {t_data['mode']} | **Questions:** {len(t_data['questions'])}")
                    
                    if t_data['status'] == "Live":
                        usr_stat = "Not Started"
                        if t_name in results_db and user in results_db[t_name]:
                            usr_stat = results_db[t_name][user]['status']
                            
                        if usr_stat == "Completed":
                            st.success("✅ You have already completed this test.")
                        else:
                            btn_text = "🚀 Start Test" if usr_stat == "Not Started" else "🔄 Resume Test"
                            if st.button(btn_text, key=f"start_{t_name}"):
                                st.session_state.active_test_view = t_name
                                st.rerun()
                    else:
                        st.warning("📅 Scheduled for later. Keep checking!")
                    st.markdown("</div><br>", unsafe_allow_html=True)
            if not has_tests: st.info("No tests available right now. Enjoy your break! ☕")

        with pt2:
            st.subheader("🏆 Declared Results & Leaderboard")
            dec_found = False
            for t_name, t_data in tests_db.items():
                if t_data.get('declared', False):
                    dec_found = True
                    st.markdown(f"### 🏅 Leaderboard: {t_name}")
                    if t_name in results_db:
                        board = []
                        for u, d in results_db[t_name].items():
                            if d['status'] == "Completed":
                                board.append({"Rank": 0, "Student": u, "Score": d.get('score', 0), "Time(s)": round(d.get('time_taken_sec', 0),1)})
                        
                        if board:
                            df_b = pd.DataFrame(board).sort_values(by=["Score", "Time(s)"], ascending=[False, True]).reset_index(drop=True)
                            df_b.index += 1
                            df_b["Rank"] = df_b.index
                            st.dataframe(df_b, use_container_width=True)
                            
                            usr_row = df_b[df_b["Student"] == user]
                            if not usr_row.empty:
                                st.success(f"🎯 **Your Rank:** {usr_row.iloc[0]['Rank']} | **Your Score:** {usr_row.iloc[0]['Score']}")
                        else: st.info("No completed submissions for this test yet.")
            if not dec_found: st.warning("⏳ No results declared by admin yet. Hang tight!")

        with pt3:
            st.subheader("⚙️ Update Profile")
            n_usr = st.text_input("New Username", value=user)
            if st.button("Save Changes"):
                df = pd.read_csv(DB_USERS)
                if n_usr in df["Username"].values and n_usr != user:
                    st.error("Username already taken!")
                else:
                    df.loc[df["Username"] == user, "Username"] = n_usr
                    df.to_csv(DB_USERS, index=False)
                    st.session_state.user = n_usr
                    st.success("Username Updated!")
                    st.rerun()