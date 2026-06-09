"""Test logika pengaturan thumbnail katalog (utils/catalog_settings.py) — murni."""
from utils import catalog_settings as cs


def test_is_valid_url():
    assert cs.is_valid_url("https://i.imgur.com/x.png")
    assert cs.is_valid_url("http://example.com/a.jpg")
    assert not cs.is_valid_url("ftp://x.com/a.png")
    assert not cs.is_valid_url("just text")
    assert not cs.is_valid_url("https://with space.com/a.png")
    assert not cs.is_valid_url("")
    assert not cs.is_valid_url(None)
    assert not cs.is_valid_url("https://")
    assert not cs.is_valid_url("https://" + "x" * 600)


def test_clean_url():
    assert cs.clean_url("  https://x.com/a.png  ") == "https://x.com/a.png"
    assert cs.clean_url("bukan url") is None
    assert cs.clean_url(123) is None


def test_merge_settings_filters_unknown_and_invalid():
    raw = {
        "robux": "https://x.com/r.png",
        "ml": "  https://x.com/ml.png  ",
        "gp": "tidak valid",
        "tidakdikenal": "https://x.com/z.png",
        "vilog": "",
    }
    m = cs.merge_settings(raw)
    assert m["robux"] == "https://x.com/r.png"
    assert m["ml"] == "https://x.com/ml.png"   # di-strip
    assert "gp" not in m                         # url invalid dibuang
    assert "tidakdikenal" not in m               # code tak dikenal dibuang
    assert "vilog" not in m                      # kosong dibuang


def test_merge_settings_accepts_nested_and_bad_input():
    assert cs.merge_settings(None) == {}
    assert cs.merge_settings("bukan json") == {}
    assert cs.merge_settings(123) == {}
    nested = {"thumbnails": {"robux": "https://x.com/a.png"}}
    assert cs.merge_settings(nested) == {"robux": "https://x.com/a.png"}
    # JSON string juga didukung
    import json
    assert cs.merge_settings(json.dumps({"gp": "https://x.com/g.png"})) == {"gp": "https://x.com/g.png"}


def test_resolve_thumbnail_fallback():
    settings = {"robux": "https://x.com/r.png"}
    assert cs.resolve_thumbnail(settings, "robux") == "https://x.com/r.png"
    assert cs.resolve_thumbnail(settings, "ml") == cs.DEFAULT_THUMBNAIL
    assert cs.resolve_thumbnail(None, "robux") == cs.DEFAULT_THUMBNAIL
    assert cs.resolve_thumbnail({}, "lainnya") == cs.DEFAULT_THUMBNAIL


def test_catalog_registry_codes():
    codes = {c for c, _ in cs.CATALOGS}
    assert codes == cs.CATALOG_CODES
    assert {"robux", "ml", "gp", "vilog", "lainnya"} <= cs.CATALOG_CODES


def test_save_and_load_round_trip(db):
    cs.save_settings({"robux": "https://x.com/r.png", "bad": "nope", "gp": "ngawur"})
    loaded = cs.load_settings()
    assert loaded == {"robux": "https://x.com/r.png"}
    assert cs.get_thumbnail("robux") == "https://x.com/r.png"
    assert cs.get_thumbnail("ml") == cs.DEFAULT_THUMBNAIL


def test_save_empty_resets(db):
    cs.save_settings({"robux": "https://x.com/r.png"})
    assert cs.load_settings() == {"robux": "https://x.com/r.png"}
    cs.save_settings({})
    assert cs.load_settings() == {}
    assert cs.get_thumbnail("robux") == cs.DEFAULT_THUMBNAIL
