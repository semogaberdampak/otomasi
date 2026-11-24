"""
================================================================================
 UJI KEMAMPUAN - DIAGNOSA APLIKASI TAKOM (Java Swing)
================================================================================
TUJUAN:
   Sebelum membangun aplikasi "pintar", kita HARUS tahu dulu:
     1. Berapa kali tombol TAB dari posisi sekarang sampai fokus masuk ke tabel?
     2. Apakah Ctrl+C menghasilkan teks baris? (baris penuh / 1 sel / kosong)
     3. Format tanggal di teks clipboard itu seperti apa?

CARA PAKAI:
   1. Buka aplikasi "Sales AND Distribution PT Takom < 1.2.0 >"
   2. Klik SATU baris transaksi di tabel (biar fokus ada di tabel)
   3. Jalankan:  python uji_kemampuan.py
   4. JANGAN sentuh mouse/keyboard lagi selama hitungan mundur
   5. Ikuti instruksi di layar

CATATAN:
   - Skrip ini TIDAK mencetak apa pun, TIDAK menyimpan file PDF.
   - 100% aman. Anda bisa tekan Ctrl+C kapan saja untuk membatalkan.
================================================================================
"""

import re
import sys
import time

import pyautogui
import pyperclip

# --- PERIHAL KEAMANAN: geser mouse ke pojok kiri-atas = STOP paksa ---
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

# Jumlah maksimal TAB yang akan dicoba saat memindai
MAKS_TAB = 20

GARIS = "=" * 68


def bersihkan_clipboard():
    """Mengosongkan clipboard agar kita pasti tahu hasil Ctrl+C benar-benar baru."""
    pyperclip.copy("")


def baca_clipboard(waktu_tunggu=0.35):
    """
    Menekan Ctrl+C lalu membaca isi clipboard.
    Mengembalikan teks hasil copy (bisa kosong).
    """
    bersihkan_clipboard()
    pyautogui.hotkey("ctrl", "c")
    time.sleep(waktu_tunggu)
    try:
        return pyperclip.paste()
    except Exception:
        return ""


def tampilkan_teks(teks, label=""):
    """Menampilkan isi teks clipboard dengan cara yang mudah dibaca."""
    print(f"\n{label}")
    print(f"  Panjang karakter : {len(teks)}")
    if not teks.strip():
        print("  Isi              : (KOSONG)")
        return

    baris = teks.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    print(f"  Jumlah baris     : {len(baris)}")

    for i, b in enumerate(baris[:12]):
        # Tampilkan karakter TAB sebagai ' | ' supaya kolomnya kelihatan
        kolom = b.split("\t")
        if len(kolom) > 1:
            isi = "  |  ".join(f"[{k.strip()}]" for k in kolom)
            print(f"  Baris {i} ({len(kolom)} kolom): {isi}")
        else:
            print(f"  Baris {i} (1 kolom)  : [{b.strip()}]")
    if len(baris) > 12:
        print(f"  ... ({len(baris) - 12} baris lagi disembunyikan)")


