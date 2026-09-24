import streamlit as st
import os
import time
import pandas as pd
from dotenv import load_dotenv
from services.auth.login_wall import render_login_wall
from services.state.session_defaults import initial_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS
from services.ui.style_loader import (
    load_css,
    inject_local_font,
    inject_webrtc_styles
)
from services.persistence.exercise_repository import init_db
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import sync_metrics_update
from services.persistence.exercise_repository import get_users_exercises
from groq import Groq
from services.coaching.llm import LLMCoach
from services.coaching.tts import TextToSpeech
from services.coaching.voice_pipeline import (
    VoicePipeline,
    autoplay_audio
)
load_dotenv()
def _estimate_audio_duration(text):
    """Estimate spoken-audio duration for live playback scheduling."""
    words = len((text or "").split())
    if words <= 0:
        return 2.0
    return max(2.5, min(15.0, (words / 2.1) + 0.8))


@st.fragment(run_every=1.0)
def live_metrics_update(context):
    # -----------------------------------------------------
    # UPDATE LIVE METRICS
    # -----------------------------------------------------
    sync_metrics_update(context)

    # -----------------------------------------------------
    # LIVE COACH AUDIO
    # -----------------------------------------------------
    # IMPORTANT:
    # The fragment must NOT render st.audio().
    #
    # A fragment is refreshed every 0.5 seconds. If the audio
    # element is rendered inside the fragment, Streamlit can
    # replace that element before the browser has started
    # playback.
    #
    # Instead, this fragment only moves one audio message into
    # `audio_to_play` and triggers a FULL app rerun. The audio
    # element is rendered outside the fragment in main(), where
    # it remains stable while the fragment continues updating.
    # -----------------------------------------------------

    now = time.time()

    busy_until = float(
        st.session_state.get(
            "coach_audio_busy_until",
            0.0,
        )
        or 0.0
    )

    queue = st.session_state.get(
        "coach_audio_queue",
        [],
    )

    if queue and now >= busy_until:
        next_item = queue.pop(0)
        st.session_state.coach_audio_queue = queue

        audio = next_item.get("audio")
        feedback = next_item.get("feedback")

        if audio:
            st.session_state.coach_feedback = feedback

            # Reserve the playback window BEFORE the full rerun.
            # This prevents the next 0.5-second fragment execution
            # from immediately selecting another queued message.
            st.session_state.coach_audio_busy_until = (
                now + _estimate_audio_duration(feedback)
            )

            # The actual st.audio() call happens in main(), outside
            # this fragment. This is the critical fix for audio
            # disappearing before playback starts.
            st.session_state.audio_to_play = audio
            st.session_state.audio_to_play_until = (
                st.session_state.coach_audio_busy_until
                + 0.5
            )

            # Full app rerun: main() will render the audio player
            # outside the fragment.
            st.rerun()

    # LIVE VALUES
    # -----------------------------------------------------
    exercise = st.session_state.get(
        "exercise_type",
        "Workout"
    )
    total_reps = st.session_state.get(
        "reps",
        0
    )
    sets_completed = st.session_state.get(
        "sets_completed",
        0
    )
    target_sets = st.session_state.get(
        "target_sets",
        0
    )
    # -----------------------------------------------------
    # FORM INFORMATION
    # -----------------------------------------------------
    if exercise == "Squats":
        form_value = st.session_state.get(
            "depth_status",
            "N/A"
        )
        technique = [
            (
                "Knee Angle",
                f"{st.session_state.get('knee_angle', 0)}°"
            ),
            (
                "Back Angle",
                f"{st.session_state.get('back_angle', 0)}°"
            ),
            (
                "Depth",
                form_value
            ),
        ]
    elif exercise == "Push-ups":
        alignment = st.session_state.get(
            "body_alignment",
            "N/A"
        )
        hip = st.session_state.get(
            "hip_status",
            "N/A"
        )
        form_value = (
            "GOOD"
            if alignment in ("Good Form", "GOOD")
            and hip not in ("SAGGING", "PIKED UP")
            else "CHECK FORM"
        )
        technique = [
            (
                "Elbow Angle",
                f"{st.session_state.get('elbow_angle', 0)}°"
            ),
            (
                "Alignment",
                alignment
            ),
            (
                "Hip Position",
                hip
            ),
        ]
    elif exercise == "Biceps Curls (Dumbbell)":
        shoulder = st.session_state.get(
            "shoulder_status",
            "N/A"
        )
        swing = st.session_state.get(
            "swing_status",
            "N/A"
        )
        form_value = (
            "GOOD"
            if swing != "SWINGING"
            and shoulder != "ELBOW DRIFTING"
            else "CHECK FORM"
        )
        technique = [
            (
                "Elbow Angle",
                f"{st.session_state.get('elbow_angle', 0)}°"
            ),
            (
                "Shoulder",
                shoulder
            ),
            (
                "Swing",
                swing
            ),
        ]
    elif exercise == "Shoulder Press":
        extension = st.session_state.get(
            "extension_status",
            "N/A"
        )
        back_arch = st.session_state.get(
            "back_arch_status",
            "N/A"
        )
        form_value = (
            "GOOD"
            if back_arch != "Excessive Arch"
            else "CHECK FORM"
        )
        technique = [
            (
                "Elbow Angle",
                f"{st.session_state.get('elbow_angle', 0)}°"
            ),
            (
                "Extension",
                extension
            ),
            (
                "Back",
                back_arch
            ),
        ]
    elif exercise == "Lunges":
        balance = st.session_state.get(
            "balance_status",
            "N/A"
        )
        form_value = (
            "GOOD"
            if balance != "OFF BALANCE"
            else "CHECK FORM"
        )
        technique = [
            (
                "Front Knee",
                f"{st.session_state.get('front_knee_angle', 0)}°"
            ),
            (
                "Torso Angle",
                f"{st.session_state.get('torso_angle', 0)}°"
            ),
            (
                "Balance",
                balance
            ),
        ]
    else:
        form_value = "N/A"
        technique = []
    # -----------------------------------------------------
    # LIVE WORKOUT HEADER
    # -----------------------------------------------------
    st.html(
        f"""
        <div class="workout-topbar">
            <div>
                <div class="workout-brand">
                    <span>●</span> Repvion
                </div>
                <div class="workout-brand-sub">
                    AI FITNESS COACH
                </div>
            </div>
            <div class="workout-status">
                <strong>{exercise.upper()}</strong>
                <span>● LIVE</span>
            </div>
        </div>
        """
    )
    # -----------------------------------------------------
    # MAIN LIVE METRICS
    # -----------------------------------------------------
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "REPS",
            f"{total_reps}"
        )
    with c2:
        st.metric(
            "SETS",
            f"{sets_completed} / {target_sets}"
        )
    with c3:
        st.metric(
            "FORM",
            form_value
        )
    # -----------------------------------------------------
    # LIVE FORM ANALYSIS
    # -----------------------------------------------------
    if technique:
        st.html(
            '<div class="technique-title">'
            'LIVE FORM ANALYSIS'
            '</div>'
        )
        t1, t2, t3 = st.columns(3)
        for col, (label, value) in zip(
            (t1, t2, t3),
            technique
        ):
            with col:
                st.metric(
                    label,
                    value
                )
