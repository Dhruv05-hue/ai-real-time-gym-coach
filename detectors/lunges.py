from core.base_exercise import BaseExercise


class LungesDetector(BaseExercise):
    # Knee-angle thresholds
    DOWN_THRESHOLD = 100
    UP_THRESHOLD = 160

    # Minimum landmark visibility
    MIN_VISIBILITY = 0.7

    # Maximum allowed horizontal shoulder/hip offset
    BALANCE_TOLERANCE = 0.10

    # Number of consecutive frames required before changing stage
    STABLE_FRAMES_REQUIRED = 2

    LEFT_HIP = 23
    LEFT_KNEE = 25
    LEFT_ANKLE = 27

    RIGHT_HIP = 24
    RIGHT_KNEE = 26
    RIGHT_ANKLE = 28

    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self) -> None:
        self.reps = 0
        self.stage = None

        # Stability counters
        self._down_frame_count = 0
        self._up_frame_count = 0

        # Keep the selected front leg stable during a rep
        self._active_front_leg = None

    def _visible(self, landmarks, indexes) -> bool:
        """Check whether all required landmarks are clearly visible."""
        return all(
            0 <= index < len(landmarks)
            and landmarks[index].visibility >= self.MIN_VISIBILITY
            for index in indexes
        )

    def _get_leg_data(self, landmarks, side):
        """Return knee angle and landmark indexes for a leg."""

        if side == "left":
            hip_idx = self.LEFT_HIP
            knee_idx = self.LEFT_KNEE
            ankle_idx = self.LEFT_ANKLE
            shoulder_idx = self.LEFT_SHOULDER
        else:
            hip_idx = self.RIGHT_HIP
            knee_idx = self.RIGHT_KNEE
            ankle_idx = self.RIGHT_ANKLE
            shoulder_idx = self.RIGHT_SHOULDER

        knee_angle = self.calculate_angle(
            self.get_point(landmarks, hip_idx),
            self.get_point(landmarks, knee_idx),
            self.get_point(landmarks, ankle_idx),
        )

        return {
            "angle": knee_angle,
            "hip": hip_idx,
            "knee": knee_idx,
            "ankle": ankle_idx,
            "shoulder": shoulder_idx,
        }

    def _select_front_leg(self, landmarks):
        """
        Select the leg currently showing the smaller knee angle.

        Once a leg is selected, keep it active until the rep is completed.
        This prevents the active leg from switching because of small
        frame-to-frame landmark fluctuations.
        """

        if self._active_front_leg is not None:
            return self._active_front_leg

        left = self._get_leg_data(landmarks, "left")
        right = self._get_leg_data(landmarks, "right")

        left_visible = self._visible(
            landmarks,
            [self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE],
        )

        right_visible = self._visible(
            landmarks,
            [self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE],
        )

        if left_visible and right_visible:
            if left["angle"] <= right["angle"]:
                self._active_front_leg = "left"
            else:
                self._active_front_leg = "right"

        elif left_visible:
            self._active_front_leg = "left"

        elif right_visible:
            self._active_front_leg = "right"

        return self._active_front_leg

    def _update_rep_stage(self, front_knee_angle):
        """
        Update the lunge state using stable multi-frame detection.

        DOWN:
            Knee reaches 100 degrees or lower.

        UP:
            Knee reaches 160 degrees or higher after being DOWN.
        """

        # -------------------------
        # DOWN detection
        # -------------------------
        if front_knee_angle <= self.DOWN_THRESHOLD:
            self._down_frame_count += 1
        else:
            self._down_frame_count = 0

        if (
            self._down_frame_count >= self.STABLE_FRAMES_REQUIRED
            and self.stage != "down"
        ):
            self.stage = "down"
            self._up_frame_count = 0

        # -------------------------
        # UP detection
        # -------------------------
        if (
            self.stage == "down"
            and front_knee_angle >= self.UP_THRESHOLD
        ):
            self._up_frame_count += 1
        else:
            self._up_frame_count = 0

        # -------------------------
        # REP COMPLETION
        # -------------------------
        if (
            self.stage == "down"
            and self._up_frame_count >= self.STABLE_FRAMES_REQUIRED
        ):
            self.stage = "up"
            self.reps += 1

            self._down_frame_count = 0
            self._up_frame_count = 0

            # Allow the next rep to select the current front leg again.
            self._active_front_leg = None

    def process(self, landmarks) -> dict:

        # --------------------------------------------------
        # Basic landmark availability check
        # --------------------------------------------------

        required_landmarks = [
            self.LEFT_HIP,
            self.LEFT_KNEE,
            self.LEFT_ANKLE,
            self.RIGHT_HIP,
            self.RIGHT_KNEE,
            self.RIGHT_ANKLE,
            self.LEFT_SHOULDER,
            self.RIGHT_SHOULDER,
        ]

        if not self._visible(landmarks, required_landmarks):
            return {
                "reps": self.reps,
                "front_knee_angle": 0,
                "torso_angle": 0,
                "balance_status": "UNKNOWN",
            }

        # --------------------------------------------------
        # Select front leg
        # --------------------------------------------------

        front_leg = self._select_front_leg(landmarks)

        if front_leg is None:
            return {
                "reps": self.reps,
                "front_knee_angle": 0,
                "torso_angle": 0,
                "balance_status": "UNKNOWN",
            }

        front = self._get_leg_data(landmarks, front_leg)

        front_knee_angle = front["angle"]

        # --------------------------------------------------
        # Rep counting
        # --------------------------------------------------

        self._update_rep_stage(front_knee_angle)

        # --------------------------------------------------
        # Torso angle
        # --------------------------------------------------

        torso_angle = self.calculate_angle(
            self.get_point(
                landmarks,
                front["shoulder"],
            ),
            self.get_point(
                landmarks,
                front["hip"],
            ),
            self.get_point(
                landmarks,
                front["knee"],
            ),
        )

        # --------------------------------------------------
        # Balance calculation
        # --------------------------------------------------

        shoulder_mid_x = (
            landmarks[self.LEFT_SHOULDER].x
            + landmarks[self.RIGHT_SHOULDER].x
        ) / 2.0

        hip_mid_x = (
            landmarks[self.LEFT_HIP].x
            + landmarks[self.RIGHT_HIP].x
        ) / 2.0

        lateral_offset = abs(
            shoulder_mid_x - hip_mid_x
        )

        if lateral_offset <= self.BALANCE_TOLERANCE:
            balance_status = "BALANCED"
        else:
            balance_status = "OFF BALANCE"

        # --------------------------------------------------
        # Return metrics
        # --------------------------------------------------

        return {
            "reps": self.reps,
            "front_knee_angle": int(front_knee_angle),
            "torso_angle": int(torso_angle),
            "balance_status": balance_status,
        }