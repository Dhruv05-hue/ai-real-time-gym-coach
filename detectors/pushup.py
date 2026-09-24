from core.base_exercise import BaseExercise


class PushUpDetector(BaseExercise):

    # ---------------------------------------------------------
    # PUSH-UP SETTINGS
    # ---------------------------------------------------------

    DOWN_THRESHOLD = 90
    UP_THRESHOLD = 160

    MIN_VISIBILITY = 0.5

    # Number of consecutive frames required
    # before accepting the DOWN position.
    MIN_DOWN_FRAMES = 4

    # Prevents accidental double counting.
    MIN_REP_INTERVAL = 0.8

    HIP_SAG_TOLERANCE = 0.08

    # ---------------------------------------------------------
    # LANDMARKS
    # ---------------------------------------------------------

    LEFT_SHOULDER = 11
    LEFT_ELBOW = 13
    LEFT_WRIST = 15

    RIGHT_SHOULDER = 12
    RIGHT_ELBOW = 14
    RIGHT_WRIST = 16

    LEFT_HIP = 23
    RIGHT_HIP = 24

    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def __init__(self):
        super().__init__()

        self.reps = 0
        self.stage = "up"

        # Used to confirm a real DOWN position.
        self.down_frames = 0

        # Time of last counted rep.
        self.last_rep_time = 0

    def reset(self) -> None:
        self.reps = 0
        self.stage = "up"
        self.down_frames = 0
        self.last_rep_time = 0

    def process(self, landmarks) -> dict:

        # ---------------------------------------------------------
        # SELECT MORE VISIBLE SIDE
        # ---------------------------------------------------------

        left_vis = landmarks[self.LEFT_ELBOW].visibility
        right_vis = landmarks[self.RIGHT_ELBOW].visibility

        if left_vis >= right_vis:

            shoulder_idx = self.LEFT_SHOULDER
            elbow_idx = self.LEFT_ELBOW
            wrist_idx = self.LEFT_WRIST
            hip_idx = self.LEFT_HIP
            ankle_idx = self.LEFT_ANKLE

        else:

            shoulder_idx = self.RIGHT_SHOULDER
            elbow_idx = self.RIGHT_ELBOW
            wrist_idx = self.RIGHT_WRIST
            hip_idx = self.RIGHT_HIP
            ankle_idx = self.RIGHT_ANKLE

        # ---------------------------------------------------------
        # ELBOW ANGLE
        # ---------------------------------------------------------

        elbow_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, elbow_idx),
            self.get_point(landmarks, wrist_idx),
        )

        # ---------------------------------------------------------
        # BODY ANGLE
        # ---------------------------------------------------------

        body_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, hip_idx),
            self.get_point(landmarks, ankle_idx),
        )

        # ---------------------------------------------------------
        # HIP POSITION
        # ---------------------------------------------------------

        shoulder_y = landmarks[shoulder_idx].y
        ankle_y = landmarks[ankle_idx].y
        hip_y = landmarks[hip_idx].y

        expected_hip_y = (shoulder_y + ankle_y) / 2

        hip_deviation = hip_y - expected_hip_y

        # ---------------------------------------------------------
        # VISIBILITY
        # ---------------------------------------------------------

        shoulder_vis = landmarks[shoulder_idx].visibility
        elbow_vis = landmarks[elbow_idx].visibility
        wrist_vis = landmarks[wrist_idx].visibility
        hip_vis = landmarks[hip_idx].visibility

        # Only these are required for REP counting.
        rep_landmarks_visible = (
            shoulder_vis >= self.MIN_VISIBILITY
            and elbow_vis >= self.MIN_VISIBILITY
            and wrist_vis >= self.MIN_VISIBILITY
        )

        # ---------------------------------------------------------
        # REP DETECTION
        # ---------------------------------------------------------

        if rep_landmarks_visible:

            # =====================================================
            # GOING DOWN
            # =====================================================

            if elbow_angle <= self.DOWN_THRESHOLD:

                self.down_frames += 1

                # Only accept DOWN after several stable frames.
                if self.down_frames >= self.MIN_DOWN_FRAMES:

                    self.stage = "down"

            else:

                # If we are not sufficiently deep,
                # don't keep accumulating DOWN frames.
                self.down_frames = 0

            # =====================================================
            # COMING BACK UP
            # =====================================================

            if (
                elbow_angle >= self.UP_THRESHOLD
                and self.stage == "down"
            ):

                import time

                current_time = time.time()

                # Prevent rapid accidental double counts.
                if (
                    current_time - self.last_rep_time
                    >= self.MIN_REP_INTERVAL
                ):

                    self.reps += 1
                    self.last_rep_time = current_time


                self.stage = "up"
                self.down_frames = 0

        # ---------------------------------------------------------
        # BODY ALIGNMENT
        # ---------------------------------------------------------

        if body_angle > 160:

            body_alignment = "Straight"

        elif body_angle > 140:

            body_alignment = "Slight Bend"

        else:

            body_alignment = "Poor Form"

        # ---------------------------------------------------------
        # HIP STATUS
        # ---------------------------------------------------------

        if hip_vis >= self.MIN_VISIBILITY:

            if abs(hip_deviation) <= self.HIP_SAG_TOLERANCE:

                hip_status = "LEVEL"

            elif hip_deviation > self.HIP_SAG_TOLERANCE:

                hip_status = "SAGGING"

            else:

                hip_status = "PIKED UP"

        else:

            hip_status = "N/A"

        # ---------------------------------------------------------
        # DEBUG
        # ---------------------------------------------------------


        # ---------------------------------------------------------
        # RETURN
        # ---------------------------------------------------------

        return {
            "reps": self.reps,
            "elbow_angle": int(elbow_angle),
            "body_alignment": body_alignment,
            "hip_status": hip_status,
            "stage": self.stage,
        }