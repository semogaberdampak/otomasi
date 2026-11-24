"""Konversi nota PDF A4 (laporan Jasper Takom) ke format kertas thermal.

Alur: baca elemen nota (kop, nomor, tanggal, pelanggan, item, total) memakai
koordinat teks PDF, lalu susun ulang menjadi baris teks monospace selebar
kertas thermal dan tulis sebagai PDF baru.
"""

import ctypes
import os
import re
from ctypes import wintypes

import pymupdf

# --- API Windows untuk mencetak langsung tanpa aplikasi PDF ---
_AKTIF_WINDOWS = os.name == "nt"
if _AKTIF_WINDOWS:
    _winspool = ctypes.WinDLL("winspool.drv")
    _gdi32 = ctypes.WinDLL("gdi32")

    _winspool.GetDefaultPrinterW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p]

    _gdi32.CreateDCW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_void_p,
    ]
    _gdi32.CreateDCW.restype = ctypes.c_void_p
    _gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
    _gdi32.GetDeviceCaps.argtypes = [ctypes.c_void_p, ctypes.c_int]
    _gdi32.StartPage.argtypes = [ctypes.c_void_p]
    _gdi32.EndPage.argtypes = [ctypes.c_void_p]
    _gdi32.EndDoc.argtypes = [ctypes.c_void_p]
    _gdi32.SetStretchBltMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
    _gdi32.StretchDIBits.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    _gdi32.StretchDIBits.restype = ctypes.c_int

    class _DOCINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_int),
            ("lpszDocName", ctypes.c_wchar_p),
            ("lpszOutput", ctypes.c_wchar_p),
            ("lpszDatatype", ctypes.c_wchar_p),
            ("fwType", ctypes.c_uint),
            ("cbData", ctypes.c_uint),
        ]

    _gdi32.StartDocW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_DOCINFOW)]

    class _RGBQUAD(ctypes.Structure):
        _fields_ = [
            ("rgbBlue", ctypes.c_ubyte),
            ("rgbGreen", ctypes.c_ubyte),
            ("rgbRed", ctypes.c_ubyte),
            ("rgbReserved", ctypes.c_ubyte),
        ]

    class _BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", ctypes.c_uint),
            ("biWidth", ctypes.c_long),
            ("biHeight", ctypes.c_long),
            ("biPlanes", ctypes.c_ushort),
            ("biBitCount", ctypes.c_ushort),
            ("biCompression", ctypes.c_uint),
            ("biSizeImage", ctypes.c_uint),
            ("biXPelsPerMeter", ctypes.c_long),
            ("biYPelsPerMeter", ctypes.c_long),
            ("biClrUsed", ctypes.c_uint),
            ("biClrImportant", ctypes.c_uint),
        ]

    class _BITMAPINFO(ctypes.Structure):
        _fields_ = [
            ("bmiHeader", _BITMAPINFOHEADER),
            ("bmiColors", _RGBQUAD * 256),
        ]


# Lebar kertas thermal bawaan (mm) dan ukuran font (pt).
LEBAR_MM_BAWAAN = 80
FONT_BAWAAN = 9
# Margin kiri/kanan halaman thermal (pt).
MARGIN_PT = 10.0
# Judul toko dicetak lebih besar dari teks isi.
SKALA_JUDUL = 1.3

JUDUL_BAWAAN = "PT KANISIUS TAMAN KOMUNIKASI"

# Elemen teks format nota thermal beserta nilai bawaannya.
# Semua bisa diubah lewat tombol "Editor Format" di tab Bulk Print Dokumen.
BAWAAN_FORMAT = {
    "judul": JUDUL_BAWAAN,
    "label_no": "No.",
    "label_tgl": "Tgl.",
    "label_kasir": "Kasir",
    "label_cust": "Cust.",
    "label_telepon": "WA :",
    "label_total": "Total",
    "label_bayar": "Bayar",
    "label_kembali": "Kembali",
    "footer_edc": "EDC BCA TAKOM",
    "footer_cash": "CASH",
    "footer_1": "Terima Kasih Atas Kunjungan Anda",
    "footer_2": "Barang yang sudah dibeli",
    "footer_3": "tidak dapat ditukar/dikembalikan",
}


def _format(pengaturan, kunci):
    """Mengambil elemen teks format; kosong/tiada = nilai bawaan."""
    nilai = pengaturan.get(kunci)
    if nilai is None or not str(nilai).strip():
        return BAWAAN_FORMAT.get(kunci, "")
    return str(nilai).strip()


