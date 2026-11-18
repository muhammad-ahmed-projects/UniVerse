"""Recognize registered faces vs unknown faces on a camera feed.

Main use, wired to the backend (people are registered from the
dashboard's Registered People page; their face samples are downloaded
from the backend and refreshed every --refresh-seconds, so a newly
registered person is recognized without restarting this script):
    python -m app.ai.prototypes.face_recognition --source 0 --camera-id 1

With --camera-id it also: uses the camera's face-match threshold from the
Settings page, reports each recognized person to the backend (People page
"last seen", at most once per --sighting-cooldown seconds per person),
raises an UNKNOWN_FACE alert with evidence images (at most once per
--alert-cooldown seconds), and streams the annotated feed to Live View.
It needs the ai_service (or an admin) account: face embeddings are
biometric data that operators can't read.

Standalone prototype mode (no backend; faces kept in the gitignored
face_db/embeddings.pkl next to this script, never committed):
    python -m app.ai.prototypes.face_recognition --register --name "Ahmed" --source 0
    python -m app.ai.prototypes.face_recognition --source 0
"""

import argparse
import pickle
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from app.ai.prototypes.backend_client import BackendClient, add_backend_args, build_client

DB_PATH = Path(__file__).parent / "face_db" / "embeddings.pkl"
UNKNOWN = "Unknown"


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


@dataclass
class Match:
    name: str
    person_id: int | None  # None for Unknown, and for local (pickle) registrations
    score: float  # best cosine similarity found, even when below threshold


class FaceIndex:
    """All registered face samples as one matrix, so matching a face is a
    single matrix-vector product instead of a Python loop.

    A person can have several samples (photos from different angles); a face
    matches the person whose *best* sample scores highest, which tolerates
    pose changes better than averaging the samples together.
    """

    def __init__(self, names: list[str], person_ids: list[int | None], embeddings: list[np.ndarray]) -> None:
        self.names = names
        self.person_ids = person_ids
        if embeddings:
            matrix = np.asarray(embeddings, dtype=np.float32)
            # Normalize rows, so the dot product below is the cosine similarity.
            self.matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
        else:
            self.matrix = np.empty((0, 512), dtype=np.float32)

    @classmethod
    def from_backend(cls, rows: list[dict]) -> "FaceIndex":
        return cls(
            [r["name"] for r in rows],
            [r["person_id"] for r in rows],
            [np.asarray(r["embedding"], dtype=np.float32) for r in rows],
        )

    @classmethod
    def from_pickle(cls, db: dict[str, np.ndarray]) -> "FaceIndex":
        return cls(list(db), [None] * len(db), list(db.values()))

    @property
    def people_count(self) -> int:
        return len(set(zip(self.names, self.person_ids, strict=True)))

    def match(self, embedding: np.ndarray, threshold: float) -> Match:
        if len(self.names) == 0:
            return Match(UNKNOWN, None, 0.0)
        query = embedding / np.linalg.norm(embedding)
        scores = self.matrix @ query
        best = int(np.argmax(scores))
        score = float(scores[best])
        if score < threshold:
            return Match(UNKNOWN, None, score)
        return Match(self.names[best], self.person_ids[best], score)


def register(args: argparse.Namespace, app: FaceAnalysis) -> None:
    """Standalone mode only. With the backend, register people from the dashboard."""
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


def load_backend_index(client: BackendClient) -> FaceIndex:
    index = FaceIndex.from_backend(client.get_face_embeddings())
    print(f"Loaded {len(index.names)} face sample(s) for {index.people_count} registered people from the backend")
    return index


