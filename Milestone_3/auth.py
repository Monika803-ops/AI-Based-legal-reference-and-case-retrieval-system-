
import os
import sqlite3
import streamlit as st
from PIL import Image
import io
import base64
from datetime import datetime
import json

# Import your main app


# ---------------- DATABASE SETUP ----------------
import sqlite3
import base64
import streamlit as st
import bcrypt

DB_NAME = "users.db"

def init_db():
    """Initialize SQLite database with users table"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password BLOB NOT NULL,
            profile_pic BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# --- Add this BELOW init_db() ---


  # Make sure your DB is consistent across all modules

# ------------------- Chat Table -------------------
def init_chat_table():
    """Initialize chat_history table storing messages as JSON per session"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message TEXT NOT NULL,            -- JSON string: {"type": "human/ai", "data": {"content": "..."}}
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_chat_message(session_id, role, content):
    """Save chat message as JSON with session ID like 'user_session_1'"""
    if not session_id:
        # Fallback if somehow session_id is missing
        session_id = generate_session_id()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    msg_json = json.dumps({
        "type": role,  # 'human' or 'ai'
        "data": {"content": content}
    })

    cursor.execute("""
        INSERT INTO chat_history (session_id, message)
        VALUES (?, ?)
    """, (session_id, msg_json))
    conn.commit()
    conn.close()


def get_chat_history(session_id):
    """Retrieve chat history for a session as list of dicts"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT message FROM chat_history
        WHERE session_id = ?
        ORDER BY timestamp ASC
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        try:
            msg_dict = json.loads(r[0])
            history.append(msg_dict)
        except json.JSONDecodeError:
            continue
    return history


def generate_session_id():
    """Generate a sequential session ID like user_session_1, user_session_2, etc."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Count how many unique sessions exist
    cursor.execute("SELECT COUNT(DISTINCT session_id) FROM chat_history")
    count = cursor.fetchone()[0] + 1  # +1 for the new session
    
    conn.close()
    return f"user_session_{count}"


# ------------------- User Table -------------------
def create_user(first_name, last_name, email, password, profile_pic=None):
    """Create new user in database (with hashed password)"""
    try:
        # Hash password before saving
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password BLOB NOT NULL,
                profile_pic TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO users (first_name, last_name, email, password, profile_pic)
            VALUES (?, ?, ?, ?, ?)
        """, (first_name, last_name, email, hashed_pw, profile_pic))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def verify_user(email, password):
    """Verify user credentials (with hashed password check)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and bcrypt.checkpw(password.encode('utf-8'), user[4]):  # user[4] = password column
        return user
    return None

def add_background(image_file):
    """Add background image to Streamlit app"""
    with open(image_file, "rb") as img:
        encoded = base64.b64encode(img.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{encoded}");
            background-size: cover;
            background-position: center;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def get_user_by_email(email):
    """Get user details by email"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user(email, first_name, last_name, new_email, new_password=None, profile_pic=None):
    """Update user details (hash new password if provided)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Hash new password if provided
    hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()) if new_password else None

    if new_password and profile_pic is not None:
        cursor.execute("""
            UPDATE users SET first_name=?, last_name=?, email=?, password=?, profile_pic=?
            WHERE email=?
        """, (first_name, last_name, new_email, hashed_pw, profile_pic, email))
    elif new_password:
        cursor.execute("""
            UPDATE users SET first_name=?, last_name=?, email=?, password=?
            WHERE email=?
        """, (first_name, last_name, new_email, hashed_pw, email))
    elif profile_pic is not None:
        cursor.execute("""
            UPDATE users SET first_name=?, last_name=?, email=?, profile_pic=?
            WHERE email=?
        """, (first_name, last_name, new_email, profile_pic, email))
    else:
        cursor.execute("""
            UPDATE users SET first_name=?, last_name=?, email=?
            WHERE email=?
        """, (first_name, last_name, new_email, email))
    
    conn.commit()
    conn.close()