def _daftar_baris(nilai):
    """Mengubah teks pengaturan menjadi daftar baris.

    Boleh dipisah baris baru atau tanda '|'. Contoh: 'Jl. A|Surakarta'.
    """
    if not nilai:
        return []
    teks = str(nilai).replace("\r", "")
    potong = teks.split("\n") if "\n" in teks else teks.split("|")
    return [t.strip() for t in potong if t.strip()]

# Batas kolom kanan (angka) sebagai pecahan lebar halaman A4.
BATAS_HARGA = 0.630
BATAS_QTY = 0.698
BATAS_DISC = 0.763
BATAS_PPN = 0.870


def _angka(teks):
    """Mengubah '72.072' / '80,000' menjadi 72072 / 80000."""
    if teks is None:
        return None
    bersih = re.sub(r"[^\d-]", "", str(teks))
    if bersih in ("", "-"):
        return None
    try:
        return int(bersih)
    except ValueError:
        return None


def _rupiah(nilai):
    """Format angka gaya nota: 271998 -> '271.998'."""
    if nilai is None:
        return "0"
    return f"{int(nilai):,}".replace(",", ".")


def _baris_kata(kata, toleransi=3.0):
    """Mengelompokkan kata menjadi baris berdasarkan koordinat Y."""
    baris = []
    for w in sorted(kata, key=lambda w: (round(w[1], 1), w[0])):
        if baris and abs(w[1] - baris[-1]["y"]) <= toleransi:
            baris[-1]["kata"].append(w)
        else:
            baris.append({"y": w[1], "kata": [w]})
    for b in baris:
        b["kata"].sort(key=lambda w: w[0])
    return baris


def _teks(kata):
    return " ".join(w[4] for w in kata).strip()


def _nilai_kolom(kata, lebar):
    """Memisahkan kata satu baris item menjadi kolom-kolomnya."""
    kode, nama = "", []
    harga = qty = disc = ppn = sub = None
    for w in kata:
        x1, teks = w[2], w[4]
        if x1 <= 0.13 * lebar:
            kode = teks
            continue
        if not re.fullmatch(r"[\d.,]+", teks):
            nama.append(teks)
            continue
        rasio = x1 / lebar
        if rasio < BATAS_HARGA:
            harga = _angka(teks)
        elif rasio < BATAS_QTY:
            qty = _angka(teks)
        elif rasio < BATAS_DISC:
            disc = _angka(teks)
        elif rasio < BATAS_PPN:
            ppn = _angka(teks)
        else:
            sub = _angka(teks)
    return kode, " ".join(nama), harga, qty, disc, ppn, sub


def baca_nota(path):
    """Membaca satu PDF nota. Mengembalikan dict data nota."""
    with pymupdf.open(path) as dokumen:
        if not dokumen.page_count:
            raise ValueError("PDF tidak memiliki halaman.")
        if dokumen[0].rect.width < 300:
            raise ValueError(
                "PDF ini sudah berformat thermal (bukan nota A4)."
            )
        nota = {
            "sumber": path,
            "halaman": dokumen.page_count,
            "judul": "",
            "alamat": [],
            "telp": "",
            "email": "",
            "web": "",
            "nomor": "",
            "tanggal": "",
            "pelanggan": "",
            "kasir": "",
            "items": [],
            "total": None,
            "bayar": None,
            "kembali": None,
        }
        for nomor_hal, halaman in enumerate(dokumen):
            lebar = halaman.rect.width
            baris = _baris_kata(halaman.get_text("words"))
            if not baris:
                continue

            # Baris judul kolom tabel item (Kode / Barang / Harga ...).
            y_tabel = None
            for b in baris:
                teks = _teks(b["kata"]).lower()
                if "kode" in teks and "barang" in teks:
                    y_tabel = b["y"]
                    break

            if nomor_hal == 0:
                batas_header = y_tabel if y_tabel is not None else 0
                _baca_header(nota, baris, batas_header, lebar)

            _baca_item(nota, baris, y_tabel, lebar)
        return nota


