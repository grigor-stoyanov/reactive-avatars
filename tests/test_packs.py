import json

import pytest

from reactive_avatars import config as cfg
from reactive_avatars import packs


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "PACKS_DIR", tmp_path / "packs")
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)


def make_pack(root, name, manifest):
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "avatar.json").write_text(json.dumps(manifest))
    (folder / "body.png").write_bytes(b"x")
    return folder


def test_builtin_example_pack_is_listed_and_valid():
    ids = {p["id"] for p in packs.list_packs()}
    assert packs.DEFAULT_PACK in ids
    manifest = json.loads((packs.pack_dir(packs.DEFAULT_PACK) / "avatar.json").read_text())
    for layer in manifest["layers"]:
        assert packs.resolve_file(packs.DEFAULT_PACK, layer["image"]) is not None


def test_user_pack_overrides_builtin_with_same_id():
    make_pack(cfg.PACKS_DIR, packs.DEFAULT_PACK, {"name": "Mine", "type": "layers", "layers": []})
    mine = next(p for p in packs.list_packs() if p["id"] == packs.DEFAULT_PACK)
    assert mine["name"] == "Mine" and not mine["builtin"]


@pytest.mark.parametrize("bad", ["../x", "a/b", "", "a b", "x" * 80, "..", "."])
def test_bad_pack_ids_rejected(bad):
    assert packs.pack_dir(bad) is None


@pytest.mark.parametrize("path", ["../../config.json", "../blobby/body.svg/../../x", "/etc/passwd", "nope.png"])
def test_files_cannot_escape_pack(path):
    make_pack(cfg.PACKS_DIR, "mine", {"type": "layers", "layers": []})
    (cfg.PACKS_DIR.parent / "config.json").write_text("{}")
    assert packs.resolve_file("mine", path) is None


def test_layer_builder_writes_manifest_in_draw_order():
    packs.set_custom_layer("mouth_open", ".png", b"1")
    packs.set_custom_layer("body", ".png", b"2")
    packs.set_custom_layer("front1", ".svg", b"3")
    packs.set_custom_reaction("front1", "lift")
    manifest = json.loads((cfg.PACKS_DIR / "custom" / "avatar.json").read_text())
    assert [layer["image"] for layer in manifest["layers"]] == ["body.png", "mouth_open.png", "front1.svg"]
    assert manifest["layers"][0]["role"] == "body"
    assert manifest["layers"][2]["react"] == "lift" and "role" not in manifest["layers"][2]


def test_layer_builder_replace_and_clear_remove_old_files():
    packs.set_custom_layer("body", ".png", b"1")
    packs.set_custom_layer("body", ".webp", b"2")
    folder = cfg.PACKS_DIR / "custom"
    assert not (folder / "body.png").exists() and (folder / "body.webp").exists()
    packs.clear_custom_layer("body")
    assert not (folder / "body.webp").exists()
    assert json.loads((folder / "avatar.json").read_text())["layers"] == []


def test_layer_builder_rejects_unknown_role_and_reaction():
    with pytest.raises(KeyError):
        packs.set_custom_layer("../evil", ".png", b"x")
    packs.set_custom_layer("front1", ".png", b"x")
    with pytest.raises(KeyError):
        packs.set_custom_reaction("front1", "explode")
    with pytest.raises(KeyError):
        packs.set_custom_reaction("body", "lift")  # body can't carry a reaction
