"""Preset palet/gaya untuk editor kartu (logika murni, tanpa PIL/discord).

Tiap preset adalah override GAYA (opacity panel, warna bingkai/ring avatar, dan
warna tiap elemen teks) — BUKAN posisi. Diterapkan di sisi klien editor: nilai
preset di-merge ke objek `theme` di JavaScript, lalu admin klik "Simpan". Dengan
begitu posisi yang sudah diatur admin tidak ikut berubah.

Key warna ("colors") mengikuti elemen teks tiap jenis kartu:
  - welcome/boost/leave : title, name, subtitle, membercount
  - rating              : title, name, stars, review

`presets_for(surface)` mengembalikan list preset untuk jenis kartu tsb (atau []).
"""

# Catatan: nilai hex sengaja uppercase 6-digit agar konsisten dgn validasi tema.
PRESETS = {
    "welcome": [
        {"id": "periwinkle", "name": "Periwinkle (default)", "opacity": 140, "ring": "#8B9BE0",
         "colors": {"title": "#FFFFFF", "name": "#8B9BE0", "subtitle": "#D8DCE6", "membercount": "#A6B1C6"}},
        {"id": "emas", "name": "Emas Kalem", "opacity": 150, "ring": "#F0C85A",
         "colors": {"title": "#F5E3B3", "name": "#F0C85A", "subtitle": "#E7E0CC", "membercount": "#C9A24B"}},
        {"id": "dark", "name": "Dark Mono", "opacity": 180, "ring": "#FFFFFF",
         "colors": {"title": "#FFFFFF", "name": "#FFFFFF", "subtitle": "#C8CCD6", "membercount": "#9AA0AC"}},
        {"id": "sunset", "name": "Sunset", "opacity": 150, "ring": "#FF8A65",
         "colors": {"title": "#FFE0D2", "name": "#FF8A65", "subtitle": "#F2D7CC", "membercount": "#E0A48C"}},
    ],
    "boost": [
        {"id": "pink", "name": "Pink Boost (default)", "opacity": 140, "ring": "#FF73FA",
         "colors": {"title": "#FFFFFF", "name": "#FF8BFB", "subtitle": "#F0D8EE", "membercount": "#E0A6D6"}},
        {"id": "ungu", "name": "Ungu Neon", "opacity": 160, "ring": "#B388FF",
         "colors": {"title": "#EDE3FF", "name": "#B388FF", "subtitle": "#DCD2F0", "membercount": "#A98FE0"}},
        {"id": "emas", "name": "Emas", "opacity": 150, "ring": "#F0C85A",
         "colors": {"title": "#F5E3B3", "name": "#F0C85A", "subtitle": "#E7E0CC", "membercount": "#C9A24B"}},
    ],
    "leave": [
        {"id": "abu", "name": "Abu Kalem (default)", "opacity": 140, "ring": "#9AA3B2",
         "colors": {"title": "#FFFFFF", "name": "#C7CDD8", "subtitle": "#CDD2DC", "membercount": "#9AA3B2"}},
        {"id": "biru", "name": "Biru Malam", "opacity": 160, "ring": "#5C7AEA",
         "colors": {"title": "#E4ECFF", "name": "#9DB4FF", "subtitle": "#CAD6F2", "membercount": "#8C9CC4"}},
    ],
    "rating": [
        {"id": "emas", "name": "Emas (default)", "opacity": 150, "ring": "#FFC107",
         "colors": {"title": "#FFC107", "name": "#FFFFFF", "stars": "#FFD24D", "review": "#E2E4EC"}},
        {"id": "hijau", "name": "Hijau Fresh", "opacity": 150, "ring": "#3DD68C",
         "colors": {"title": "#3DD68C", "name": "#FFFFFF", "stars": "#7CF0B8", "review": "#DDEDE5"}},
        {"id": "dark", "name": "Dark Mono", "opacity": 185, "ring": "#FFFFFF",
         "colors": {"title": "#FFFFFF", "name": "#FFFFFF", "stars": "#E6E6E6", "review": "#C8CCD6"}},
    ],
}


def presets_for(surface):
    """List preset untuk jenis kartu `surface` (welcome/boost/leave/rating)."""
    return PRESETS.get(surface, [])