def _baca_header(nota, baris, batas, lebar):
    """Mengisi kop, nomor, tanggal, pelanggan, dan nama kasir."""
    kata_header = []
    for b in baris:
        if b["y"] >= batas:
            continue
        teks = _teks(b["kata"])
        if teks.count("/") >= 2 and re.search(r"\d{2}:\d{2}", teks):
            # Cap cetak: "Nama / Divisi / YYYY-MM-DD HH:MM:SS"
            nota["kasir"] = teks.split("/")[0].strip()
            continue
        kata_header.extend(b["kata"])

    kiri = _baris_kata([w for w in kata_header if w[0] < 0.5 * lebar])
    kanan = _baris_kata([w for w in kata_header if w[0] >= 0.5 * lebar])

    for b in kiri:
        teks = _teks(b["kata"])
        rendah = teks.lower()
        if not nota["judul"]:
            nota["judul"] = teks
            continue
        if "email" in rendah or "web" in rendah:
            cocok = re.search(r"email\s*:\s*([^\s|]+)", teks, re.I)
            if cocok:
                nota["email"] = cocok.group(1)
            cocok = re.search(r"web\s*:\s*([^\s|]+)", teks, re.I)
            if cocok:
                nota["web"] = cocok.group(1)
            continue
        if re.search(r"\b(telp|wa|phone)\b", rendah):
            cocok = re.search(r"([\d\s\-+()]{6,})$", teks)
            if cocok:
                nota["telp"] = cocok.group(1).strip()
            continue
        if not re.search(r"\d{2}:\d{2}", teks):
            nota["alamat"].append(teks)

    sudah_kepada = False
    for b in kanan:
        teks = _teks(b["kata"])
        rendah = teks.lower()
        if "nomor" in rendah:
            nota["nomor"] = teks.split(":", 1)[-1].strip()
        elif "tanggal" in rendah:
            nota["tanggal"] = teks.split(":", 1)[-1].strip()
        elif "kepada" in rendah:
            nilai = teks.split(":", 1)[-1].strip()
            nota["pelanggan"] = nilai
            sudah_kepada = True
        elif sudah_kepada and not re.search(r"\d{2}:\d{2}", teks):
            # Lanjutan nama pelanggan yang terpotong ke baris berikutnya.
            nota["pelanggan"] = (nota["pelanggan"] + " " + teks).strip()


def _baca_item(nota, baris, y_tabel, lebar):
    """Mengisi daftar item dan baris total/bayar/kembali."""
    if y_tabel is None:
        return
    for b in baris:
        if b["y"] <= y_tabel:
            continue
        teks_awal = _teks(b["kata"])
        rendah = teks_awal.lower()

        if rendah.startswith(("total", "pembayaran", "bayar", "kembalian")):
            nilai = [w for w in b["kata"] if w[0] >= 0.7 * lebar]
            angka = _angka(_teks(nilai)) if nilai else None
            if rendah.startswith("total"):
                nota["total"] = angka
            elif rendah.startswith(("pembayaran", "bayar")):
                nota["bayar"] = angka
            else:
                nota["kembali"] = angka
                # Baris setelah 'Kembalian' adalah footer, bukan item.
                break
            continue

        kode, nama, harga, qty, disc, ppn, sub = _nilai_kolom(b["kata"], lebar)
        if kode:
            nota["items"].append(
                {
                    "kode": kode,
                    "nama": nama,
                    "harga": harga,
                    "qty": qty if qty is not None else 1,
                    "disc": disc or 0,
                    "ppn": ppn,
                    "sub": sub if sub is not None else harga,
                }
            )
        elif nama and nota["items"]:
            item = nota["items"][-1]
            item["nama"] = (item["nama"] + " " + nama).strip()


def _cari_peta_kasir(peta, nama):
    """Mencari padanan nama kasir pada peta (abaikan spasi/huruf besar)."""
    if not isinstance(peta, dict) or not nama:
        return ""
    kunci = " ".join(nama.lower().split())
    for nama_pdf, kode in peta.items():
        if " ".join(str(nama_pdf).lower().split()) == kunci:
            return str(kode).strip()
    return ""


def _potong(teks, lebar):
    """Memotong teks menjadi beberapa baris sepanjang `lebar` karakter."""
    teks = teks.strip()
    if not teks:
        return []
    hasil = []
    while len(teks) > lebar:
        potong = teks[:lebar]
        spasi = potong.rfind(" ")
        if spasi > lebar // 2:
            hasil.append(potong[:spasi].rstrip())
            teks = teks[spasi + 1 :].lstrip()
        else:
            hasil.append(potong)
            teks = teks[lebar:]
    hasil.append(teks)
    return hasil