# ---------------- STYLING ----------------
def apply_dark_theme():
    """Apply dark theme"""
    st.markdown("""
        <style>
        /* Main background */
        .stApp {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        }
        
        /* Remove default padding */
        .block-container {
            padding-top: 3rem;
            padding-bottom: 2rem;
        }
        
        /* Labels */
        .stTextInput label, .stFileUploader label {
            color: #c0c0c0 !important;
            font-weight: 500;
            font-size: 0.9rem;
        }
        
        /* Input fields */
        .stTextInput input {
            background-color: rgba(40, 40, 60, 0.6) !important;
            color: #e0e0e0 !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 8px !important;
        }
        
        .stTextInput input:focus {
            border-color: #667eea !important;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.3) !important;
        }
        
        /* Buttons */
        .stButton button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.6rem 1.5rem;
            font-weight: 600;
            width: 100%;
            transition: all 0.3s ease;
        }
        
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e1e2e 0%, #2a2a3e 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        section[data-testid="stSidebar"] .stMarkdown {
            color: #e0e0e0;
        }
        
        /* Profile container */
        .profile-container {
            text-align: center;
            padding: 1.4rem 0;
        }
        
        .profile-img {
            border-radius: 50%;
            width: 90px;
            height: 90px;
            align=center;
            object-fit: cover;
            border: 3px solid #667eea;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        
        .welcome-text {
            color: #e0e0e0;
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: 0.8rem;
        }
        
        /* File uploader */
        .stFileUploader {
            background-color: rgba(40, 40, 60, 0.4);
            border: 1px dashed rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            padding: 1rem;
        }
        
        /* Chat styling */
        .stChatMessage {
            background-color: rgba(30, 30, 46, 0.6) !important;
            border-radius: 12px !important;
            color: #e0e0e0 !important;
        }
        
        .stChatInput {
            max-width: 70%;
            margin: 0 auto;
        }
        
        .stChatInput input {
            background-color: rgba(30, 30, 46, 0.6) !important;
            color: #e0e0e0 !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
        }
        
        /* Text colors */
        p, span, div, label {
            color: #d0d0d0;
        }
        
        h1, h2, h3 {
            color: #e0e0e0 !important;
        }
        
        /* Success/Error messages */
        .stSuccess {
            background-color: rgba(46, 125, 50, 0.2) !important;
            color: #81c784 !important;
        }
        
        .stError {
            background-color: rgba(198, 40, 40, 0.2) !important;
            color: #ef5350 !important;
        }
        
        .stWarning {
            background-color: rgba(237, 108, 2, 0.2) !important;
            color: #ffb74d !important;
        }
        
        /* Divider */
        hr {
            border-color: rgba(255, 255, 255, 0.15);
            margin: 1.5rem 0;
        }
        
        </style>
    """, unsafe_allow_html=True)

# ---------------- PAGES ----------------
import streamlit as st

