from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from loguru import logger

from guardianmapstudio.domain.contracts import GeoPoint, RoadDirection

# OSM highway tag values that produce a Road in GuardianMapStudio.
# Pedestrian-only ways are excluded by default but can be opted-in via the
# include_pedestrian flag in OsmParser.parse().
DRIVABLE_HIGHWAY_TAGS: frozenset[str] = frozenset({
    "residential", "service", "unclassified", "living_street",
    "tertiary", "secondary", "primary", "trunk",
    "tertiary_link", "secondary_link", "primary_link", "trunk_link",
})

PEDESTRIAN_HIGHWAY_TAGS: frozenset[str] = frozenset({
    "footway", "path", "cycleway", "pedestrian", "track", "steps",
})


@dataclass(frozen=True, slots=True)
class ParsedRoad:
    """A single road extracted from an OSM XML file.

    This is the parser's output contract — independent of the database.
    The importer (see importer.py) converts these to Road records via MapRepository.
    """
    osm_way_id: int                # OSM way id, for traceability
    name: str                      # never empty (synthetic name if OSM had none)
    coordinates: list[GeoPoint]    # >= 2 points; in OSM way node order
    direction: RoadDirection       # derived from oneway tag
    speed_limit_kmh: int           # 20 if maxspeed missing or invalid
    width_meters: float            # 6.0 if width missing or invalid
    highway_tag: str               # e.g. "residential" — for UI display
    had_name: bool                 # False if name was synthesized
    osm_warnings: list[str]        # e.g. "maxspeed not parseable"


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Outcome of parsing an OSM XML file."""
    roads: list[ParsedRoad]
    skipped_ways: int              # ways present in XML but excluded
    skipped_reasons: dict[str, int]  # {"not_drivable": 12, "no_nodes": 1, ...}
    total_ways_in_file: int


class OsmParser:
    """Parses OpenStreetMap XML exports into ParsedRoad objects.

    Usage:
        parser = OsmParser()
        result = parser.parse(xml_bytes, include_pedestrian=False,
                              include_unnamed=False)
    """

    def parse(
        self,
        xml_bytes: bytes,
        *,
        include_pedestrian: bool = False,
        include_unnamed: bool = False,
    ) -> ParseResult:
        """Parse an OSM XML payload.

        Raises:
            ValueError: if the XML is malformed or not an OSM document.
        """
        try:
            root = ET.fromstring(xml_bytes)  # noqa: S314 — file-size limit mitigates XML injection risk
        except ET.ParseError as e:
            raise ValueError(f"Malformed OSM XML: {e}") from e

        if root.tag != "osm":
            raise ValueError(
                f"Root element is <{root.tag}>, expected <osm>"
            )

        nodes: dict[int, GeoPoint] = self._index_nodes(root)
        roads, skipped, reasons = self._extract_ways(
            root, nodes,
            include_pedestrian=include_pedestrian,
            include_unnamed=include_unnamed,
        )

        total_ways = len(root.findall("way"))
        logger.info(
            "OSM parse complete: {} roads, {} ways skipped (of {} total)",
            len(roads), skipped, total_ways,
        )
        return ParseResult(
            roads=roads,
            skipped_ways=skipped,
            skipped_reasons=reasons,
            total_ways_in_file=total_ways,
        )

    # --- internals ---

    @staticmethod
    def _index_nodes(root: ET.Element) -> dict[int, GeoPoint]:
        """Build {node_id: GeoPoint} from all <node> elements."""
        index: dict[int, GeoPoint] = {}
        for node in root.findall("node"):
            try:
                nid = int(node.get("id", ""))
                lat = float(node.get("lat", ""))
                lng = float(node.get("lon", ""))
                # GeoPoint.__post_init__ raises on out-of-range coords
                index[nid] = GeoPoint(latitude=lat, longitude=lng)
            except (ValueError, TypeError):
                continue
        return index

    def _extract_ways(
        self,
        root: ET.Element,
        nodes: dict[int, GeoPoint],
        *,
        include_pedestrian: bool,
        include_unnamed: bool,
    ) -> tuple[list[ParsedRoad], int, dict[str, int]]:
        roads: list[ParsedRoad] = []
        skipped = 0
        reasons: dict[str, int] = {}

        unnamed_counter = 0

        for way in root.findall("way"):
            way_id_str = way.get("id", "0")
            try:
                way_id = int(way_id_str)
            except ValueError:
                skipped += 1
                reasons["bad_way_id"] = reasons.get("bad_way_id", 0) + 1
                continue

            tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
            highway = tags.get("highway")

            # Filter: must be a highway tag
            if not highway:
                skipped += 1
                reasons["not_highway"] = reasons.get("not_highway", 0) + 1
                continue

            # Filter: drivable vs pedestrian
            if highway in DRIVABLE_HIGHWAY_TAGS:
                pass  # accept
            elif highway in PEDESTRIAN_HIGHWAY_TAGS and include_pedestrian:
                pass  # accept
            else:
                skipped += 1
                reasons["not_drivable"] = reasons.get("not_drivable", 0) + 1
                continue

            # Resolve node references
            coords: list[GeoPoint] = []
            for nd in way.findall("nd"):
                ref_str = nd.get("ref", "")
                try:
                    ref = int(ref_str)
                except ValueError:
                    continue
                point = nodes.get(ref)
                if point is not None:
                    coords.append(point)

            if len(coords) < 2:
                skipped += 1
                reasons["lt_2_points"] = reasons.get("lt_2_points", 0) + 1
                continue

            # Name handling
            name = (tags.get("name") or "").strip()
            had_name = bool(name)
            if not had_name:
                if not include_unnamed:
                    skipped += 1
                    reasons["unnamed"] = reasons.get("unnamed", 0) + 1
                    continue
                unnamed_counter += 1
                name = f"Sem nome {unnamed_counter}"

            # Direction
            oneway = (tags.get("oneway") or "").lower()
            direction = (RoadDirection.ONE_WAY
                         if oneway in ("yes", "true", "1", "-1")
                         else RoadDirection.TWO_WAY)
            # Note: oneway=-1 means reverse direction. For MVP we treat it
            # as one_way and trust the operator to verify direction.

            # Speed limit (best-effort)
            warnings: list[str] = []
            speed_limit, sw = self._parse_maxspeed(tags.get("maxspeed"))
            if sw:
                warnings.append(sw)

            # Width (best-effort)
            width, ww = self._parse_width(tags.get("width"))
            if ww:
                warnings.append(ww)

            roads.append(ParsedRoad(
                osm_way_id=way_id,
                name=name,
                coordinates=coords,
                direction=direction,
                speed_limit_kmh=speed_limit,
                width_meters=width,
                highway_tag=highway,
                had_name=had_name,
                osm_warnings=warnings,
            ))

        return roads, skipped, reasons

    @staticmethod
    def _parse_maxspeed(value: str | None) -> tuple[int, str | None]:
        """Parse OSM maxspeed tag. Returns (kmh, warning_or_none).

        Defaults to 20 km/h (condominium standard) if missing or unparseable.
        """
        if not value:
            return 20, None
        # OSM allows "30", "30 mph", "RU:urban", etc. We accept only plain numbers.
        try:
            cleaned = value.split()[0]
            kmh = int(float(cleaned))
            if kmh <= 0 or kmh > 200:
                return 20, f"maxspeed '{value}' out of range; using 20"
            return kmh, None
        except (ValueError, IndexError):
            return 20, f"maxspeed '{value}' not parseable; using 20"

    @staticmethod
    def _parse_width(value: str | None) -> tuple[float, str | None]:
        """Parse OSM width tag (meters). Defaults to 6.0."""
        if not value:
            return 6.0, None
        try:
            cleaned = value.split()[0].replace(",", ".")
            meters = float(cleaned)
            if meters <= 0 or meters > 50:
                return 6.0, f"width '{value}' out of range; using 6.0"
            return meters, None
        except (ValueError, IndexError):
            return 6.0, f"width '{value}' not parseable; using 6.0"