def susun_baris(nota, pengaturan=None):
    """Menyusun isi nota menjadi daftar baris monospace."""
    pengaturan = pengaturan or {}
    lebar_mm = float(pengaturan.get("lebar_mm", LEBAR_MM_BAWAAN))
    font = float(pengaturan.get("font_size", FONT_BAWAAN))

    # Lebar efektif kertas dalam satuan karakter monospace.
    lebar_pt = lebar_mm * 72 / 25.4
    margin = MARGIN_PT
    kolom = max(20, int((lebar_pt - 2 * margin) / (0.6 * font)))

    baris = []  # daftar (teks, rata)

    def tambah(teks="", rata="kiri"):
        baris.append((teks, rata))

    # --- Kop ---
    judul = (pengaturan.get("judul") or nota.get("judul") or JUDUL_BAWAAN).strip()
    tambah(judul.upper(), "judul")
    nama_toko = (pengaturan.get("nama_toko") or "").strip()
    if nama_toko:
        tambah(nama_toko, "tengah")
    # Alamat/email/web/telepon: isi di pengaturan = pakai itu (cabang lain),
    # kosong = ikut data dari PDF nota.
    alamat = _daftar_baris(pengaturan.get("alamat")) or (nota.get("alamat") or [])
    for teks in alamat:
        for potong in _potong(teks, kolom):
            tambah(potong, "tengah")
    email = (pengaturan.get("email") or nota.get("email") or "").strip()
    if email:
        tambah(email, "tengah")
    web = (pengaturan.get("web") or nota.get("web") or "").strip()
    if web:
        tambah(web, "tengah")
    telp = (pengaturan.get("telp") or nota.get("telp") or "").strip()
    if telp:
        tambah(f"{_format(pengaturan, 'label_telepon')} {telp}", "tengah")

    tambah("-" * kolom)

    # --- Nomor, tanggal, kasir, pelanggan ---
    if nota.get("nomor"):
        tambah(f"{_format(pengaturan, 'label_no'):<6}: {nota['nomor']}")
    if nota.get("tanggal"):
        tambah(f"{_format(pengaturan, 'label_tgl'):<6}: {nota['tanggal']}")
    kasir = (pengaturan.get("kasir") or "").strip()
    if not kasir:
        kasir = _cari_peta_kasir(
            pengaturan.get("peta_kasir"), nota.get("kasir") or ""
        ) or (nota.get("kasir") or "").strip()
    if kasir:
        tambah(f"{_format(pengaturan, 'label_kasir'):<6}: {kasir}")
    if nota.get("pelanggan"):
        pelanggan = _potong(nota["pelanggan"], kolom - 8)
        tambah(f"{_format(pengaturan, 'label_cust'):<6}: {pelanggan[0]}")
        for lanjutan in pelanggan[1:]:
            tambah(" " * 8 + lanjutan)

    tambah("-" * kolom)

    # --- Item ---
    for item in nota.get("items") or []:
        tambah(item.get("kode", ""))
        for potong in _potong(item.get("nama", ""), kolom):
            tambah(potong)
        kiri = (
            f"{item.get('qty', 1):>4}"
            f"{_rupiah(item.get('harga') or item.get('sub')):>12}"
            f"{item.get('disc', 0):>4}%"
        )
        # Nominal item rata kanan seperti nota kasir.
        tambah(f"{kiri}{_rupiah(item.get('sub')):>{max(10, kolom - len(kiri))}}")

    tambah("-" * kolom)

    # --- Total ---
    tambah(f"{_format(pengaturan, 'label_total'):<8}: {_rupiah(nota.get('total'))}")
    if nota.get("bayar") is not None:
        tambah(f"{_format(pengaturan, 'label_bayar'):<8}: {_rupiah(nota.get('bayar'))}")
    if nota.get("kembali") is not None:
        tambah(f"{_format(pengaturan, 'label_kembali'):<8}: {_rupiah(nota.get('kembali'))}")
    # Ada kembalian (uang tunai) -> CASH, tanpa kembalian -> EDC BCA TAKOM.
    if (nota.get("kembali") or 0) > 0:
        keterangan_bayar = _format(pengaturan, "footer_cash")
    else:
        keterangan_bayar = _format(pengaturan, "footer_edc")
    if keterangan_bayar:
        tambah(keterangan_bayar)

    tambah("-" * kolom)

    # --- Ucapan penutup ---
    for kunci in ("footer_1", "footer_2", "footer_3"):
        nilai = pengaturan.get(kunci)
        # Belum diatur -> pakai bawaan; diisi kosong -> baris dihilangkan.
        teks = (BAWAAN_FORMAT[kunci] if nilai is None else str(nilai)).strip()
        if teks:
            for potong in _potong(teks, kolom):
                tambah(potong, "tengah")
    return baris


