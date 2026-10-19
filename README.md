# UniVerse — AI-Powered General-Purpose Smart Surveillance System

UniVerse is an AI-powered surveillance platform built for organizations — offices, 
warehouses, shops — that processes live/recorded camera feeds to detect and track 
people, recognize registered faces (where authorized), and flag security events such 
as loitering or entry into restricted zones. It also monitors camera health and 
tampering (covered, moved, defocused, or offline cameras), surfacing everything on a 
real-time dashboard with incident management.

## Features
- 🎥 Real-time camera stream processing (OpenCV)
- 🧑‍🤝‍🧑 Multi-person detection & tracking (YOLO + DeepSORT-style MOT)
- 🔐 Face detection & authorized recognition (InsightFace/ArcFace embeddings)
- 🚧 Restricted-area (ROI) and loitering detection
- 📷 Camera tampering detection (covered/moved/defocused)
- 📡 Camera health monitoring (offline, feed loss, power-loss where supported)
- 🚨 Real-time alerting & incident management (acknowledge/resolve workflow)
- 📊 Live dashboard (React/TypeScript + WebSockets)

## Tech Stack
- **Backend:** FastAPI, PostgreSQL, WebSockets
- **Frontend:** React, TypeScript
- **AI/ML:** OpenCV, YOLO (person detection), InsightFace/ArcFace (face recognition), MOT tracking
- **Auth:** Role-based access control (admin / security operator)

## Project Status
Final Year Project (Batch 2026) — Department of Computer Sciences, Iqra University.
Team: Khawaja Shees Uddin, Aiman Shahid, Muhammad Ahmed | Supervisor: Dr. Noman Islam
