"""Guard konsistensi lintas-editor teks (meta-test).

Setelah ada banyak editor teks yang berbagi satu tabel `bot_state`, test ini
menjaga agar:
  1. Tidak ada DUA editor memakai kunci bot_state yang sama (collision = saling
     menimpa diam-diam).
  2. Semua kunci editor ter-cover oleh utils.text_backup (backup/restore/reset
     tidak pernah melewatkan editor baru).
  3. Tiap entry SPECS punya bentuk yang benar (key/default/label/placeholders).
  4. Setiap {token} di teks default sudah dideklarasikan sebagai placeholder.
"""
from utils import text_backup as tb
from utils import welcome as wl
from utils import store_status as ss


def _all_keys_with_source():
    """List (key, sumber) dari SEMUA editor teks — sengaja list (bukan set) agar
    duplikat terdeteksi."""
    pairs = []
    for specs in tb._simple_specs():
        for kind, spec in specs.items():
            pairs.append((spec["key"], kind))
    for kind, spec in wl.MSG_SPECS.items():
        pairs.append((spec["title_key"], "welcome:" + kind))
        pairs.append((spec["desc_key"], "welcome:" + kind))
    for kind, spec in wl.TEXT_SPECS.items():
        pairs.append((spec["key"], "welcome:" + kind))
    for k in wl.DM_KEYS:
        pairs.append((k, "welcome:dm"))
    pairs.append((ss.OPEN_LABEL_KEY, "store_status"))
    pairs.append((ss.CLOSE_LABEL_KEY, "store_status"))
    return pairs


def test_no_duplicate_bot_state_keys():
    pairs = _all_keys_with_source()
    keys = [k for k, _ in pairs]
    seen = {}
    dups = {}
    for k, src in pairs:
        if k in seen:
            dups.setdefault(k, [seen[k]]).append(src)
        else:
            seen[k] = src
    assert not dups, f"Kunci bot_state bentrok antar editor: {dups}"
    assert len(keys) == len(set(keys))


def test_backup_covers_every_editor_key():
    covered = tb.collect_keys()
    missing = [k for k, _ in _all_keys_with_source() if k not in covered]
    assert not missing, f"Kunci tidak ter-cover backup: {missing}"


def test_simple_specs_shape():
    for specs in tb._simple_specs():
        assert isinstance(specs, dict) and specs
        for kind, spec in specs.items():
            assert isinstance(kind, str) and kind
            assert spec.get("key"), f"key kosong di {kind}"
            assert spec.get("default"), f"default kosong di {kind}"
            assert spec.get("label"), f"label kosong di {kind}"
            assert isinstance(spec.get("placeholders"), tuple)


def test_default_tokens_are_declared():
    """Setiap {token} yang muncul di teks default harus terdaftar sebagai
    placeholder (mencegah default mereferensi placeholder yang tak diumumkan ke
    admin). Placeholder yang dideklarasikan tapi tak dipakai default tetap boleh
    (admin bebas menambahkannya)."""
    import re
    tok_re = re.compile(r"\{([a-z_]+)\}")
    for specs in tb._simple_specs():
        for kind, spec in specs.items():
            declared = set(spec["placeholders"])
            for tok in tok_re.findall(spec["default"]):
                assert ("{" + tok + "}") in declared, (
                    f"Token {{{tok}}} di default '{kind}' belum dideklarasikan "
                    f"sebagai placeholder {declared}"
                )


def test_keys_are_reasonable_strings():
    for k, _ in _all_keys_with_source():
        assert isinstance(k, str) and k.strip() == k and " " not in k


def test_collect_keys_is_exact_union():
    """collect_keys() harus sama persis dengan union semua kunci editor."""
    expected = {k for k, _ in _all_keys_with_source()}
    assert tb.collect_keys() == expected
