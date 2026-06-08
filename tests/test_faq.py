"""Test knowledge base FAQ + matcher Auto-CS (utils/faq.py), murni."""
from utils import faq as f


def test_default_and_render():
    entries = f.default_faq()
    assert any(e["id"] == "produk" for e in entries)
    # placeholder {store} diganti nama toko
    ident = next(e for e in entries if e["id"] == "identitas")
    rendered = f.render_text(ident["a"], "Toko ABC")
    assert "Toko ABC" in rendered and "{store}" not in rendered


def test_normalize_tolerant():
    # input rusak -> fallback default
    assert f.normalize_faq("bukan json") == f.default_faq()
    assert f.normalize_faq(None) == f.default_faq()
    # entri tak lengkap dibuang; keywords string dipecah
    norm = f.normalize_faq([
        {"q": "Halo?", "a": "Hai", "keywords": "sapa, halo"},
        {"q": "", "a": "kosong"},          # dibuang (q kosong)
        {"a": "tanpa q"},                   # dibuang
    ])
    assert len(norm) == 1
    assert norm[0]["keywords"] == ["sapa", "halo"]


def test_match_question_basic():
    entries = f.default_faq()
    assert f.match_question("min cara order gimana ya?", entries)["id"] == "cara_order"
    assert f.match_question("ini garansi nya gimana?", entries)["id"] == "garansi"
    assert f.match_question("metode pembayaran apa aja?", entries)["id"] == "pembayaran"
    assert f.match_question("jual apa aja sih disini", entries)["id"] == "produk"


def test_match_question_no_match():
    entries = f.default_faq()
    # pertanyaan tak relevan -> None (tidak menjawab ngawur)
    assert f.match_question("cuaca hari ini gimana", entries) is None
    assert f.match_question("hi", entries) is None


def test_save_load_round_trip(db):
    custom = f.default_faq()
    custom.append({"id": "x", "q": "Tes?", "a": "Jawab tes", "keywords": ["tes"]})
    f.save_faq(custom)
    loaded = f.load_faq()
    assert any(e["id"] == "x" for e in loaded)
    assert f.match_question("ini tes ya", loaded)["id"] == "x"
