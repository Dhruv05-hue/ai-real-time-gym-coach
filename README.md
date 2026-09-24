# 🏋️ AI Real-Time Gym Coach

An AI-powered real-time fitness coaching application that uses **Computer Vision, MediaPipe Pose Estimation, exercise-specific movement analysis, LLM-powered coaching, and Text-to-Speech** to act as an interactive virtual gym trainer.

The application uses a webcam to analyze body movements in real time, automatically count exercise repetitions, monitor workout metrics, detect form issues, track sets, store workout data, and provide dynamic voice coaching during a workout.

---

## ✨ Features

### 🎥 Real-Time Pose Detection

* Uses **MediaPipe Pose Landmarker** to detect human body landmarks.
* Processes webcam frames in real time.
* Tracks body movement while exercising.
* Uses pose visibility and movement thresholds to improve detection reliability.

### 🔢 Automatic Rep Counting

* Automatically counts repetitions during exercises.
* Uses exercise-specific movement states and angle thresholds.
* Synchronizes the latest repetition count with the Streamlit application.
* Detects newly completed repetitions in real time.

### 🏋️ Multiple Exercise Support

The application currently includes exercise-specific detectors for:

* 🦵 Squats
* 💪 Push-Ups
* 💪 Biceps Curls
* 🏋️ Shoulder Press
* 🦵 Lunges

Each detector contains its own movement thresholds and form-analysis logic.

### 📐 Exercise Form Analysis

The system analyzes exercise-specific body movements and metrics to identify potential form problems.

Examples include:

* Incorrect squat depth
* Incorrect push-up movement
* Excessive elbow movement during curls
* Excessive body movement during exercises
* Balance-related issues during lunges
* Pose visibility problems

### 🤖 AI Coaching

The coaching system uses **Groq LLM** to generate contextual workout feedback.

The coaching pipeline can process events such as:

* Workout started
* Repetition completed
* Form issue detected
* Ongoing form check
* No pose detected
* Workout completed

The system is designed to avoid unnecessary coaching messages and focuses on meaningful feedback.

### 🔊 Dynamic Voice Coaching

The application converts coaching feedback into speech using **gTTS**.

The voice pipeline is designed to:

* Provide an introduction when a workout starts.
* Announce selected repetition milestones.
* Give corrective feedback when significant form issues are detected.
* Provide a workout summary when the session ends.
* Avoid continuously speaking after every repetition.
* Prevent large amounts of stale coaching audio from building up.

### 📊 Live Workout Tracking

The application tracks workout information including:

* Current exercise
* Repetitions
* Repetitions per set
* Completed sets
* Current set repetitions
* Workout completion status
* Exercise-specific metrics
* Workout timing

### 💾 Workout Persistence

Workout information is stored locally and can be used to maintain workout history.

The persistence layer separates database operations from the rest of the application.

### 🔐 User Authentication

The application includes a login layer that controls access to the workout interface and maintains user-specific session information.

### 🖥️ Interactive Streamlit Dashboard

The complete application is built using **Streamlit** and includes:

* Login interface
* Exercise selection
* Workout controls
* Live webcam processing
* Workout metrics
* Voice coaching
* Workout completion handling
* Workout history

---

# 🧠 System Architecture

The application follows a modular architecture where computer vision, exercise detection, workout tracking, AI coaching, text-to-speech, persistence, and UI logic are separated into different components.

```text
                        ┌──────────────────┐
                        │      User        │
                        └────────┬─────────┘
                                 │
                                 ▼
                       ┌──────────────────┐
                       │ Streamlit UI     │
                       │ Login / Workout  │
                       └────────┬─────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Webcam / WebRTC  │
                       └────────┬─────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ VideoProcessorClass    │
                    │ Real-Time Processing   │
                    └───────────┬────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ MediaPipe Pose      │
                     │ Landmarks           │
                     └──────────┬──────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ Exercise Detector      │
                    │ Squat / Push-up / Curl │
                    │ Shoulder Press / Lunge │
                    └───────────┬────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
             ┌─────────────┐       ┌────────────────┐
             │ Rep Counter │       │ Form Analysis  │
             └──────┬──────┘       └───────┬────────┘
                    │                       │
                    └───────────┬───────────┘
                                ▼
                     ┌────────────────────┐
                     │ Metrics Tracking   │
                     │ sync_metrics_update│
                     └──────────┬─────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Voice Pipeline   │
                       └────────┬─────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
             ┌─────────────┐       ┌──────────────┐
             │ Groq LLM    │       │ Form Rules   │
             │ AI Coaching │       │ / Events     │
             └──────┬──────┘       └──────┬───────┘
                    │                     │
                    └──────────┬──────────┘
                               ▼
                       ┌────────────────┐
                       │ Text-to-Speech │
                       │     gTTS       │
                       └───────┬────────┘
                               │
                               ▼
                       🔊 Voice Feedback
```

---

# 🔄 Workout Processing Flow

The core workout loop works approximately as follows:

