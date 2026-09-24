import time
import base64

import streamlit.components.v1 as components
import streamlit as st


class VoicePipeline:
    """
    Controls all AI coach voice events.

    Responsibilities:
    - Workout start announcement
    - Rep milestone announcements every 5 reps
    - Controlled form-error coaching
    - Prevent repeated identical warnings
    - Track actual form issues during workout
    - Workout completion summary
    """

    FORM_WARNING_COOLDOWN = 5.0
    SAME_ISSUE_COOLDOWN = 10.0

    def __init__(self, llm, tts):
        self.llm = llm
        self.tts = tts

        self.last_spoken_at = 0.0
        self.last_announced_rep = 0

        self.last_spoken_issue = None
        self.last_issue_spoken_at = 0.0

        self.detected_issues = []

    def _find_form_issue(self, exercise, metrics):
        if not metrics:
            return None

        direct_issue = metrics.get("issue")
        if direct_issue:
            return direct_issue

        if exercise == "Squats":
            depth = metrics.get("depth_status", "")
            back_angle = metrics.get("back_angle", 180)

            if depth == "TOO HIGH":
                return (
                    "The user's squat is not deep enough. "
                    "They need to bend their knees more."
                )

            if isinstance(back_angle, (int, float)) and back_angle < 130:
                return (
                    "The user is leaning too far forward "
                    "during the squat. They should keep their "
                    "chest more upright."
                )

        elif exercise == "Push-ups":
            alignment = metrics.get("body_alignment", "")
            hip_status = metrics.get("hip_status", "")

            if alignment == "Poor Form":
                return (
                    "The user's body is not straight "
                    "during the push-up."
                )

            if hip_status == "SAGGING":
                return (
                    "The user's hips are sagging down "
                    "during the push-up. They should keep "
                    "their body straight."
                )

            if hip_status == "PIKED UP":
                return (
                    "The user's hips are too high during "
                    "the push-up. They should keep their "
                    "body in a straight line."
                )

        elif exercise == "Biceps Curls (Dumbbell)":
            swing = metrics.get("swing_status", "")
            shoulder = metrics.get("shoulder_status", "")

            if swing == "SWINGING":
                return (
                    "The user is swinging their torso during "
                    "the curl. They should keep their body still."
                )

            if shoulder == "ELBOW DRIFTING":
                return (
                    "The user's elbow is drifting away from "
                    "their side during the curl. They should "
                    "keep the elbow closer to the body."
                )

        elif exercise == "Shoulder Press":
            back_arch = metrics.get("back_arch_status", "")

            if back_arch == "Excessive Arch":
                return (
                    "The user is arching their lower back "
                    "excessively during the press. They should "
                    "brace their core."
                )

            if back_arch == "Slight Arch":
                return (
                    "A slight back arch is detected. "
                    "The user should brace their core."
                )

        elif exercise == "Lunges":
            balance = metrics.get("balance_status", "")

            if balance == "OFF BALANCE":
                return (
                    "The user is losing balance during the lunge. "
                    "They should keep their feet about hip-width apart."
                )

        return None

    def reset(self):
        self.last_spoken_at = 0.0
        self.last_announced_rep = 0
        self.last_spoken_issue = None
        self.last_issue_spoken_at = 0.0
        self.detected_issues = []

    def _remember_issue(self, issue):
        if not issue:
            return

        normalized_issue = issue.strip()

        if normalized_issue and normalized_issue not in self.detected_issues:
            self.detected_issues.append(normalized_issue)

    def _speak(self, text, now):
        if not text:
            return None

        try:
            voice = self.tts.speak(text)
        except Exception:
            return None

        if not voice:
            return None

        self.last_spoken_at = now
        return voice, text

    def _handle_workout_started(self, exercise, now):
        if exercise:
            text = (
                f"Workout started. Let's begin with {exercise}. "
                "Focus on controlled movement and proper form."
            )
        else:
            text = (
                "Workout started. Focus on controlled movement "
                "and proper form."
            )

        return self._speak(text, now)

    def _handle_rep_completed(self, metrics, now):
        if not metrics:
            return None

        rep_count = metrics.get("reps", 0)

        try:
            rep_count = int(rep_count)
        except (TypeError, ValueError):
            return None

        if rep_count <= 0:
            return None

        # Only 5, 10, 15, 20... trigger a rep announcement.
        if rep_count % 5 != 0:
            return None

        # The same milestone can only be announced once.
        if rep_count <= self.last_announced_rep:
            return None

        self.last_announced_rep = rep_count

        if rep_count % 10 == 0:
            text = f"{rep_count} reps completed. Great job, keep going!"
        else:
            text = f"{rep_count} reps completed. Keep going!"

        return self._speak(text, now)

    def _handle_form_coaching(self, issue, now):
        if not issue:
            return None

        self._remember_issue(issue)

        # Do not repeat the same correction while the same problem
        # remains active.
        if issue == self.last_spoken_issue:
            if now - self.last_issue_spoken_at < self.SAME_ISSUE_COOLDOWN:
                return None

        # Do not let different corrections fire back-to-back.
        if now - self.last_spoken_at < self.FORM_WARNING_COOLDOWN:
            return None

        try:
            text = self.llm.give_feedback(
                "form_issue",
                issue,
            )
        except Exception:
            text = None

        if not text:
            text = issue

        result = self._speak(text, now)

        if result:
            self.last_spoken_issue = issue
            self.last_issue_spoken_at = now

        return result

    def _handle_workout_completed(self, exercise, metrics, now):
        completed_reps = 0
        completed_sets = 0

        if metrics:
            try:
                completed_reps = int(metrics.get("reps", 0))
            except (TypeError, ValueError):
                completed_reps = 0

            try:
                completed_sets = int(metrics.get("sets_completed", 0))
            except (TypeError, ValueError):
                completed_sets = 0

        if self.detected_issues:
            issues_for_summary = self.detected_issues[:5]

            issue_text = " ".join(
                f"{index + 1}. {issue}"
                for index, issue in enumerate(issues_for_summary)
            )

            summary_prompt = (
                "The workout has finished. Give a short and encouraging "
                "final coaching summary. Mention the actual form problems "
                "detected during the workout and give concise advice to "
                "improve them. Do not invent additional problems. "
                f"Exercise: {exercise}. "
                f"Completed reps: {completed_reps}. "
                f"Completed sets: {completed_sets}. "
                f"Detected form problems: {issue_text}"
            )

            try:
                text = self.llm.give_feedback(
                    "workout_completed",
                    summary_prompt,
                )
            except Exception:
                text = None

            if not text:
                text = (
                    f"Workout complete. You finished {completed_reps} reps. "
                    "Focus next time on the form issues we identified."
                )
        else:
            text = (
                f"Workout complete. Great job! You finished "
                f"{completed_reps} reps"
            )

            if completed_sets:
                text += f" across {completed_sets} sets"

            text += ". Keep maintaining this controlled form."

        return self._speak(text, now)

    def process_event(self, event, exercise, metrics):
        now = time.time()
        metrics = metrics or {}

        if event == "workout_started":
            self.reset()
            return self._handle_workout_started(exercise, now)

        if event == "workout_completed":
            return self._handle_workout_completed(
                exercise,
                metrics,
                now,
            )

        if event == "rep_completed":
            # The milestone check has priority. A 5th/10th/15th...
            # rep should not also generate a form warning in the
            # same event.
            milestone_result = self._handle_rep_completed(
                metrics,
                now,
            )

            if milestone_result:
                return milestone_result

            issue = self._find_form_issue(
                exercise,
                metrics,
            )

            return self._handle_form_coaching(issue, now)

        if event in (
            "form_issue",
            "coaching",
            "live_metrics",
            "ongoing_form_check",
            "no_pose_detected",
        ):
            issue = self._find_form_issue(
                exercise,
                metrics,
            )

            return self._handle_form_coaching(issue, now)

        if event == "set_completed":
            # Avoid an extra voice message competing with rep
            # milestones or form corrections.
            return None

        return None


