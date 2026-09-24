from core.base_exercise import BaseExercise


class SquatDetector(BaseExercise):

    # --------------------------------------------------
    # Squat thresholds
    # --------------------------------------------------
    DOWN_THRESHOLD = 135
    UP_THRESHOLD = 160

    # Lower visibility requirement
    MIN_VISIBILITY = 0.5

    # --------------------------------------------------
    # MediaPipe landmark indexes
    # --------------------------------------------------
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

        self.reps = 0
        self.stage = "up"

    # --------------------------------------------------
    # Reset detector
    # --------------------------------------------------
    def reset(self):
        self.reps = 0
        self.stage = "up"

    # --------------------------------------------------
    # Process frame
    # --------------------------------------------------
    def process(self, landmarks):

        # ==================================================
        # 1. Calculate LEFT knee angle
        # ==================================================
        left_knee_angle = self.calculate_angle(
            self.get_point(landmarks, self.LEFT_HIP),
            self.get_point(landmarks, self.LEFT_KNEE),
            self.get_point(landmarks, self.LEFT_ANKLE)
        )

        # ==================================================
        # 2. Calculate RIGHT knee angle
        # ==================================================
        right_knee_angle = self.calculate_angle(
            self.get_point(landmarks, self.RIGHT_HIP),
            self.get_point(landmarks, self.RIGHT_KNEE),
            self.get_point(landmarks, self.RIGHT_ANKLE)
        )

        # ==================================================
        # 3. Get visibility
        # ==================================================
        left_vis = landmarks[self.LEFT_KNEE].visibility
        right_vis = landmarks[self.RIGHT_KNEE].visibility

        # ==================================================
        # 4. Select the side with better knee visibility
        # ==================================================
        if left_vis >= right_vis:

            knee_angle = left_knee_angle

            hip_idx = self.LEFT_HIP
            knee_idx = self.LEFT_KNEE
            ankle_idx = self.LEFT_ANKLE
            shoulder_idx = self.LEFT_SHOULDER

        else:

            knee_angle = right_knee_angle

            hip_idx = self.RIGHT_HIP
            knee_idx = self.RIGHT_KNEE
            ankle_idx = self.RIGHT_ANKLE
            shoulder_idx = self.RIGHT_SHOULDER

        # ==================================================
        # 5. Get visibility of selected landmarks
        # ==================================================
        hip_visibility = landmarks[hip_idx].visibility
        knee_visibility = landmarks[knee_idx].visibility
        ankle_visibility = landmarks[ankle_idx].visibility

        # ==================================================
        # 6. Calculate back angle
        # ==================================================
        back_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, hip_idx),
            self.get_point(landmarks, knee_idx)
        )

        # ==================================================
        # 7. Check visibility
        # ==================================================
        key_landmark_visible = (
            hip_visibility >= self.MIN_VISIBILITY
            and knee_visibility >= self.MIN_VISIBILITY
            and ankle_visibility >= self.MIN_VISIBILITY
        )
        # ==================================================
        # 9. REP COUNTING
        # ==================================================
        if key_landmark_visible:

            # ----------------------------------------------
            # User has gone DOWN
            # ----------------------------------------------
            if knee_angle <= self.DOWN_THRESHOLD:

                self.stage = "down"

            # ----------------------------------------------
            # User has returned UP
            # ----------------------------------------------
            elif (
                knee_angle >= self.UP_THRESHOLD
                and self.stage == "down"
            ):

                self.reps += 1

                self.stage = "up"


        # ==================================================
        # 10. Depth status
        # ==================================================
        if self.stage == "down":

            if knee_angle <= self.DOWN_THRESHOLD:
                depth_status = "GOOD DEPTH"
            else:
                depth_status = "TOO HIGH"

        elif self.stage == "up":

            depth_status = "STANDING"

        else:

            depth_status = "N/A"

        # ==================================================
        # 11. Return metrics
        # ==================================================
        return {
            "reps": self.reps,
            "knee_angle": int(knee_angle),
            "back_angle": int(back_angle),
            "depth_status": depth_status,
            "stage": self.stage
        }