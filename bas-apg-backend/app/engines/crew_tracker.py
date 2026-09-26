"""
Crew Safety & Proximity Tracker
────────────────────────────────
Lightweight Euclidean centroid tracker that assigns persistent IDs to
detected persons and monitors their proximity to hazardous objects.

Designed for Apple Silicon (M4) — uses ZERO extra neural networks.
All tracking is pure math (centroids + Euclidean distance).
"""

import time
import math
from collections import OrderedDict, deque


class CrewMember:
    """Represents a single tracked crew member."""

    __slots__ = (
        "crew_id", "centroid", "bbox", "history",
        "last_seen", "status", "zone_entry_time",
        "immobile_start", "frames_immobile",
    )

    def __init__(self, crew_id: int, centroid: tuple, bbox: tuple):
        self.crew_id = crew_id
        self.centroid = centroid          # (cx, cy)
        self.bbox = bbox                  # (x1, y1, x2, y2)
        self.history: deque = deque(maxlen=60)   # rolling 2-second window @ 30fps
        self.history.append(centroid)
        self.last_seen = time.time()
        self.status = "NOMINAL"           # NOMINAL | WARNING | CRITICAL
        self.zone_entry_time = None       # timestamp when entered hazard zone
        self.immobile_start = None        # timestamp when velocity dropped to ~0
        self.frames_immobile = 0

    @property
    def velocity(self) -> float:
        """Pixel displacement over the last ~1 second of history."""
        if len(self.history) < 10:
            return 999.0  # not enough data, assume moving
        old = self.history[0]
        new = self.history[-1]
        return math.sqrt((new[0] - old[0]) ** 2 + (new[1] - old[1]) ** 2)


class CrewTracker:
    """
    Euclidean centroid-based multi-person tracker.

    - Matches detected 'person' bounding boxes across frames
      by finding the closest centroid from the previous frame.
    - Assigns persistent integer IDs (Crew 1, Crew 2, …).
    - Monitors proximity to hazard objects and immobility.
    - Evicts stale tracks after `max_disappeared` frames.
    """

    def __init__(
        self,
        max_disappeared: int = 30,
        proximity_px: int = 250,
        immobility_threshold_px: float = 8.0,
        immobility_time_s: float = 5.0,
    ):
        self._next_id = 1
        self._members: OrderedDict[int, CrewMember] = OrderedDict()
        self._disappeared: dict[int, int] = {}

        self.max_disappeared = max_disappeared
        self.proximity_px = proximity_px
        self.immobility_threshold_px = immobility_threshold_px
        self.immobility_time_s = immobility_time_s

    # ─── public API ──────────────────────────────────────────────

    def update(self, person_bboxes: list[tuple]) -> list[dict]:
        """
        Accept a list of (x1, y1, x2, y2) bounding boxes for every
        detected person in the current frame.

        Returns a list of crew telemetry dicts ready for the WebSocket.
        """
        input_centroids = []
        for (x1, y1, x2, y2) in person_bboxes:
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            input_centroids.append(((cx, cy), (x1, y1, x2, y2)))

        # ── no detections this frame ─────────────────────────────
        if len(input_centroids) == 0:
            for cid in list(self._disappeared):
                self._disappeared[cid] += 1
                if self._disappeared[cid] > self.max_disappeared:
                    self._deregister(cid)
            return self._build_telemetry()

        # ── no existing tracks → register all ────────────────────
        if len(self._members) == 0:
            for centroid, bbox in input_centroids:
                self._register(centroid, bbox)
            return self._build_telemetry()

        # ── match existing tracks to new detections ──────────────
        existing_ids = list(self._members.keys())
        existing_centroids = [self._members[cid].centroid for cid in existing_ids]

        # Build distance matrix
        D = []
        for ec in existing_centroids:
            row = []
            for (ic, _) in input_centroids:
                row.append(math.sqrt((ec[0] - ic[0]) ** 2 + (ec[1] - ic[1]) ** 2))
            D.append(row)

        # Greedy assignment (simple and crash-proof on M4)
        used_rows = set()
        used_cols = set()
        assignments = []

        # Sort all (row, col) pairs by distance ascending
        pairs = []
        for r in range(len(D)):
            for c in range(len(D[0])):
                pairs.append((D[r][c], r, c))
        pairs.sort()

        for dist, r, c in pairs:
            if r in used_rows or c in used_cols:
                continue
            # Max matching distance — beyond this, it's a new person
            if dist > 300:
                break
            assignments.append((r, c))
            used_rows.add(r)
            used_cols.add(c)

        # Update matched tracks
        for r, c in assignments:
            cid = existing_ids[r]
            centroid, bbox = input_centroids[c]
            member = self._members[cid]
            member.centroid = centroid
            member.bbox = bbox
            member.history.append(centroid)
            member.last_seen = time.time()
            self._disappeared[cid] = 0

        # Unmatched existing tracks → disappeared
        for r in range(len(existing_ids)):
            if r not in used_rows:
                cid = existing_ids[r]
                self._disappeared[cid] += 1
                if self._disappeared[cid] > self.max_disappeared:
                    self._deregister(cid)

        # Unmatched new detections → new crew members
        for c in range(len(input_centroids)):
            if c not in used_cols:
                centroid, bbox = input_centroids[c]
                self._register(centroid, bbox)

        return self._build_telemetry()

    def evaluate_safety(self, hazard_centroids: list[tuple]):
        """
        Given a list of (cx, cy) centroids for hazardous objects,
        evaluate each crew member's proximity and immobility.
        """
        now = time.time()

        for member in self._members.values():
            in_zone = False
            for hx, hy in hazard_centroids:
                dist = math.sqrt(
                    (member.centroid[0] - hx) ** 2 +
                    (member.centroid[1] - hy) ** 2
                )
                if dist < self.proximity_px:
                    in_zone = True
                    break

            if not in_zone:
                # Outside all hazard zones → reset
                member.status = "NOMINAL"
                member.zone_entry_time = None
                member.immobile_start = None
                member.frames_immobile = 0
                continue

            # Inside a hazard zone
            if member.zone_entry_time is None:
                member.zone_entry_time = now

            velocity = member.velocity
            if velocity < self.immobility_threshold_px:
                member.frames_immobile += 1
                if member.immobile_start is None:
                    member.immobile_start = now

                elapsed = now - member.immobile_start
                if elapsed >= self.immobility_time_s:
                    member.status = "CRITICAL"
                else:
                    member.status = "WARNING"
            else:
                # Moving inside the zone — warning only
                member.status = "WARNING"
                member.immobile_start = None
                member.frames_immobile = 0

    # ─── internals ───────────────────────────────────────────────

    def _register(self, centroid: tuple, bbox: tuple):
        cid = self._next_id
        self._members[cid] = CrewMember(cid, centroid, bbox)
        self._disappeared[cid] = 0
        self._next_id += 1

    def _deregister(self, cid: int):
        del self._members[cid]
        del self._disappeared[cid]

    def _build_telemetry(self) -> list[dict]:
        """Build the telemetry payload array for the WebSocket."""
        telemetry = []
        for member in self._members.values():
            telemetry.append({
                "crew_id": member.crew_id,
                "status": member.status,
                "centroid": [round(member.centroid[0], 1), round(member.centroid[1], 1)],
                "bbox": [round(v, 1) for v in member.bbox],
                "velocity_px": round(member.velocity, 1),
                "frames_immobile": member.frames_immobile,
                "zone_entry_time": member.zone_entry_time,
            })
        return telemetry
