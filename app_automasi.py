import os
import sys
import json
import time
import queue
import socket
import ctypes
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog
import pyautogui
from versi import __versi__
from pembaruan import cek_versi_terbaru

# Konversi nota A4 -> kertas thermal (tab Bulk Print Thermal).
try:
    import konversi_thermal
except Exception:  # pymupdf belum terpasang
    konversi_thermal = None

# Import DateEntry dari library tkcalendar
try:
    from tkcalendar import DateEntry
except ImportError:
    messagebox.showerror(
        "Library Kurang", 
        "Library 'tkcalendar' belum terinstal.\n\nJalankan perintah ini di CMD:\npip install tkcalendar"
    )

# =========================================================
# PERIHAL KEAMANAN (FAILSAFE)
# Geser kursor mouse secara cepat ke pojok KIRI-ATAS layar
# untuk menghentikan program secara paksa jika terjadi kendala.
# =========================================================
pyautogui.FAILSAFE = True

# Folder kerja: saat dijalankan sebagai .exe, pengaturan/log/gambar dibaca
# dari folder .exe; saat dijalankan sebagai skrip, dari folder skrip.
if getattr(sys, "frozen", False):
    FOLDER_APP = os.path.dirname(sys.executable)
else:
    FOLDER_APP = os.path.dirname(os.path.abspath(__file__))


def jalur_berkas(nama):
    """Cari berkas di folder kerja; bila tidak ada, pakai bawaan di dalam .exe."""
    jalur = os.path.join(FOLDER_APP, nama)
    if os.path.exists(jalur):
        return jalur
    bawaan = os.path.join(getattr(sys, "_MEIPASS", FOLDER_APP), nama)
    return bawaan if os.path.exists(bawaan) else jalur


NAMA_FILE_PENGATURAN = jalur_berkas("pengaturan.json")
NAMA_FILE_PROGRES = jalur_berkas("progres_automasi.json")
NAMA_FILE_LOG = jalur_berkas("automasi.log")

# Pengaturan bawaan. Bisa diubah lewat 'pengaturan.json'.
PENGATURAN_BAWAAN = {
    # Jumlah baris transaksi dalam satu halaman tabel Takom.
    # Sesuaikan bila jumlah baris per halaman berbeda.
    "transaksi_per_halaman": 10,
    # Tingkat keyakinan pencocokan gambar tombol (0.0 - 1.0).
    "confidence_gambar": 0.8,
    # Berapa kali tombol dicari ulang sebelum dianggap tidak ada.
    "percobaan_deteksi": 3,
    # Jeda (detik) setelah klik tombol NEXT sebelum lanjut.
    "jeda_setelah_next": 2.5,
    # Lama hitung mundur sebelum otomatisasi mulai (detik).
    "hitung_mundur": 5,
    # Simpan catatan aktivitas ke automasi.log.
    "simpan_log_file": True,
    # Simpan screenshot saat tombol gagal ditemukan.
    "simpan_screenshot_gagal": True,
    # Batas waktu (detik) menunggu tombol muncul di layar.
    "timeout_tombol": 20,
    # Batas waktu (detik) menunggu jendela/dialog baru muncul.
    "timeout_jendela": 20,
    # Batas waktu (detik) menunggu dialog/jendela tertutup.
    "timeout_tutup_jendela": 10,
    # Berapa kali satu transaksi diulang bila gagal.
    "retry_transaksi": 2,
    # Jeda (detik) memberi waktu aplikasi Java pulih sebelum diulang.
    "jeda_pemulihan": 30,
    # Jeda (detik) setelah dialog terdeteksi sebelum mulai mengetik.
    "jeda_dialog_siap": 0.6,
    # --- Tab Bulk Print Thermal ---
    "thermal": {
        # Lebar kertas thermal (mm) dan ukuran font (pt) hasil konversi.
        "lebar_mm": 80,
        "font_size": 9,
        # Judul tebal di paling atas (kosong = ikut PDF / bawaan modul).
        "judul": "PT KANISIUS TAMAN KOMUNIKASI",
        # Nama toko tambahan di bawah kop (kosongkan bila tidak perlu).
        "nama_toko": "Toko Rohani - TAKOM SANTO ANTONIUS",
        # Alamat/email/web/telepon cabang. Kosong = ikut data PDF nota.
        # Beberapa baris alamat dipisah '|' atau baris baru.
        "alamat": "",
        "email": "",
        "web": "",
        "telp": "",
        # Label kolom data nota.
        "label_no": "No.",
        "label_tgl": "Tgl.",
        "label_kasir": "Kasir",
        "label_cust": "Cust.",
        "label_telepon": "WA :",
        # Label baris total pembayaran.
        "label_total": "Total",
        "label_bayar": "Bayar",
        "label_kembali": "Kembali",
        # Baris keterangan pembayaran sebelum footer (kosongkan bila tidak perlu).
        "footer_edc": "EDC BCA TAKOM",
        # Dipakai bila ada kembalian (pembayaran tunai).
        "footer_cash": "CASH",
        # Ucapan penutup (boleh dikosongkan).
        "footer_1": "Terima Kasih Atas Kunjungan Anda",
        "footer_2": "Barang yang sudah dibeli",
        "footer_3": "tidak dapat ditukar/dikembalikan",
        # Nama kasir; kosong = pakai nama operator dari cap cetak PDF.
        "kasir": "",
        # Padanan nama operator PDF -> kode kasir di nota thermal.
        "peta_kasir": {"Stephanus Edward Saputro": "2341"},
        # Folder hasil konversi; kosong = subfolder 'thermal' di samping PDF asal.
        "folder_hasil": "",
        # Cetak otomatis ke printer default setelah konversi.
        "cetak_setelah_konversi": True,
        # Simpan PDF thermal ke disk. False = konversi di memori lalu langsung
        # dikirim ke antrean cetak tanpa menyimpan berkas.
        "simpan_pdf_thermal": True,
        # Nama printer tujuan; kosong = printer default Windows.
        "nama_printer": "",
        # Jeda (detik) antar dokumen saat mencetak berurutan.
        "jeda_antar_cetak": 2,
    },
    # Cek judul jendela sebelum mengetik (mencegah ketikan masuk ke jendela salah).
    "cek_jendela": True,
    # Verifikasi berkas PDF di folder tujuan.
    "verifikasi_file": True,
    # Folder tujuan penyimpanan PDF. Dipilih lewat dialog saat menekan
    # 'MULAI OTOMATISASI'; nilai terakhir dipakai sebagai pilihan awal.
    "folder_pdf": "",
    # Ingat folder penyimpanan per tanggal ("2026-10-01": "D:\\Laporan").
    "folder_pdf_per_tanggal": {},
    # True = dialog folder selalu muncul walau folder tanggal itu sudah diingat.
    "tanya_folder_setiap_kali": False,
}


# Susunan field pada jendela "Editor Format" tab Bulk Print Dokumen.
# (kunci di pengaturan.json, label, jenis widget)
SKEMA_EDITOR_THERMAL = (
    (
        "Kop Nota",
        (
            ("judul", "Judul tebal (dicetak huruf besar)", "entry"),
            ("nama_toko", "Nama toko di bawah judul", "entry"),
            (
                "alamat",
                "Alamat (pisah '|' atau baris baru; kosong = ikut PDF)",
                "text",
            ),
            ("email", "Email (kosong = ikut PDF)", "entry"),
            ("web", "Website (kosong = ikut PDF)", "entry"),
            ("telp", "No. WA/HP (kosong = ikut PDF)", "entry"),
            ("label_telepon", "Awalan nomor WA/HP", "entry"),
        ),
    ),
    (
        "Label Data Nota",
        (
            ("label_no", "Label nomor nota", "entry"),
            ("label_tgl", "Label tanggal", "entry"),
            ("label_kasir", "Label kasir", "entry"),
            ("label_cust", "Label pelanggan", "entry"),
        ),
    ),
    (
        "Label Pembayaran",
        (
            ("label_total", "Label total", "entry"),
            ("label_bayar", "Label bayar", "entry"),
            ("label_kembali", "Label kembali", "entry"),
            ("footer_edc", "Keterangan non-tunai (EDC)", "entry"),
            ("footer_cash", "Keterangan tunai (ada kembalian)", "entry"),
        ),
    ),
    (
        "Ucapan Penutup",
        (
            ("footer_1", "Baris 1 (kosongkan bila tidak perlu)", "entry"),
            ("footer_2", "Baris 2", "entry"),
            ("footer_3", "Baris 3", "entry"),
        ),
    ),
    (
        "Kasir",
        (
            ("kasir", "Kode kasir tetap (kosong = ikut PDF)", "entry"),
            (
                "peta_kasir",
                "Padanan nama operator = kode kasir (satu per baris)",
                "peta",
            ),
        ),
    ),
    (
        "Kertas & Ukuran",
        (
            ("lebar_mm", "Lebar kertas (mm)", "number"),
            ("font_size", "Ukuran font (pt)", "number"),
        ),
    ),
)


# ---------------------------------------------------------
# UTILITAS JENDELA (Windows, tanpa dependensi tambahan)
# Dipakai untuk mendeteksi aplikasi Java yang lambat / macet / terputus.
# ---------------------------------------------------------
JUDUL_JENDELA_TERSEDIA = hasattr(ctypes, "windll")

if JUDUL_JENDELA_TERSEDIA:
    try:
        _user32 = ctypes.windll.user32
        _user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
        _user32.GetWindowTextW.argtypes = [
            ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int
        ]
        _user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
        _user32.GetForegroundWindow.restype = ctypes.c_void_p
        _user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        _user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    except Exception:
        pass


