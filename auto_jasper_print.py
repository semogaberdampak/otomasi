import os
import time
import pyautogui

# =========================================================
# PERIHAL KEAMANAN (FAILSAFE)
# Geser kursor mouse secara cepat ke pojok KIRI-ATAS layar
# untuk menghentikan program secara paksa jika terjadi kendala.
# =========================================================
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.8  # Jeda waktu default (detik) antar perintah

# =========================================================
# KONFIGURASI PENGGUNA (SESUAIKAN DI SINI)
# =========================================================
# Tanggal yang ingin diproses (Format: DD-MM-YY)
TANGGAL_DICARI = "07-10-26"

# Folder tujuan penyimpanan PDF
FOLDER_SIMPAN = rf"C:\Laporan_PDF\{TANGGAL_DICARI}"

# Nomor transaksi awal (3 digit terakhir)
NO_TRANSAKSI_AWAL = 1

# Jumlah transaksi yang ingin diproses pada halaman saat ini
JUMLAH_TRANSAKSI_PER_HALAMAN = 10

# Jumlah halaman yang ingin diproses
BATAS_HALAMAN = 5

# Buat folder penyimpanan jika folder belum ada di komputer
if not os.path.exists(FOLDER_SIMPAN):
    os.makedirs(FOLDER_SIMPAN)
    print(f"[INFO] Folder penyimpanan siap: {FOLDER_SIMPAN}")


def beri_waktu_persiapan():
    """Memberikan waktu 5 detik agar Anda bisa memfokuskan layar ke aplikasi Java"""
    print("=" * 65)
    print(" BERSAIP-SAIP... Segera klik aplikasi Java Anda sekarang!")
    print("=" * 65)
    for i in range(5, 0, -1):
        print(f"Otomatisasi akan dimulai dalam {i} detik...", end="\r")
        time.sleep(1)
    print("\n[INFO] Otomatisasi dimulai!\n")


def klik_tombol_preview():
    """
    Mencari dan mengeklik tombol fisik PRINT PREVIEW pada layar
    menggunakan acuan gambar 'tombol_preview.png'
    """
    try:
        lokasi = pyautogui.locateOnScreen('tombol_preview.png', confidence=0.8)
        if lokasi:
            # Klik tepat di tengah-tengah tombol
            pyautogui.click(pyautogui.center(lokasi))
            return True
        else:
            print("[ERROR] Tombol 'PRINT PREVIEW' tidak ditemukan di layar!")
            return False
    except Exception as e:
        print(f"[ERROR] Kendala saat mencari tombol PRINT PREVIEW: {e}")
        return False


def klik_next_pagination():
    """
    Mencari dan mengeklik tombol NEXT PAGINATION pada layar
    menggunakan acuan gambar 'tombol_next.png'
    """
    try:
        lokasi_next = pyautogui.locateOnScreen('tombol_next.png', confidence=0.8)
        if lokasi_next:
            pyautogui.click(pyautogui.center(lokasi_next))
            print("[INFO] Berhasil klik NEXT PAGINATION. Memuat halaman baru...")
            time.sleep(3.0)  # Tunggu data di aplikasi Java selesai memuat
            return True
        else:
            print("[INFO] Tombol NEXT PAGINATION tidak ditemukan / Halaman Habis.")
            return False
    except Exception as e:
        print(f"[ERROR] Kendala saat mencari tombol NEXT PAGINATION: {e}")
        return False


def proses_cetak_pdf(nama_file):
    """Menjalankan Poin 2 sampai Poin 8"""
    path_file_lengkap = os.path.join(FOLDER_SIMPAN, nama_file)

    # 1. Klik tombol fisik PRINT PREVIEW di layar (Poin 2)
    berhasil_preview = klik_tombol_preview()
    if not berhasil_preview:
        return False

    time.sleep(2.5)  # Tunggu jendela JASPER VIEW muncul

    # 2. Klik ikon Print di JASPER VIEW (Poin 3)
    pyautogui.hotkey('ctrl', 'p')
    time.sleep(1.5)  # Tunggu PROMPT PRINT muncul

    # 3. Pilih Printer (Microsoft Print to PDF) & Enter (Poin 4)
    pyautogui.write("Microsoft Print to PDF", interval=0.05)
    pyautogui.press('enter')
    time.sleep(2.0)  # Tunggu prompt 'Save Print Output As' muncul (Poin 5)

    # 4. Ketik Nama File Gabungan (Tanggal + 3 digit transaksi) (Poin 6)
    pyautogui.write(path_file_lengkap, interval=0.05)
    time.sleep(0.5)

    # 5. Klik SAVE via tombol Enter (Poin 7)
    pyautogui.press('enter')
    time.sleep(2.0)  # Tunggu proses penyimpanan PDF selesai

    # 6. Menutup jendela JASPER VIEW (Poin 8)
    pyautogui.hotkey('alt', 'f4')
    time.sleep(1.0)

    print(f"[BERHASIL] Tersimpan: {nama_file}.pdf")
    return True


def jalankan_otomatisasi():
    """Fungsi utama pengendali alur kerja (Poin 1 - 9)"""
    beri_waktu_persiapan()

    counter_transaksi = NO_TRANSAKSI_AWAL

    for halaman in range(1, BATAS_HALAMAN + 1):
        print(f"=== Memproses Halaman {halaman} ===")

        # Memproses setiap baris transaksi pada halaman saat ini
        for item in range(1, JUMLAH_TRANSAKSI_PER_HALAMAN + 1):
            # Membuat format 3 digit transaksi (misal: 1 -> 001, 2 -> 002)
            digit_3 = f"{counter_transaksi:03d}"
            nama_file = f"{TANGGAL_DICARI}-{digit_3}"

            print(f"-> Memproses transaksi [{counter_transaksi}] (Item {item} di hal {halaman})...")
            
            # Jalankan alur simpan PDF
            sukses = proses_cetak_pdf(nama_file)
            if not sukses:
                print("[STOP] Proses dihentikan karena tombol tidak terdeteksi.")
                return

            counter_transaksi += 1

            # Pindah ke baris nomor transaksi berikutnya di tabel Java (Poin 1)
            pyautogui.press('down')
            time.sleep(0.5)

        # Setelah item pada halaman saat ini selesai, periksa NEXT PAGINATION (Poin 9)
        print(f"\n[INFO] Halaman {halaman} selesai diproses.")
        if halaman < BATAS_HALAMAN:
            berhasil_pindah = klik_next_pagination()
            if not berhasil_pindah:
                print("[STOP] Tidak ada transaksi lagi pada tanggal terpilih / Pagination habis.")
                break

    print("\n=========================================================")
    print(" SELESAI! Seluruh proses penyimpanan PDF telah berhasil.")
    print("=========================================================")


if __name__ == "__main__":
    jalankan_otomatisasi()