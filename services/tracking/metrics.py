import streamlit as st
import time

from services.config.workout_config import METRICS_FIELDS
from services.persistence.exercise_repository import add_exercise


def _store_voice_result(result):
    """Store one coach message in the unified live-audio queue."""
    if not result:
        return

    audio, feedback = result

    if not audio:
        return

    queue = st.session_state.setdefault("coach_audio_queue", [])

    # Keeping a bounded queue so stale coaching messages can never build up.
    queue.append(
        {
            "audio": audio,
            "feedback": feedback,
            "created_at": time.time(),
        }
    )

    # The newest coaching event is more useful than a large backlog.
    if len(queue) > 3:
        del queue[:-3]


def sync_metrics_update(context):
    if (
        not context
        or not hasattr(context, "state")
        or not context.state.playing
    ):
        return

    processor = getattr(context, "video_processor", None)

    if not processor:
        return

    exercise = st.session_state.get("exercise_type")

    if not exercise:
        return

    processor.set_exercise(exercise)

    latest_metrics = processor.get_latest_metrics()

    if not latest_metrics:
        return

    reps = latest_metrics.get("reps", 0)

    if reps is None:
        reps = 0

    try:
        reps = int(reps)
    except (TypeError, ValueError):
        reps = 0

    previous_reps = int(st.session_state.get("reps", 0) or 0)

    st.session_state.reps = reps

    # =========================================================
    # METRICS
    # =========================================================

    fields = METRICS_FIELDS.get(exercise)

    if fields:
        for key, default in fields.items():
            st.session_state[key] = latest_metrics.get(
                key,
                default,
            )

    # =========================================================
    # VOICE PIPELINE
    # =========================================================

    voice_pipeline = st.session_state.get("voice_pipeline")
    voice_result = None
    new_rep_detected = reps > previous_reps

    # =========================================================
    # NEW REP
    # =========================================================
    # Every new rep is sent to VoicePipeline.
    # VoicePipeline itself decides whether this rep is a
    # milestone (5, 10, 15...) or should remain silent.
    # =========================================================

    if new_rep_detected and voice_pipeline:
        voice_result = voice_pipeline.process_event(
            event="rep_completed",
            exercise=exercise,
            metrics={
                **latest_metrics,
                "reps": reps,
            },
        )

        if voice_result:
            _store_voice_result(voice_result)

    # =========================================================
    # REP RESET
    # =========================================================

    if reps == 0:
        st.session_state.last_announced_rep = 0

    # Keep this state for compatibility with the rest of the app.
    # VoicePipeline is now the authoritative milestone tracker.
    st.session_state.last_announced_rep = max(
        int(st.session_state.get("last_announced_rep", 0) or 0),
        reps if reps % 5 == 0 else 0,
    )

    # =========================================================
    # SET CALCULATION
    # =========================================================

    reps_per_set = st.session_state.get("reps_per_set", 0)
    target_sets = st.session_state.get("target_sets", 0)

    if reps_per_set > 0 and target_sets > 0:
        sets_completed = reps // reps_per_set
        current_set_reps = reps % reps_per_set
        workout_completed = sets_completed >= target_sets
    else:
        sets_completed = 0
        current_set_reps = reps
        workout_completed = False

    st.session_state.sets_completed = sets_completed
    st.session_state.current_set_reps = current_set_reps
    st.session_state.workout_completed = workout_completed

    # =========================================================
    # SET COMPLETED
    # =========================================================

    last_saved_sets = st.session_state.get(
        "last_saved_sets_completed",
        0,
    )

    if (
        target_sets > 0
        and reps_per_set > 0
        and sets_completed > last_saved_sets
    ):
        newly_completed = sets_completed - last_saved_sets
        now_ts = time.time()

        started_at = st.session_state.get(
            "set_cycle_started_at",
            now_ts,
        )

        time_taken = now_ts - started_at

        user_id = st.session_state.get("user_id", 0)

        add_exercise(
            user_id,
            exercise,
            newly_completed * reps_per_set,
            newly_completed,
            time_taken,
        )

        st.session_state.set_cycle_started_at = now_ts
        st.session_state.last_saved_sets_completed = sets_completed

        # A set completion does not generate an additional voice
        # message. This avoids competing with a 5-rep milestone.

    # =========================================================
    # AUTOMATIC WORKOUT COMPLETION
    # =========================================================
    # Only mark the state here. The main Streamlit workout-end
    # flow is responsible for generating the final voice message.
    # This prevents two completion messages from being generated.
    # =========================================================

    if workout_completed:
        st.session_state.workout_completed = True

    # =========================================================
    # NO POSE
    # =========================================================

    pose_detected = latest_metrics.get(
        "pose_detected",
        True,
    )

    if (
        not pose_detected
        and voice_pipeline
        and not voice_result
    ):
        voice_result = voice_pipeline.process_event(
            event="no_pose_detected",
            exercise=exercise,
            metrics={
                "issue": (
                    "No pose detected. Please step into the camera frame."
                )
            },
        )

        if voice_result:
            _store_voice_result(voice_result)

    # =========================================================
    # ONGOING FORM CHECK
    # =========================================================
    # Do not run this again immediately after a new-rep event.
    # The rep event already performs the form check.
    # =========================================================

    if (
        not new_rep_detected
        and voice_pipeline
        and not voice_result
        and pose_detected
    ):
        voice_result = voice_pipeline.process_event(
            event="ongoing_form_check",
            exercise=exercise,
            metrics=latest_metrics,
        )

        if voice_result:
            _store_voice_result(voice_result)
