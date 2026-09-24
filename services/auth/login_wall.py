import streamlit as st
from services.persistence.exercise_repository import get_or_create_user


def render_login_wall():
    if st.session_state.get("user_id") is not None:
        return True

    st.html("""
    <style>
        .login-wrapper {
            width: 560px;
            max-width: 100%;
            margin: 7vh auto 0 auto;
        }

        .login-brand {
            text-align: center;
            margin-bottom: 24px;
        }

        .login-logo-row {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 9px;
            height: 54px;
        }

        .login-logo {
            color: #f5f7fa;
            font-size: 3.1rem;
            font-weight: 850;
            letter-spacing: -0.06em;
            line-height: 1;
        }

        .login-dot {
            width: 16px;
            height: 16px;
            flex-shrink: 0;
            border-radius: 50%;
            background: #b8ff3d;
            box-shadow: 0 0 22px rgba(184, 255, 61, 0.65);
            position: relative;
            top: 1px;
        }

        .login-tagline {
            margin-top: 10px;
            color: #b8ff3d;
            font-size: 0.74rem;
            letter-spacing: 0.18em;
            font-weight: 700;
        }

        .login-description {
            margin-top: 9px;
            color: #9299a5;
            font-size: 0.9rem;
        }

        .login-card {
            width: 100%;
            box-sizing: border-box;
            background: linear-gradient(
                145deg,
                #191d23,
                #111419
            );
            border: 1px solid #292e36;
            border-radius: 20px;
            padding: 25px 30px;
            text-align: center;
            box-shadow: 0 20px 55px rgba(0, 0, 0, 0.28);
            margin-bottom: 18px;
        }

        .login-card-title {
            color: #f5f7fa;
            font-size: 1.25rem;
            font-weight: 750;
            margin-bottom: 5px;
        }

        .login-card-subtitle {
            color: #9299a5;
            font-size: 0.86rem;
        }

        div[data-testid="stForm"] {
            width: 560px !important;
            max-width: 100% !important;
            margin: 0 auto !important;
            border: none !important;
            padding: 0 !important;
            background: transparent !important;
        }

        div[data-testid="stTextInput"] {
            width: 100%;
        }

        div[data-testid="stTextInput"] label {
            color: #d9dde3 !important;
            font-weight: 650 !important;
        }

        div[data-testid="stTextInput"] input {
            width: 100% !important;
            box-sizing: border-box !important;
            background: #0c0f13 !important;
            color: #f5f7fa !important;
            border: 1px solid #303640 !important;
            border-radius: 11px !important;
            min-height: 48px !important;
        }

        div[data-testid="stTextInput"] input::placeholder {
            color: #686f7a !important;
        }

        div[data-testid="stTextInput"] input:focus {
            border-color: #b8ff3d !important;
            box-shadow: 0 0 0 1px #b8ff3d !important;
        }

        div[data-testid="stFormSubmitButton"] {
            width: 100% !important;
            margin-top: 8px !important;
        }

        div[data-testid="stFormSubmitButton"] button {
            width: 100% !important;
            min-height: 50px !important;
            border-radius: 11px !important;
            background: #b8ff3d !important;
            color: #0b0d10 !important;
            border: 1px solid #b8ff3d !important;
            font-size: 0.95rem !important;
            font-weight: 800 !important;
            box-shadow: 0 8px 25px rgba(184, 255, 61, 0.14) !important;
            transition: all 0.18s ease !important;
        }

        div[data-testid="stFormSubmitButton"] button p {
            color: #0b0d10 !important;
            font-weight: 800 !important;
        }

        div[data-testid="stFormSubmitButton"] button:hover {
            background: #c7ff68 !important;
            border-color: #c7ff68 !important;
            color: #0b0d10 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 12px 32px rgba(184, 255, 61, 0.24) !important;
        }

        div[data-testid="stFormSubmitButton"] button:hover p {
            color: #0b0d10 !important;
        }

        .login-footer {
            width: 560px;
            max-width: 100%;
            margin: 20px auto 0 auto;
            text-align: center;
            color: #626975;
            font-size: 0.73rem;
        }

        .login-footer span {
            color: #b8ff3d;
        }

        @media (max-width: 700px) {
            .login-wrapper {
                width: 100%;
                margin-top: 5vh;
            }

            .login-logo {
                font-size: 2.7rem;
            }

            .login-card {
                padding: 22px;
            }

            div[data-testid="stForm"] {
                width: 100% !important;
            }

            .login-footer {
                width: 100%;
            }
        }
    </style>

    <div class="login-wrapper">

        <div class="login-brand">

            <div class="login-logo-row">
                <span class="login-dot"></span>
                <span class="login-logo">Repvion</span>
            </div>

            <div class="login-tagline">
                AI FITNESS COACH
            </div>

            <div class="login-description">
                Your real-time AI workout companion
            </div>

        </div>

        <div class="login-card">

            <div class="login-card-title">
                Start your session
            </div>

            <div class="login-card-subtitle">
                Enter your name to access your personalized workout dashboard.
            </div>

        </div>

    </div>
    """)

    with st.form("login_form", clear_on_submit=False):

        username = st.text_input(
            "Name",
            placeholder="Enter your unique name"
        )

        submit_button = st.form_submit_button(
            "Enter Repvion",
            width="stretch"
        )

    st.html("""
        <div class="login-footer">
            AI-powered pose detection
            &nbsp;•&nbsp;
            Real-time form analysis
            &nbsp;•&nbsp;
            <span>Voice coaching</span>
        </div>
    """)

    if submit_button:

        if not username:
            st.error("Name can't be empty.")
            return False

        user = get_or_create_user(username)

        st.session_state["user_id"] = user["id"]
        st.session_state["username"] = user["username"]

        st.rerun()

    return False