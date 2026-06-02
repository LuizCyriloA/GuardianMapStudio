from __future__ import annotations

from pathlib import Path

import pytest

from guardianmapstudio.domain.contracts import RoadDirection
from guardianmapstudio.osm.parser import OsmParser, ParsedRoad, ParseResult

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_condominio.osm"


def _osm(ways_xml: str, nodes_xml: str = "") -> bytes:
    """Build a minimal OSM XML document for testing."""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f"<osm version=\"0.6\">{nodes_xml}{ways_xml}</osm>"
    ).encode()


def _two_nodes() -> str:
    return (
        '<node id="1" lat="-23.55" lon="-46.63"/>'
        '<node id="2" lat="-23.56" lon="-46.64"/>'
    )


def _residential_way(
    way_id: int = 100,
    name: str = "Rua A",
    extra_tags: str = "",
    refs: str = '<nd ref="1"/><nd ref="2"/>',
) -> str:
    return (
        f'<way id="{way_id}">'
        f"{refs}"
        f'<tag k="highway" v="residential"/>'
        f'<tag k="name" v="{name}"/>'
        f"{extra_tags}"
        f"</way>"
    )


# ---------------------------------------------------------------------------
# test_parse_empty_osm_returns_zero_roads
# ---------------------------------------------------------------------------


def test_parse_empty_osm_returns_zero_roads() -> None:
    xml = b'<?xml version="1.0"?><osm version="0.6"></osm>'
    result = OsmParser().parse(xml)
    assert isinstance(result, ParseResult)
    assert result.roads == []
    assert result.skipped_ways == 0
    assert result.total_ways_in_file == 0


# ---------------------------------------------------------------------------
# test_parse_one_residential_way_returns_one_road
# ---------------------------------------------------------------------------


def test_parse_one_residential_way_returns_one_road() -> None:
    xml = _osm(_residential_way(), _two_nodes())
    result = OsmParser().parse(xml)
    assert len(result.roads) == 1
    road = result.roads[0]
    assert isinstance(road, ParsedRoad)
    assert road.name == "Rua A"
    assert road.highway_tag == "residential"
    assert len(road.coordinates) == 2


# ---------------------------------------------------------------------------
# test_parse_pedestrian_way_excluded_by_default
# ---------------------------------------------------------------------------


def test_parse_pedestrian_way_excluded_by_default() -> None:
    nodes = _two_nodes()
    way = (
        '<way id="10"><nd ref="1"/><nd ref="2"/>'
        '<tag k="highway" v="footway"/>'
        '<tag k="name" v="Calçada"/>'
        "</way>"
    )
    result = OsmParser().parse(_osm(way, nodes))
    assert result.roads == []
    assert result.skipped_ways == 1
    assert result.skipped_reasons.get("not_drivable", 0) == 1


# ---------------------------------------------------------------------------
# test_parse_pedestrian_way_included_when_flag_set
# ---------------------------------------------------------------------------


def test_parse_pedestrian_way_included_when_flag_set() -> None:
    nodes = _two_nodes()
    way = (
        '<way id="10"><nd ref="1"/><nd ref="2"/>'
        '<tag k="highway" v="footway"/>'
        '<tag k="name" v="Calçada"/>'
        "</way>"
    )
    result = OsmParser().parse(_osm(way, nodes), include_pedestrian=True)
    assert len(result.roads) == 1
    assert result.roads[0].highway_tag == "footway"


# ---------------------------------------------------------------------------
# test_parse_unnamed_way_excluded_by_default
# ---------------------------------------------------------------------------


def test_parse_unnamed_way_excluded_by_default() -> None:
    nodes = _two_nodes()
    way = (
        '<way id="10"><nd ref="1"/><nd ref="2"/>'
        '<tag k="highway" v="residential"/>'
        "</way>"
    )
    result = OsmParser().parse(_osm(way, nodes))
    assert result.roads == []
    assert result.skipped_reasons.get("unnamed", 0) == 1


# ---------------------------------------------------------------------------
# test_parse_unnamed_way_included_with_synthetic_name
# ---------------------------------------------------------------------------