def cari_tanggal(teks):
    """
    Mencari potongan yang terlihat seperti tanggal di dalam teks.
    Mengembalikan list berisi (tanggal_ditemukan, pola_yang_cocok, posisi).
    """
    if not teks:
        return []

    # Berbagai pola tanggal yang umum dipakai aplikasi Indonesia
    pola = [
        (r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b", "dd-mm-yyyy / dd-mm-yy"),
        (r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", "yyyy-mm-dd"),
        (r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|Mei|May|Jun|Jul|Agu|Aug|Sep|Okt|Oct|Nov|Des|Dec)[a-z]*\s+(\d{2,4})\b",
         "dd-NamaBulan-yyyy"),
        (r"\b(Jan|Feb|Mar|Apr|Mei|May|Jun|Jul|Agu|Aug|Sep|Okt|Oct|Nov|Des|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})\b",
         "NamaBulan dd, yyyy"),
    ]

    hasil = []
    for rx, nama_pola in pola:
        for cocok in re.finditer(rx, teks, flags=re.IGNORECASE):
            hasil.append((cocok.group(0), nama_pola, cocok.start()))
    return hasil


def hitung_mundur(detik, pesan):
    """Hitung mundur agar user sempat fokus ke jendela Takom."""
    print(f"\n{pesan}")
    for i in range(detik, 0, -1):
        print(f"  Mulai dalam {i} detik...  (gerakkan mouse ke pojok kiri-atas untuk batal)",
              end="\r")
        time.sleep(1)
    print(" " * 74, end="\r")  # bersihkan baris hitungan mundur



def main():
    print(GARIS)
    print(" DIAGNOSA APLIKASI TAKOM - PENGECEKAN KEMAMPUAN BACA LAYAR")
    print(GARIS)
    print()
    print("LANGKAH PERSIAPAN (lakukan SEKARANG, sebelum hitungan mundur):")
    print("  1. Pastikan aplikasi Takom sudah terbuka.")
    print("  2. Klik SATU baris transaksi di tabel (fokus harus ada di tabel).")
    print("  3. Balik ke jendela CMD/VS Code ini.")
    print()
    print("CATATAN: Skrip ini TIDAK mencetak & TIDAK menyimpan file apa pun.")
    print("         Anda aman. Tekan Ctrl+C untuk membatalkan kapan saja.")
    print()

    input(">>> Tekan ENTER jika sudah siap, lalu JANGAN sentuh mouse/keyboard... ")

    hitung_mundur(8, "Mempersiapkan pemindaian...")

    # ---------------------------------------------------------------
    # TAHAP 1: Baca baris pada posisi SEKARANG (tanpa TAB)
    # ---------------------------------------------------------------
    print(GARIS)
    print(" TAHAP 1: PEMBACAAN POSISI AWAL (tanpa menekan TAB)")
    print(GARIS)

    teks_awal = baca_clipboard()
    tampilkan_teks(teks_awal, ">> Hasil Ctrl+C di posisi awal:")

    if not teks_awal.strip():
        print()
        print("[!] Clipboard KOSONG di posisi awal.")
        print("    Kemungkinan penyebab:")
        print("      - Fokus belum benar-benar ada di dalam tabel.")
        print("      - Tabel Takom TIDAK mendukung Ctrl+C.")
        print("    -> Kita lanjut memindai dengan TAB untuk memastikan.")

    # ---------------------------------------------------------------
    # TAHAP 2: Pindai dengan menekan TAB secara bertahap
    # ---------------------------------------------------------------
    print()
    print(GARIS)
    print(" TAHAP 2: PEMINDAIAN BERTAHAP DENGAN TOMBOL TAB")
    print(GARIS)
    print("Kita tekan TAB 1x, 2x, 3x, ... lalu Ctrl+C di setiap langkah.")
    print("Tujuannya mencari di TAB ke berapa baris tabel berhasil tercopy.")
    print()

    hasil_pindai = []

    for n in range(1, MAKS_TAB + 1):
        pyautogui.press("tab")
        time.sleep(0.25)

        teks = baca_clipboard()
        ada_isi = bool(teks.strip())

        # Ringkasan singkat per langkah
        if ada_isi:
            baris = teks.replace("\r\n", "\n").split("\n")
            baris_pertama = baris[0].strip()
            potong = baris_pertama[:60] + ("..." if len(baris_pertama) > 60 else "")
            jumlah_kolom = len(baris[0].split("\t"))
            status = f"ADA ISI ({jumlah_kolom} kolom): {potong}"
        else:
            status = "kosong"

        print(f"  TAB ke-{n:>2}  ->  {status}")
        hasil_pindai.append((n, ada_isi, teks))

    # ---------------------------------------------------------------
    # TAHAP 3: Analisa & Rekomendasi
    # ---------------------------------------------------------------
    print()
    print(GARIS)
    print(" TAHAP 3: HASIL ANALISA & REKOMENDASI")
    print(GARIS)

    # Cari langkah pertama yang menghasilkan teks mengandung tanggal
    kandidat = []
    for n, ada_isi, teks in hasil_pindai:
        if ada_isi:
            tg = cari_tanggal(teks)
            if tg:
                kandidat.append((n, teks, tg))

    if kandidat:
        n_terbaik, teks_terbaik, tanggal_ketemu = kandidat[0]
        print()
        print(f"[SUKSES] Ctrl+C BEKERJA pada TAB ke-{n_terbaik}!")
        print()
        print("Contoh teks baris yang tercopy:")
        print("  " + "-" * 60)
        kolom = teks_terbaik.replace("\r\n", "\n").split("\n")[0].split("\t")
        for idx, k in enumerate(kolom):
            print(f"    Kolom {idx:>2}: [{k.strip()}]")
        print("  " + "-" * 60)
        print()
        print("Tanggal yang terdeteksi:")
        for nilai, pola, _pos in tanggal_ketemu:
            print(f"    - '{nilai}'  (pola: {pola})")
        print()
        print(">> REKOMENDASI: metode CLIPBOARD bisa dipakai.")
        print(f">> Jumlah TAB dari posisi awal tabel ke baris tercopy: {n_terbaik}")
        print()
        print("   Silakan salin hasil TAHAP 2 & 3 ini ke saya,")
        print("   supaya saya bisa set konfigurasi aplikasi dengan tepat.")

    else:
        print()
        print("[GAGAL] Tidak ada teks berisi tanggal yang tercopy di semua percobaan TAB.")
        print()
        print("Kemungkinan penyebab:")
        print("  1. Tabel Takom benar-benar TIDAK mendukung Ctrl+C.")
        print("  2. Baris belum ter-select saat Ctrl+C ditekan.")
        print("  3. Teks tercopy tapi format tanggalnya tidak dikenali pola kami.")
        print()
        print("Langkah selanjutnya:")
        print("  - Coba manual: klik baris di Takom, tekan Ctrl+C, lalu Ctrl+V di Notepad.")
        print("    Apakah muncul teks? Jika YA, kirim screenshot isinya ke saya.")
        print("  - Jika TIDAK muncul apa-apa, kita perlu pakai metode OCR (baca gambar layar).")
        print()
        print("Kirim hasil diagnostik ini ke saya agar saya bisa menyesuaikan rencana.")

    print()
    print(GARIS)
    print(" DIAGNOSA SELESAI")
    print(GARIS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[DIBATALKAN] Diagnosa dihentikan oleh pengguna.")
        sys.exit(0)
    except pyautogui.FailSafeException:
        print("\n\n[DIBATALKAN] FAILSAFE aktif (mouse ke pojok kiri-atas).")
        sys.exit(0)