def buat_dokumen(baris, pengaturan=None):
    """Membuat dokumen PDF thermal di memori (belum ditulis ke berkas)."""
    pengaturan = pengaturan or {}
    lebar_mm = float(pengaturan.get("lebar_mm", LEBAR_MM_BAWAAN))
    font = float(pengaturan.get("font_size", FONT_BAWAAN))
    tinggi_mm = float(pengaturan.get("tinggi_mm", 0) or 0)

    lebar_pt = lebar_mm * 72 / 25.4
    margin = MARGIN_PT

    # Ukuran tiap baris (judul lebih besar), dipastikan tidak melebihi lebar.
    ukuran = []
    for teks, rata in baris:
        besar = font * SKALA_JUDUL if rata == "judul" else font
        while besar > font:
            panjang = pymupdf.get_text_length(
                teks, fontname="cobo", fontsize=besar
            )
            if panjang <= lebar_pt - 2 * margin:
                break
            besar -= 0.25
        ukuran.append(besar)

    tinggi_isi = margin * 2 + max(
        1, sum(u * 1.3 for u in ukuran)
    )
    tinggi_pt = max(tinggi_isi, tinggi_mm * 72 / 25.4 if tinggi_mm else 0)

    dokumen = pymupdf.open()
    halaman = dokumen.new_page(width=lebar_pt, height=tinggi_pt)

    y = margin + font
    for (teks, rata), besar in zip(baris, ukuran):
        if teks:
            tebal = rata == "judul"
            nama_font = "cobo" if tebal else "cour"
            if rata in ("tengah", "judul"):
                panjang = pymupdf.get_text_length(
                    teks, fontname=nama_font, fontsize=besar
                )
                x = max(margin, (lebar_pt - panjang) / 2)
            else:
                x = margin
            halaman.insert_text(
                (x, y), teks, fontname=nama_font, fontsize=besar, color=(0, 0, 0)
            )
        y += besar * 1.3

    return dokumen


def simpan_pdf(baris, path_keluar, pengaturan=None):
    """Menulis daftar baris menjadi PDF kertas thermal."""
    dokumen = buat_dokumen(baris, pengaturan)
    folder = os.path.dirname(os.path.abspath(path_keluar))
    if folder:
        os.makedirs(folder, exist_ok=True)
    dokumen.save(path_keluar)
    dokumen.close()
    return path_keluar


def konversi(path_masuk, path_keluar, pengaturan=None):
    """Konversi satu PDF nota A4 menjadi PDF thermal."""
    nota = baca_nota(path_masuk)
    if not nota.get("items"):
        raise ValueError("Tabel item tidak ditemukan di PDF ini.")
    baris = susun_baris(nota, pengaturan)
    simpan_pdf(baris, path_keluar, pengaturan)
    return nota


def printer_default():
    """Nama printer default Windows (string kosong bila tidak ada)."""
    if not _AKTIF_WINDOWS:
        return ""
    try:
        ukuran = wintypes.DWORD(0)
        _winspool.GetDefaultPrinterW(None, ctypes.byref(ukuran))
        if not ukuran.value:
            return ""
        buffer = ctypes.create_unicode_buffer(ukuran.value)
        if not _winspool.GetDefaultPrinterW(buffer, ctypes.byref(ukuran)):
            return ""
        return buffer.value
    except Exception:
        return ""


