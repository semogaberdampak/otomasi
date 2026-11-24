# Catatan Lanjutan — Aplikasi Automasi Nota (Takom)

Terakhir diperbarui: 24 November 2026. Baca file ini dulu sebelum melanjutkan.

## Yang sudah selesai

**Tab Automasi Jasper (lama, jangan diutak-atik alurnya)**
- Automasi print preview → Microsoft Print to PDF → simpan → tutup Jasper.
- Saat **MULAI OTOMATISASI** / **LANJUTKAN PROSES** diklik, muncul dialog
  **pilih folder penyimpanan PDF**; nama file diketik dengan **path lengkap**
  sehingga PDF tidak lagi bergantung pada folder terakhir aplikasi Java.
- Folder **diingat per tanggal** (`folder_pdf_per_tanggal`), jadi dialog
  dilewati bila tanggal itu sudah punya folder. Checkbox
  "Tanyakan folder setiap kali mulai" memaksa dialog selalu muncul.
- Label "Folder PDF:" di form menampilkan folder tanggal terpilih.
- Folder yang sudah dihapus tidak dianggap diingat (dialog muncul lagi).

**Tab Bulk Print Dokumen (thermal 80 mm)**
- Konversi nota A4 (Jasper) → PDF thermal; parsing berbasis koordinat kata.
- CASH bila kembalian > 0, EDC BCA TAKOM bila 0 / tanpa baris kembalian.
- Tombol **Editor Format...**: mengedit semua elemen teks nota (kop, label,
  footer, peta kasir, lebar kertas, font) dan menyimpan ke `pengaturan.json`.
- Checkbox **"Simpan file PDF hasil konversi"**: dimatikan = konversi di memori
  lalu **langsung ke antrean cetak** (spooler) tanpa menulis file.
- Cetak memakai GDI (ctypes: winspool/gdi32) — tidak butuh aplikasi PDF,
  karena PDF diasosiasikan ke BravePDF (tanpa print verb).

## File penting

| File | Peran |
|---|---|
| `app_automasi.py` | GUI 2 tab, alur automasi Java, worker thermal, editor format |
| `konversi_thermal.py` | baca nota, susun baris, `buat_dokumen`, `simpan_pdf`, `cetak_dokumen`, `cetak_pdf`, `konversi_dan_cetak` |
| `pengaturan.json` | konfigurasi runtime (bagian `thermal` = format nota) |
| `AutomasiNota.spec` | resep build exe (sudah memuat pengecualian modul) |
| `dist/` | hasil build: `AutomasiNota.exe` (50 MB) + pengaturan + 2 PNG tombol |

File lama yang **tidak dipakai** `app_automasi.py` dan sengaja dibiarkan:
`auto_jasper_print.py`, `mesin_pintar.py`, `pembaca_layar.py`,
`kelola_progres.py`, `uji_kemampuan.py`, `kalibrasi.json`. Boleh dihapus bila
pemilik proyek setuju.

## Kunci konfigurasi penting

- `folder_pdf`, `folder_pdf_per_tanggal`, `tanya_folder_setiap_kali`
- `thermal.simpan_pdf_thermal`, `thermal.cetak_setelah_konversi`,
  `thermal.jeda_antar_cetak`, `thermal.nama_printer`
- `thermal.peta_kasir` — contoh `{"Stephanus Edward Saputro": "2341"}`
- `thermal.footer_edc` / `footer_cash` / `footer_1..3`, `thermal.label_*`
- Kosong pada `thermal.alamat/email/web/telp` = ikut data PDF nota.

## Build exe

```
python -m PyInstaller --noconfirm AutomasiNota.spec
```
Spec sudah memakai pengecualian: pandas, numpy, cv2, scipy, matplotlib,
pyarrow, psycopg2/psycopg, torch, sklearn, IPython, PyQt5/6, PySide2/6, wx,
notebook, pytest, sqlalchemy, pymupdf4llm, pymupdf_layout.
Tanpa pengecualian exe 156 MB; dengan pengecualian 50 MB dan konversi pymupdf
sudah diuji tetap jalan di dalam exe.

Catatan: tutup dulu `AutomasiNota.exe` sebelum build (`taskkill //F //IM
AutomasiNota.exe`), kalau tidak PyInstaller gagal menimpa file.

## Verifikasi yang sudah dilakukan

- `python -m py_compile app_automasi.py konversi_thermal.py` → OK.
- Uji GUI nyata untuk: prompt folder (batal/pilih), memori per tanggal,
  checkbox tanya-setiap-kali, editor format (simpan & validasi angka).
- `buat_dokumen` → 1 halaman 226,8 × 316 pt tanpa file; `simpan_pdf` →
  5.631 byte; `konversi_dan_cetak` → nol file dibuat; printer salah → OSError.
- Exe dinyalakan nyata di folder kosong: membuat `pengaturan.json` lengkap.

## Belum diuji / terbuka

- Cetak fisik sungguhan dari dalam **exe** (jalur GDI pernah terbukti dari
  skrip, tapi belum dari exe hasil build).
- Kategori folder selain per tanggal (mis. harian vs borongan) — belum ada,
  strukturnya mudah ditambah.
- Mode tanpa file membuat **1 job cetak per nota**; untuk ratusan nota antrean
  bisa penuh.

## Rencana berikutnya (saran yang disimpan)

1. **Gabung satu job cetak**: semua nota dalam satu `StartDoc` berurutan agar
   antrean tidak dipenuhi ratusan job kecil.
2. **Kelola antrean printer dari aplikasi**: tampilkan daftar job dan tombol
   kosongkan/batalkan.
3. **Jeda adaptif**: tunggu antrean printer kosong (atau di bawah ambang)
   sebelum mengirim job berikutnya, alih-alih jeda tetap `jeda_antar_cetak`.