def test_parse_unnamed_way_included_with_synthetic_name() -> None:
    nodes = _two_nodes()
    way = (
        '<way id="10"><nd ref="1"/><nd ref="2"/>'
        '<tag k="highway" v="residential"/>'
        "</way>"
    )
    result = OsmParser().parse(_osm(way, nodes), include_unnamed=True)
    assert len(result.roads) == 1
    road = result.roads[0]
    assert road.had_name is False
    assert road.name == "Sem nome 1"


# ---------------------------------------------------------------------------
# test_parse_way_with_lt_2_nodes_skipped
# ---------------------------------------------------------------------------


def test_parse_way_with_lt_2_nodes_skipped() -> None:
    nodes = '<node id="1" lat="-23.55" lon="-46.63"/>'
    way = (
        '<way id="10"><nd ref="1"/>'
        '<tag k="highway" v="residential"/>'
        '<tag k="name" v="Rua Curta"/>'
        "</way>"
    )
    result = OsmParser().parse(_osm(way, nodes))
    assert result.roads == []
    assert result.skipped_reasons.get("lt_2_points", 0) == 1


# ---------------------------------------------------------------------------
# test_parse_oneway_yes_sets_one_way_direction
# ---------------------------------------------------------------------------


def test_parse_oneway_yes_sets_one_way_direction() -> None:
    xml = _osm(
        _residential_way(extra_tags='<tag k="oneway" v="yes"/>'),
        _two_nodes(),
    )
    result = OsmParser().parse(xml)
    assert result.roads[0].direction == RoadDirection.ONE_WAY


# ---------------------------------------------------------------------------
# test_parse_oneway_missing_defaults_to_two_way
# ---------------------------------------------------------------------------


def test_parse_oneway_missing_defaults_to_two_way() -> None:
    xml = _osm(_residential_way(), _two_nodes())
    result = OsmParser().parse(xml)
    assert result.roads[0].direction == RoadDirection.TWO_WAY


# ---------------------------------------------------------------------------
# test_parse_maxspeed_valid_kmh
# ---------------------------------------------------------------------------


def test_parse_maxspeed_valid_kmh() -> None:
    xml = _osm(
        _residential_way(extra_tags='<tag k="maxspeed" v="40"/>'),
        _two_nodes(),
    )
    result = OsmParser().parse(xml)
    assert result.roads[0].speed_limit_kmh == 40
    assert result.roads[0].osm_warnings == []


# ---------------------------------------------------------------------------
# test_parse_maxspeed_with_mph_unit_falls_back_to_20
# ---------------------------------------------------------------------------


def test_parse_maxspeed_with_mph_unit_falls_back_to_20() -> None:
    # "RU:urban" is a valid OSM shorthand but not a parseable number —
    # first token "RU:urban" fails int(float(...)), so the parser falls back to 20.
    xml = _osm(
        _residential_way(extra_tags='<tag k="maxspeed" v="RU:urban"/>'),
        _two_nodes(),
    )
    result = OsmParser().parse(xml)
    assert result.roads[0].speed_limit_kmh == 20
    assert len(result.roads[0].osm_warnings) == 1


# ---------------------------------------------------------------------------
# test_parse_maxspeed_missing_defaults_to_20
# ---------------------------------------------------------------------------


def test_parse_maxspeed_missing_defaults_to_20() -> None:
    xml = _osm(_residential_way(), _two_nodes())
    result = OsmParser().parse(xml)
    assert result.roads[0].speed_limit_kmh == 20


# ---------------------------------------------------------------------------
# test_parse_width_valid_meters
# ---------------------------------------------------------------------------


def test_parse_width_valid_meters() -> None:
    xml = _osm(
        _residential_way(extra_tags='<tag k="width" v="8.5"/>'),
        _two_nodes(),
    )
    result = OsmParser().parse(xml)
    assert result.roads[0].width_meters == pytest.approx(8.5)
    assert result.roads[0].osm_warnings == []


# ---------------------------------------------------------------------------
# test_parse_width_invalid_falls_back_to_6
# ---------------------------------------------------------------------------


