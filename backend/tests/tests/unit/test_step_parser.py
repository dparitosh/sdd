from __future__ import annotations

from pathlib import Path

import pytest

from src.parsers.step_parser import detect_step_format, iter_part21_entities, iter_stepx_refs, parse_step_metadata


def test_detect_step_format_sniffs_part21(tmp_path: Path) -> None:
    p = tmp_path / "sample.unknown"
    p.write_text("ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n")
    assert detect_step_format(p) == "p21"


def test_parse_step_metadata_part21_extracts_schema_and_filename(tmp_path: Path) -> None:
    p = tmp_path / "a.stp"
    p.write_text(
        """ISO-10303-21;
HEADER;
FILE_NAME('demo.stp','2026-01-01T00:00:00',('a'),('b'),'c','d','e');
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));
ENDSEC;
DATA;
#1=PRODUCT('P1','name','desc',(#999));
#2=PRODUCT_DEFINITION('id','desc',#1,#3);
#3=PRODUCT_DEFINITION_CONTEXT('part definition',#10,'design');
#10=APPLICATION_CONTEXT('dummy');
ENDSEC;
END-ISO-10303-21;
"""
    )

    meta = parse_step_metadata(p)
    assert meta.format == "p21"
    assert meta.file_schema == "AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF"
    assert meta.file_name == "demo.stp"


def test_iter_part21_entities_extracts_refs_and_ignores_refs_in_strings(tmp_path: Path) -> None:
    p = tmp_path / "b.step"
    p.write_text(
        """ISO-10303-21;
HEADER;
FILE_SCHEMA(('AP242'));
ENDSEC;
DATA;
#1=APPLICATION_CONTEXT('contains #999 but should not be a ref');
#2=PRODUCT_DEFINITION('id','desc',#1,#3);
#3=PRODUCT_DEFINITION_CONTEXT('ctx',#10,'design');
#10=APPLICATION_CONTEXT('dummy');
ENDSEC;
END-ISO-10303-21;
"""
    )

    entities = list(iter_part21_entities(p))
    by_id = {e.step_id: e for e in entities}

    assert set(by_id.keys()) == {1, 2, 3, 10}

    # #1 has a '#999' in a quoted string; it should not be treated as a reference.
    assert by_id[1].ref_ids == ()

    assert by_id[2].ref_ids == (1, 3)
    assert by_id[3].ref_ids == (10,)
    assert by_id[10].ref_ids == ()


def test_iter_stepx_refs_best_effort(tmp_path: Path) -> None:
    p = tmp_path / "c.stpx"
    p.write_text(
        """<?xml version='1.0' encoding='utf-8'?>
<iso_10303_28 id='root'>
  <item id='i1' ref='i2' someOther='x' />
  <item id='i2' ownerRef='i3' />
  <item id='i3' />
</iso_10303_28>
"""
    )

    refs = list(iter_stepx_refs(p))
    assert ("i1", "ref", "i2") in refs
    assert ("i2", "ownerRef", "i3") in refs


@pytest.mark.parametrize("ext", [".stp", ".step", ".stpx"])
def test_detect_step_format_by_extension(tmp_path: Path, ext: str) -> None:
    p = tmp_path / ("file" + ext)
    p.write_text("dummy")
    assert detect_step_format(p) in {"p21", "stpx"}