```text
User logs in
     ↓
Select exercise
     ↓
Start workout
     ↓
Webcam starts
     ↓
WebRTC receives video frames
     ↓
VideoProcessorClass processes frames
     ↓
MediaPipe detects pose landmarks
     ↓
Selected exercise detector analyzes movement
     ↓
Exercise metrics are generated
     ↓
Rep count / form metrics updated
     ↓
sync_metrics_update()
     ↓
Streamlit session state updated
     ↓
New repetition detected?
     │
     ├── No ──→ Continue monitoring
     │
     └── Yes
           ↓
     VoicePipeline
           ↓
     Coaching decision
           ↓
     ┌───────────────────────────────┐
     │ Milestone / Form Issue / None │
     └───────────────┬───────────────┘
                     │
                     ▼
               Voice generated
                     ↓
                  gTTS
                     ↓
              Audio queue
                     ↓
              Browser playback
```

---

# 🧩 Project Architecture

The project is organized into separate modules so that each major responsibility can be developed independently.

```text
ai-real-time-gym-coach/
│
├── core/
│   └── base_exercise.py
│
├── detectors/
│   ├── squat.py
│   ├── pushup.py
│   ├── biceps_curl.py
│   ├── shoulder_press.py
│   └── lunges.py
│
├── services/
│   ├── auth/
│   ├── coaching/
│   │   ├── llm.py
│   │   ├── tts.py
│   │   └── voice_pipeline.py
│   │
│   ├── config/
│   │   └── workout_config.py
│   │
│   ├── persistence/
│   │   └── exercise_repository.py
│   │
│   ├── state/
│   │   └── session_defaults.py
│   │
│   ├── tracking/
│   │   └── metrics.py
│   │
│   ├── ui/
│   │   └── style_loader.py
│   │
│   └── vision/
│       └── exercise_video_processor.py
│
├── ml_models/
│   └── pose_landmarker_full.task
│
├── static/
│   └── ...
│
├── main_app_updated.py
├── requirements.txt
├── .gitignore
└── README.md
```

> The exact filenames and structure may vary depending on the current version of the project.

---

# 🛠️ Technologies Used

| Technology           | Purpose                              |
| -------------------- | ------------------------------------ |
| **Python**           | Core programming language            |
| **Streamlit**        | Web application and dashboard        |
| **Streamlit-WebRTC** | Real-time webcam/video streaming     |
| **MediaPipe**        | Pose landmark detection              |
| **OpenCV**           | Computer vision and image processing |
| **NumPy**            | Numerical operations                 |
| **Groq**             | LLM-powered coaching                 |
| **LLaMA**            | AI coaching model                    |
| **gTTS**             | Text-to-speech generation            |
| **SQLite**           | Local workout persistence            |
| **PyAV**             | Video frame processing               |
| **HTML/JavaScript**  | Browser-side audio playback          |

---

# 🚀 Getting Started

## Prerequisites

Before running the application, make sure you have:

* Python 3.11 recommended
* A working webcam
* Git
* Internet connection
* A Groq API key

Python 3.11 is recommended because some computer-vision dependencies used by the project can be sensitive to Python/package versions.

---

## 1. Clone the Repository

```bash
git clone https://github.com/Dhruv05-hue/ai-real-time-gym-coach.git
```

Move into the project directory:

```bash
cd ai-real-time-gym-coach
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Configure the Groq API

The AI coaching component requires a Groq API key.

For local development, use Streamlit secrets or an environment variable according to your configuration.

### Streamlit Secrets

Create:

```text
.streamlit/secrets.toml
```

Add:

```toml
GROQ_API_KEY = "your_groq_api_key_here"
```

### ⚠️ Security

Never commit your actual API key to GitHub.

Make sure files containing secrets are included in `.gitignore`.

---

# ▶️ Run the Application

Start the Streamlit application:

```bash
streamlit run main_app_updated.py
```

Then open:

```text
http://localhost:8501
```

in your browser.

> If your current entry-point filename differs, replace `main_app_updated.py` with the actual main application file.

---

# 🏋️ How to Use

## 1. Login

Log into the application using your registered account.

## 2. Select an Exercise

Choose the exercise you want to perform.

## 3. Configure Your Workout

Set your desired repetitions and sets.

## 4. Start Workout

Click **Start Workout**.

The application initializes the workout and the AI coach provides an introductory voice message.

## 5. Position Yourself

Stand where your webcam can clearly see the required body landmarks.

For best results:

* Keep your body visible.
* Use sufficient lighting.
* Avoid objects blocking your body.
* Keep the camera stable.
* Maintain an appropriate distance from the camera.

## 6. Perform the Exercise

The system continuously:

```text
Camera
   ↓
Pose Detection
   ↓
Landmark Processing
   ↓
Exercise Analysis
   ↓
Rep Counting
   ↓
Form Monitoring
```

## 7. Receive Coaching

The AI coach can provide:

* Rep milestone announcements
* Form corrections
* No-pose warnings
* Workout completion feedback

The current voice architecture intentionally avoids speaking on every repetition.

## 8. Complete the Workout

When the configured workout target is reached, the workout state is marked as completed and the final workout flow can generate a completion message.

---

# 🔊 Voice Coaching Architecture

The voice system is separated into multiple layers:

```text
Workout Event
      ↓
VoicePipeline
      ↓