def test_parse_width_invalid_falls_back_to_6() -> None:
    xml = _osm(
        _residential_way(extra_tags='<tag k="width" v="narrow"/>'),
        _two_nodes(),
    )
    result = OsmParser().parse(xml)
    assert result.roads[0].width_meters == pytest.approx(6.0)
    assert len(result.roads[0].osm_warnings) == 1


# ---------------------------------------------------------------------------
# test_parse_malformed_xml_raises_value_error
# ---------------------------------------------------------------------------


def test_parse_malformed_xml_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Malformed OSM XML"):
        OsmParser().parse(b"<this is not valid xml<<<")


# ---------------------------------------------------------------------------
# test_parse_root_not_osm_raises_value_error
# ---------------------------------------------------------------------------


def test_parse_root_not_osm_raises_value_error() -> None:
    with pytest.raises(ValueError, match="expected <osm>"):
        OsmParser().parse(b"<gpx></gpx>")


# ---------------------------------------------------------------------------
# test_parse_node_with_invalid_coordinate_skipped
# ---------------------------------------------------------------------------


def test_parse_node_with_invalid_coordinate_skipped() -> None:
    nodes = (
        '<node id="1" lat="abc" lon="-46.63"/>'  # invalid lat
        '<node id="2" lat="-23.56" lon="-46.64"/>'
        '<node id="3" lat="-23.57" lon="-46.65"/>'
    )
    way = (
        '<way id="10"><nd ref="2"/><nd ref="3"/>'
        '<tag k="highway" v="residential"/>'
        '<tag k="name" v="Rua Válida"/>'
        "</way>"
    )
    result = OsmParser().parse(_osm(way, nodes))
    # node 1 is skipped, but way references 2 and 3 which are valid
    assert len(result.roads) == 1
    assert len(result.roads[0].coordinates) == 2


# ---------------------------------------------------------------------------
# test_parse_way_with_unresolved_node_ref_uses_only_resolved_nodes
# ---------------------------------------------------------------------------


def test_parse_way_with_unresolved_node_ref_uses_only_resolved_nodes() -> None:
    # Node 999 is referenced by the way but not declared
    nodes = (
        '<node id="1" lat="-23.55" lon="-46.63"/>'
        '<node id="2" lat="-23.56" lon="-46.64"/>'
    )
    way = (
        '<way id="10"><nd ref="1"/><nd ref="999"/><nd ref="2"/>'
        '<tag k="highway" v="residential"/>'
        '<tag k="name" v="Rua Parcial"/>'
        "</way>"
    )
    result = OsmParser().parse(_osm(way, nodes))
    assert len(result.roads) == 1
    # Only 2 resolved nodes
    assert len(result.roads[0].coordinates) == 2


# ---------------------------------------------------------------------------
# test_skipped_reasons_aggregated_correctly
# ---------------------------------------------------------------------------


def test_skipped_reasons_aggregated_correctly() -> None:
    # 1 footway + 1 unnamed = 2 skipped, reasons aggregated
    nodes = _two_nodes()
    ways = (
        '<way id="10"><nd ref="1"/><nd ref="2"/>'
        '<tag k="highway" v="footway"/>'
        '<tag k="name" v="Calçada"/>'
        "</way>"
        '<way id="11"><nd ref="1"/><nd ref="2"/>'
        '<tag k="highway" v="residential"/>'
        "</way>"
    )
    result = OsmParser().parse(_osm(ways, nodes))
    assert result.skipped_ways == 2
    assert result.skipped_reasons["not_drivable"] == 1
    assert result.skipped_reasons["unnamed"] == 1


# ---------------------------------------------------------------------------
# test_unicode_road_name_preserved
# ---------------------------------------------------------------------------


def test_unicode_road_name_preserved() -> None:
    fixture_bytes = FIXTURE_PATH.read_bytes()
    result = OsmParser().parse(fixture_bytes)
    names = [r.name for r in result.roads]
    # The fixture has "Avenida São João" — unicode must be preserved
    assert "Avenida São João" in names