def judul_jendela_aktif():
    """Judul jendela yang sedang fokus; string kosong bila gagal."""
    if not JUDUL_JENDELA_TERSEDIA:
        return ""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        panjang = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(panjang + 1)
        user32.GetWindowTextW(hwnd, buffer, panjang + 1)
        return buffer.value
    except Exception:
        return ""


def daftar_judul_jendela():
    """Seluruh judul jendela yang terlihat; None bila gagal dibaca."""
    if not JUDUL_JENDELA_TERSEDIA:
        return None
    judul = []
    try:
        user32 = ctypes.windll.user32
        tipe_callback = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
        )

        def kumpulkan(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                panjang = user32.GetWindowTextLengthW(hwnd)
                if panjang:
                    buffer = ctypes.create_unicode_buffer(panjang + 1)
                    user32.GetWindowTextW(hwnd, buffer, panjang + 1)
                    judul.append(buffer.value)
            return True

        user32.EnumWindows(tipe_callback(kumpulkan), 0)
    except Exception:
        return None
    return judul


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


if JUDUL_JENDELA_TERSEDIA:
    try:
        _user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    except Exception:
        pass


def cari_hwnd(judul):
    """Mencari handle jendela berdasarkan judul persis."""
    if not JUDUL_JENDELA_TERSEDIA or not judul:
        return None
    hasil = {"hwnd": None}
    try:
        user32 = ctypes.windll.user32
        tipe_callback = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
        )

        def cari(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                panjang = user32.GetWindowTextLengthW(hwnd)
                if panjang:
                    buffer = ctypes.create_unicode_buffer(panjang + 1)
                    user32.GetWindowTextW(hwnd, buffer, panjang + 1)
                    if buffer.value == judul:
                        hasil["hwnd"] = hwnd
                        return False
            return True

        user32.EnumWindows(tipe_callback(cari), 0)
        return hasil["hwnd"]
    except Exception:
        return None


def fokuskan_jendela(judul):
    """Membawa jendela dengan judul persis tertentu ke depan."""
    hwnd = cari_hwnd(judul)
    if not hwnd:
        return False
    try:
        user32 = ctypes.windll.user32
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        return bool(user32.SetForegroundWindow(hwnd))
    except Exception:
        return False


def klik_judul_jendela(judul):
    """Mengaktifkan jendela dengan mengeklik title bar-nya (cadangan)."""
    hwnd = cari_hwnd(judul)
    if not hwnd:
        return False
    try:
        user32 = ctypes.windll.user32
        rect = _RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        x = (rect.left + rect.right) // 2
        y = rect.top + 12  # area title bar
        if x <= 0 or y <= 0:
            return False
        posisi_awal = pyautogui.position()
        pyautogui.click(x, y)
        pyautogui.moveTo(posisi_awal)
        return True
    except Exception:
        return False


def ambil_angka(pengaturan, kunci, bawaan, tipe=float):
    """Mengambil nilai angka dari pengaturan dengan aman."""
    try:
        return tipe(pengaturan.get(kunci, bawaan))
    except (TypeError, ValueError):
        return bawaan


def muat_pengaturan():
    """Memuat pengaturan.json; membuat file bawaan bila belum ada."""
    pengaturan = dict(PENGATURAN_BAWAAN)
    if os.path.exists(NAMA_FILE_PENGATURAN):
        try:
            with open(NAMA_FILE_PENGATURAN, "r", encoding="utf-8") as f:
                isi = json.load(f)
            if isinstance(isi, dict):
                pengaturan.update(
                    {k: v for k, v in isi.items() if k in pengaturan}
                )
                # Bagian thermal digabung agar kunci baru tetap terpakai.
                if isinstance(isi.get("thermal"), dict):
                    pengaturan["thermal"] = {
                        **PENGATURAN_BAWAAN["thermal"],
                        **isi["thermal"],
                    }
        except Exception:
            pass  # file rusak -> pakai bawaan
    else:
        try:
            with open(NAMA_FILE_PENGATURAN, "w", encoding="utf-8") as f:
                json.dump(pengaturan, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return pengaturan


class AutoJasperApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Aplikasi Automasi Save PDF Jasper v{__versi__}")
        self.root.geometry("540x700")
        self.root.resizable(False, False)

        # Selalu tampil di depan, kecuali saat jendela di-minimize
        self.root.attributes("-topmost", True)
        self.root.bind("<Unmap>", self.saat_jendela_diperkecil)
        self.root.bind("<Map>", self.saat_jendela_dipulihkan)

        # Status kontrol thread
        self.is_running = False
        # Status proses tab Bulk Print Thermal
        self._thermal_aktif = False
        # Nilai slider disimpan agar bisa dibaca thread pekerja tanpa akses Tkinter
        self._delay_multiplier = 0.6
        # Judul jendela preview terakhir (untuk verifikasi saat menutup)
        self._judul_preview = ""
        # Judul jendela aplikasi Java (agar Escape tidak dikirim ke tabel)
        self._judul_aplikasi = ""
        # Judul jendela GUI ini, agar tidak dianggap sebagai dialog target
        self._judul_gui = self.root.title()

        # Pengaturan & antrean update UI dari thread pekerja
        self.pengaturan = muat_pengaturan()
        self.transaksi_per_halaman = max(
            1, ambil_angka(self.pengaturan, "transaksi_per_halaman", 10, int)
        )
        self._ui_queue = queue.Queue()
        self._log_lock = threading.Lock()
        self._progres_lock = threading.Lock()

        # Progres terakhir (untuk tombol Lanjutkan)
        self.progres = self.muat_progres()

        # --- TAMPILAN GUI ---
        self.create_widgets()
        self.perbarui_tombol_resume()
        self.root.after(100, self._proses_ui_queue)

        # Catat versi, lalu cek pembaruan di latar belakang (aman bila offline)
        self.log(f"Aplikasi versi {__versi__} dimulai")
        threading.Thread(target=self._cek_pembaruan, daemon=True).start()

    def _cek_pembaruan(self):
        tag, ada_update = cek_versi_terbaru()
        if ada_update:
            self.log(
                f"Tersedia versi baru {tag}. Tutup aplikasi lalu jalankan "
                "PASANG_atau_PERBARUI.bat untuk memperbarui."
            )

    def create_widgets(self):
        # Tab: automasi Jasper (lama) dan Bulk Print Thermal (baru)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, pady=(6, 0))
        self.tab_automasi = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_automasi, text=" Automasi Jasper ")

        # Header
        header_frame = ttk.Frame(self.tab_automasi, padding=10)
        header_frame.pack(fill="x")
        
        lbl_title = ttk.Label(
            header_frame, 
            text="Automasi Cetak Laporan PDF (Jasper)", 
            font=("Helvetica", 14, "bold")
        )
        lbl_title.pack(anchor="w")

        # Form Input Frame
        form_frame = ttk.LabelFrame(
            self.tab_automasi, text=" Pengaturan Automasi ", padding=12
        )
        form_frame.pack(fill="x", padx=15, pady=5)

        # 1. Input Tanggal Target (Toggle Calendar)
        ttk.Label(form_frame, text="Tanggal Target:").grid(row=0, column=0, sticky="w", pady=4)
        self.cal_tanggal = DateEntry(
            form_frame, 
            width=22, 
            background='#2c3e50',
            foreground='white', 
            bordercolor='#2c3e50',
            headersbackground='#34495e',
            headersforeground='white',
            date_pattern='dd-mm-yy',
            firstweekday='sunday'
        )
        self.cal_tanggal.grid(row=0, column=1, sticky="w", pady=4, padx=5)

        # 2. Input Rentang Nomor Transaksi
        ttk.Label(form_frame, text="No. Transaksi:").grid(row=1, column=0, sticky="w", pady=4)
        no_subframe = ttk.Frame(form_frame)
        no_subframe.grid(row=1, column=1, sticky="w", pady=4, padx=5)

        self.ent_no_awal = ttk.Entry(no_subframe, width=10)
        self.ent_no_awal.insert(0, "1")
        self.ent_no_awal.pack(side="left")

        ttk.Label(no_subframe, text="sampai").pack(side="left", padx=6)

        self.ent_no_akhir = ttk.Entry(no_subframe, width=10)
        self.ent_no_akhir.insert(0, "10")
        self.ent_no_akhir.pack(side="left")

        # 3. Jumlah Transaksi (otomatis dari rentang awal-akhir)
        ttk.Label(form_frame, text="Jumlah Transaksi:").grid(row=2, column=0, sticky="w", pady=4)
        self.lbl_jumlah_transaksi = ttk.Label(form_frame, text="10", font=("Helvetica", 9, "bold"))
        self.lbl_jumlah_transaksi.grid(row=2, column=1, sticky="w", pady=4, padx=5)

        self.ent_no_awal.bind("<KeyRelease>", self.update_jumlah_transaksi)
        self.ent_no_akhir.bind("<KeyRelease>", self.update_jumlah_transaksi)

        # 3b. Folder PDF yang diingat untuk tanggal terpilih
        ttk.Label(form_frame, text="Folder PDF:").grid(row=4, column=0, sticky="w", pady=4)
        self.lbl_folder_pdf = ttk.Label(
            form_frame, text="", font=("Helvetica", 8), wraplength=330
        )
        self.lbl_folder_pdf.grid(row=4, column=1, sticky="w", pady=4, padx=5)

        self.var_tanya_folder = tk.BooleanVar(
            value=bool(self.pengaturan.get("tanya_folder_setiap_kali", False))
        )
        self.chk_tanya_folder = ttk.Checkbutton(
            form_frame,
            text="Tanyakan folder setiap kali mulai",
            variable=self.var_tanya_folder,
            command=self._ubah_tanya_folder,
        )
        self.chk_tanya_folder.grid(row=5, column=1, sticky="w", padx=5)

        self.cal_tanggal.bind("<<DateEntrySelected>>", self.update_folder_pdf_label)
        self.update_folder_pdf_label()

        # 4. Pengaturan Kecepatan Automasi (Slider Jeda / Delay)
        ttk.Label(form_frame, text="Kecepatan Respon:").grid(row=3, column=0, sticky="w", pady=4)
        speed_subframe = ttk.Frame(form_frame)
        speed_subframe.grid(row=3, column=1, sticky="w", pady=4, padx=5)

        # Slider Nilai Multiplier Jeda (0.3x = Sangat Cepat, 1.0x = Normal)
        self.slider_speed = ttk.Scale(
            speed_subframe, 
            from_=0.3, 
            to=1.5, 
            value=0.6, 
            orient="horizontal", 
            length=130,
            command=self.update_label_speed
        )
        self.slider_speed.pack(side="left", padx=(0, 5))

        self.lbl_speed_val = ttk.Label(speed_subframe, text="Cepat (0.6x)", font=("Helvetica", 8, "bold"))
        self.lbl_speed_val.pack(side="left")

        # Frame Tombol Aksi
        btn_frame = ttk.Frame(self.tab_automasi, padding=10)
        btn_frame.pack(fill="x", padx=15)

        self.btn_start = tk.Button(
            btn_frame, 
            text="MULAI OTOMATISASI", 
            bg="#2ecc71", 
            fg="white", 
            font=("Helvetica", 10, "bold"),
            height=2,
            command=self.mulai_proses
        )
        self.btn_start.pack(fill="x", pady=4)

        self.btn_stop = tk.Button(
            btn_frame, 
            text="HENTIKAN PROSES", 
            bg="#e74c3c", 
            fg="white", 
            font=("Helvetica", 10, "bold"),
            height=1,
            state="disabled",
            command=self.hentikan_proses
        )
        self.btn_stop.pack(fill="x")

        self.btn_resume = tk.Button(
            btn_frame, 
            text="LANJUTKAN PROSES", 
            bg="#f39c12", 
            fg="white", 
            font=("Helvetica", 10, "bold"),
            height=1,
            state="disabled",
            command=self.lanjutkan_proses
        )
        self.btn_resume.pack(fill="x", pady=(4, 0))

        # Frame Status / Log Aktivitas
        log_frame = ttk.LabelFrame(
            self.tab_automasi, text=" Log Aktivitas ", padding=10
        )
        log_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.txt_log = tk.Text(log_frame, height=8, state="disabled", font=("Consolas", 9))
        self.txt_log.pack(fill="both", expand=True)

        # Tab kedua: konversi + cetak massal ke kertas thermal
        self.create_tab_thermal()

    # ------------------------------------------------------------------
    # TAB BULK PRINT THERMAL
    # ------------------------------------------------------------------
    def create_tab_thermal(self):
        """Membuat tab konversi nota A4 menjadi PDF kertas thermal."""
        self.tab_thermal = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_thermal, text=" Bulk Print Dokumen ")

        if konversi_thermal is None:
            ttk.Label(
                self.tab_thermal,
                text=(
                    "Fitur ini butuh library 'pymupdf'.\n\n"
                    "Jalankan di CMD:\npip install pymupdf"
                ),
                justify="left",
                padding=15,
            ).pack(anchor="w")
            return

        pengaturan_thermal = self.pengaturan.get("thermal", {})

        ttk.Label(
            self.tab_thermal,
            text=(
                "PDF nota A4 diubah ke format kertas thermal lebih dulu, "
                "lalu dicetak berurutan."
            ),
            wraplength=500,
            justify="left",
            padding=(12, 8, 12, 2),
        ).pack(anchor="w")

        # Daftar PDF yang akan diproses
        list_frame = ttk.LabelFrame(self.tab_thermal, text=" Daftar PDF ", padding=8)
        list_frame.pack(fill="both", expand=True, padx=12, pady=6)

        self.lst_pdf = tk.Listbox(
            list_frame, height=7, selectmode="extended", font=("Consolas", 8)
        )
        scroll = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.lst_pdf.yview
        )
        self.lst_pdf.config(yscrollcommand=scroll.set)
        self.lst_pdf.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        baris_tombol = ttk.Frame(self.tab_thermal)
        baris_tombol.pack(fill="x", padx=12)
        ttk.Button(
            baris_tombol, text="Tambah File...", command=self.tambah_file_thermal
        ).pack(side="left")
        ttk.Button(
            baris_tombol, text="Tambah Folder...", command=self.tambah_folder_thermal
        ).pack(side="left", padx=6)
        ttk.Button(
            baris_tombol, text="Hapus Terpilih", command=self.hapus_file_thermal
        ).pack(side="left")
        ttk.Button(
            baris_tombol, text="Kosongkan", command=self.kosongkan_file_thermal
        ).pack(side="left", padx=6)
        ttk.Button(
            baris_tombol, text="Editor Format...", command=self.editor_format_thermal
        ).pack(side="right")

        # Folder hasil konversi
        out_frame = ttk.Frame(self.tab_thermal)
        out_frame.pack(fill="x", padx=12, pady=(8, 0))
        ttk.Label(out_frame, text="Folder hasil:").pack(side="left")
        self.ent_folder_thermal = ttk.Entry(out_frame)
        self.ent_folder_thermal.pack(side="left", fill="x", expand=True, padx=6)
        self.ent_folder_thermal.insert(
            0, str(pengaturan_thermal.get("folder_hasil", "") or "")
        )
        ttk.Button(
            out_frame, text="Pilih...", command=self.pilih_folder_hasil_thermal
        ).pack(side="left")
        ttk.Label(
            self.tab_thermal,
            text=(
                "Kosongkan folder hasil = disimpan ke subfolder 'thermal' "
                "di samping PDF asal."
            ),
            font=("Helvetica", 8),
        ).pack(anchor="w", padx=12)

        self.var_simpan_thermal = tk.BooleanVar(
            value=bool(pengaturan_thermal.get("simpan_pdf_thermal", True))
        )
        ttk.Checkbutton(
            self.tab_thermal,
            text=(
                "Simpan file PDF hasil konversi "
                "(matikan = langsung ke antrean cetak)"
            ),
            variable=self.var_simpan_thermal,
        ).pack(anchor="w", padx=12, pady=(6, 0))

        self.var_cetak_thermal = tk.BooleanVar(
            value=bool(pengaturan_thermal.get("cetak_setelah_konversi", True))
        )
        ttk.Checkbutton(
            self.tab_thermal,
            text="Cetak otomatis ke printer default setelah konversi",
            variable=self.var_cetak_thermal,
        ).pack(anchor="w", padx=12, pady=(6, 0))

        aksi_frame = ttk.Frame(self.tab_thermal, padding=10)
        aksi_frame.pack(fill="x")
        self.btn_thermal_mulai = tk.Button(
            aksi_frame,
            text="MULAI KONVERSI & CETAK",
            bg="#2ecc71",
            fg="white",
            font=("Helvetica", 10, "bold"),
            height=2,
            command=self.mulai_thermal,
        )
        self.btn_thermal_mulai.pack(fill="x", pady=4)
        self.btn_thermal_stop = tk.Button(
            aksi_frame,
            text="HENTIKAN",
            bg="#e74c3c",
            fg="white",
            font=("Helvetica", 10, "bold"),
            state="disabled",
            command=self.hentikan_thermal,
        )
        self.btn_thermal_stop.pack(fill="x")

        self.btn_thermal_cetak = tk.Button(
            aksi_frame,
            text="CETAK HASIL KONVERSI",
            bg="#2980b9",
            fg="white",
            font=("Helvetica", 10, "bold"),
            command=self.cetak_hasil_thermal,
        )
        self.btn_thermal_cetak.pack(fill="x", pady=(4, 0))

        ttk.Label(
            self.tab_thermal,
            text=(
                "Cetak hasil: pilih file di daftar = cetak satuan, "
                "tanpa pilihan = cetak semua yang sudah dikonversi."
            ),
            font=("Helvetica", 8),
            wraplength=500,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(6, 0))

        self.lbl_thermal_status = ttk.Label(
            self.tab_thermal,
            text="Belum ada file dipilih.",
            font=("Helvetica", 9, "bold"),
        )
        self.lbl_thermal_status.pack(anchor="w", padx=12, pady=(0, 10))

    def tambah_file_thermal(self):
        """Menambahkan file PDF ke daftar."""
        daftar = filedialog.askopenfilenames(
            title="Pilih PDF nota", filetypes=[("PDF", "*.pdf")]
        )
        self._tambah_ke_daftar(daftar)

    def tambah_folder_thermal(self):
        """Menambahkan semua PDF di folder (termasuk subfolder)."""
        folder = filedialog.askdirectory(title="Pilih folder PDF nota")
        if not folder:
            return
        daftar = []
        for akar, _, file in os.walk(folder):
            for nama in file:
                rendah = nama.lower()
                # Lewati PDF hasil konversi sendiri agar tidak diproses ulang.
                if rendah.endswith(".pdf") and not rendah.endswith("_thermal.pdf"):
                    daftar.append(os.path.join(akar, nama))
        self._tambah_ke_daftar(sorted(daftar))

    def _tambah_ke_daftar(self, daftar):
        """Memasukkan file ke listbox tanpa duplikat."""
        yang_ada = set(self.lst_pdf.get(0, tk.END))
        for path in sorted(daftar):
            if path and path not in yang_ada:
                self.lst_pdf.insert(tk.END, path)
                yang_ada.add(path)
        jumlah = self.lst_pdf.size()
        self.lbl_thermal_status.config(text=f"{jumlah} file siap diproses.")

    def hapus_file_thermal(self):
        """Menghapus file yang dipilih dari daftar."""
        for indeks in reversed(self.lst_pdf.curselection()):
            self.lst_pdf.delete(indeks)
        self.lbl_thermal_status.config(
            text=f"{self.lst_pdf.size()} file siap diproses."
        )

    def kosongkan_file_thermal(self):
        """Mengosongkan daftar file."""
        self.lst_pdf.delete(0, tk.END)
        self.lbl_thermal_status.config(text="Belum ada file dipilih.")

    def pilih_folder_hasil_thermal(self):
        """Memilih folder hasil konversi."""
        folder = filedialog.askdirectory(title="Pilih folder hasil")
        if folder:
            self.ent_folder_thermal.delete(0, tk.END)
            self.ent_folder_thermal.insert(0, folder)

    def editor_format_thermal(self):
        """Membuka editor semua elemen teks format nota thermal."""
        thermal = dict(self.pengaturan.get("thermal", {}))
        bawaan = PENGATURAN_BAWAAN["thermal"]

        jendela = tk.Toplevel(self.root)
        jendela.title("Editor Format Nota Thermal")
        jendela.geometry("560x640")
        jendela.transient(self.root)
        jendela.attributes("-topmost", True)

        # Area isian yang bisa digulir.
        kanvas = tk.Canvas(jendela, borderwidth=0, highlightthickness=0)
        gulir = ttk.Scrollbar(jendela, orient="vertical", command=kanvas.yview)
        isi = ttk.Frame(kanvas)
        isi.bind(
            "<Configure>",
            lambda e: kanvas.configure(scrollregion=kanvas.bbox("all")),
        )
        kanvas.create_window((0, 0), window=isi, anchor="nw", width=520)
        kanvas.configure(yscrollcommand=gulir.set)
        kanvas.pack(side="left", fill="both", expand=True)
        gulir.pack(side="right", fill="y")

        def gulir_mouse(event):
            kanvas.yview_scroll(int(-event.delta / 120), "units")

        def lepas_mouse(event=None):
            if event is None or event.widget is jendela:
                jendela.unbind_all("<MouseWheel>")

        jendela.bind_all("<MouseWheel>", gulir_mouse)
        jendela.bind("<Destroy>", lepas_mouse)

        kolom_isian = {}
        for judul_bagian, daftar in SKEMA_EDITOR_THERMAL:
            kotak = ttk.LabelFrame(isi, text=f" {judul_bagian} ", padding=8)
            kotak.pack(fill="x", padx=10, pady=6)
            for kunci, label, jenis in daftar:
                ttk.Label(kotak, text=label, font=("Helvetica", 8)).pack(
                    anchor="w", pady=(4, 0)
                )
                nilai = thermal.get(kunci, bawaan.get(kunci, ""))
                if jenis == "peta":
                    wadah = tk.Text(kotak, height=4, font=("Consolas", 9), wrap="none")
                    teks = "\n".join(
                        f"{nama} = {kode}"
                        for nama, kode in (nilai or {}).items()
                    )
                    wadah.insert("1.0", teks)
                elif jenis == "text":
                    wadah = tk.Text(kotak, height=3, font=("Consolas", 9), wrap="word")
                    wadah.insert("1.0", str(nilai or ""))
                else:
                    wadah = ttk.Entry(kotak)
                    wadah.insert(0, "" if nilai is None else str(nilai))
                wadah.pack(fill="x")
                kolom_isian[kunci] = (wadah, jenis)

        tombol = ttk.Frame(jendela, padding=8)
        tombol.pack(side="bottom", fill="x")
        ttk.Button(
            tombol,
            text="Batal",
            command=jendela.destroy,
        ).pack(side="right", padx=(6, 0))
        ttk.Button(
            tombol,
            text="Simpan ke pengaturan.json",
            command=lambda: self._simpan_editor_thermal(jendela, kolom_isian),
        ).pack(side="right")

    def _simpan_editor_thermal(self, jendela, kolom_isian):
        """Menyimpan isian editor ke pengaturan.json."""
        thermal = dict(self.pengaturan.get("thermal", {}))
        for kunci, (wadah, jenis) in kolom_isian.items():
            if jenis in ("text", "peta"):
                nilai = wadah.get("1.0", "end").strip()
            else:
                nilai = wadah.get().strip()

            if jenis == "number":
                try:
                    angka = float(nilai.replace(",", "."))
                except ValueError:
                    messagebox.showwarning(
                        "Nilai tidak valid",
                        f"'{kunci}' harus berupa angka.",
                        parent=jendela,
                    )
                    return
                if angka <= 0:
                    messagebox.showwarning(
                        "Nilai tidak valid",
                        f"'{kunci}' harus lebih besar dari 0.",
                        parent=jendela,
                    )
                    return
                thermal[kunci] = int(angka) if angka == int(angka) else angka
            elif jenis == "peta":
                peta = {}
                for baris in nilai.splitlines():
                    if "=" in baris:
                        nama, kode = baris.split("=", 1)
                        if nama.strip():
                            peta[nama.strip()] = kode.strip()
                thermal[kunci] = peta
            else:
                thermal[kunci] = nilai

        self.pengaturan["thermal"] = thermal
        if not self.simpan_pengaturan():
            return
        jendela.destroy()
        self.lbl_thermal_status.config(
            text="Format nota disimpan ke pengaturan.json."
        )

    def simpan_pengaturan(self):
        """Menulis self.pengaturan ke pengaturan.json."""
        try:
            with open(NAMA_FILE_PENGATURAN, "w", encoding="utf-8") as f:
                json.dump(self.pengaturan, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror(
                "Gagal menyimpan",
                f"pengaturan.json tidak bisa ditulis:\n{e}",
            )
            return False

    def hentikan_thermal(self):
        """Menghentikan proses konversi/cetak massal."""
        self._thermal_aktif = False

    def _atur_tombol_thermal(self, aktif):
        """Mengatur tombol tab thermal saat proses berjalan/selesai."""
        kondisi = "disabled" if aktif else "normal"
        self.btn_thermal_mulai.config(state=kondisi)
        self.btn_thermal_cetak.config(state=kondisi)
        self.btn_thermal_stop.config(state="normal" if aktif else "disabled")

    def mulai_thermal(self):
        """Menjalankan konversi + cetak massal di background."""
        if self._thermal_aktif:
            return
        daftar = list(self.lst_pdf.get(0, tk.END))
        if not daftar:
            messagebox.showwarning(
                "Belum Ada File", "Tambahkan file PDF nota terlebih dahulu."
            )
            return

        self._thermal_aktif = True
        self._atur_tombol_thermal(True)

        folder = self.ent_folder_thermal.get().strip()
        simpan = bool(self.var_simpan_thermal.get())
        cetak = bool(self.var_cetak_thermal.get())

        # Pilihan disimpan agar dipakai lagi pada sesi berikutnya.
        thermal = self.pengaturan.setdefault("thermal", {})
        thermal["simpan_pdf_thermal"] = simpan
        thermal["cetak_setelah_konversi"] = cetak
        self.simpan_pengaturan()

        self.log("=" * 45)
        self.log(f"[THERMAL] Memproses {len(daftar)} file PDF nota.")
        if not simpan:
            self.log(
                "[THERMAL] Mode tanpa file: hasil konversi langsung masuk "
                "antrean cetak."
            )
        threading.Thread(
            target=self._kerja_thermal,
            args=(daftar, folder, cetak, simpan),
            daemon=True,
        ).start()

    def _kerja_thermal(self, daftar, folder, cetak, simpan=True):
        """Worker: konversi tiap PDF, simpan dan/atau langsung cetak."""
        pengaturan = dict(self.pengaturan.get("thermal", {}))
        jeda = max(0.0, ambil_angka(pengaturan, "jeda_antar_cetak", 2))
        berhasil = 0
        gagal = 0
        gagal_cetak = 0
        try:
            for nomor, sumber in enumerate(daftar, 1):
                if not self._thermal_aktif:
                    self.log("[THERMAL] Dihentikan oleh pengguna.")
                    break

                nama = os.path.basename(sumber)
                self._status_thermal(f"{nomor}/{len(daftar)}: {nama}")
                tujuan_folder = folder or os.path.join(
                    os.path.dirname(sumber), "thermal"
                )
                tujuan = konversi_thermal.nama_hasil(sumber, tujuan_folder)

                # Mode tanpa file: konversi di memori -> langsung ke antrean cetak.
                if not simpan:
                    try:
                        nota, printer = konversi_thermal.konversi_dan_cetak(
                            sumber, pengaturan, pengaturan.get("nama_printer", "")
                        )
                    except OSError as e:
                        gagal_cetak += 1
                        self.log(f"[GAGAL CETAK] {nama}: {e}")
                        continue
                    except Exception as e:  # file rusak / format berbeda
                        gagal += 1
                        self.log(f"[GAGAL] {nama}: {e}")
                        continue
                    berhasil += 1
                    self.log(
                        f"[{nomor}/{len(daftar)}] {nama} -> cetak langsung "
                        f"({len(nota.get('items') or [])} item) ke {printer}"
                    )
                    time.sleep(jeda)
                    continue

                try:
                    nota = konversi_thermal.konversi(sumber, tujuan, pengaturan)
                except Exception as e:  # file rusak / format berbeda
                    gagal += 1
                    self.log(f"[GAGAL] {nama}: {e}")
                    continue

                berhasil += 1
                self.log(
                    f"[{nomor}/{len(daftar)}] {nama} -> "
                    f"{os.path.basename(tujuan)} "
                    f"({len(nota.get('items') or [])} item)"
                )

                if cetak:
                    try:
                        printer = konversi_thermal.cetak_pdf(
                            tujuan, pengaturan.get("nama_printer", "")
                        )
                        self.log(f"[CETAK] -> {printer}")
                    except OSError as e:
                        gagal_cetak += 1
                        self.log(
                            f"[GAGAL CETAK] {os.path.basename(tujuan)}: {e}"
                        )
                    time.sleep(jeda)
        finally:
            self._thermal_aktif = False
            if simpan:
                self.log(
                    f"[SELESAI] Konversi berhasil {berhasil} file, gagal "
                    f"{gagal}; cetak gagal {gagal_cetak}."
                )
            else:
                self.log(
                    f"[SELESAI] Cetak langsung berhasil {berhasil} file, "
                    f"gagal {gagal}."
                )
            self._ui_queue.put(self._selesai_thermal)

    def _status_thermal(self, teks):
        """Memperbarui label status dari thread pekerja."""
        self._ui_queue.put(
            lambda t=teks: self.lbl_thermal_status.config(text=t)
        )

    def _selesai_thermal(self):
        """Mengembalikan tombol tab thermal setelah proses selesai."""
        self._atur_tombol_thermal(False)
        self.lbl_thermal_status.config(text="Selesai.")

    def cetak_hasil_thermal(self):
        """Mencetak PDF thermal hasil konversi (terpilih atau semua)."""
        if self._thermal_aktif:
            return
        semua = list(self.lst_pdf.get(0, tk.END))
        pilihan = [self.lst_pdf.get(i) for i in self.lst_pdf.curselection()]
        daftar = pilihan or semua
        if not daftar:
            messagebox.showwarning(
                "Belum Ada File", "Tambahkan file PDF nota terlebih dahulu."
            )
            return

        folder = self.ent_folder_thermal.get().strip()
        tujuan = []
        for sumber in daftar:
            folder_tujuan = folder or os.path.join(
                os.path.dirname(sumber), "thermal"
            )
            tujuan.append(konversi_thermal.nama_hasil(sumber, folder_tujuan))

        if not any(os.path.exists(path) for path in tujuan):
            messagebox.showwarning(
                "Belum Dikonversi",
                "PDF thermal hasil konversi belum ada. Jalankan konversi dulu.",
            )
            return

        self._thermal_aktif = True
        self._atur_tombol_thermal(True)
        self.log("=" * 45)
        self.log(f"[CETAK] Mencetak {len(tujuan)} file hasil konversi.")
        threading.Thread(
            target=self._kerja_cetak, args=(tujuan,), daemon=True
        ).start()

    def _kerja_cetak(self, tujuan):
        """Worker: mencetak PDF thermal hasil konversi."""
        pengaturan = dict(self.pengaturan.get("thermal", {}))
        jeda = max(0.0, ambil_angka(pengaturan, "jeda_antar_cetak", 2))
        berhasil = 0
        gagal = 0
        try:
            for nomor, path in enumerate(tujuan, 1):
                if not self._thermal_aktif:
                    self.log("[CETAK] Dihentikan oleh pengguna.")
                    break

                nama = os.path.basename(path)
                if not os.path.exists(path):
                    gagal += 1
                    self.log(f"[LEWATI] {nama}: belum dikonversi.")
                    continue

                self._status_thermal(f"{nomor}/{len(tujuan)}: {nama}")
                try:
                    printer = konversi_thermal.cetak_pdf(
                        path, pengaturan.get("nama_printer", "")
                    )
                    berhasil += 1
                    self.log(f"[CETAK] {nama} -> {printer}")
                except OSError as e:
                    gagal += 1
                    self.log(f"[GAGAL CETAK] {nama}: {e}")
                time.sleep(jeda)
        finally:
            self._thermal_aktif = False
            self.log(f"[SELESAI] Cetak berhasil {berhasil}, gagal {gagal}.")
            self._ui_queue.put(self._selesai_thermal)

    def saat_jendela_diperkecil(self, event=None):
        """Matikan always-on-top saat jendela di-minimize."""
        if self.root.state() == "iconic":
            self.root.attributes("-topmost", False)

    def saat_jendela_dipulihkan(self, event=None):
        """Aktifkan kembali always-on-top saat jendela dipulihkan."""
        self.root.attributes("-topmost", True)

    def update_jumlah_transaksi(self, event=None):
        """Menghitung jumlah transaksi dari rentang no. awal sampai no. akhir."""
        try:
            no_awal = int(self.ent_no_awal.get().strip())
            no_akhir = int(self.ent_no_akhir.get().strip())
            jumlah = no_akhir - no_awal + 1 if no_akhir >= no_awal else 0
            self.lbl_jumlah_transaksi.config(text=str(jumlah) if jumlah > 0 else "-")
        except ValueError:
            self.lbl_jumlah_transaksi.config(text="-")

    def update_label_speed(self, val):
        """Mengubah teks label saat slider kecepatan digeser"""
        val_float = float(val)
        self._delay_multiplier = val_float
        if val_float <= 0.4:
            txt = f"Sangat Cepat ({val_float:.1f}x)"
        elif val_float <= 0.7:
            txt = f"Cepat ({val_float:.1f}x)"
        elif val_float <= 1.1:
            txt = f"Sedang ({val_float:.1f}x)"
        else:
            txt = f"Lambat ({val_float:.1f}x)"
        self.lbl_speed_val.config(text=txt)

    def get_delay_multiplier(self):
        """Mengambil faktor pengali jeda waktu (thread-safe)."""
        return self._delay_multiplier

    # ------------------------------------------------------------------
    # UPDATE UI DARI THREAD PEKERJA (THREAD-SAFE)
    # ------------------------------------------------------------------
    def _proses_ui_queue(self):
        """Menjalankan pembaruan UI yang dikirim dari thread pekerja."""
        try:
            while True:
                aksi = self._ui_queue.get_nowait()
                try:
                    aksi()
                except Exception:
                    pass
        except queue.Empty:
            pass
        self.root.after(100, self._proses_ui_queue)

    def log(self, pesan):
        """Menampilkan pesan ke log dan (opsional) menulisnya ke file."""
        self._ui_queue.put(lambda p=pesan: self._tampilkan_log(p))
        if self.pengaturan.get("simpan_log_file", True):
            try:
                with self._log_lock:
                    with open(NAMA_FILE_LOG, "a", encoding="utf-8") as f:
                        f.write(
                            f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {pesan}\n"
                        )
            except Exception:
                pass

    def _tampilkan_log(self, pesan):
        self.txt_log.config(state="normal")
        self.txt_log.insert(tk.END, pesan + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state="disabled")

    # ------------------------------------------------------------------
    # KONFIGURASI & PROGRES
    # ------------------------------------------------------------------
    def muat_progres(self):
        """Memuat progres terakhir yang belum selesai (jika ada)."""
        if not os.path.exists(NAMA_FILE_PROGRES):
            return None
        try:
            with open(NAMA_FILE_PROGRES, "r", encoding="utf-8") as f:
                data = json.load(f)
            wajib = ("tanggal", "no_awal", "no_akhir", "no_terakhir")
            if not isinstance(data, dict) or any(k not in data for k in wajib):
                return None
            return data
        except Exception:
            return None

    def simpan_progres(self):
        """Menulis progres ke disk."""
        if not self.progres:
            return
        try:
            with open(NAMA_FILE_PROGRES, "w", encoding="utf-8") as f:
                json.dump(self.progres, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def siapkan_progres(self, tanggal_iso, no_awal, no_akhir):
        """Membuat catatan progres baru sebelum proses dimulai."""
        self.progres = {
            "tanggal": tanggal_iso,
            "no_awal": no_awal,
            "no_akhir": no_akhir,
            "no_terakhir": no_awal - 1,
            "selesai": False,
            "terakhir_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with self._progres_lock:
            self.simpan_progres()

    def catat_progres(self, no_terakhir, selesai=False):
        """Mencatat nomor transaksi terakhir yang berhasil."""
        if not self.progres:
            return
        with self._progres_lock:
            self.progres["no_terakhir"] = no_terakhir
            self.progres["selesai"] = selesai
            self.progres["terakhir_update"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self.simpan_progres()

    def perbarui_tombol_resume(self):
        """Mengaktifkan/menonaktifkan tombol Lanjutkan sesuai progres."""
        data = self.progres
        if not data:
            self.btn_resume.config(state="disabled", text="LANJUTKAN PROSES")
            return
        try:
            no_lanjut = int(data["no_terakhir"]) + 1
            no_akhir = int(data["no_akhir"])
        except (KeyError, TypeError, ValueError):
            self.btn_resume.config(state="disabled", text="LANJUTKAN PROSES")
            return

        if data.get("selesai") or no_lanjut > no_akhir:
            self.btn_resume.config(state="disabled", text="LANJUTKAN PROSES")
            return

        self.btn_resume.config(
            state="normal", text=f"LANJUTKAN PROSES (dari {no_lanjut})"
        )

    def lanjutkan_proses(self):
        """Mengisi form dari progres terakhir lalu memulai proses."""
        if self.is_running or not self.progres:
            return

        try:
            no_lanjut = int(self.progres["no_terakhir"]) + 1
            no_akhir = int(self.progres["no_akhir"])
            tanggal = datetime.strptime(self.progres["tanggal"], "%Y-%m-%d").date()
        except (KeyError, TypeError, ValueError):
            messagebox.showwarning(
                "Progres Tidak Valid", "Data progres tidak bisa dibaca."
            )
            return

        if no_lanjut > no_akhir:
            messagebox.showinfo(
                "Sudah Selesai", "Seluruh rentang transaksi sudah diproses."
            )
            return

        self.cal_tanggal.set_date(tanggal)
        self.ent_no_awal.delete(0, tk.END)
        self.ent_no_awal.insert(0, str(no_lanjut))
        self.ent_no_akhir.delete(0, tk.END)
        self.ent_no_akhir.insert(0, str(no_akhir))
        self.update_jumlah_transaksi()

        self.log("=" * 45)
        self.log(f"[RESUME] Melanjutkan dari transaksi {no_lanjut} sampai {no_akhir}.")
        self.log(
            f"PILIH/KLIK BARIS TRANSAKSI {no_lanjut} DI TABEL SEBELUM HITUNG MUNDUR SELESAI!"
        )
        self.log("=" * 45)
        self.mulai_proses()

    # ------------------------------------------------------------------
    # KONTROL PROSES
    # ------------------------------------------------------------------
    def baca_input(self):
        """Membaca dan memvalidasi input. Mengembalikan (awal, akhir) atau None."""
        try:
            no_awal = int(self.ent_no_awal.get().strip())
            no_akhir = int(self.ent_no_akhir.get().strip())
        except ValueError:
            messagebox.showerror(
                "Error Input", "No. Transaksi awal dan akhir harus berupa angka!"
            )
            return None

        if no_awal <= 0 or no_akhir < no_awal:
            messagebox.showerror(
                "Error Input",
                "No. Transaksi akhir harus lebih besar atau sama dengan no. awal!",
            )
            return None

        return no_awal, no_akhir

    def pilih_folder_pdf(self, tanggal_iso):
        """Menentukan folder tujuan PDF untuk tanggal tertentu.

        Bila folder tanggal itu sudah diingat (dan masih ada), dialog
        dilewati. Mengembalikan path folder, atau string kosong bila pengguna
        membatalkan dialog (otomatisasi tidak dijalankan).
        """
        diingat = self.folder_pdf_untuk(tanggal_iso)
        if diingat and not self.pengaturan.get("tanya_folder_setiap_kali", False):
            self.pengaturan["folder_pdf"] = diingat
            self.log(
                f"[INFO] Folder PDF tanggal {tanggal_iso} sudah diingat: {diingat}"
            )
            return diingat

        awal = diingat or str(self.pengaturan.get("folder_pdf", "") or "").strip()
        awal = os.path.expanduser(awal)
        if not os.path.isdir(awal):
            awal = os.path.expanduser("~")

        folder = filedialog.askdirectory(
            title=f"Pilih folder penyimpanan file PDF ({tanggal_iso})",
            initialdir=awal,
            mustexist=True,
        )
        if not folder:
            self.log(
                "[INFO] Folder penyimpanan tidak dipilih. "
                "Otomatisasi dibatalkan."
            )
            return ""

        folder = os.path.normpath(os.path.abspath(folder))
        self.pengaturan["folder_pdf"] = folder
        peta = self.pengaturan.get("folder_pdf_per_tanggal")
        if not isinstance(peta, dict):
            peta = {}
        peta[tanggal_iso] = folder
        self.pengaturan["folder_pdf_per_tanggal"] = peta
        self.simpan_pengaturan()
        self.update_folder_pdf_label()
        self.log(
            f"[INFO] Folder penyimpanan PDF tanggal {tanggal_iso}: {folder}"
        )
        return folder

    def folder_pdf_untuk(self, tanggal_iso):
        """Folder yang diingat untuk satu tanggal (kosong bila belum/tiada)."""
        peta = self.pengaturan.get("folder_pdf_per_tanggal")
        if not isinstance(peta, dict):
            return ""
        folder = str(peta.get(tanggal_iso, "") or "").strip()
        folder = os.path.expanduser(folder)
        return folder if folder and os.path.isdir(folder) else ""

    def tanggal_iso_terpilih(self):
        """Tanggal pada kalender dalam format ISO (dipakai sebagai kunci)."""
        return self.cal_tanggal.get_date().strftime("%Y-%m-%d")

    def update_folder_pdf_label(self, event=None):
        """Menampilkan folder PDF yang diingat untuk tanggal terpilih."""
        if not hasattr(self, "lbl_folder_pdf"):
            return
        folder = self.folder_pdf_untuk(self.tanggal_iso_terpilih())
        if folder:
            teks = f"{folder}  (dialog dilewati)"
        else:
            teks = "belum diatur - dialog folder akan muncul"
        self.lbl_folder_pdf.config(text=teks)

    def _ubah_tanya_folder(self):
        """Menyimpan pilihan 'tanyakan folder setiap kali mulai'."""
        self.pengaturan["tanya_folder_setiap_kali"] = bool(
            self.var_tanya_folder.get()
        )
        self.simpan_pengaturan()
        self.update_folder_pdf_label()

    def mulai_proses(self):
        """Menjalankan proses di background thread agar GUI tidak membeku."""
        if self.is_running:
            return

        data = self.baca_input()
        if not data:
            return
        no_awal, no_akhir = data

        tanggal_target = self.cal_tanggal.get_date()
        tanggal_iso = tanggal_target.strftime("%Y-%m-%d")
        tanggal = tanggal_target.strftime("%d-%m-%y")

        # Folder tujuan PDF ditentukan sebelum otomatisasi dimulai; dilewati
        # bila folder tanggal tersebut sudah diingat.
        if not self.pilih_folder_pdf(tanggal_iso):
            return
        self.is_running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.btn_resume.config(state="disabled")
        self.siapkan_progres(tanggal_iso, no_awal, no_akhir)

        thread = threading.Thread(
            target=self.jalankan_otomatisasi,
            args=(tanggal, no_awal, no_akhir),
            daemon=True,
        )
        thread.start()

    def hentikan_proses(self):
        """Menghentikan siklus otomatisasi."""
        self.is_running = False
        self.log("[INFO] Menghentikan proses otomatisasi...")
        if threading.current_thread() is threading.main_thread():
            self._set_ui_berhenti()
        else:
            self._ui_queue.put(self._set_ui_berhenti)

    def _set_ui_berhenti(self):
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.perbarui_tombol_resume()

    # ------------------------------------------------------------------
    # DETEKSI GAMBAR
    # ------------------------------------------------------------------
    def cari_gambar(self, nama_gambar):
        """Mencari gambar di layar dengan beberapa percobaan."""
        confidence = ambil_angka(self.pengaturan, "confidence_gambar", 0.8)
        percobaan = max(
            1, ambil_angka(self.pengaturan, "percobaan_deteksi", 3, int)
        )

        for i in range(percobaan):
            try:
                lokasi = pyautogui.locateOnScreen(
                    nama_gambar, confidence=confidence
                )
                if lokasi:
                    return lokasi
            except Exception as e:
                self.log(f"[ERROR] Gagal mendeteksi {nama_gambar}: {e}")
                return None
            if i < percobaan - 1:
                time.sleep(0.4)
        return None

    def simpan_screenshot_debug(self, label):
        """Menyimpan screenshot saat tombol gagal ditemukan."""
        if not self.pengaturan.get("simpan_screenshot_gagal", True):
            return
        nama = f"debug_{label}_{datetime.now():%Y%m%d_%H%M%S}.png"
        try:
            pyautogui.screenshot(nama)
            self.log(f"[INFO] Screenshot layar disimpan: {nama}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # PENANTIAN ADAPTIF (menggantikan jeda tetap)
    # ------------------------------------------------------------------
    def cek_jendela_aktif(self):
        """Apakah pengecekan judul jendela bisa dan ingin dilakukan."""
        return JUDUL_JENDELA_TERSEDIA and bool(
            self.pengaturan.get("cek_jendela", True)
        )

    def tunggu_gambar(self, nama_gambar, keterangan):
        """Menunggu gambar muncul di layar sampai batas waktu."""
        timeout = max(1.0, ambil_angka(self.pengaturan, "timeout_tombol", 20))
        batas = time.time() + timeout
        while self.is_running and time.time() < batas:
            lokasi = self.cari_gambar(nama_gambar)
            if lokasi:
                return lokasi
            time.sleep(0.2)
        if self.is_running:
            self.log(
                f"[PERINGATAN] {keterangan} tidak muncul dalam {timeout:.0f} detik."
            )
        return None

    def tunggu_jendela_berubah(self, judul_sebelum, keterangan, pola=None):
        """Menunggu jendela aktif berganti menjadi dialog yang diharapkan.

        `pola` membatasi judul yang diterima (mis. hanya dialog simpan), supaya
        jendela lain seperti GUI automasi ini tidak dianggap sebagai dialog.
        """
        timeout = max(1.0, ambil_angka(self.pengaturan, "timeout_jendela", 20))
        batas = time.time() + timeout
        while self.is_running and time.time() < batas:
            if pola:
                # Dialog bisa terbuka tanpa memegang fokus, jadi cari di semua
                # jendela yang terlihat (bukan hanya jendela aktif).
                for judul in daftar_judul_jendela() or []:
                    if (
                        judul != judul_sebelum
                        and judul != self._judul_gui
                        and any(p in judul.lower() for p in pola)
                    ):
                        return judul
            else:
                judul = judul_jendela_aktif()
                if judul and judul != judul_sebelum and judul != self._judul_gui:
                    return judul
            time.sleep(0.2)
        if self.is_running:
            self.log(
                f"[PERINGATAN] {keterangan} tidak terdeteksi dalam "
                f"{timeout:.0f} detik."
            )
        return None

    def tunggu_fokus(self, judul_target, keterangan):
        """Memberi waktu dialog siap, lalu memastikan fokus masih di sana.

        Mencegah ketikan masuk ke jendela lain saat aplikasi Java lambat atau
        saat dialog belum selesai dimuat.
        """
        if not self.cek_jendela_aktif():
            return True
        time.sleep(
            max(0.0, ambil_angka(self.pengaturan, "jeda_dialog_siap", 0.6))
            * self.get_delay_multiplier()
        )
        judul = judul_jendela_aktif()
        if not judul or judul == judul_target:
            return True

        # Fokus bisa direbut jendela lain (mis. GUI automasi yang always-on-top).
        self.log(
            f"[INFO] Fokus ada di '{judul}'. Mengembalikan fokus ke "
            f"{keterangan}..."
        )
        if fokuskan_jendela(judul_target) or klik_judul_jendela(judul_target):
            time.sleep(0.4 * self.get_delay_multiplier())
            judul = judul_jendela_aktif()
            if not judul or judul == judul_target:
                return True

        self.log(
            f"[GAGAL] Fokus tetap di '{judul}', bukan {keterangan}. "
            "Ketikan dibatalkan agar tidak masuk ke jendela lain."
        )
        self.simpan_screenshot_debug("fokus_berpindah")
        return False

    def tunggu_jendela_tertutup(self, judul, keterangan):
        """Menunggu jendela dengan judul tertentu hilang dari layar."""
        timeout = max(
            1.0, ambil_angka(self.pengaturan, "timeout_tutup_jendela", 10)
        )
        batas = time.time() + timeout
        while self.is_running and time.time() < batas:
            daftar = daftar_judul_jendela()
            if daftar is None:
                return True  # tidak bisa diperiksa -> jangan menghalangi alur
            if judul not in daftar:
                return True
            time.sleep(0.2)
        if self.is_running:
            self.log(
                f"[PERINGATAN] {keterangan} masih terbuka setelah "
                f"{timeout:.0f} detik."
            )
        return False

    def konfirmasi_timpa_file(self, judul_save):
        """Menerima dialog 'file sudah ada' bawaan Windows bila muncul."""
        if not self.cek_jendela_aktif():
            return
        judul = judul_jendela_aktif()
        if not judul or judul == judul_save:
            return
        kata_kunci = (
            "confirm", "konfirmasi", "simpan sebagai", "save as",
            "replace", "timpa",
        )
        if any(k in judul.lower() for k in kata_kunci):
            self.log(
                f"[INFO] Dialog konfirmasi terdeteksi ('{judul}'), "
                "menekan Enter untuk menerima."
            )
            pyautogui.press('enter')
            time.sleep(0.5 * self.get_delay_multiplier())

    def verifikasi_pdf(self, nama_file_saja):
        """Memastikan berkas PDF benar-benar tersimpan di folder tujuan."""
        if not self.pengaturan.get("verifikasi_file", True):
            return True
        folder = str(self.pengaturan.get("folder_pdf", "") or "").strip()
        if not folder:
            return True  # folder belum diisi -> tidak bisa diverifikasi
        jalur = os.path.join(os.path.expanduser(folder), f"{nama_file_saja}.pdf")
        try:
            return os.path.isfile(jalur) and os.path.getsize(jalur) > 0
        except OSError:
            return False

    def bersihkan_dialog(self):
        """Menutup dialog sisa agar percobaan ulang mulai dari kondisi bersih.

        Escape hanya dikirim bila fokus sedang berada di dialog/preview, supaya
        tabel aplikasi Java tidak ikut tertutup atau kehilangan pilihan baris.
        """
        mult = self.get_delay_multiplier()
        if not self.cek_jendela_aktif():
            pyautogui.press('escape')
            time.sleep(0.2 * mult)
            return

        judul = judul_jendela_aktif()
        if judul and judul != self._judul_aplikasi:
            for _ in range(2):
                pyautogui.press('escape')
                time.sleep(0.2 * mult)
                judul = judul_jendela_aktif()
                if not judul or judul in (
                    self._judul_aplikasi, self._judul_preview
                ):
                    break

        # Tutup preview yang masih terbuka. alt+f4 hanya dikirim saat fokus
        # bukan di aplikasi utama, agar aplikasi Java tidak ikut tertutup.
        for _ in range(3):
            if (
                not self._judul_preview
                or self._judul_preview == self._judul_aplikasi
                or self._judul_preview not in (daftar_judul_jendela() or [])
            ):
                break
            judul = judul_jendela_aktif()
            if not judul or judul == self._judul_aplikasi:
                self.log(
                    "[INFO] Jendela preview masih terbuka; tutup manual bila perlu."
                )
                break
            self.log("[INFO] Menutup jendela preview yang masih terbuka.")
            pyautogui.hotkey('alt', 'f4')
            time.sleep(0.4 * mult)

    def tunggu_pemulihan(self):
        """Jeda sebelum percobaan ulang, memberi waktu aplikasi Java pulih."""
        jeda = max(0.0, ambil_angka(self.pengaturan, "jeda_pemulihan", 30))
        if jeda <= 0:
            return self.is_running
        self.log(
            f"[JEDA] Menunggu {jeda:.0f} detik agar aplikasi Java pulih "
            "sebelum mencoba lagi..."
        )
        batas = time.time() + jeda
        while self.is_running and time.time() < batas:
            time.sleep(0.5)
        return self.is_running

    def klik_tombol_preview(self):
        """Mencari dan mengeklik tombol PRINT PREVIEW via 'tombol_preview.png'"""
        gambar = jalur_berkas('tombol_preview.png')
        if not os.path.exists(gambar):
            self.log("[ERROR] File 'tombol_preview.png' belum ada di folder aplikasi!")
            return False

        lokasi = self.tunggu_gambar(gambar, "Tombol PRINT PREVIEW")
        if lokasi:
            pyautogui.click(pyautogui.center(lokasi))
            return True

        self.log("[ERROR] Tombol PRINT PREVIEW tidak terlihat di layar!")
        self.simpan_screenshot_debug("preview")
        return False

    def klik_next_pagination(self, mult):
        """Mencari dan mengeklik tombol NEXT PAGINATION via 'tombol_next.png'"""
        gambar = jalur_berkas('tombol_next.png')
        if not os.path.exists(gambar):
            self.log("[INFO] File 'tombol_next.png' tidak ada. Lewati pagination.")
            return False

        lokasi_next = self.cari_gambar(gambar)
        if lokasi_next:
            pyautogui.click(pyautogui.center(lokasi_next))
            self.log("[INFO] Klik NEXT PAGINATION... Memuat halaman baru.")
            time.sleep(
                ambil_angka(self.pengaturan, "jeda_setelah_next", 2.5) * mult
            )
            return True

        self.log("[INFO] Tombol NEXT PAGINATION tidak ditemukan / Halaman Habis.")
        return False

    def pindah_ke_baris_berikutnya(self, mult):
        """Mengembalikan fokus ke tabel dengan tekan TAB 8x lalu PANAH BAWAH 1x"""
        for _ in range(8):
            pyautogui.press('tab')
            time.sleep(0.02 * mult)
        
        time.sleep(0.1 * mult)
        pyautogui.press('down')
        time.sleep(0.3 * mult)

    def proses_cetak_pdf(self, nama_file_saja, mult):
        """Proses pengerjaan PDF (Poin 2 - 8).

        Jeda tetap diganti penantian sampai kondisi terpenuhi, dan setiap
        langkah penting diverifikasi. Bila aplikasi Java lambat/macet, fungsi
        ini mengembalikan False (bukan mengetik buta ke jendela lain) supaya
        transaksi bisa diulang.
        """
        pyautogui.PAUSE = 0.2 * mult  # Jeda aksi internal pyautogui
        cek = self.cek_jendela_aktif()
        judul_awal = judul_jendela_aktif() if cek else ""
        if judul_awal:
            self._judul_aplikasi = judul_awal

        # 1. Klik Print Preview (Poin 2)
        if not self.klik_tombol_preview():
            return False

        # 2. Tunggu JasperViewer benar-benar terbuka
        if cek:
            judul_preview = self.tunggu_jendela_berubah(
                judul_awal, "Jendela preview Jasper"
            )
            if judul_preview:
                self._judul_preview = judul_preview
            else:
                time.sleep(1.2 * mult)  # deteksi gagal -> pakai jeda lama
        else:
            time.sleep(1.2 * mult)

        # 3. TAB -> SPASI untuk pemicu Print (Poin 3)
        judul_sebelum = judul_jendela_aktif() if cek else ""
        pyautogui.press('tab')
        time.sleep(0.1 * mult)
        pyautogui.press('space')

        # 4. Tunggu dialog Print muncul sebelum memilih printer
        if cek:
            judul_print = self.tunggu_jendela_berubah(
                judul_sebelum, "Dialog Print", pola=("print", "cetak")
            )
            if not judul_print:
                self.log(
                    "[GAGAL] Dialog Print tidak muncul. Aplikasi Java "
                    "kemungkinan lambat atau koneksinya terputus."
                )
                self.simpan_screenshot_debug("dialog_print")
                return False
            if not self.tunggu_fokus(judul_print, "dialog Print"):
                return False
        else:
            time.sleep(1.1 * mult)

        # 5. Pilih Printer Microsoft Print to PDF & Enter (Poin 4)
        pyautogui.write("Microsoft Print to PDF", interval=0.02 * mult)
        judul_sebelum_save = judul_jendela_aktif() if cek else ""
        pyautogui.press('enter')

        # 6. Tunggu dialog 'Save Print Output As' muncul (Poin 5)
        judul_save = ""
        if cek:
            judul_save = (
                self.tunggu_jendela_berubah(
                    judul_sebelum_save,
                    "Dialog Save Print Output As",
                    pola=("save print output as", "simpan cetak", "save as", "simpan sebagai"),
                )
                or ""
            )
            if not judul_save:
                self.log(
                    "[GAGAL] Dialog penyimpanan tidak muncul. Nama file "
                    "tidak diketik agar tidak masuk ke jendela yang salah."
                )
                self.simpan_screenshot_debug("dialog_save")
                return False
            if not self.tunggu_fokus(judul_save, "dialog penyimpanan"):
                return False
        else:
            time.sleep(1.6 * mult)

        # 7. Ketik Nama File Saja & Enter (Poin 6 - 7)
        # Alt+N memastikan kursor ada di kolom 'File name', Ctrl+A menghapus
        # isi lama, sehingga nama file selalu tertulis utuh.
        # Path lengkap diketik bila folder tujuan sudah dipilih, supaya PDF
        # masuk ke folder itu dan tidak bergantung pada folder terakhir Java.
        folder_pdf = str(self.pengaturan.get("folder_pdf", "") or "").strip()
        if folder_pdf:
            nama_ketik = os.path.join(os.path.expanduser(folder_pdf), nama_file_saja)
        else:
            nama_ketik = nama_file_saja

        pyautogui.hotkey('alt', 'n')
        time.sleep(0.2 * mult)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.1 * mult)
        pyautogui.write(nama_ketik, interval=0.02 * mult)
        time.sleep(0.3 * mult)
        pyautogui.press('enter')
        time.sleep(0.4 * mult)

        # Dialog 'file sudah ada' bisa muncul saat percobaan ulang
        self.konfirmasi_timpa_file(judul_save)

        # 8. Pastikan dialog simpan benar-benar tertutup
        if cek and judul_save:
            if not self.tunggu_jendela_tertutup(judul_save, "Dialog simpan"):
                self.log(
                    "[GAGAL] Dialog simpan masih terbuka. Proses "
                    "penyimpanan tidak selesai."
                )
                self.simpan_screenshot_debug("dialog_macet")
                return False
        else:
            time.sleep(1.0 * mult)  # Tunggu proses render PDF selesai

        # 9. Menutup JasperViewer (Poin 8)
        pyautogui.hotkey('alt', 'f4')
        time.sleep(0.5 * mult)  # Kembali ke jendela aplikasi Java

        # 10. Pastikan jendela preview benar-benar tertutup
        if cek and self._judul_preview:
            if not self.tunggu_jendela_tertutup(
                self._judul_preview, "Jendela preview Jasper"
            ):
                self.log(
                    "[GAGAL] Jendela preview masih terbuka. Transaksi "
                    "dianggap belum selesai."
                )
                self.simpan_screenshot_debug("preview_macet")
                return False

        # 11. Verifikasi berkas benar-benar tersimpan
        if not self.verifikasi_pdf(nama_file_saja):
            self.log(
                f"[GAGAL] File '{nama_file_saja}.pdf' tidak ditemukan di "
                "folder tujuan."
            )
            self.simpan_screenshot_debug("file_hilang")
            return False

        self.log(f"[BERHASIL] Tersimpan: {nama_file_saja}.pdf")
        return True

    def jalankan_otomatisasi(self, tanggal, no_awal, no_akhir):
        """Fungsi Utama Pengendali Alur (dijalankan di thread pekerja)."""
        jumlah_transaksi = no_akhir - no_awal + 1

        mult = self.get_delay_multiplier()

        self.log("=" * 45)
        self.log(f"Rentang transaksi: {no_awal} sampai {no_akhir} ({jumlah_transaksi} transaksi)")
        self.log(f"{self.transaksi_per_halaman} transaksi per halaman (pengaturan.json)")
        folder_pdf = str(self.pengaturan.get("folder_pdf", "") or "").strip()
        if folder_pdf:
            self.log(f"PDF disimpan ke folder: {folder_pdf}")
        else:
            self.log(
                "[PERINGATAN] Folder tujuan belum dipilih; PDF mengikuti "
                "folder terakhir aplikasi Java."
            )
        self.log("SEGERA BUKA & KLIK TABEL PADA APLIKASI JAVA!")
        if not self.cek_jendela_aktif():
            self.log(
                "[INFO] Pengecekan judul jendela nonaktif (cek_jendela=false "
                "atau bukan Windows)."
            )
        folder_pdf = str(self.pengaturan.get("folder_pdf", "") or "").strip()
        if self.pengaturan.get("verifikasi_file", True) and folder_pdf:
            self.log(f"[INFO] Verifikasi PDF di folder: {folder_pdf}")
        else:
            self.log(
                "[INFO] Verifikasi berkas nonaktif karena folder tujuan belum "
                "dipilih."
            )
        self.log("=" * 45)

        hitung_mundur = max(
            0, ambil_angka(self.pengaturan, "hitung_mundur", 5, int)
        )
        for i in range(hitung_mundur, 0, -1):
            if not self.is_running:
                return
            self.log(f"Memulai otomatisasi dalam {i} detik...")
            time.sleep(1)
        self.log("[INFO] Otomatisasi berjalan...\n")

        counter_transaksi = no_awal
        jumlah_diproses = 0
        halaman = 1

        while self.is_running and jumlah_diproses < jumlah_transaksi:
            self.log(f"=== Memproses Halaman {halaman} ===")

            # Sisa baris pada halaman aktif, supaya klik NEXT tepat di akhir halaman
            # (penting saat melanjutkan proses dari tengah halaman).
            sisa_di_halaman = self.transaksi_per_halaman - (
                (counter_transaksi - 1) % self.transaksi_per_halaman
            )
            item_di_halaman = min(
                sisa_di_halaman, jumlah_transaksi - jumlah_diproses
            )

            for item in range(1, item_di_halaman + 1):
                if not self.is_running:
                    break

                # Ambil nilai terbaru slider kecepatan jika pengguna mengubahnya di tengah jalan
                mult = self.get_delay_multiplier()

                digit_3 = f"{counter_transaksi:03d}"
                nama_file_saja = f"{tanggal}-{digit_3}"

                self.log(
                    f"-> Transaksi [{counter_transaksi}] "
                    f"({jumlah_diproses + 1}/{jumlah_transaksi})..."
                )

                # Coba ulang transaksi yang sama bila aplikasi Java lambat/macet,
                # supaya satu kendala sementara tidak membatalkan seluruh proses.
                maks_percobaan = 1 + max(
                    0, ambil_angka(self.pengaturan, "retry_transaksi", 2, int)
                )
                sukses = False
                for percobaan in range(1, maks_percobaan + 1):
                    if not self.is_running:
                        break
                    sukses = self.proses_cetak_pdf(nama_file_saja, mult)
                    if sukses:
                        break
                    if percobaan < maks_percobaan:
                        self.log(
                            f"[ULANG] Percobaan {percobaan}/{maks_percobaan} "
                            f"gagal. Mencoba lagi transaksi "
                            f"[{counter_transaksi}]..."
                        )
                        self.bersihkan_dialog()
                        if not self.tunggu_pemulihan():
                            break

                if not self.is_running:
                    break

                if not sukses:
                    self.log("[STOP] Proses terhenti karena kendala pada alur.")
                    self.catat_progres(counter_transaksi - 1, selesai=False)
                    self.hentikan_proses()
                    return

                counter_transaksi += 1
                jumlah_diproses += 1
                self.catat_progres(counter_transaksi - 1)

                # Navigasi TAB 8x + DOWN 1x untuk pindah baris
                self.pindah_ke_baris_berikutnya(mult)

            if jumlah_diproses < jumlah_transaksi and self.is_running:
                berhasil_next = self.klik_next_pagination(mult)
                if not berhasil_next:
                    self.log("[STOP] Data pada tanggal terpilih sudah habis.")
                    break

            halaman += 1

        selesai = jumlah_diproses >= jumlah_transaksi
        self.catat_progres(counter_transaksi - 1, selesai=selesai)

        if selesai:
            self.log("\n[SELESAI] Seluruh proses telah berakhir.")
        else:
            self.log(
                "\n[BERHENTI] Proses belum selesai. "
                "Gunakan tombol LANJUTKAN PROSES untuk melanjutkan."
            )
        self.hentikan_proses()


if __name__ == "__main__":
    # Cegah dua instance berjalan bersamaan (bisa saling menimpa ketikan/klik).
    kunci_instance = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        kunci_instance.bind(("127.0.0.1", 47653))
    except OSError:
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "Aplikasi Sudah Berjalan",
            "Aplikasi automasi ini sudah terbuka.\n"
            "Tutup instance sebelumnya terlebih dahulu.",
        )
        root.destroy()
        sys.exit(0)

    root = tk.Tk()
    app = AutoJasperApp(root)
    root.mainloop()