def cetak_dokumen(dokumen, printer="", nama_dokumen="thermal"):
    """Mengirim dokumen pymupdf yang sudah terbuka ke antrean printer.

    Halaman dirender menjadi gambar lalu dikirim lewat GDI (masuk ke antrean
    cetak Windows), jadi berkas PDF tidak perlu ditulis ke disk lebih dulu.
    Dokumen tidak ditutup di sini - pemanggil yang menutupnya.
    Mengembalikan nama printer yang dipakai.
    """
    if not _AKTIF_WINDOWS:
        raise OSError("Cetak langsung hanya tersedia di Windows.")

    nama_printer = (printer or "").strip() or printer_default()
    if not nama_printer:
        raise OSError("Printer default Windows tidak ditemukan.")

    dc = _gdi32.CreateDCW("WINSPOOL", nama_printer, None, None)
    if not dc:
        raise OSError(f"Printer '{nama_printer}' tidak bisa dibuka.")

    started = False
    try:
        dpi = _gdi32.GetDeviceCaps(dc, 88) or 203  # LOGPIXELSX
        lebar_area = _gdi32.GetDeviceCaps(dc, 8)  # HORZRES
        tinggi_area = _gdi32.GetDeviceCaps(dc, 10)  # VERTRES
        if lebar_area <= 0 or tinggi_area <= 0:
            raise OSError(f"Printer '{nama_printer}' tidak melaporkan area cetak.")

        info = _DOCINFOW(
            ctypes.sizeof(_DOCINFOW), nama_dokumen, None, None, 0, 0
        )
        if _gdi32.StartDocW(dc, ctypes.byref(info)) <= 0:
            raise OSError(
                f"Printer '{nama_printer}' menolak pekerjaan cetak "
                "(periksa status printer/antrean)."
            )
        started = True

        _gdi32.SetStretchBltMode(dc, 4)  # HALFTONE (abu-abu -> titik printer)
        for halaman in dokumen:
            pix = halaman.get_pixmap(
                dpi=int(dpi), colorspace=pymupdf.csGRAY, alpha=False
            )
            if not pix.width or not pix.height:
                continue

            lebar = lebar_area
            tinggi = max(1, round(lebar * pix.height / pix.width))
            if tinggi > tinggi_area:
                # Konten lebih panjang dari kertas: perkecil agar tidak terpotong.
                skala = tinggi_area / tinggi
                lebar = max(1, round(lebar * skala))
                tinggi = tinggi_area

            info_bitmap = _BITMAPINFO()
            info_bitmap.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
            info_bitmap.bmiHeader.biWidth = pix.width
            info_bitmap.bmiHeader.biHeight = -pix.height  # top-down
            info_bitmap.bmiHeader.biPlanes = 1
            info_bitmap.bmiHeader.biBitCount = 8
            info_bitmap.bmiHeader.biCompression = 0  # BI_RGB
            info_bitmap.bmiHeader.biSizeImage = pix.stride * pix.height
            for i in range(256):
                info_bitmap.bmiColors[i].rgbRed = i
                info_bitmap.bmiColors[i].rgbGreen = i
                info_bitmap.bmiColors[i].rgbBlue = i

            buffer = ctypes.create_string_buffer(pix.samples, len(pix.samples))
            if _gdi32.StartPage(dc) <= 0:
                raise OSError(f"Printer '{nama_printer}' gagal memulai halaman.")
            _gdi32.StretchDIBits(
                dc,
                0,
                0,
                lebar,
                tinggi,
                0,
                0,
                pix.width,
                pix.height,
                ctypes.cast(buffer, ctypes.c_void_p),
                ctypes.byref(info_bitmap),
                0,  # DIB_RGB_COLORS
                0x00CC0020,  # SRCCOPY
            )
            _gdi32.EndPage(dc)
    finally:
        if started:
            _gdi32.EndDoc(dc)
        _gdi32.DeleteDC(dc)
    return nama_printer


def cetak_pdf(path, printer=""):
    """Mencetak PDF langsung ke printer (tanpa aplikasi PDF).

    Halaman PDF dirender menjadi gambar lalu dikirim ke printer lewat GDI.
    Mengembalikan nama printer yang dipakai.
    """
    if not _AKTIF_WINDOWS:
        raise OSError("Cetak langsung hanya tersedia di Windows.")
    dokumen = pymupdf.open(path)
    try:
        return cetak_dokumen(dokumen, printer, os.path.basename(path))
    finally:
        dokumen.close()


def konversi_dan_cetak(path_masuk, pengaturan=None, printer=""):
    """Konversi nota di memori lalu langsung kirim ke antrean cetak.

    Tidak ada berkas PDF thermal yang ditulis ke disk. Mengembalikan
    (nota, nama_printer).
    """
    nota = baca_nota(path_masuk)
    if not nota.get("items"):
        raise ValueError("Tabel item tidak ditemukan di PDF ini.")
    baris = susun_baris(nota, pengaturan)
    dokumen = buat_dokumen(baris, pengaturan)
    nama_dokumen = (
        os.path.splitext(os.path.basename(path_masuk))[0] + "_thermal"
    )
    try:
        nama_printer = cetak_dokumen(dokumen, printer, nama_dokumen)
    finally:
        dokumen.close()
    return nota, nama_printer


def nama_hasil(path_masuk, folder_hasil):
    """Nama file hasil konversi (suffix _thermal)."""
    dasar = os.path.splitext(os.path.basename(path_masuk))[0]
    return os.path.join(folder_hasil, f"{dasar}_thermal.pdf")
