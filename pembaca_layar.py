"""
================================================================================
 pembaca_layar.py - MODUL PEMBACA LAYAR APLIKASI TAKOM (Metode Clipboard)
================================================================================
Modul ini membuat aplikasi jadi "PINTAR" dengan MEMBACA isi baris tabel Takom
melalui clipboard (Ctrl+C), lalu mengekstrak:

    - Tanggal transaksi  -> kolom ke-1  (format dd-mm-yyyy, contoh: 01-10-2026)
    - No. Transaksi      -> kolom ke-0  (contoh: 210726100001)

HASIL DIAGNOSA (uji_kemampuan.py) YANG MENJADI DASAR MODUL INI:
    - Ctrl+C BEKERJA, menghasilkan 8 kolom dipisahkan karakter TAB.
    - 8 x tekan TAB  =  turun 1 baris di tabel.
    - Kolom 0 = No. Transaksi, Kolom 1 = Tanggal.

Semua pengaturan disimpan di 'kalibrasi.json' supaya mudah disesuaikan
kalau suatu saat layout aplikasi Takom berubah.
================================================================================
"""

import re
import os
import json
import time
from datetime import datetime, date

import pyautogui
import pyperclip

# --- PERIHAL KEAMANAN: geser mouse ke pojok kiri-atas layar = STOP paksa ---
pyautogui.FAILSAFE = True

NAMA_FILE_KALIBRASI = "kalibrasi.json"

# Pengaturan bawaan (berasal dari hasil diagnosa). Bisa ditimpa kalibrasi.json.
KALIBRASI_BAWAAN = {
    "jumlah_tab_per_baris": 8,    # 8x TAB = turun 1 baris di tabel
    "jumlah_kolom": 8,            # tabel Takom punya 8 kolom
    "indeks_kolom_tanggal": 1,    # kolom ke-1 berisi tanggal
    "indeks_kolom_transaksi": 0,  # kolom ke-0 berisi no. transaksi
    "jeda_baca": 0.35,            # jeda setelah Ctrl+C sebelum baca clipboard
    "jeda_per_tab": 0.25,         # jeda setiap kali menekan TAB
    "sumber_no_file": "asli",     # 'asli' = no. transaksi dari tabel, 'urut' = 001,002,...
}