def login_page():
    """Login page UI with per-user session IDs like user1, user2, etc."""
    add_background("assets/bg.jpg")
    
    # ---------------- Layout ----------------
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        # Outer card
        st.markdown("""
<div style='text-align: center; width: 100%;'>
    <div style='
        display: inline-block;
        background: rgba(50, 50, 80, 0.95);
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 12px;
        padding: 1rem 2rem;
        text-align: center;
        margin-bottom: 2rem;
    '>
        <h1 style='color: #e0e0e0; margin: 0; font-size: 1.6rem;'>⚖️ LegalBot</h1>
        <p style='color: #9090a0; margin: 0; font-size: 0.85rem;'>AI Legal Reference and Case Retrieval System</p>
    </div>
</div>
""", unsafe_allow_html=True)

        # Show success message if coming from signup
        if "signup_success" in st.session_state and st.session_state.signup_success:
            st.success("✅ Account created successfully! Please login.")
            st.session_state.signup_success = False
        
        # ---------------- Login Form ----------------
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email", placeholder="your.email@example.com")
            password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
            
            col_btn1, col_btn2 = st.columns(2)
            
            # ---- Login Button ----
            with col_btn1:
                login_btn = st.form_submit_button("Login", use_container_width=True)
                if login_btn:
                    if email and password:
                        user = verify_user(email, password)
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.user_email = email
                            st.session_state.user_data = user
                            st.session_state.page = "chat"
                            
                            # ---- Use user ID as session ID (user1, user2, ...) ----
                            if "session_id" not in st.session_state:
                                st.session_state.session_id = f"user{user[0]}"  # user[0] = ID from DB
                            
                            # ---- LOAD CHAT HISTORY FROM DATABASE ----
                            st.session_state.chat_history = get_chat_history(st.session_state.session_id)
                            st.rerun()
                        else:
                            st.error("❌ Username/password is incorrect")
                    else:
                        st.warning("⚠️ Please fill all fields")
            
            # ---- Create Account Button ----
            with col_btn2:
                create_btn = st.form_submit_button("Create Account", use_container_width=True)
                if create_btn:
                    st.session_state.page = "signup"
                    st.rerun()
        
        # Close the outer card div
        st.markdown("</div>", unsafe_allow_html=True)

