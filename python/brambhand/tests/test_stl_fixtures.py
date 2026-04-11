import json
from pathlib import Path


def test_stl_fixture_manifest_and_files_exist() -> None:
    here = Path(__file__).resolve()
    repo_root = next(
        parent for parent in here.parents if (parent / "assets/stl/metadata/fixtures.json").exists()
    )
    manifest_path = repo_root / "assets/stl/metadata/fixtures.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "idealized" in manifest and manifest["idealized"]
    assert "reference" in manifest and manifest["reference"]

    idealized_names = {item["name"] for item in manifest["idealized"]}
    assert {
        "cube_1m",
        "cylinder_r0p5_h1",
        "cone_r0p5_h1",
        "frustum_r0p2_r0p5_h1",
        "de_laval_nozzle_idealized",
    }.issubset(idealized_names)

    for group in ("idealized", "reference"):
        for item in manifest[group]:
            path = repo_root / item["path"]
            assert path.exists(), f"missing fixture file: {path}"
            text = path.read_text(encoding="utf-8")
            assert text.lstrip().startswith("solid ")
            assert "facet normal" in text
            assert text.rstrip().endswith(f"endsolid {path.stem}")