# ==============================================================================
# PENGELOLAAN KALIBRASI
# ==============================================================================
def muat_kalibrasi():
    """
    Memuat kalibrasi dari 'kalibrasi.json'.
    Jika file belum ada atau rusak, otomatis pakai KALIBRASI_BAWAAN (tidak error).
    """
    kal = dict(KALIBRASI_BAWAAN)
    if os.path.exists(NAMA_FILE_KALIBRASI):
        try:
            with open(NAMA_FILE_KALIBRASI, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Hanya ambil key yang kita kenal, agar file asing tidak merusak
            kal.update({k: v for k, v in data.items() if k in kal})
        except Exception:
            pass  # file rusak -> tenang, pakai bawaan
    return kal


def simpan_kalibrasi(kal):
    """Menyimpan kalibrasi ke 'kalibrasi.json'."""
    with open(NAMA_FILE_KALIBRASI, "w", encoding="utf-8") as f:
        json.dump(kal, f, indent=2, ensure_ascii=False)
    return kal


# ==============================================================================
# PEMBACAAN TEKS DARI LAYAR (CLIPBOARD)
# ==============================================================================
def baca_baris(jeda=0.35):
    """
    Menekan Ctrl+C pada sel yang sedang fokus, lalu membaca isi clipboard.
    Mengembalikan teks mentah hasil copy (bisa kosong).
    """
    pyperclip.copy("")  # kosongkan dulu, supaya yakin hasilnya benar-benar baru
    pyautogui.hotkey("ctrl", "c")
    time.sleep(jeda)
    try:
        return pyperclip.paste()
    except Exception:
        return ""


def pecah_kolom(teks):
    """Memecah teks satu baris menjadi list kolom (dipisahkan karakter TAB)."""
    if not teks:
        return []
    baris_pertama = teks.replace("\r\n", "\n").replace("\r", "\n").split("\n")[0]
    return [k.strip() for k in baris_pertama.split("\t")]


# ==============================================================================
# PEMROSESAN TANGGAL (TAHAN BEDA FORMAT)
# ==============================================================================
# Urutan penting: yang paling spesifik di atas, yang paling umum di bawah.
POLA_TANGGAL = [
    # 01-10-2026 / 01-10-26   (format utama aplikasi Takom)
    (r"^(\d{1,2})-(\d{1,2})-(\d{4})$", "dmy4"),
    (r"^(\d{1,2})-(\d{1,2})-(\d{2})$", "dmy2"),
    # 01/10/2026 / 01/10/26
    (r"^(\d{1,2})/(\d{1,2})/(\d{4})$", "dmy4"),
    (r"^(\d{1,2})/(\d{1,2})/(\d{2})$", "dmy2"),
    # 01.10.2026
    (r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", "dmy4"),
    # 2026-10-01 (ISO)
    (r"^(\d{4})-(\d{1,2})-(\d{1,2})$", "ymd"),
    (r"^(\d{4})/(\d{1,2})/(\d{1,2})$", "ymd"),
]

# Nama bulan (Indonesia & Inggris) untuk format '01 Okt 2026'
NAMA_BULAN = {
    "jan": 1, "januari": 1, "january": 1,
    "feb": 2, "februari": 2, "february": 2,
    "mar": 3, "maret": 3, "march": 3,
    "apr": 4, "april": 4,
    "mei": 5, "may": 5,
    "jun": 6, "juni": 6, "june": 6,
    "jul": 7, "juli": 7, "july": 7,
    "agu": 8, "agt": 8, "agustus": 8, "august": 8, "aug": 8,
    "sep": 9, "sept": 9, "september": 9,
    "okt": 10, "oct": 10, "oktober": 10, "october": 10,
    "nov": 11, "november": 11,
    "des": 12, "dec": 12, "desember": 12, "december": 12,
}


def _perbaiki_tahun_2digit(tahun):
    """
    Mengubah tahun 2 digit jadi 4 digit.
    Aturan praktis: 00-69 -> 2000-an, 70-99 -> 1900-an.
    """
    if tahun >= 100:
        return tahun
    if tahun <= 69:
        return 2000 + tahun
    return 1900 + tahun


def parsing_tanggal(teks):
    """
    Mengubah teks tanggal menjadi objek datetime.date.
    Mengembalikan None jika teks bukan tanggal yang dikenali.
    """
    if not teks:
        return None

    teks = str(teks).strip()
    if not teks:
        return None

    # 1) Coba pola angka (dd-mm-yyyy, yyyy-mm-dd, dst)
    for pola, urutan in POLA_TANGGAL:
        cocok = re.match(pola, teks)
        if not cocok:
            continue
        angka = [int(x) for x in cocok.groups()]
        try:
            if urutan == "ymd":
                tahun, bulan, hari = angka[0], angka[1], angka[2]
            else:  # dmy4 / dmy2 -> hari-bulan-tahun
                hari, bulan, tahun = angka[0], angka[1], angka[2]
            tahun = _perbaiki_tahun_2digit(tahun)
            return date(tahun, bulan, hari)
        except ValueError:
            # Contoh: 32-13-2026 -> bukan tanggal valid, lanjut ke pola lain
            continue

    # 2) Coba pola nama bulan: '01 Okt 2026' atau 'Oct 1, 2026'
    cocok = re.match(r"^(\d{1,2})[\s\-/]+([A-Za-z]+)[\s\-/,]+(\d{2,4})$", teks)
    if cocok:
        hari = int(cocok.group(1))
        bulan = NAMA_BULAN.get(cocok.group(2).lower())
        tahun = _perbaiki_tahun_2digit(int(cocok.group(3)))
        if bulan:
            try:
                return date(tahun, bulan, hari)
            except ValueError:
                return None

    cocok = re.match(r"^([A-Za-z]+)[\s\-/]+(\d{1,2}),?[\s\-/]+(\d{2,4})$", teks)
    if cocok:
        bulan = NAMA_BULAN.get(cocok.group(1).lower())
        hari = int(cocok.group(2))
        tahun = _perbaiki_tahun_2digit(int(cocok.group(3)))
        if bulan:
            try:
                return date(tahun, bulan, hari)
            except ValueError:
                return None

    return None


def cari_tanggal_dalam_teks(teks):
    """
    Mencari tanggal di dalam teks panjang (misal hasil copy seluruh baris
    yang mengandung banyak kolom). Mengembalikan (tanggal, kolom_asli).
    """
    if not teks:
        return None, None
    for bagian in str(teks).split():
        tgl = parsing_tanggal(bagian.strip(" ,;|"))
        if tgl:
            return tgl, bagian.strip(" ,;|")
    return None, None


# ==============================================================================
# PEMBACA BARIS TABEL (KELAS UTAMA)
# ==============================================================================
class PembacaLayar:
    """
    Mengambil data baris dari tabel Takom lewat clipboard.

    Cara pakai:
        pembaca = PembacaLayar()
        data = pembaca.baca_baris_sekarang()
        # data = {"tanggal": date(2026,10,1), "no_transaksi": "210726100001",
        #         "kolom": [...], "mentah": "..."}
    """

    def __init__(self, kalibrasi=None):
        self.kal = dict(kalibrasi) if kalibrasi else muat_kalibrasi()
        self.jumlah_kolom_terbaca = 0

    def baca_baris_sekarang(self, coba_lagi=2):
        """
        Membaca baris yang sedang fokus di tabel Takom.

        Mengembalikan dict:
            {
              "tanggal"      : datetime.date atau None,
              "no_transaksi" : str atau None,
              "kolom"        : list kolom mentah,
              "mentah"       : teks clipboard asli,
              "valid"        : True jika tanggal & no transaksi berhasil dibaca
            }
        """
        teks_terakhir = ""
        for _percobaan in range(max(1, coba_lagi)):
            mentah = baca_baris(self.kal.get("jeda_baca", 0.35))
            teks_terakhir = mentah
            kolom = pecah_kolom(mentah)

            if not kolom:
                continue  # kosong -> coba lagi

            self.jumlah_kolom_terbaca = len(kolom)

            # --- Ambil tanggal dari kolom yang ditentukan ---
            idx_tgl = int(self.kal.get("indeks_kolom_tanggal", 1))
            teks_tanggal = kolom[idx_tgl] if idx_tgl < len(kolom) else ""
            tanggal = parsing_tanggal(teks_tanggal)

            # Cadangan: kalau kolom tetap kosong, cari tanggal di kolom mana pun
            if tanggal is None:
                tanggal, teks_tanggal = cari_tanggal_dalam_teks(mentah)

            # --- Ambil no. transaksi dari kolom yang ditentukan ---
            idx_no = int(self.kal.get("indeks_kolom_transaksi", 0))
            no_transaksi = kolom[idx_no] if idx_no < len(kolom) else ""
            no_transaksi = no_transaksi.strip()

            if tanggal is not None:
                return {
                    "tanggal": tanggal,
                    "no_transaksi": no_transaksi or None,
                    "kolom": kolom,
                    "mentah": mentah,
                    "valid": True,
                    "kosong": False,
                }

        # Gagal membaca tanggal setelah beberapa percobaan.
        # "kosong" = clipboard benar-benar tidak berisi teks sama sekali
        #            (biasanya karena sudah mencapai baris/ tabel terakhir).
        # Bedakan dari kasus "ada teks tapi bukan tanggal" (baris rusak).
        return {
            "tanggal": None,
            "no_transaksi": None,
            "kolom": pecah_kolom(teks_terakhir),
            "mentah": teks_terakhir,
            "valid": False,
            "kosong": not teks_terakhir.strip(),
        }

    def turun_satu_baris(self):
        """
        Pindah fokus ke baris tabel berikutnya.
        Berdasarkan diagnosa: 8x TAB = turun 1 baris.
        """
        jumlah = int(self.kal.get("jumlah_tab_per_baris", 8))
        jeda = float(self.kal.get("jeda_per_tab", 0.25))
        for _ in range(jumlah):
            pyautogui.press("tab")
            time.sleep(jeda)

    def turun_satu_baris_dengan_panah(self):
        """
        Alternatif navigasi: tekan PANAH BAWAH sekali.
        Dipakai kalau TAB ternyata tidak memindahkan baris.
        """
        pyautogui.press("down")
        time.sleep(0.3)

    def pindai_halaman(self, maks_baris=15):
        """
        Membaca beberapa baris pertama pada halaman aktif.

        Mengembalikan list of dict (sama format baca_baris_sekarang),
        atau list kosong jika tidak ada yang terbaca.

        CATATAN PENTING: fungsi ini MENAIKKAN posisi baris. Setelah dipakai,
        Anda perlu mengembalikan fokus ke baris awal (lihat kembali_ke_awal).
        """
        hasil = []
        for _ in range(maks_baris):
            data = self.baca_baris_sekarang()
            if not data["valid"]:
                break
            hasil.append(data)
            self.turun_satu_baris()
        return hasil

    def naik_satu_baris(self):
        """Pindah fokus ke baris atas (membatalkan hasil turun_satu_baris)."""
        jumlah = int(self.kal.get("jumlah_tab_per_baris", 8))
        jeda = float(self.kal.get("jeda_per_tab", 0.25))
        for _ in range(jumlah):
            pyautogui.press("shift+tab")
            time.sleep(jeda)

    def cari_tanggal_di_halaman(self, tanggal_dicari, maks_baris=15):
        """
        Memindai halaman aktif untuk mencari tanggal tertentu.

        Mengembalikan:
            (ditemukan, posisi_baris, daftar_hasil_pindai)
            ditemukan     : True jika tanggal ada di halaman ini
            posisi_baris  : index baris (0-based) tempat tanggal ditemukan, atau None
        """
        hasil_pindai = []
        posisi = None

        for i in range(maks_baris):
            data = self.baca_baris_sekarang()
            if not data["valid"]:
                break
            hasil_pindai.append(data)
            if data["tanggal"] == tanggal_dicari and posisi is None:
                posisi = i
            self.turun_satu_baris()

        return (posisi is not None), posisi, hasil_pindai


# ==============================================================================
# PEMBUAT NAMA FILE
# ==============================================================================
def bersihkan_untuk_nama_file(teks):
    """Membersihkan teks agar aman dipakai sebagai nama file Windows."""
    if teks is None:
        return ""
    # Karakter yang dilarang Windows: \ / : * ? " < > |
    hasil = re.sub(r'[\\/:*?"<>|]', "-", str(teks))
    hasil = re.sub(r"\s+", " ", hasil).strip()
    return hasil[:120]  # batasi panjang nama file


def buat_nomor_urut(no_transaksi, jumlah_digit=3):
    """
    Mengubah no. transaksi panjang (mis: '210726100001') menjadi nomor urut 3 digit.
    Diambil dari 3 digit TERAKHIR, mengikuti kebiasaan aplikasi lama.
    Contoh: '210726100001' -> '001'
    """
    if not no_transaksi:
        return None
    digit = re.sub(r"\D", "", str(no_transaksi))
    if not digit:
        return None
    return digit[-jumlah_digit:]


def buat_nama_file(tanggal, no_transaksi, sumber="asli", counter_urut=None):
    """
    Membuat nama file PDF (tanpa ekstensi).

    Format sesuai permintaan Anda:  <tanggal>-<nomor>
      - sumber='asli' -> pakai no. transaksi asli dari tabel
                          contoh: 01-10-26-210726100001
      - sumber='urut' -> pakai hitungan 3 digit
                          contoh: 01-10-26-001
    """
    if tanggal is None:
        return None

    teks_tanggal = tanggal.strftime("%d-%m-%y")

    if sumber == "asli" and no_transaksi:
        nomor = bersihkan_untuk_nama_file(no_transaksi)
    elif counter_urut is not None:
        nomor = f"{counter_urut:03d}"
    elif no_transaksi:
        nomor = buat_nomor_urut(no_transaksi) or bersihkan_untuk_nama_file(no_transaksi)
    else:
        nomor = None

    nama = teks_tanggal if not nomor else f"{teks_tanggal}-{nomor}"
    return bersihkan_untuk_nama_file(nama)


def tanggal_sesudahnya(tanggal, jumlah_hari=1):
    """Mengembalikan tanggal + n hari (untuk auto-advance tanggal)."""
    if tanggal is None:
        return None
    from datetime import timedelta
    return tanggal + timedelta(days=jumlah_hari)


# ==============================================================================
# UJI MANDIRI (dijalankan: python pembaca_layar.py)
# ==============================================================================
if __name__ == "__main__":
    print("=" * 66)
    print(" UJI MODUL pembaca_layar.py (tanpa sentuh layar)")
    print("=" * 66)

    print("\n[1] Uji parsing_tanggal")
    uji_tanggal = [
        "01-10-2026", "1-10-26", "01/10/2026", "2026-10-01",
        "01.10.2026", "07 Okt 2026", "Oct 7, 2026",
        "bukan tanggal", "", "32-13-2026",
    ]
    for t in uji_tanggal:
        hasil = parsing_tanggal(t)
        print(f"    {t!r:<18} -> {hasil}")

    print("\n[2] Uji pecah_kolom (simulasi hasil Ctrl+C dari Takom)")
    simulasi = "210726100001\t01-10-2026\t2341\t11522170\tTAMAN KOMUNIKASI\tA\tB\tC"
    kol = pecah_kolom(simulasi)
    print(f"    Jumlah kolom: {len(kol)}")
    for i, k in enumerate(kol):
        print(f"      Kolom {i}: {k!r}")

    print("\n[3] Uji buat_nama_file")
    tgl = parsing_tanggal("01-10-2026")
    print(f"    sumber=asli -> {buat_nama_file(tgl, '210726100001', 'asli')}")
    print(f"    sumber=urut -> {buat_nama_file(tgl, '210726100001', 'urut', 7)}")

    print("\n[4] Uji buat_nomor_urut")
    for n in ["210726100001", "210726100012", "", None, "ABC"]:
        print(f"    {n!r:<16} -> {buat_nomor_urut(n)}")

    print("\n[5] Uji tanggal_sesudahnya")
    print(f"    01-10-2026 + 1 hari -> {tanggal_sesudahnya(tgl, 1)}")

    print("\n[6] Uji bersihkan_untuk_nama_file")
    for s in ['A/B:C*D', '  spasi   banyak  ']:
        print(f"    {s!r:<20} -> {bersihkan_untuk_nama_file(s)!r}")

    print("\n" + "=" * 66)
    print(" SELESAI - modul pembaca_layar.py berfungsi normal")
    print("=" * 66)
