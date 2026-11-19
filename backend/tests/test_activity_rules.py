"""Unusual-activity rules on synthetic tracks (no camera or model needed)."""

from app.ai.prototypes.activity_rules import ActivityRules

W = 1000  # frame width in pixels
STANDING = (100.0, 100.0, 160.0, 300.0)  # 60 wide, 200 tall
LYING = (100.0, 240.0, 300.0, 300.0)  # 200 wide, 60 tall


def rules(**overrides) -> ActivityRules:
    params = {"crowd_threshold": 3, "running_speed": 0.6, "abandoned_seconds": 10, "fall_seconds": 2}
    return ActivityRules(frame_width=W, **(params | overrides))


def kinds(events) -> list[str]:
    return [e.kind for e in events]


def test_crowd_fires_once_per_episode() -> None:
    r = rules()
    people = {i: STANDING for i in range(3)}
    assert kinds(r.update(0, people, {})) == ["CROWD"]
    assert kinds(r.update(1, people, {})) == []  # still the same crowd
    assert kinds(r.update(2, {0: STANDING}, {})) == []  # dispersed
    assert kinds(r.update(3, people, {})) == ["CROWD"]  # a new crowd


def test_walking_is_not_running_but_running_is() -> None:
    r = rules()
    events = []
    for i in range(11):  # walk: 0.2 frame widths per second
        t = i * 0.1
        x = 100 + 0.2 * W * t
        events += r.update(t, {7: (x, 100, x + 60, 300)}, {})
    assert "RUNNING" not in kinds(events)

    events = []
    for i in range(11):  # run: 1.0 frame width per second
        t = 2 + i * 0.1
        x = 100 + 1.0 * W * (t - 2)
        events += r.update(t, {8: (x, 100, x + 60, 300)}, {})
    assert kinds(events).count("RUNNING") == 1
    assert r.person_label(8) == "running"


def test_fall_after_standing() -> None:
    r = rules()
    events = r.update(0, {1: STANDING}, {})
    for t in (0.5, 1.5, 2.6, 3.0):
        events += r.update(t, {1: LYING}, {})
    assert kinds(events) == ["FALL_DETECTED"]
    assert r.person_label(1) == "FALL?"
    # Standing up again resets it.
    r.update(4, {1: STANDING}, {})
    assert r.person_label(1) is None


def test_lying_without_standing_first_is_not_a_fall() -> None:
    r = rules()
    events = []
    for t in range(6):
        events += r.update(t, {2: LYING}, {})  # e.g. someone already on a sofa
    assert "FALL_DETECTED" not in kinds(events)


def test_brief_lying_shape_is_not_a_fall() -> None:
    r = rules()
    events = r.update(0, {3: STANDING}, {})
    events += r.update(0.5, {3: LYING}, {})  # bends down for a moment
    events += r.update(1.0, {3: STANDING}, {})
    assert "FALL_DETECTED" not in kinds(events)


BAG = (500.0, 400.0, 560.0, 460.0)
FAR_PERSON = (100.0, 100.0, 160.0, 300.0)
NEAR_PERSON = (480.0, 250.0, 540.0, 450.0)


def test_abandoned_bag_alerts_once() -> None:
    r = rules()
    events = []
    for t in range(0, 15):
        events += r.update(t, {1: FAR_PERSON}, {50: BAG})
    assert kinds(events) == ["ABANDONED_OBJECT"]
    assert r.bag_label(50) == "unattended"


def test_bag_with_owner_nearby_is_fine() -> None:
    r = rules()
    events = []
    for t in range(0, 30):
        events += r.update(t, {1: NEAR_PERSON}, {50: BAG})
    assert events == []


def test_moving_bag_restarts_the_timer() -> None:
    r = rules()
    events = []
    for t in range(0, 30):
        x = 500 + (t % 2) * 100  # carried back and forth
        events += r.update(t, {}, {50: (x, 400, x + 60, 460)})
    assert events == []


def test_zero_turns_rules_off() -> None:
    r = rules(crowd_threshold=0, running_speed=0, abandoned_seconds=0, fall_seconds=0)
    events = []
    for i in range(30):
        t = i * 0.1
        x = 100 + W * t
        box = STANDING if i < 5 else LYING
        events += r.update(t, {k: (x, box[1], x + box[2] - box[0], box[3]) for k in range(6)}, {50: BAG})
    assert events == []