def autoplay_audio(audio_bytes):
    """
    Play coach audio using a persistent browser-side HTML audio element.

    This intentionally does not use st.audio(). The Streamlit audio
    element can be recreated during app updates, while the browser-side
    element gives the audio its own playback lifecycle.
    """
    if not audio_bytes:
        return

    encoded_audio = base64.b64encode(audio_bytes).decode("ascii")

    html = f"""
    <div style="width:100%; font-family:Arial,sans-serif;">
        <audio
            id="repvion-coach-audio"
            controls
            autoplay
            preload="auto"
            style="width:100%; height:42px;"
        >
            <source
                src="data:audio/mpeg;base64,{encoded_audio}"
                type="audio/mpeg"
            >
        </audio>
        <div id="repvion-play-help"
             style="display:none; font-size:12px; margin-top:4px;">
            Browser blocked automatic playback. Press Play to hear the coach.
        </div>
    </div>

    <script>
        const audio = document.getElementById("repvion-coach-audio");
        const help = document.getElementById("repvion-play-help");

        if (audio) {{
            audio.volume = 1.0;

            const tryPlay = () => {{
                const promise = audio.play();

                if (promise !== undefined) {{
                    promise.catch(() => {{
                        if (help) help.style.display = "block";
                    }});
                }}
            }};

            setTimeout(tryPlay, 100);
        }}
    </script>
    """

    components.html(
        html,
        height=72,
        scrolling=False,
    )
