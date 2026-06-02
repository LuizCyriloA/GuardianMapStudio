from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from guardianmapstudio.domain.contracts import GeoPoint, Road
from guardianmapstudio.geometry.engine import GeometryEngine

# Two endpoints within this distance (projected meters) are considered
# the same point during merge. Matches CrossroadEngine.INTERSECTION_PROXIMITY_M
# for consistency.
MERGE_JOIN_TOLERANCE_M = 1.0


@dataclass(frozen=True, slots=True)
class MergedPolyline:
    """Output of the merge geometry algorithm.

    coordinates: concatenated polyline in chain order.
    chain_order: ids of input roads in the order they were joined.
    gaps: list of (after_road_id, gap_meters) pairs for joins that
          exceeded MERGE_JOIN_TOLERANCE_M.
    reversed_roads: ids of roads whose coordinate order was reversed
                    to fit the chain (operator may want to verify
                    direction afterwards).
    """
    coordinates: list[GeoPoint]
    chain_order: list[int]
    gaps: list[tuple[int, float]]
    reversed_roads: list[int]


class RoadMergeService:
    """Concatenates multiple Road polylines into a single polyline.

    Uses a greedy nearest-endpoint chain:
      1. Start with the first road's coordinates as the chain.
      2. Repeatedly pick the unjoined road whose endpoint is closest
         to either end of the current chain.
      3. Reverse that road's coordinates if needed so its near endpoint
         touches the chain end.
      4. Append (or prepend) its remaining coordinates to the chain.
      5. If the gap at join time exceeds MERGE_JOIN_TOLERANCE_M, record
         a warning but proceed (avoids leaving operator with a half-merge).
    """

    def __init__(self, geo: GeometryEngine) -> None:
        self._geo = geo

    def merge(self, roads: list[Road]) -> MergedPolyline:
        """Merge the given roads into a single polyline.

        Roads are merged in greedy nearest-endpoint order, regardless
        of the input list order.

        Raises:
            ValueError: if `roads` has fewer than 2 entries or any
                        road has fewer than 2 points.
        """
        if len(roads) < 2:
            raise ValueError("merge() requires at least 2 roads")
        for r in roads:
            if len(r.coordinates) < 2:
                raise ValueError(
                    f"Road {r.id} has fewer than 2 points; cannot merge"
                )

        # Start with the first road
        first = roads[0]
        chain: list[GeoPoint] = list(first.coordinates)
        chain_order: list[int] = [first.id]
        reversed_ids: list[int] = []
        gaps: list[tuple[int, float]] = []

        remaining: dict[int, Road] = {r.id: r for r in roads[1:]}

        while remaining:
            best_id, best_op, best_dist = self._find_best_join(chain, remaining)
            road = remaining.pop(best_id)
            coords = list(road.coordinates)

            if best_op == "append_forward":
                # road.coordinates[0] is near chain[-1]
                if best_dist > 0:
                    chain.append(coords[0])  # join with snap to road start
                chain.extend(coords[1:])
            elif best_op == "append_reverse":
                # road.coordinates[-1] is near chain[-1]; reverse and append
                coords.reverse()
                reversed_ids.append(road.id)
                if best_dist > 0:
                    chain.append(coords[0])
                chain.extend(coords[1:])
            elif best_op == "prepend_forward":
                # road.coordinates[-1] is near chain[0]
                if best_dist > 0:
                    chain.insert(0, coords[-1])
                chain = coords[:-1] + chain
            elif best_op == "prepend_reverse":
                # road.coordinates[0] is near chain[0]; reverse and prepend
                coords.reverse()
                reversed_ids.append(road.id)
                if best_dist > 0:
                    chain.insert(0, coords[-1])
                chain = coords[:-1] + chain

            chain_order.append(road.id)

            if best_dist > MERGE_JOIN_TOLERANCE_M:
                gaps.append((road.id, best_dist))
                logger.warning(
                    "Road merge: joined road {} with gap of {:.2f}m",
                    road.id, best_dist,
                )

        return MergedPolyline(
            coordinates=chain,
            chain_order=chain_order,
            gaps=gaps,
            reversed_roads=reversed_ids,
        )

    def _find_best_join(
        self,
        chain: list[GeoPoint],
        remaining: dict[int, Road],
    ) -> tuple[int, str, float]:
        """Return (road_id, operation, distance_meters) for the best next join.

        Considers four operations per candidate road:
          - append_forward:  chain[-1] ↔ road.coords[0]
          - append_reverse:  chain[-1] ↔ road.coords[-1]
          - prepend_forward: chain[0]  ↔ road.coords[-1]
          - prepend_reverse: chain[0]  ↔ road.coords[0]
        """
        chain_start = chain[0]
        chain_end = chain[-1]
        best: tuple[int, str, float] | None = None

        for rid, road in remaining.items():
            r_start = road.coordinates[0]
            r_end = road.coordinates[-1]
            candidates = [
                (rid, "append_forward",  self._geo.haversine_distance(chain_end, r_start)),
                (rid, "append_reverse",  self._geo.haversine_distance(chain_end, r_end)),
                (rid, "prepend_forward", self._geo.haversine_distance(chain_start, r_end)),
                (rid, "prepend_reverse", self._geo.haversine_distance(chain_start, r_start)),
            ]
            for cand in candidates:
                if best is None or cand[2] < best[2]:
                    best = cand

        assert best is not None  # remaining is non-empty
        return best
