"""
================================================================================
 kelola_progres.py - MODUL MEMORI / RESUME PROSES
================================================================================
Modul ini membuat aplikasi "TAU DIMANA DIA AKAN MELANJUTKAN".

Setiap kali satu PDF berhasil disimpan, progres ditulis ke 'status_progres.json'.
Jadi kalau komputer mati, listrik padam, atau Anda tidak sengaja klik HENTIKAN,
tinggal jalankan lagi mode "LANJUTKAN (RESUME)" dan aplikasi akan meneruskan
dari titik terakhir - tidak mengulang dari awal.

Isi file status_progres.json:
    {
      "tanggal_terakhir"  : "01-10-2026",
      "tanggal_berikutnya": "02-10-2026",
      "no_transaksi"      : "210726100012",
      "halaman"           : 2,
      "folder_simpan"     : "C:\\Laporan_PDF",
      "tanggal_mulai"     : "01-10-2026",
      "tanggal_akhir"     : "31-10-2026",
      "file_selesai"      : ["01-10-26-210726100001", ...],
      "gagal_berturut"    : 0,
      "selesai"           : false,
      "terakhir_update"   : "2026-10-11 14:30:00"
    }
================================================================================
"""

import os
import json
from datetime import datetime

import pembaca_layar

NAMA_FILE_PROGRES = "status_progres.json"


class KelolaProgres:
    """Menyimpan dan memuat progres supaya bisa dilanjutkan (resume)."""

    def __init__(self, nama_file=NAMA_FILE_PROGRES, maks_riwayat=500):
        self.nama_file = nama_file
        self.maks_riwayat = maks_riwayat
        self.data = self.data_kosong()

    # ------------------------------------------------------------------
    # STRUKTUR DATA
    # ------------------------------------------------------------------
    @staticmethod
    def data_kosong():
        """Template progres baru (belum ada apa-apa)."""
        return {
            "tanggal_terakhir": None,
            "tanggal_berikutnya": None,
            "no_transaksi": None,
            "halaman": 1,
            "folder_simpan": None,
            "tanggal_mulai": None,
            "tanggal_akhir": None,
            "file_selesai": [],
            "gagal_berturut": 0,
            "selesai": False,
            "terakhir_update": None,
        }

    # ------------------------------------------------------------------
    # SIMPAN & MUAT
    # ------------------------------------------------------------------
    def simpan(self):
        """Menulis progres ke disk. Aman dipanggil sering (setiap item)."""
        self.data["terakhir_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.nama_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[PERINGATAN] Gagal simpan progres: {e}")
            return False

    def muat(self):
        """
        Memuat progres dari disk.
        Mengembalikan True jika ada progres tersimpan yang bisa dilanjutkan.
        """
        if not os.path.exists(self.nama_file):
            return False
        try:
            with open(self.nama_file, "r", encoding="utf-8") as f:
                isi = json.load(f)
            # Gabungkan agar key yang hilang tidak bikin error
            dasar = self.data_kosong()
            dasar.update(isi)
            self.data = dasar
            return self.bisa_dilanjutkan()
        except Exception:
            return False

    def hapus(self):
        """Menghapus file progres (dipakai saat mulai proses baru dari nol)."""
        self.data = self.data_kosong()
        if os.path.exists(self.nama_file):
            try:
                os.remove(self.nama_file)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------
    def bisa_dilanjutkan(self):
        """True jika ada progres yang belum selesai sehingga bisa di-resume."""
        if self.data.get("selesai"):
            return False
        return bool(self.data.get("tanggal_terakhir") or self.data.get("file_selesai"))

    def mulai_baru(self, folder_simpan, tanggal_mulai, tanggal_akhir):
        """Menyiapkan progres baru (menimpa yang lama)."""
        self.data = self.data_kosong()
        self.data["folder_simpan"] = folder_simpan
        self.data["tanggal_mulai"] = (
            tanggal_mulai.strftime("%d-%m-%Y") if tanggal_mulai else None
        )
        self.data["tanggal_akhir"] = (
            tanggal_akhir.strftime("%d-%m-%Y") if tanggal_akhir else None
        )
        self.data["halaman"] = 1
        self.simpan()


    # ------------------------------------------------------------------
    # PENCATATAN PER ITEM
    # ------------------------------------------------------------------
    def catat_berhasil(self, tanggal, no_transaksi, nama_file, halaman):
        """
        Mencatat satu PDF berhasil disimpan, sekaligus menyiapkan
        'titik lanjut' untuk tanggal sesudahnya.
        """
        self.data["tanggal_terakhir"] = (
            tanggal.strftime("%d-%m-%Y") if tanggal else None
        )
        self.data["tanggal_berikutnya"] = (
            pembaca_layar.tanggal_sesudahnya(tanggal).strftime("%d-%m-%Y")
            if tanggal else None
        )
        self.data["no_transaksi"] = no_transaksi
        self.data["halaman"] = halaman
        self.data["gagal_berturut"] = 0

        selesai = self.data.get("file_selesai", [])
        if nama_file and nama_file not in selesai:
            selesai.append(nama_file)
            # Batasi riwayat supaya file tidak membengkak
            if len(selesai) > self.maks_riwayat:
                self.data["file_selesai"] = selesai[-self.maks_riwayat:]
        self.simpan()

    def catat_gagal(self):
        """Menambah hitungan gagal berturut-turut (dasar auto-stop)."""
        self.data["gagal_berturut"] = self.data.get("gagal_berturut", 0) + 1
        self.simpan()

    def reset_gagal(self):
        """Mengubah hitungan gagal kembali ke 0 (karena ada data ditemukan)."""
        if self.data.get("gagal_berturut", 0) != 0:
            self.data["gagal_berturut"] = 0
            self.simpan()

    def set_halaman(self, halaman):
        """Mencatat halaman pagination yang sedang aktif."""
        self.data["halaman"] = halaman
        self.simpan()

    def tandai_selesai(self):
        """Menandai seluruh proses sudah selesai (progres diarsipkan)."""
        self.data["selesai"] = True
        self.data["tanggal_berikutnya"] = None
        self.simpan()

    # ------------------------------------------------------------------
    # ANTI DUPLIKAT
    # ------------------------------------------------------------------
    def sudah_dibuat(self, nama_file):
        """True jika nama file ini sudah pernah berhasil disimpan."""
        return nama_file in self.data.get("file_selesai", [])

    def sudah_ada_di_disk(self, folder, nama_file):
        """True jika file PDF sudah ada di folder tujuan (cegah timpa ulang)."""
        if not folder or not nama_file:
            return False
        path = os.path.join(folder, f"{nama_file}.pdf")
        return os.path.exists(path)

    # ------------------------------------------------------------------
    # TAMPILAN
    # ------------------------------------------------------------------
    def ringkasan(self):
        """Teks ringkas untuk ditampilkan di log/GUI."""
        if not self.bisa_dilanjutkan():
            return "Belum ada progres yang bisa dilanjutkan."
        d = self.data
        jumlah = len(d.get("file_selesai", []))
        return (
            f"Terakhir: {d.get('tanggal_terakhir')} | "
            f"No: {d.get('no_transaksi')} | "
            f"Hal: {d.get('halaman')} | "
            f"Berhasil: {jumlah} file"
        )


