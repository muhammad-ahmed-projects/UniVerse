"""Unusual-activity rules over tracked detections (no model of their own).

Fed once per frame with YOLO + ByteTrack output (people and bags), these
turn movement over time into events:

- CROWD:            at least `crowd_threshold` people in view.
- RUNNING:          a person's centre moves faster than `running_speed`
                    frame-widths per second (measured over ~1 s).
- FALL_DETECTED:    a person who was standing (box clearly taller than
                    wide) has a lying-down box (clearly wider than tall)
                    for `fall_seconds`. A shape heuristic, not a pose model,
                    so it runs on a CPU; it can be fooled by someone
                    crouching side-on, which is why alerts go to a human.
- ABANDONED_OBJECT: a bag/suitcase that hasn't moved for
                    `abandoned_seconds` with no person near it.

Each rule fires once per transition (per track, or per crowd episode), not
every frame. A threshold of 0 turns that rule off. All positions are in
pixels; distances are compared as fractions of the frame width so the
same settings work at any resolution.
"""

from collections import deque
from dataclasses import dataclass, field

Box = tuple[float, float, float, float]  # x1, y1, x2, y2

# Box shape ratios: a standing person is much taller than wide; lying down is wider than tall.
STANDING_HEIGHT_RATIO = 1.3  # h > 1.3 * w
LYING_WIDTH_RATIO = 1.2  # w > 1.2 * h
# How recently the person must have been standing for a lying box to count as a fall.
FALL_STANDING_WINDOW_SECONDS = 3.0
RUN_WINDOW_SECONDS = 1.0
# A bag "hasn't moved" if its centre stays within this fraction of the frame width.
STILL_TOLERANCE = 0.02
# Nobody "near" a bag: no person centre within this fraction of the frame width.
OWNER_DISTANCE = 0.15
# A crowd episode ends when the count drops this far below the threshold (hysteresis,
# so a count hovering at the threshold doesn't re-fire every few frames).
CROWD_HYSTERESIS = 1


@dataclass
class Event:
    kind: str  # CROWD | RUNNING | FALL_DETECTED | ABANDONED_OBJECT
    track_id: int | None
    message: str
    extra: dict = field(default_factory=dict)


@dataclass
class _PersonState:
    history: deque = field(default_factory=lambda: deque(maxlen=64))  # (t, cx, cy)
    last_standing: float | None = None
    lying_since: float | None = None
    fell: bool = False
    running: bool = False


@dataclass
class _BagState:
    anchor: tuple[float, float]
    still_since: float
    alone_since: float | None = None
    alerted: bool = False


def _center(box: Box) -> tuple[float, float]:
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


class ActivityRules:
    def __init__(
        self,
        frame_width: int,
        crowd_threshold: int,
        running_speed: float,
        abandoned_seconds: float,
        fall_seconds: float,
    ) -> None:
        self.frame_width = max(frame_width, 1)
        self.crowd_threshold = crowd_threshold
        self.running_speed = running_speed
        self.abandoned_seconds = abandoned_seconds
        self.fall_seconds = fall_seconds
        self.people: dict[int, _PersonState] = {}
        self.bags: dict[int, _BagState] = {}
        self.in_crowd = False

    # Labels the caller can draw next to a track's box.
    def person_label(self, track_id: int) -> str | None:
        state = self.people.get(track_id)
        if state is None:
            return None
        if state.fell:
            return "FALL?"
        if state.running:
            return "running"
        return None

    def bag_label(self, track_id: int) -> str | None:
        state = self.bags.get(track_id)
        return "unattended" if state and state.alerted else None

    def update(self, now: float, people: dict[int, Box], bags: dict[int, Box]) -> list[Event]:
        events: list[Event] = []
        events += self._crowd(len(people))
        for tid, box in people.items():
            events += self._person(now, tid, box)
        events += self._bags(now, people, bags)
        # Forget tracks that left the view, so state doesn't grow forever.
        for tid in list(self.people):
            if tid not in people and now - self.people[tid].history[-1][0] > 10:
                del self.people[tid]
        for tid in list(self.bags):
            if tid not in bags:
                del self.bags[tid]
        return events

    def _crowd(self, count: int) -> list[Event]:
        if self.crowd_threshold <= 0:
            return []
        if not self.in_crowd and count >= self.crowd_threshold:
            self.in_crowd = True
            return [Event("CROWD", None, f"Crowd: {count} people in view", {"people": count})]
        if self.in_crowd and count <= self.crowd_threshold - 1 - CROWD_HYSTERESIS:
            self.in_crowd = False
        return []

    def _person(self, now: float, tid: int, box: Box) -> list[Event]:
        events: list[Event] = []
        state = self.people.setdefault(tid, _PersonState())
        cx, cy = _center(box)
        state.history.append((now, cx, cy))
        w, h = box[2] - box[0], box[3] - box[1]

        # Running: distance covered over the last ~second.
        if self.running_speed > 0:
            old = next((p for p in state.history if now - p[0] <= RUN_WINDOW_SECONDS), None)
            if old is not None and now - old[0] >= 0.5:
                dist = ((cx - old[1]) ** 2 + (cy - old[2]) ** 2) ** 0.5
                speed = dist / self.frame_width / (now - old[0])
                is_running = speed >= self.running_speed
                if is_running and not state.running:
                    events.append(Event("RUNNING", tid, f"Person (track {tid}) running", {"speed": round(speed, 2)}))
                state.running = is_running

        # Fall: standing recently, then lying-down shaped for fall_seconds.
        if self.fall_seconds > 0 and w > 0 and h > 0:
            if h > STANDING_HEIGHT_RATIO * w:
                state.last_standing = now
                state.lying_since = None
                state.fell = False
            elif w > LYING_WIDTH_RATIO * h:
                if state.lying_since is None:
                    recently_standing = (
                        state.last_standing is not None and now - state.last_standing <= FALL_STANDING_WINDOW_SECONDS
                    )
                    state.lying_since = now if recently_standing else None
                if state.lying_since is not None and not state.fell and now - state.lying_since >= self.fall_seconds:
                    state.fell = True
                    events.append(Event("FALL_DETECTED", tid, f"Person (track {tid}) may have fallen"))
        return events

    def _bags(self, now: float, people: dict[int, Box], bags: dict[int, Box]) -> list[Event]:
        if self.abandoned_seconds <= 0:
            return []
        events: list[Event] = []
        person_centres = [_center(b) for b in people.values()]
        tolerance = STILL_TOLERANCE * self.frame_width
        near = OWNER_DISTANCE * self.frame_width
        for tid, box in bags.items():
            cx, cy = _center(box)
            state = self.bags.get(tid)
            if state is None:
                self.bags[tid] = _BagState(anchor=(cx, cy), still_since=now)
                continue
            if abs(cx - state.anchor[0]) > tolerance or abs(cy - state.anchor[1]) > tolerance:
                # Moved: someone has it. Start over from here.
                self.bags[tid] = _BagState(anchor=(cx, cy), still_since=now)
                continue
            owner_near = any(((cx - px) ** 2 + (cy - py) ** 2) ** 0.5 <= near for px, py in person_centres)
            if owner_near:
                state.alone_since = None
                continue
            if state.alone_since is None:
                state.alone_since = now
            unattended = min(now - state.still_since, now - state.alone_since)
            if not state.alerted and unattended >= self.abandoned_seconds:
                state.alerted = True
                events.append(
                    Event(
                        "ABANDONED_OBJECT",
                        tid,
                        f"Unattended object (track {tid}) for {unattended:.0f}s",
                        {"seconds": round(unattended, 1)},
                    )
                )
        return events