def main():
    st.set_page_config(
        page_icon="🏋️",
        page_title="Repvion | AI Fitness Coach",
        initial_sidebar_state="expanded",
        layout="centered"
    )
    # =====================================================
    # LOAD CSS
    # =====================================================
    load_css(
        os.path.join(
            os.getcwd(),
            "static",
            "style.css"
        )
    )
    inject_local_font(
        os.path.join(
            os.getcwd(),
            "static",
            "AdobeClean.otf"
        ),
        "AdobeClean"
    )
    # =====================================================
    # REPVION UI
    # =====================================================
    st.html(
        """
        <style>
            :root {
                --rv-bg:#0b0d10;
                --rv-card:#14171c;
                --rv-card2:#191d23;
                --rv-border:#292e36;
                --rv-text:#f5f7fa;
                --rv-muted:#9299a5;
                --rv-accent:#b8ff3d;
            }
            .stApp {
                background:
                    radial-gradient(
                        circle at 85% 0%,
                        rgba(184,255,61,.08),
                        transparent 28%
                    ),
                    radial-gradient(
                        circle at 0% 20%,
                        rgba(184,255,61,.035),
                        transparent 25%
                    ),
                    var(--rv-bg);
            }
            .block-container {
                max-width:1250px;
                padding-top:2rem;
                padding-bottom:3rem;
            }
            section[data-testid="stSidebar"] {
                background:
                    linear-gradient(
                        180deg,
                        #101318 0%,
                        #0b0d10 100%
                    );
                border-right:1px solid var(--rv-border);
            }
            section[data-testid="stSidebar"] .block-container {
                padding:1.35rem 1.05rem 2rem;
            }
            h1,h2,h3 {
                font-weight:800 !important;
                letter-spacing:-.035em !important;
            }
            div[data-testid="stMetric"] {
                background:
                    linear-gradient(
                        145deg,
                        var(--rv-card2),
                        var(--rv-card)
                    );
                border:1px solid var(--rv-border);
                border-radius:16px;
                padding:14px 16px;
                box-shadow:0 10px 30px rgba(0,0,0,.16);
            }
            div[data-testid="stMetricLabel"] {
                color:var(--rv-muted);
                font-size:.78rem;
                font-weight:650;
            }
            div[data-testid="stMetricValue"] {
                color:var(--rv-text);
                font-weight:800;
            }
            .stButton > button {
                min-height:46px;
                border-radius:12px;
                border:1px solid var(--rv-border);
                font-weight:750;
                transition:all .18s ease;
            }
            .stButton > button:hover {
                transform:translateY(-1px);
                border-color:var(--rv-accent);
                box-shadow:
                    0 8px 24px
                    rgba(184,255,61,.10);
            }
            .stButton > button[kind="primary"] {
                background:var(--rv-accent);
                color:#0a0d08;
                border-color:var(--rv-accent);
            }
            div[data-baseweb="select"] > div,
            div[data-testid="stNumberInput"] input {
                border-radius:11px;
            }
            div[data-testid="stAlert"] {
                border-radius:14px;
                border:1px solid var(--rv-border);
            }
            div[data-testid="stVideo"] {
                border-radius:18px;
                overflow:hidden;
                border:1px solid var(--rv-border);
                box-shadow:
                    0 18px 45px
                    rgba(0,0,0,.22);
            }
            div[data-testid="stTable"] {
                border-radius:14px;
                overflow:hidden;
                border:1px solid var(--rv-border);
            }
            hr {
                border-color:var(--rv-border) !important;
            }
            .workout-topbar {
                display:flex;
                justify-content:space-between;
                align-items:center;
                gap:20px;
                padding:18px 22px;
                margin:0 0 14px;
                background:
                    linear-gradient(
                        145deg,
                        #191d23,
                        #111419
                    );
                border:1px solid #292e36;
                border-radius:16px;
            }
            .workout-brand {
                color:#f5f7fa;
                font-size:1.35rem;
                font-weight:850;
                letter-spacing:-.035em;
            }
            .workout-brand span {
                color:#b8ff3d;
                text-shadow:
                    0 0 16px
                    rgba(184,255,61,.55);
            }
            .workout-brand-sub {
                color:#9299a5;
                font-size:.68rem;
                letter-spacing:.14em;
                margin-top:4px;
            }
            .workout-status {
                display:flex;
                align-items:center;
                gap:14px;
                color:#f5f7fa;
                font-size:.78rem;
                letter-spacing:.08em;
            }
            .workout-status span {
                color:#b8ff3d;
                font-weight:800;
            }
            .technique-title {
                color:#9299a5;
                font-size:.72rem;
                font-weight:750;
                letter-spacing:.13em;
                margin:18px 0 8px;
            }
            .repvion-hero {
                text-align:center;
                padding:4px 0 18px;
            }
            .hero-logo {
                color:#f5f7fa;
                font-size:2.35rem;
                font-weight:850;
                letter-spacing:-.055em;
            }
            .hero-logo span {
                color:#b8ff3d;
                text-shadow:
                    0 0 16px
                    rgba(184,255,61,.55);
            }
            .hero-subtitle {
                color:#9299a5;
                font-size:.72rem;
                letter-spacing:.13em;
                margin-top:7px;
            }
            .setup-card {
                text-align:center;
                padding:46px 30px;
                margin:10px 0 28px;
                background:
                    linear-gradient(
                        145deg,
                        #191d23,
                        #111419
                    );
                border:1px solid #292e36;
                border-radius:20px;
            }
            .setup-icon {
                font-size:1.8rem;
                margin-bottom:6px;
            }
            .setup-title {
                color:#f5f7fa;
                font-size:1.25rem;
                font-weight:750;
                margin-bottom:8px;
            }
            .setup-text {
                max-width:620px;
                margin:auto;
                color:#9299a5;
                line-height:1.6;
                font-size:.93rem;
            }
            .coach-card {
                margin-top:18px;
                padding:18px 20px;
                background:
                    linear-gradient(
                        145deg,
                        #191d23,
                        #111419
                    );
                border:1px solid #292e36;
                border-left:3px solid #b8ff3d;
                border-radius:15px;
            }
            .coach-title {
                color:#b8ff3d;
                font-size:.74rem;
                font-weight:800;
                letter-spacing:.11em;
                margin-bottom:7px;
            }
            .coach-message {
                color:#f5f7fa;
                font-size:1rem;
                line-height:1.5;
            }
            @media (max-width:900px) {
                .block-container {
                    padding-left:1rem;
                    padding-right:1rem;
                }
            }
        </style>
        """
    )
    # =====================================================
    # DATABASE
    # =====================================================
    init_db()
    # =====================================================
    # LOGIN
    # =====================================================
    if not render_login_wall():
        return
    # =====================================================
    # SESSION DEFAULTS
    # =====================================================
    initial_session_defaults()
    # =====================================================
    # VOICE PIPELINE
    # =====================================================
    if "voice_pipeline" not in st.session_state:
        try:
            api_key = os.environ.get(
                "GROQ_API_KEY",
                ""
            )
            if (
                not api_key
                and hasattr(st, "secrets")
                and "GROQ_API_KEY" in st.secrets
            ):
                api_key = st.secrets[
                    "GROQ_API_KEY"
                ]
            groq_client = Groq(
                api_key=api_key
            )
            llm_coach = LLMCoach(
                groq_client
            )
            tts = TextToSpeech()
            st.session_state.voice_pipeline = (
                VoicePipeline(
                    llm_coach,
                    tts
                )
            )
        except Exception as e:
            st.session_state.voice_pipeline = None
            st.error(
                f"Voice pipeline error: {e}"
            )
    # =====================================================
    # VOICE SESSION STATE
    # =====================================================
    if "audio_to_play" not in st.session_state:
        st.session_state.audio_to_play = None

    if "audio_to_play_until" not in st.session_state:
        st.session_state.audio_to_play_until = 0.0

    if "coach_audio_queue" not in st.session_state:
        st.session_state.coach_audio_queue = []

    if "coach_audio_busy_until" not in st.session_state:
        st.session_state.coach_audio_busy_until = 0.0

    if "coach_audio_message_id" not in st.session_state:
        st.session_state.coach_audio_message_id = 0

    if "coach_audio_current_id" not in st.session_state:
        st.session_state.coach_audio_current_id = None

    if "coach_audio_current_audio" not in st.session_state:
        st.session_state.coach_audio_current_audio = None

    if "coach_audio_current_feedback" not in st.session_state:
        st.session_state.coach_audio_current_feedback = None

    if "coach_feedback" not in st.session_state:
        st.session_state.coach_feedback = None
    if "last_announced_rep" not in st.session_state:
        st.session_state.last_announced_rep = 0
    # =====================================================
    # WORKOUT STATE
    # =====================================================
    workout_started = st.session_state.get(
        "workout_started",
        False
    )
    start_session_button = False
    # =====================================================
    # SIDEBAR
    # =====================================================
    with st.sidebar:
        st.html(
            """
            <div style='padding:6px 0 14px;'>
                <div style='font-size:1.65rem;
                            font-weight:850;
                            letter-spacing:-.045em;'>
                    🏋️ Repvion
                </div>
                <div style='color:#9299a5;
                            font-size:.76rem;
                            letter-spacing:.12em;
                            margin-top:4px;'>
                    AI FITNESS COACH
                </div>
            </div>
            """
        )
        if st.session_state.username:
            st.caption(
                f"👤 Login as "
                f"{st.session_state.username}"
            )
        st.divider()
        st.subheader("Workout Plan")
        # =================================================
        # BEFORE WORKOUT
        # =================================================
        if not workout_started:
            plan_exercise = st.selectbox(
                "Exercise",
                options=EXERCISE_OPTIONS,
                key="plan_exercise"
            )
            plan_sets = st.number_input(
                "Sets",
                min_value=0,
                max_value=50,
                key="plan_sets",
                step=1
            )
            plan_reps = st.number_input(
                "Reps per Set",
                min_value=0,
                max_value=50,
                key="plan_reps",
                step=1
            )
            st.markdown("")
            start_session_button = st.button(
                "Start Workout",
                width="stretch",
                key="start_session_button"
            )
            if start_session_button:
                # -----------------------------------------
                # WORKOUT SETTINGS
                # -----------------------------------------
                st.session_state.exercise_type = (
                    plan_exercise
                )
                st.session_state.target_sets = int(
                    plan_sets
                )
                st.session_state.reps_per_set = int(
                    plan_reps
                )
                # -----------------------------------------
                # RESET WORKOUT METRICS
                # -----------------------------------------
                st.session_state.reps = 0
                st.session_state.current_set_reps = 0
                st.session_state.sets_completed = 0
                st.session_state.workout_complete = False
                st.session_state.workout_started = True
                st.session_state.set_cycle_started_at = (
                    time.time()
                )
                st.session_state.last_saved_sets_completed = 0
                # -----------------------------------------
                # RESET VOICE STATE
                # -----------------------------------------
                st.session_state.audio_to_play = None
                st.session_state.audio_to_play_until = 0.0
                st.session_state.coach_audio_queue = []
                st.session_state.coach_audio_busy_until = 0.0
                st.session_state.coach_audio_current_id = None
                st.session_state.coach_audio_current_audio = None
                st.session_state.coach_audio_current_feedback = None
                st.session_state.coach_feedback = None
                st.session_state.last_announced_rep = 0
                st.session_state.last_notified_sets_completed = 0
                st.session_state.last_notified_workout_complete = False
                # -----------------------------------------
                # START WORKOUT VOICE
                # -----------------------------------------
                if st.session_state.voice_pipeline:
                    result = (
                        st.session_state.voice_pipeline.process_event(
                            event="workout_started",
                            exercise=plan_exercise,
                            metrics={}
                        )
                    )
                    if result:
                        audio, feedback = result
                       
                       
                        st.session_state.audio_to_play = (
                            audio
                        )
                        st.session_state.audio_to_play_until = (
                            time.time()
                            + _estimate_audio_duration(feedback)
                            + 0.5
                        )
                        st.session_state.coach_feedback = (
                            feedback
                        )
                
                workout_started = True
        # =================================================
        # DURING WORKOUT
        # =================================================
        else:
            exercise = st.session_state.get(
                "exercise_type"
            )
            sets = st.session_state.get(
                "target_sets"
            )
            reps = st.session_state.get(
                "reps_per_set"
            )
            st.info(
                f"**{exercise}** -- "
                f"{sets} Sets / {reps} Reps"
            )
            end_session_button = st.button(
                "End Workout",
                key="end_session_button",
                width="stretch"
            )
            if end_session_button:
                # -----------------------------------------
                # GET VALUES BEFORE ENDING WORKOUT
                # -----------------------------------------
                completed_reps = st.session_state.get(
                    "reps",
                    0
                )
                completed_sets = st.session_state.get(
                    "sets_completed",
                    0
                )
                # -----------------------------------------
                # END WORKOUT
                # -----------------------------------------
                st.session_state.workout_started = False
                workout_started = False
                # -----------------------------------------
                # WORKOUT COMPLETION VOICE
                # -----------------------------------------
                if st.session_state.voice_pipeline:
                    result = (
                        st.session_state.voice_pipeline.process_event(
                            event="workout_completed",
                            exercise=exercise,
                            metrics={
                                "reps": completed_reps,
                                "sets_completed": completed_sets
                            }
                        )
                    )
                    if result:
                        audio, feedback = result
                        st.session_state.audio_to_play = (
                            audio
                        )
                        st.session_state.audio_to_play_until = (
                            time.time()
                            + _estimate_audio_duration(feedback)
                            + 0.5
                        )
                        st.session_state.coach_feedback = (
                            feedback
                        )
                # Clear pending live coaching audio so the final
                # workout summary is the next and only message.
                st.session_state.coach_audio_queue = []
                st.session_state.coach_audio_busy_until = 0.0
                # End workout requires rerun
                st.rerun()
    # =====================================================
    # IMPORTANT AUDIO SECTION
    #
    # This is intentionally BEFORE WebRTC.
    #
    # When Start Workout is clicked, the audio is already
    # stored in audio_to_play and is rendered here during
    # the SAME Streamlit execution caused by the button.
    # =====================================================
    current_audio = st.session_state.get("audio_to_play")
    audio_until = float(
        st.session_state.get("audio_to_play_until", 0.0)
        or 0.0
    )

    if current_audio and time.time() <= audio_until:
        autoplay_audio(current_audio)
    # =====================================================
    # MAIN PAGE
    # =====================================================
    if not workout_started:
        st.html(
            """
            <div class="repvion-hero">
                <div class="hero-logo">
                    <span>●</span> Repvion
                </div>
                <div class="hero-subtitle">
                    AI FITNESS COACH • REAL-TIME FORM ANALYSIS
                </div>
            </div>
            """
        )
        st.html(
            """
            <div class="setup-card">
                <div class="setup-icon">
                    👋
                </div>
                <div class="setup-title">
                    Set up your Repvion workout
                </div>
                <div class="setup-text">
                    Choose your exercise, sets and reps in
                    the sidebar, then click
                    <strong>Start Workout</strong>
                    to activate your camera and AI coach.
                </div>
            </div>
            """
        )
    else:
        # =================================================
        # WEBRTC CAMERA
        # =================================================
        context = webrtc_streamer(
            key="exercise-analysis",
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=VideoProcessorClass,
            rtc_configuration={
                "iceServers": [
                    {
                        "urls": [
                            "stun:stun.l.google.com:19302"
                        ]
                    }
                ]
            },
            media_stream_constraints={
                "video": True,
                "audio": False
            },
            async_processing=True
        )
        inject_webrtc_styles()
        # =================================================
        # LIVE METRICS + LIVE AUDIO
        # =================================================
        live_metrics_update(context)
        # =================================================
        # COACH FEEDBACK
        # =================================================
        if st.session_state.get("coach_feedback"):
            st.html(
                f"""
                <div class="coach-card">
                    <div class="coach-title">
                        🤖 REPVION COACH
                    </div>
                    <div class="coach-message">
                        {st.session_state.coach_feedback}
                    </div>
                </div>
                """
            )
    # =====================================================
    # WORKOUT HISTORY
    # =====================================================
    st.divider()
    st.markdown(
        "#### Workout History"
    )
    user_id = st.session_state.get(
        "user_id",
        0
    )
    if isinstance(
        user_id,
        int
    ):
        history_rows = get_users_exercises(
            user_id
        )
        arr = [
            {
                "Exercise": row["exercise_name"],
                "Reps": row["reps"],
                "Sets": row["sets"],
                "Time (sec)": row["time"],
                "Date": row["created_at"]
            }
            for row in history_rows
        ]
        df = pd.DataFrame(
            arr
        )
        if not df.empty:
            df["Date"] = pd.to_datetime(
                df["Date"]
            ).dt.date
            agg_df = (
                df
                .groupby(
                    [
                        "Exercise",
                        "Date"
                    ]
                )
                .agg(
                    {
                        "Reps": "sum",
                        "Sets": "sum",
                        "Time (sec)": "sum"
                    }
                )
                .reset_index()
            )
            agg_df.index += 1
            st.table(
                agg_df,
                border="horizontal"
            )
        else:
            st.info(
                "No workout history found."
            )
if __name__ == "__main__":
    main()