def recognize(args: argparse.Namespace, app: FaceAnalysis) -> None:
    client = build_client(args, "face_recognition")
    threshold = args.threshold
    if client is not None:
        threshold = client.get_camera_settings()["face_match_threshold"]
        print(f"Face-match threshold for camera {args.camera_id}: {threshold}")
        try:
            index = load_backend_index(client)
        except PermissionError as exc:
            raise SystemExit(str(exc)) from None
    else:
        index = FaceIndex.from_pickle(load_db())
    if not index.names:
        print("No registered faces yet -- every face will be labeled Unknown.")

    out_dir = Path(args.save_frames) if args.save_frames else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            raise RuntimeError(f"Could not read image: {args.image}")
        _recognize_frame(frame, app, index, threshold)
        if out_dir:
            cv2.imwrite(str(out_dir / "result.png"), frame)
        if not args.headless:
            cv2.imshow("UniVerse - Recognition", frame)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        if client is not None:
            client.close()
        return

    cap = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {args.source}")

    frame_idx = 0
    t_start = time.time()
    last_refresh = time.time()
    last_unknown_alert = float("-inf")
    last_sighting: dict[int, float] = {}
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        now = time.time()

        if client is not None and now - last_refresh >= args.refresh_seconds:
            last_refresh = now
            try:
                index = load_backend_index(client)
            except Exception as exc:  # keep recognizing with the old list if the backend is briefly down
                print(f"Could not refresh registered faces ({exc}); keeping the previous list")

        matches = _recognize_frame(frame, app, index, threshold)

        if client is not None:
            for m in matches:
                if (
                    m.person_id is not None
                    and now - last_sighting.get(m.person_id, float("-inf")) >= args.sighting_cooldown
                ):
                    last_sighting[m.person_id] = now
                    client.report_sighting(m.person_id, m.score)

        # No tracking here, so a cooldown (not per-person state) keeps one
        # lingering unknown face from raising an alert every frame.
        unknown = sum(m.name == UNKNOWN for m in matches)
        if unknown and now - last_unknown_alert >= args.alert_cooldown:
            last_unknown_alert = now
            print(f"[frame {frame_idx}] ALERT: unknown face detected")
            if client is not None:
                client.post_alert(
                    "UNKNOWN_FACE",
                    "medium",
                    "Unregistered person detected",
                    extra_data={"frame": frame_idx, "faces_in_frame": len(matches), "unknown_faces": unknown},
                )

        if client is not None:
            client.publish_frame(frame)
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
    if client is not None:
        client.close()
    if not args.headless:
        cv2.destroyAllWindows()


def _recognize_frame(frame: np.ndarray, app: FaceAnalysis, index: FaceIndex, threshold: float) -> list[Match]:
    """Annotates the frame in place and returns the match for each detected face."""
    matches: list[Match] = []
    for face in app.get(frame):
        m = index.match(face.normed_embedding, threshold)
        matches.append(m)
        x1, y1, x2, y2 = map(int, face.bbox)
        color = (0, 255, 0) if m.name != UNKNOWN else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            f"{m.name} ({m.score:.2f})",
            (x1, max(y1 - 8, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )
    return matches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UniVerse: face recognition (registered vs unknown)")
    parser.add_argument("--source", default="0", help="Webcam index, video file path, or RTSP URL")
    parser.add_argument("--image", default="", help="Run recognition on a single image instead of a video source")
    parser.add_argument("--register", action="store_true", help="Standalone mode: register a face to the local file")
    parser.add_argument("--name", default="", help="Name to register (required with --register)")
    parser.add_argument("--samples", type=int, default=15, help="Number of frames to average when registering")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.45,
        help="Cosine similarity needed for a match (with --camera-id, the camera's Settings value is used)",
    )
    parser.add_argument("--headless", action="store_true", help="Run without a display window (for automated testing)")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0 = unlimited)")
    parser.add_argument("--save-frames", default="", help="Directory to save sample annotated frames")
    parser.add_argument(
        "--frame-sample-every", type=int, default=15, help="Save every Nth frame when --save-frames is set"
    )
    parser.add_argument("--alert-cooldown", type=float, default=30.0, help="Min seconds between UNKNOWN_FACE alerts")
    parser.add_argument(
        "--sighting-cooldown", type=float, default=10.0, help="Min seconds between 'last seen' reports per person"
    )
    parser.add_argument(
        "--refresh-seconds", type=float, default=30.0, help="Re-download registered faces from the backend this often"
    )
    add_backend_args(parser)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.register and not args.name:
        raise SystemExit("--register requires --name")
    if args.register and args.camera_id is not None:
        raise SystemExit("With the backend, register people from the dashboard's Registered People page")
    face_app = load_face_app()
    if args.register:
        register(args, face_app)
    else:
        recognize(args, face_app)
