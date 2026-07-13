# 🚨 Smart Crowd Panic Detection System using YOLOv8 & Deep Learning

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLO-v8-111827?style=for-the-badge)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![Computer Vision](https://img.shields.io/badge/Computer-Vision-success?style=for-the-badge)
![Deep Learning](https://img.shields.io/badge/Deep-Learning-blue?style=for-the-badge)

# 🎯 AI-Powered Real-Time Crowd Panic Detection System

Automatically detects abnormal crowd behavior using YOLOv8 and Computer Vision. The system analyzes video streams, estimates crowd movement, detects panic situations, triggers alerts, and assists authorities in responding quickly to emergencies.

</div>

---

# 📖 Table of Contents

- Overview
- Problem Statement
- Features
- Solution
- Workflow
- Project Architecture
- Project Structure
- Technologies Used
- AI Model
- Installation
- Usage
- Output
- Future Enhancements
- Applications
- Author

---

# 📌 Overview

The **Smart Crowd Panic Detection System** is an Artificial Intelligence based surveillance application designed to monitor crowded environments and detect panic situations in real time.

Using **YOLOv8**, **OpenCV**, and **Python**, the system detects people from live video or CCTV footage, analyzes crowd behavior, identifies sudden abnormal movement, and generates alerts whenever panic conditions are detected.

The goal is to reduce response time during emergencies and improve public safety in crowded places.

---

# ❗ Problem Statement

Large public gatherings such as railway stations, stadiums, shopping malls, airports, and concerts are vulnerable to sudden panic situations.

Traditional CCTV monitoring relies heavily on human operators, making it difficult to continuously monitor every camera and detect emergencies immediately.

An automated AI-powered monitoring system can recognize abnormal crowd behavior much faster and notify authorities instantly.

---

# ✨ Features

- 🎥 Real-time video monitoring
- 👥 YOLOv8 human detection
- 📈 Crowd density estimation
- 🏃 Crowd movement analysis
- 🚨 Panic detection
- 🔔 Automatic alarm triggering
- 📝 Event logging
- 📊 Live dashboard visualization
- ⚡ Fast inference using Deep Learning
- 💻 Simple and lightweight implementation

---

# 💡 Proposed Solution

The application continuously processes video frames and performs the following operations:

- Detects every person using YOLOv8.
- Counts the number of people in each frame.
- Estimates crowd density.
- Monitors sudden crowd movement.
- Detects panic situations based on abnormal movement.
- Displays visual alerts.
- Plays alarm sounds.
- Generates logs for future analysis.

---

# 🔄 Workflow

```text
Video Input
      │
      ▼
Frame Extraction
      │
      ▼
YOLOv8 Person Detection
      │
      ▼
Crowd Density Estimation
      │
      ▼
Movement Analysis
      │
      ▼
Panic Detection
      │
      ▼
Alert Generation
      │
      ▼
Alarm + Event Logging
```

---

# 🏗 System Architecture

```text
                     Video Input
                          │
                          ▼
                  OpenCV Frame Capture
                          │
                          ▼
                 YOLOv8 Person Detection
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
   Crowd Density                  Motion Analysis
          │                               │
          └───────────────┬───────────────┘
                          ▼
                 Panic Detection Engine
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
      Alarm System                 Event Logging
                          │
                          ▼
                  Monitoring Dashboard
```

---

# 📁 Project Structure

```text
CrowdPanic/
│
├── app.py
├── crowd_dashboard.html
├── yolov8n.pt
├── README.md
└── .gitignore
```

> **Note:** During execution, the application automatically creates runtime files and folders such as logs, cached files, output videos, and other temporary data. These files are intentionally excluded from Git using `.gitignore`.

---

# 🛠 Technologies Used

| Technology | Purpose |
|------------|---------|
| Python | Core Programming Language |
| YOLOv8 | Human Detection |
| OpenCV | Image & Video Processing |
| PyTorch | Deep Learning Framework |
| NumPy | Numerical Operations |
| HTML | Dashboard Interface |

---

# 🤖 AI Model

### Model Used

**YOLOv8 (Ultralytics)**

The application uses the YOLOv8 object detection model for fast and accurate human detection.

### Responsibilities

- Person Detection
- Bounding Box Generation
- Crowd Counting
- Real-Time Detection
- Crowd Analysis
- Panic Detection Support

---

# ⚙ Installation

Clone the repository

```bash
git clone https://github.com/Hari-preetham-B/crowdPanic.git
```

Navigate into the project

```bash
cd crowdPanic
```

Install dependencies

```bash
pip install ultralytics opencv-python numpy
```

---

# ▶ Usage

Run the application

```bash
python app.py
```

The application will automatically:

- Load the YOLOv8 model
- Read the input video or camera feed
- Detect people
- Analyze crowd density
- Detect panic situations
- Trigger alerts
- Generate logs
- Display the monitoring dashboard

---

# 📊 Sample Output

The system provides:

- Live video feed
- Human detection bounding boxes
- Crowd count
- Crowd density status
- Panic alerts
- Alarm notifications
- Event logs

Example Alert

```text
⚠ WARNING

PANIC DETECTED

High Crowd Movement Detected

Alarm Activated

Event Logged Successfully
```

---

# 📈 Performance

| Feature | Status |
|---------|--------|
| Real-Time Detection | ✅ |
| YOLOv8 Human Detection | ✅ |
| Crowd Density Analysis | ✅ |
| Panic Detection | ✅ |
| Event Logging | ✅ |
| Alarm Generation | ✅ |
| Dashboard Interface | ✅ |
| Python Implementation | ✅ |

---

# 🚀 Future Enhancements

- Multi-camera surveillance
- Live CCTV integration
- Crowd heatmap visualization
- DeepSORT object tracking
- Fire and smoke detection
- Violence detection
- Cloud deployment
- Web dashboard
- SMS & Email alert system
- Mobile application
- AI analytics dashboard
- Emergency service integration

---

# 🌍 Applications

- Railway Stations
- Airports
- Metro Stations
- Shopping Malls
- Stadiums
- Concerts
- Public Events
- Smart Cities
- Educational Institutions
- Government Surveillance
- Industrial Facilities
- Disaster Management Centers

---

# 👨‍💻 Author

## Bade Hari Preetham

**Artificial Intelligence & Machine Learning Engineering**

### Skills

- Artificial Intelligence
- Computer Vision
- Deep Learning
- YOLOv8
- OpenCV
- Python
- Machine Learning

---

<div align="center">

## ⭐ Star this repository if you found it useful!

### Smart Crowd Panic Detection System

**Built using Artificial Intelligence, Computer Vision, YOLOv8, OpenCV, and Python**

</div>
