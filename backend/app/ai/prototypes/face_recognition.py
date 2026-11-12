"""Phase 1 prototype: register faces -> recognize known vs unknown on webcam.

Standalone script, not yet wired into the FastAPI backend.

Register a person (averages embeddings over a few captured frames):
    python -m app.ai.prototypes.face_recognition --register --name "Ahmed" --source 0

Run recognition against everyone registered so far:
    python -m app.ai.prototypes.face_recognition --source 0

Face embeddings are biometric data -> stored only in the gitignored
`face_db/` directory next to this script, never committed.
"""
import argparse
import pickle
import time
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis

DB_PATH = Path(__file__).parent / "face_db" / "embeddings.pkl"


def load_face_app() -> FaceAnalysis:
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
    return app


def load_db() -> dict[str, np.ndarray]:
    if not DB_PATH.exists():
        return {}
    with open(DB_PATH, "rb") as f:
        return pickle.load(f)


def save_db(db: dict[str, np.ndarray]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DB_PATH, "wb") as f:
        pickle.dump(db, f)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def match_face(embedding: np.ndarray, db: dict[str, np.ndarray], threshold: float) -> tuple[str, float]:
    best_name, best_score = "Unknown", 0.0
    for name, ref_embedding in db.items():
        score = cosine_similarity(embedding, ref_embedding)
        if score > best_score:
            best_name, best_score = name, score
    if best_score < threshold:
        return "Unknown", best_score
    return best_name, best_score


def register(args: argparse.Namespace, app: FaceAnalysis) -> None:
    cap = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {args.source}")

    embeddings = []
    captured = 0
    while captured < args.samples:
        ok, frame = cap.read()
        if not ok:
            break
        faces = app.get(frame)
        if len(faces) == 1:
            embeddings.append(faces[0].normed_embedding)
            captured += 1
        if not args.headless:
            cv2.imshow("UniVerse - Registering", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    cap.release()
    if not args.headless:
        cv2.destroyAllWindows()

    if not embeddings:
        raise RuntimeError("No face captured -- make sure exactly one face is visible to the camera.")

    avg_embedding = np.mean(embeddings, axis=0)
    db = load_db()
    db[args.name] = avg_embedding
    save_db(db)
    print(f"Registered '{args.name}' from {len(embeddings)} sample(s). DB now has: {list(db.keys())}")


def recognize(args: argparse.Namespace, app: FaceAnalysis) -> None:
    db = load_db()
    if not db:
        print("No registered faces yet -- run with --register --name <name> first.")

    out_dir = Path(args.save_frames) if args.save_frames else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            raise RuntimeError(f"Could not read image: {args.image}")
        _recognize_frame(frame, app, db, args.threshold)
        if out_dir:
            cv2.imwrite(str(out_dir / "result.png"), frame)
        if not args.headless:
            cv2.imshow("UniVerse - Recognition", frame)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return

    cap = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {args.source}")

    frame_idx = 0
    t_start = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        _recognize_frame(frame, app, db, args.threshold)
        if out_dir and frame_idx % args.frame_sample_every == 0:
            cv2.imwrite(str(out_dir / f"frame_{frame_idx:04d}.png"), frame)
        if not args.headless:
            cv2.imshow("UniVerse - Recognition", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        frame_idx += 1
        if args.max_frames and frame_idx >= args.max_frames:
            break
    elapsed = max(time.time() - t_start, 1e-6)
    print(f"Processed {frame_idx} frames in {elapsed:.1f}s (avg FPS: {frame_idx / elapsed:.1f})")
    cap.release()
    if not args.headless:
        cv2.destroyAllWindows()


def _recognize_frame(frame, app: FaceAnalysis, db: dict[str, np.ndarray], threshold: float) -> None:
    faces = app.get(frame)
    for face in faces:
        name, score = match_face(face.normed_embedding, db, threshold)
        x1, y1, x2, y2 = map(int, face.bbox)
        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame, f"{name} ({score:.2f})", (x1, max(y1 - 8, 0)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UniVerse Phase 1: face recognition prototype")
    parser.add_argument("--source", default="0", help="Webcam index or video file path")
    parser.add_argument("--image", default="", help="Run recognition on a single image instead of a video source")
    parser.add_argument("--register", action="store_true", help="Register a new face instead of recognizing")
    parser.add_argument("--name", default="", help="Name to register (required with --register)")
    parser.add_argument("--samples", type=int, default=15, help="Number of frames to average when registering")
    parser.add_argument("--threshold", type=float, default=0.45, help="Cosine similarity threshold for a match")
    parser.add_argument("--headless", action="store_true", help="Run without a display window (for automated testing)")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0 = unlimited)")
    parser.add_argument("--save-frames", default="", help="Directory to save sample annotated frames")
    parser.add_argument("--frame-sample-every", type=int, default=15, help="Save every Nth frame when --save-frames is set")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.register and not args.name:
        raise SystemExit("--register requires --name")
    face_app = load_face_app()
    if args.register:
        register(args, face_app)
    else:
        recognize(args, face_app)