def signup_page():
    """Signup page UI"""
    add_background("assets/bg.jpg")
    
    # ---------------- Gradient Button CSS ----------------
    st.markdown("""
    <style>
    /* Gradient style for form buttons */
    .css-1emrehy.edgvbvh3, .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
    }

    .css-1emrehy.edgvbvh3:hover, .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        # ---------------- Title Box ----------------
        st.markdown("""
        <div style='text-align: center; width: 100%;'>
            <div style='
                display: inline-block;
                background: rgba(50, 50, 80, 0.95);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 12px;
                padding: 1rem 1.5rem;
                text-align: center;
                margin-bottom: 1.5rem;  /* gap below title */
                max-width: 400px;        /* keep same width */
            '>
                <h1 style='color: #e0e0e0; margin: 0; font-size: 1.6rem;'>⚖️ Create Account</h1>
        <p style='color: #9090a0; margin: 0; font-size: 0.85rem;'>Join LegalBot Today</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # ---------------- Signup Form ----------------
        with st.form("signup_form"):
            first_name = st.text_input("First Name", placeholder="John", key="signup_fname")
            last_name = st.text_input("Last Name", placeholder="Doe", key="signup_lname")
            email = st.text_input("Email", placeholder="your.email@example.com", key="signup_email")
            password = st.text_input("Password", type="password", placeholder="Create a strong password", key="signup_pass")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password", key="signup_confirm")
            profile_pic = st.file_uploader("Profile Picture (Optional)", type=["jpg", "jpeg", "png"], key="signup_pic")
            
            # ---------------- Buttons ----------------
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                create_btn = st.form_submit_button("Create Account", use_container_width=True, key="btn_create")
                if create_btn:
                    if first_name and last_name and email and password and confirm_password:
                        if password != confirm_password:
                            st.error("❌ Passwords don't match")
                        else:
                            pic_data = None
                            if profile_pic:
                                pic_data = profile_pic.read()
                            
                            if create_user(first_name, last_name, email, password, pic_data):
                                st.session_state.page = "login"
                                st.session_state.signup_success = True
                                st.rerun()
                            else:
                                st.error("❌ Email already exists")
                    else:
                        st.warning("⚠️ Please fill all required fields")
            
            with col_btn2:
                back_btn = st.form_submit_button("Back to Login", use_container_width=True, key="btn_back_login")
                if back_btn:
                    st.session_state.page = "login"
                    st.rerun()


def show_sidebar():
    """Display sidebar with profile picture"""
    add_background("assets/bgc.jpg")
    
    
    with st.sidebar:
        user = st.session_state.user_data
        
        st.markdown('<div style="text-align: center; padding: 1.5rem 0;">', unsafe_allow_html=True)
        
        # Display profile picture
        if user[5]:  # profile_pic exists
            try:
                img = Image.open(io.BytesIO(user[5]))
                size = (90, 90)
                img = img.resize(size, Image.Resampling.LANCZOS)
                st.image(img, use_container_width=False)
            except:
                st.markdown('<div style="font-size: 60px;">👤</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size: 60px;">👤</div>', unsafe_allow_html=True)
        
        st.markdown(f'<p style="color: #e0e0e0; font-size: 1.1rem; font-weight: 600; margin-top: 0.8rem;">Welcome, {user[1]}!</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("💬 New Chat", use_container_width=True, key="btn_new_chat"):
            st.session_state.page = "chat"
            st.session_state.chat_history = []
            st.rerun()
        
        if st.button("👤 Profile", use_container_width=True, key="btn_profile"):
            st.session_state.page = "profile"
            st.rerun()
        
        if st.button("ℹ️ About", use_container_width=True, key="btn_about"):
            st.session_state.page = "about"
            st.rerun()
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True, key="btn_logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

def chat_page():
    """Main chat interface - centered with input at bottom"""
    from auth import apply_dark_theme, show_sidebar
    apply_dark_theme()
    show_sidebar()
    
    col1, col2, col3 = st.columns([0.2, 2.6, 0.2])
    
    # Normalize old chat messages to avoid KeyError
    normalized_history = []
    for msg in st.session_state.get("chat_history", []):
        if "role" in msg and "content" in msg:
            normalized_history.append(msg)
        elif "type" in msg and "data" in msg and "content" in msg["data"]:
            normalized_history.append({
                "role": "human" if msg["type"] == "human" else "ai",
                "content": msg["data"]["content"]
            })
    st.session_state.chat_history = normalized_history
    
    with col2:
        st.markdown(
            "<h1 style='text-align: center; font-size: 1.8rem;'>⚖️ LegalBot - AI Legal Reference and Case Retrieval System</h1>", 
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)

        # Display previous chat messages
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    
    # Chat input at bottom
    query = st.chat_input("Type your legal question here...")

    if query:
        # ---------------- User Message ----------------
        with col2:
            st.chat_message("user").markdown(query)
        st.session_state.chat_history.append({"role": "human", "content": query})
        save_chat_message(st.session_state.session_id, "human", query)

        # ---------------- Assistant Thinking ----------------
        with col2:
            assistant_msg = st.chat_message("assistant")
            placeholder = assistant_msg.container()
            placeholder.markdown("💭 Typing...")  # keep thinking visible while bot generates

        try:
            # ---------------- Bot Response ----------------
            history_for_ai = st.session_state.chat_history
            response = st.session_state.rag_chain.invoke({
                "input": query,
                "chat_history": history_for_ai
            })

            if isinstance(response, dict):
                answer_text = response.get("answer") or response.get("output_text") or str(response)
            else:
                answer_text = str(response)

            # ---------------- Replace Thinking with Actual Response ----------------
            placeholder.markdown(answer_text)  # overwrite thinking with actual response

            # Save assistant response
            st.session_state.chat_history.append({"role": "ai", "content": answer_text})
            save_chat_message(st.session_state.session_id, "ai", answer_text)

            st.rerun()

        except Exception as e:
            placeholder.markdown(f"❌ Error: {e}")

def profile_page():
    """Profile view page - centered"""
    apply_dark_theme()
    show_sidebar()
    
    user = st.session_state.user_data
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("""
            <div style="
    background: rgba(30, 30, 50, 0.9);      /* subtle dark card */
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 1rem 1.5rem;                   
    margin: 1.5rem auto;                    
    max-width: 500px;                       
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    text-align: center;                     /* ensure text and image align center */
">
    <h1 style="
        text-align: center;
        color: #e0e0e0;
        font-size: 1.3rem;                   
        margin-bottom: 0.5rem;               
        font-weight: 600;
    ">
        👤 My Profile
    </h1>
</div>

        """, unsafe_allow_html=True)
        
        # Profile picture (centered)
        if user[5]:
            try:
                img = Image.open(io.BytesIO(user[5]))
                img = img.resize((150, 150), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                img_base64 = base64.b64encode(buf.getvalue()).decode()
                
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: center; align-items: center; margin: 10px 0;">
                        <img src="data:image/png;base64,{img_base64}" 
                             style="width:150px; height:150px; border-radius: 50%; object-fit: cover;"/>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            except:
                st.markdown("<p style='font-size: 80px; text-align: center;'>👤</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='font-size: 80px; text-align: center;'>👤</p>", unsafe_allow_html=True)
        
        # Keep all text and button layouts the same
        st.markdown(f"<p style='color: #c0c0c0; font-size: 1.1rem; text-align: center;'><strong>Name:</strong> {user[1]} {user[2]}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #c0c0c0; font-size: 1.1rem; text-align: center;'><strong>Email:</strong> {user[3]}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #c0c0c0; font-size: 1.1rem; text-align: center;'><strong>Member since:</strong> {user[6][:10]}</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("✏️ Edit Profile", use_container_width=True, key="btn_edit_prof"):
                st.session_state.page = "edit_profile"
                st.rerun()
        with col_btn2:
            if st.button("💬 Back to Chat", use_container_width=True, key="btn_back_chat1"):
                st.session_state.page = "chat"
                st.rerun()

def edit_profile_page():
    """Edit profile page - centered with all editable fields"""
    apply_dark_theme()
    show_sidebar()
    
    user = st.session_state.user_data
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("""
            <div style="
    background: rgba(30, 30, 50, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 1rem 1.5rem;
    margin: 1.5rem auto;
    max-width: 500px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
">
    <h1 style="
        text-align: center;
        color: #e0e0e0;
        font-size: 1.3rem;
        margin-bottom: 0.5rem;
        font-weight: 600;
    ">
        ✏️ Edit Profile
    </h1>
</div>
        """, unsafe_allow_html=True)
        
        # Current profile picture preview
        st.markdown("<p style='text-align: center; color: #9090a0; font-size: 0.9rem;'>Current Profile Picture</p>", unsafe_allow_html=True)
        if user[5]:
            try:
                img = Image.open(io.BytesIO(user[5]))
                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                col_a, col_b, col_c = st.columns([1.2, 1, 1.2])
                with col_b:
                    st.image(img, use_container_width=False)
            except:
                st.markdown("<p style='font-size: 60px; text-align: center;'>👤</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='font-size: 60px; text-align: center;'>👤</p>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Editable fields
        first_name = st.text_input("First Name", value=user[1], key="edit_fname")
        last_name = st.text_input("Last Name", value=user[2], key="edit_lname")
        email = st.text_input("Email", value=user[3], key="edit_email")
        
        st.markdown("<p style='color: #9090a0; font-size: 0.85rem; margin-top: 1rem;'>Change Password (leave blank to keep current)</p>", unsafe_allow_html=True)
        current_password = st.text_input("Current Password", type="password", placeholder="Enter current password", key="edit_currpass")
        new_password = st.text_input("New Password", type="password", placeholder="Enter new password", key="edit_newpass")
        confirm_password = st.text_input("Confirm New Password", type="password", placeholder="Confirm new password", key="edit_confpass")
        
        profile_pic = st.file_uploader("Update Profile Picture", type=["jpg", "jpeg", "png"], key="edit_pic")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 Save Changes", use_container_width=True, key="btn_save_prof"):
                # Validate current password if changing password
                if new_password:
                    if not current_password:
                        st.error("❌ Please enter current password")
                    # ✅ Use bcrypt to check hashed password
                    elif not bcrypt.checkpw(current_password.encode('utf-8'), user[4]):
                        st.error("❌ Current password is incorrect")
                    elif new_password != confirm_password:
                        st.error("❌ New passwords don't match")
                    else:
                        # Update with new password
                        pic_data = profile_pic.read() if profile_pic else user[5]
                        update_user(user[3], first_name, last_name, email, new_password, pic_data)
                        
                        # Refresh user data
                        updated_user = get_user_by_email(email)
                        st.session_state.user_data = updated_user
                        st.session_state.user_email = email
                        st.success("✅ Profile updated successfully!")
                        st.rerun()
                else:
                    # Update without password change
                    pic_data = profile_pic.read() if profile_pic else user[5]
                    update_user(user[3], first_name, last_name, email, user[4], pic_data)
                    
                    # Refresh user data
                    updated_user = get_user_by_email(email)
                    st.session_state.user_data = updated_user
                    st.session_state.user_email = email
                    st.success("✅ Profile updated successfully!")
                    st.rerun()
        
        with col_btn2:
            if st.button("💬 Back to Chat", use_container_width=True, key="btn_back_chat2"):
                st.session_state.page = "chat"
                st.rerun()

def about_page():
    """About page - centered"""
    apply_dark_theme()
    show_sidebar()
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("""
          <div style="
    background: rgba(30, 30, 50, 0.9);           /* subtle dark card */
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 1rem 1.5rem;                        /* compact padding */
    margin: 1.5rem auto;                         /* center card */
    max-width: 500px;                             /* moderate width */
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);      /* soft shadow */
">
    <h1 style="
        text-align: center;
        color: #e0e0e0;
        font-size: 1.3rem;                        /* smaller, readable */
        margin-bottom: 0.5rem;                    /* reduce space below title */
        font-weight: 600;
    ">
        ℹ️ About LegalBot
    </h1>
</div>

        """, unsafe_allow_html=True)
        
        st.markdown("""
        <p style='color: #c0c0c0; line-height: 1.8;'>
    <strong style='color: #e0e0e0;'>LegalBot</strong> is an AI-powered legal reference and case retrieval system designed to assist with legal research and queries.
</p>

<h3 style='color: #e0e0e0; margin-top: 1.5rem;'>Technology:</h3>
<ul style='color: #c0c0c0; line-height: 1.8;'>
    <li>Built with LangChain & OpenAI</li>
    <li>Vector database powered by Pinecone</li>
    <li>Streamlit UI framework</li>
</ul>

<h3 style='color: #e0e0e0; margin-top: 1.5rem;'>Legal Disclaimer:</h3>
<p style='color: #c0c0c0; line-height: 1.8;'>
    ⚖️ LegalBot is for informational purposes only and does not provide legal advice. 
    For matters affecting your legal rights, please consult a qualified attorney.
</p>

<hr style='border-color: rgba(255, 255, 255, 0.15); margin: 1.5rem 0;'>

<p style='color: #9090a0; font-style: italic; text-align: center;'>
    "Justice delayed is justice denied." - William E. Gladstone
</p>

        """, unsafe_allow_html=True)
        
        if st.button("💬 Back to Chat", use_container_width=True, key="btn_back_chat3"):
            st.session_state.page = "chat"
            st.rerun()

# ---------------- MAIN ----------------
def main():
    st.set_page_config(page_title="LegalBot", page_icon="⚖️", layout="wide")
    
    # Initialize database
    init_db()
    
    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Route to appropriate page
    if not st.session_state.logged_in:
        if st.session_state.page == "signup":
            signup_page()
        else:
            login_page()
    else:
        if st.session_state.page == "profile":
            profile_page()
        elif st.session_state.page == "edit_profile":
            edit_profile_page()
        elif st.session_state.page == "about":
            about_page()
        else:
            chat_page()

if __name__ == "__main__":
    main()
