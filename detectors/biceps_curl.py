import math
import time
from core.base_exercise import BaseExercise


class BicepsCurlDetector(BaseExercise):

    # Rep detection
    UP_THRESHOLD = 65
    DOWN_THRESHOLD = 150

    # Visibility
    MIN_VISIBILITY = 0.5

    # Form detection
    ELBOW_DRIFT_TOLERANCE = 0.06
    SWING_THRESHOLD = 15

    # Rep stability
    MIN_UP_FRAMES = 2
    MIN_REP_INTERVAL = 0.7

    LEFT_SHOULDER = 11
    LEFT_ELBOW = 13
    LEFT_WRIST = 15

    RIGHT_SHOULDER = 12
    RIGHT_ELBOW = 14
    RIGHT_WRIST = 16

    LEFT_HIP = 23
    RIGHT_HIP = 24

    def __init__(self):
        super().__init__()

        self.reps = 0
        self.stage = "down"

        self._shoulder_x_baseline = None

        self._up_frames = 0
        self._last_rep_time = 0

    def reset(self) -> None:
        self.reps = 0
        self.stage = "down"

        self._shoulder_x_baseline = None

        self._up_frames = 0
        self._last_rep_time = 0

    def process(self, landmarks) -> dict:

        # ---------------------------------------------------------
        # SELECT THE BETTER VISIBLE ARM
        # ---------------------------------------------------------

        left_vis = landmarks[self.LEFT_ELBOW].visibility
        right_vis = landmarks[self.RIGHT_ELBOW].visibility

        if left_vis >= right_vis:
            shoulder_idx = self.LEFT_SHOULDER
            elbow_idx = self.LEFT_ELBOW
            wrist_idx = self.LEFT_WRIST
        else:
            shoulder_idx = self.RIGHT_SHOULDER
            elbow_idx = self.RIGHT_ELBOW
            wrist_idx = self.RIGHT_WRIST

        # ---------------------------------------------------------
        # ELBOW ANGLE
        # ---------------------------------------------------------

        elbow_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, elbow_idx),
            self.get_point(landmarks, wrist_idx),
        )

        # ---------------------------------------------------------
        # VISIBILITY CHECK
        # ---------------------------------------------------------

        key_landmarks_visible = (
            landmarks[shoulder_idx].visibility >= self.MIN_VISIBILITY
            and landmarks[elbow_idx].visibility >= self.MIN_VISIBILITY
            and landmarks[wrist_idx].visibility >= self.MIN_VISIBILITY
        )

        # ---------------------------------------------------------
        # REP COUNTING
        # ---------------------------------------------------------

        if key_landmarks_visible:

            # Arm is sufficiently curled
            if elbow_angle <= self.UP_THRESHOLD:

                self._up_frames += 1

                if self._up_frames >= self.MIN_UP_FRAMES:
                    self.stage = "up"

            else:
                self._up_frames = 0

            # Arm has returned down after being curled
            if (
                elbow_angle >= self.DOWN_THRESHOLD
                and self.stage == "up"
            ):

                current_time = time.time()

                if current_time - self._last_rep_time >= self.MIN_REP_INTERVAL:

                    self.reps += 1
                    self._last_rep_time = current_time

                self.stage = "down"
                self._up_frames = 0

        # ---------------------------------------------------------
        # ELBOW DRIFT
        # ---------------------------------------------------------

        shoulder_x = landmarks[shoulder_idx].x
        elbow_x = landmarks[elbow_idx].x

        elbow_drift = abs(elbow_x - shoulder_x)

        if elbow_drift <= self.ELBOW_DRIFT_TOLERANCE:
            shoulder_status = "STABLE"
        else:
            shoulder_status = "ELBOW DRIFTING"

        # ---------------------------------------------------------
        # TORSO SWING
        # ---------------------------------------------------------

        shoulder_mid_x = (
            landmarks[self.LEFT_SHOULDER].x
            + landmarks[self.RIGHT_SHOULDER].x
        ) / 2

        shoulder_mid_y = (
            landmarks[self.LEFT_SHOULDER].y
            + landmarks[self.RIGHT_SHOULDER].y
        ) / 2

        hip_mid_x = (
            landmarks[self.LEFT_HIP].x
            + landmarks[self.RIGHT_HIP].x
        ) / 2

        hip_mid_y = (
            landmarks[self.LEFT_HIP].y
            + landmarks[self.RIGHT_HIP].y
        ) / 2

        dx = shoulder_mid_x - hip_mid_x
        dy = shoulder_mid_y - hip_mid_y

        torso_angle_from_vertical = self._safe_angle(dx, dy)

        if torso_angle_from_vertical <= self.SWING_THRESHOLD:
            swing_status = "NO SWING"
        else:
            swing_status = "SWINGING"

        # ---------------------------------------------------------
        # RETURN METRICS
        # ---------------------------------------------------------

        return {
            "reps": self.reps,
            "elbow_angle": int(elbow_angle),
            "shoulder_status": shoulder_status,
            "swing_status": swing_status,
            "stage": self.stage,
        }

    def _safe_angle(self, dx, dy):
        if dy == 0:
            return 0.0

        return math.degrees(
            math.atan2(abs(dx), abs(dy))
        )