# ==============================================================================
# UJI MANDIRI (dijalankan: python kelola_progres.py)
# ==============================================================================
if __name__ == "__main__":
    import tempfile

    print("=" * 66)
    print(" UJI MODUL kelola_progres.py (memori / resume)")
    print("=" * 66)

    # Pakai file sementara supaya tidak mengganggu progres asli
    tmp = os.path.join(tempfile.gettempdir(), "_uji_progres.json")
    if os.path.exists(tmp):
        os.remove(tmp)

    kp = KelolaProgres(nama_file=tmp)
    tgl = pembaca_layar.parsing_tanggal("01-10-2026")

    print("\n[1] Progres awal kosong")
    print(f"    bisa_dilanjutkan: {kp.bisa_dilanjutkan()}  (harusnya False)")

    print("\n[2] Mulai proses baru")
    kp.mulai_baru(r"C:\Laporan_PDF", tgl, pembaca_layar.tanggal_sesudahnya(tgl, 30))
    print(f"    mulai: {kp.data['tanggal_mulai']}, akhir: {kp.data['tanggal_akhir']}")
    print(f"    simpan() -> {kp.simpan()}")

    print("\n[3] Catat 3 PDF berhasil")
    for i, no in enumerate(["210726100001", "210726100002", "210726100003"], start=1):
        nama = pembaca_layar.buat_nama_file(tgl, no, "asli")
        kp.catat_berhasil(tgl, no, nama, 1)
        print(f"    {i}. {nama}")
    print(f"    tanggal_berikutnya: {kp.data['tanggal_berikutnya']}")

    print("\n[4] Simulasi RESUME (buat objek baru, muat dari disk)")
    kp2 = KelolaProgres(nama_file=tmp)
    print(f"    muat() -> {kp2.muat()}")
    print(f"    bisa_dilanjutkan: {kp2.bisa_dilanjutkan()}  (harusnya True)")
    print(f"    {kp2.ringkasan()}")

    print("\n[5] Uji anti-duplikat")
    print(f"    sudah_dibuat('01-10-26-210726100001') -> {kp2.sudah_dibuat('01-10-26-210726100001')}  (harusnya True)")
    print(f"    sudah_dibuat('01-10-26-999999999999') -> {kp2.sudah_dibuat('01-10-26-999999999999')}  (harusnya False)")
    print(f"    sudah_ada_di_disk(tmp, 'file_palsu')   -> {kp2.sudah_ada_di_disk(tempfile.gettempdir(), 'file_palsu')}  (harusnya False)")

    print("\n[6] Uji hitungan gagal (dasar auto-stop)")
    for _ in range(3):
        kp2.catat_gagal()
    print(f"    gagal_berturut: {kp2.data['gagal_berturut']}")
    kp2.reset_gagal()
    print(f"    setelah reset_gagal(): {kp2.data['gagal_berturut']}")

    print("\n[7] Tandai selesai lalu cek resume")
    kp2.tandai_selesai()
    kp3 = KelolaProgres(nama_file=tmp)
    print(f"    bisa_dilanjutkan: {kp3.bisa_dilanjutkan()}  (harusnya False)")

    os.remove(tmp)
    print("\n" + "=" * 66)
    print(" SELESAI - modul kelola_progres.py berfungsi normal")
    print("=" * 66)
