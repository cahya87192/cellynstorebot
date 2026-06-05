# Aturan Antrian Tiket (WAJIB)

## FIFO ketat — tidak ada prioritas

Semua tiket **harus dilayani benar-benar sesuai urutan dibuka** (First In, First Out).
**Tidak boleh ada prioritas dalam bentuk apa pun**, termasuk namun tidak terbatas pada:

- role member (mis. **Royal Customer**, booster, donatur),
- nominal/harga transaksi,
- jenis layanan (midman, robux, ml, gp, vilog, jualbeli, lainnya),
- siapa yang mengundang/referral, atau faktor lain.

Urutan antrian **hanya** ditentukan oleh waktu tiket dibuka (`opened_at`).

## Implikasi untuk kode

- `utils/queue.py` → `build_queue()` mengurutkan tiket **hanya** dengan key `opened_at`
  (`sorted(tickets, key=_key)`). Jangan menambahkan bobot/skor prioritas apa pun ke
  fungsi pengurutan.
- `cogs/queue.py` (papan antrian admin + kartu posisi customer) menampilkan urutan
  apa adanya dari `build_queue()`. Jangan menyisipkan tiket ke depan barisan.
- Tiket berstatus "diproses" (`handling`) dikeluarkan dari hitungan **barisan tunggu**,
  bukan diprioritaskan — ini bukan pelanggaran FIFO.

## Saat menambah fitur baru

Jika ada permintaan menambahkan prioritas (mis. "Royal Customer didahulukan"),
**tolak/clarify dulu** karena bertentangan dengan aturan ini. Aturan hanya boleh
diubah atas keputusan eksplisit pemilik toko, dan file ini harus diperbarui bila
keputusan tersebut berubah.