Coaching Decision
      ↓
LLMCoach / Rule-Based Feedback
      ↓
Text Response
      ↓
TextToSpeech
      ↓
Audio Bytes
      ↓
Audio Queue
      ↓
Browser
      ↓
🔊 Spoken Feedback
```

### Workout Events

The pipeline can process events such as:

```text
workout_started
rep_completed
form_issue
ongoing_form_check
no_pose_detected
workout_completed
```

This event-driven design allows the application to keep video processing and coaching logic separate.

---

# 📈 Rep & Metrics Architecture

The metrics system acts as the bridge between real-time computer vision and the Streamlit application.

```text
VideoProcessorClass
        ↓
get_latest_metrics()
        ↓
sync_metrics_update()
        ↓
Normalize metrics
        ↓
Update session state
        ↓
Detect new repetition
        ↓
Send event to VoicePipeline
```

The system sends every newly detected repetition to the `VoicePipeline`.

The `VoicePipeline` then decides whether the repetition should generate a voice response, such as a configured milestone, or remain silent.

This separation keeps **rep detection** independent from **coaching decisions**.

---

# 🎯 Form Coaching

Form feedback combines exercise-specific detection logic with the coaching pipeline.

The detector identifies movement characteristics and possible issues.

The coaching layer can then convert those issues into user-friendly feedback.

For example:

```text
Exercise Detector
       ↓
Form issue detected
       ↓
VoicePipeline
       ↓
Coaching logic
       ↓
Groq LLM
       ↓
Natural-language feedback
       ↓
gTTS
       ↓
Voice instruction
```

---

# 💾 Workout Data

Workout-related information is handled through the persistence layer.

The application can store information such as:

* User
* Exercise
* Repetitions
* Sets
* Time taken
* Workout history

The persistence layer keeps database operations separate from the UI and computer-vision components.

---

# 🧠 Why This Project Is Technically Interesting

This project combines several AI engineering concepts into one real-time application:

```text
Computer Vision
       +
Pose Estimation
       +
Real-Time Video Processing
       +
Exercise State Logic
       +
Rep Counting
       +
Form Analysis
       +
LLM Integration
       +
Text-to-Speech
       +
Event-Driven Coaching
       +
Database Persistence
       +
Streamlit
```

Rather than simply sending a recorded image or video to an AI model, the application continuously processes webcam frames and converts visual information into structured workout events.

---

# 🏗️ Design Principles

The project separates responsibilities into different layers.

### Vision Layer

Responsible for:

* Webcam frames
* Pose detection
* Landmark extraction
* Exercise movement processing

### Exercise Layer

Responsible for:

* Exercise-specific thresholds
* Rep counting
* Movement states
* Form rules

### Tracking Layer

Responsible for:

* Current metrics
* Rep changes
* Set calculation
* Workout completion state

### Coaching Layer

Responsible for:

* Workout events
* Coaching decisions
* Form feedback
* AI-generated responses

### Voice Layer

Responsible for:

* Text-to-speech
* Audio generation
* Audio queue management
* Browser playback

### Persistence Layer

Responsible for:

* Saving workout information
* Retrieving workout information
* User-specific workout history

### UI Layer

Responsible for:

* Login
* Exercise selection
* Workout controls
* Live metrics
* Dashboard rendering

---

# 🔮 Future Improvements

Potential improvements include:

* [ ] More exercise detectors
* [ ] Improved multi-person handling
* [ ] Advanced temporal movement analysis
* [ ] Personalized workout plans
* [ ] Workout performance analytics
* [ ] Progress charts
* [ ] Exercise difficulty adaptation
* [ ] Calorie estimation
* [ ] Heart-rate integration
* [ ] Cloud-based workout history
* [ ] Mobile application
* [ ] Improved AI personalization
* [ ] More advanced voice interaction
* [ ] Exercise recommendations
* [ ] Gamification and achievements

---

# ⚠️ Limitations

This project is intended as an **AI/computer-vision fitness application and portfolio project**.

The pose detection and form-analysis rules depend on camera position, lighting, visibility of body landmarks, and exercise-specific thresholds.

AI-generated feedback should not be considered medical advice or a substitute for a qualified fitness professional.

---

# 🔐 Security

Do not commit:

* API keys
* `.env` files
* Streamlit secrets
* Local databases containing private user information
* Virtual environments
* Python cache files

Use environment variables or Streamlit secrets for sensitive credentials.

GitHub also provides security features such as secret scanning and push protection that can help prevent credentials from being accidentally committed.

---

# 👨‍💻 Author

## Dhruv Pawar

BSc IT Student | Aspiring AI/ML Engineer

Interested in:

* Artificial Intelligence
* Machine Learning
* Computer Vision
* Deep Learning
* AI Engineering
* Real-Time AI Applications

### GitHub

[@Dhruv05-hue](https://github.com/Dhruv05-hue)

### Project Repository

[ai-real-time-gym-coach](https://github.com/Dhruv05-hue/ai-real-time-gym-coach)

---

# 📜 License

This project is currently intended for educational and portfolio purposes.

If you decide to open-source the project formally, consider adding an appropriate license file to the repository.
