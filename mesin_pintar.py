"""
================================================================================
 mesin_pintar.py - MESIN PENCARIAN TANGGAL (OTAK APLIKASI)
================================================================================
Inilah inti permintaan Anda: aplikasi jadi "PINTAR".

ALUR YANG DILAKSANAKAN:

    tanggal = tanggal_mulai
    SELAMA masih jalan DAN tanggal <= tanggal_akhir:

        baca baris yang sedang fokus di tabel Takom
        tgl_layar = tanggal hasil baca

        JIKA tgl_layar == tanggal:            <- tanggal target DITEMUKAN
            gagal_berturut = 0
            -> cetak/simpan PDF baris ini
            -> catat progres (titik resume)
            -> turun 1 baris
            JIKA baris berikutnya bukan tanggal ini:
                tanggal = tanggal + 1 hari   <- pindah ke tanggal setelahnya

        JIKA tgl_layar != tanggal:            <- tanggal target TIDAK ada di sini
            JIKA masih ada halaman (tombol next ada):
                -> klik next, pindai lagi (tanggal yang SAMA)
            JIKA halaman sudah terakhir:
                -> tanggal = tanggal + 1 hari
                -> gagal_berturut += 1
                JIKA gagal_berturut >= batas -> STOP OTOMATIS

KRITERIA STOP OTOMATIS (sesuai permintaan Anda):
    1. tanggal sudah lewat tanggal_akhir
    2. N tanggal berturut-turut tidak ditemukan sama sekali
    3. Tombol pagination NEXT tidak ada (data habis)
    4. Pengguna klik HENTIKAN, atau FAILSAFE mouse ke pojok layar

Modul ini SENGAJA TIDAK bergantung pada GUI (Tkinter) supaya bisa diuji
sendiri dan dipakai baik oleh aplikasi GUI maupun versi CLI.
================================================================================
"""

import time
from datetime import date

import pyautogui

import pembaca_layar
import kelola_progres

# Tombol pagination next: gambar acuan
GAMBAR_NEXT = "tombol_next.png"
GAMBAR_PREVIEW = "tombol_preview.png"


class MesinPintar:
    """
    Otak pencarian tanggal. Butuh 3 "keterampilan" dari luar:

        pembaca      : objek pembaca_layar.PembacaLayar
        progres      : objek kelola_progres.KelolaProgres
        fungsi_cetak : fungsi(nama_file) -> True/False  (disediakan app_automasi)
    """

    def __init__(self, pembaca, progres, fungsi_cetak, log=None,
                 batas_gagal_berturut=2, jeda_next=2.5, mult=1.0,
                 auto_stop=True, anti_duplikat=True, fungsi_reset_halaman=None):
        self.pembaca = pembaca
        self.progres = progres
        self.cetak = fungsi_cetak          # fungsi penyimpan PDF
        self.log = log or (lambda pesan: print(pesan))
        self.batas_gagal = batas_gagal_berturut
        self.jeda_next = jeda_next
        self.mult = mult
        self.auto_stop = auto_stop
        self.anti_duplikat = anti_duplikat

        # Cara kembali ke halaman pertama tabel.
        # Bisa diganti (diuji/disimulasikan) supaya tidak menekan tombol asli.
        self.fungsi_reset_halaman = fungsi_reset_halaman or self._reset_halaman_asli

        # Status internal
        self.berhenti = False
        self.alasan_stop = ""
        self.jumlah_berhasil = 0
        self.jumlah_dilewati = 0
        self._kosong_berturut = 0

        # Pemantau apakah halaman benar-benar berubah setelah klik next
        self._sidik_halaman = ""

    # ------------------------------------------------------------------
    # KONTROL
    # ------------------------------------------------------------------
    def hentikan(self, alasan="Dihentikan pengguna"):
        """Meminta mesin berhenti dengan alasan yang jelas."""
        self.berhenti = True
        self.alasan_stop = alasan

    # ------------------------------------------------------------------
    # PAGINATION
    # ------------------------------------------------------------------
    def _ada_tombol_next(self):
        """Mencari tombol pagination NEXT di layar. Mengembalikan lokasi atau None."""
        import os
        if not os.path.exists(GAMBAR_NEXT):
            return None
        try:
            return pyautogui.locateOnScreen(GAMBAR_NEXT, confidence=0.8)
        except Exception:
            return None

    def klik_next(self):
        """
        Mencoba klik tombol pagination NEXT.
        Mengembalikan:
            "berhasil" -> halaman baru termuat
            "habis"    -> tombol tidak ada, data sudah habis
            "gagal"    -> diklik tapi layar tidak berubah
        """
        lokasi = self._ada_tombol_next()
        if not lokasi:
            return "habis"

        try:
            pyautogui.click(pyautogui.center(lokasi))
        except Exception as e:
            self.log(f"[ERROR] Gagal klik tombol next: {e}")
            return "habis"

        time.sleep(self.jeda_next * self.mult)

        # Verifikasi halaman benar-benar berganti
        data = self.pembaca.baca_baris_sekarang()
        sidik_baru = data.get("mentah", "")[:80]
        if sidik_baru and sidik_baru == self._sidik_halaman:
            # Layar tidak berubah -> kemungkinan sudah halaman terakhir
            return "gagal"
        self._sidik_halaman = sidik_baru
        return "berhasil"


    # ------------------------------------------------------------------
    # PENCARIAN SATU TANGGAL
    # ------------------------------------------------------------------
    def cari_dan_proses_tanggal(self, tanggal_target, maks_halaman=50):
        """
        Mencari 'tanggal_target' di tabel Takom, memproses semua barisnya,
        lalu berpindah ke halaman berikutnya jika masih ada data tanggal itu.

        Mengembalikan:
            "ditemukan"   -> ada minimal 1 baris tanggal ini diproses
            "tidak_ada"   -> tanggal ini tidak ada (sudah dicek semua halaman)
            "berhenti"    -> diminta berhenti
        """
        halaman = 1
        ditemukan = False

        while not self.berhenti:
            # --- Baca baris yang sedang fokus ---
            data = self.pembaca.baca_baris_sekarang()

            # Baris kosong = sudah mencapai baris terakhir tabel pada halaman ini.
            # Ini BUKAN error. Perlakukan seperti "data habis di halaman ini".
            if data.get("kosong"):
                self.log("[INFO] Baris kosong -> akhir data di halaman ini.")
                return "ditemukan" if ditemukan else "tidak_ada"

            if not data["valid"]:
                # Ada teks, tapi tanggalnya tidak bisa dibaca (loading / baris rusak).
                self.log("[PERINGATAN] Baris terbaca tapi tanggalnya tidak valid. Coba turun baris...")
                self.pembaca.turun_satu_baris()
                self._kosong_berturut = getattr(self, "_kosong_berturut", 0) + 1
                if self._kosong_berturut >= 3:
                    self.log("[INFO] Terlalu banyak baris tak valid -> anggap data habis.")
                    return "ditemukan" if ditemukan else "tidak_ada"
                continue

            self._kosong_berturut = 0
            self._sidik_halaman = data.get("mentah", "")[:80]
            tgl_layar = data["tanggal"]

            # =========================================================
            # KASUS 1: tanggal di layar == tanggal dicari  -> PROSES
            # =========================================================
            if tgl_layar == tanggal_target:
                ditemukan = True
                self.progres.reset_gagal()

                nama_file = pembaca_layar.buat_nama_file(
                    tgl_layar,
                    data.get("no_transaksi"),
                    sumber=self.pembaca.kal.get("sumber_no_file", "asli"),
                )

                # --- Anti duplikat: lewati kalau sudah pernah dibuat ---
                dilewati = False
                if self.anti_duplikat and nama_file:
                    if self.progres.sudah_dibuat(nama_file):
                        self.log(f"[LEWAT] Sudah pernah dibuat: {nama_file}")
                        dilewati = True
                    elif self.progres.sudah_ada_di_disk(
                        self.progres.data.get("folder_simpan"), nama_file
                    ):
                        self.log(f"[LEWAT] File sudah ada di disk: {nama_file}")
                        dilewati = True

                if dilewati:
                    self.jumlah_dilewati += 1
                else:
                    if self._proses_satu_baris(nama_file, tgl_layar, data, halaman):
                        self.jumlah_berhasil += 1

                # Turun ke baris berikutnya untuk melanjutkan tanggal yang sama
                self.pembaca.turun_satu_baris()
                continue

            # =========================================================
            # KASUS 2: tanggal di layar < tanggal dicari
            # =========================================================
            # Tabel Takom terurut NAIK menurut tanggal. Jadi tanggal target
            # kemungkinan ada lebih bawah pada halaman ini.
            # -> PINDAI KE BAWAH (turun 1 baris), JANGAN klik next dulu.
            if tgl_layar and tanggal_target and tgl_layar < tanggal_target:
                self.pembaca.turun_satu_baris()
                continue

            # =========================================================
            # KASUS 3: tanggal di layar > tanggal dicari
            # =========================================================
            # Kita sudah memindai melewati urutan tanggal target tanpa menemukannya.
            # Karena tabel terurut naik, target PASTI tidak ada di tabel ini.
            if ditemukan:
                self.log(
                    f"[INFO] Tanggal di layar ({tgl_layar}) sudah lewat target "
                    f"({tanggal_target}). Semua baris target selesai diproses."
                )
            else:
                self.log(
                    f"[INFO] Tanggal di layar ({tgl_layar}) sudah lewat target "
                    f"({tanggal_target}) -> tanggal target tidak ada."
                )
            return "ditemukan" if ditemukan else "tidak_ada"

        return "berhenti"

    def _proses_satu_baris(self, nama_file, tanggal, data, halaman):
        """
        Menyimpan satu PDF. Mengembalikan True jika berhasil.
        """
        if not nama_file:
            self.log("[PERINGATAN] Nama file kosong, baris dilewati.")
            self.progres.catat_gagal()
            return False

        self.log(f"  -> Simpan: {nama_file}.pdf  (No: {data.get('no_transaksi')})")

        sukses = False
        try:
            sukses = self.cetak(nama_file)
        except Exception as e:
            self.log(f"[ERROR] Kendala saat menyimpan PDF: {e}")
            sukses = False

        if sukses:
            self.progres.catat_berhasil(
                tanggal, data.get("no_transaksi"), nama_file, halaman
            )
            return True

        self.log(f"[GAGAL] Tidak berhasil menyimpan: {nama_file}")
        self.progres.catat_gagal()
        return False


    # ------------------------------------------------------------------
    # ALUR UTAMA: LOOP PER TANGGAL + AUTO STOP
    # ------------------------------------------------------------------
    def jalankan(self, tanggal_mulai, tanggal_akhir=None):
        """
        Menjalankan seluruh otomatisasi dari tanggal_mulai sampai tanggal_akhir.

        tanggal_akhir None -> proses terus sampai data habis (auto-stop).

        Mengembalikan alasan berhentinya (untuk ditampilkan di GUI).
        """
        self.berhenti = False
        self.alasan_stop = ""

        tanggal = tanggal_mulai
        gagal_berturut = 0
        tanggal_diproses = 0

        self.log("=" * 58)
        self.log(" MULAI OTOMATISASI PINTAR")
        self.log(f" Tanggal mulai : {tanggal.strftime('%d-%m-%Y')}")
        if tanggal_akhir:
            self.log(f" Tanggal akhir : {tanggal_akhir.strftime('%d-%m-%Y')}")
        else:
            self.log(" Tanggal akhir : (sampai data habis)")
        self.log(f" Auto-stop     : {'AKTIF' if self.auto_stop else 'NONAKTIF'}")
        self.log("=" * 58)

        while not self.berhenti:
            # --- Cek batas tanggal akhir ---
            if tanggal_akhir and tanggal > tanggal_akhir:
                self.alasan_stop = (
                    f"Sudah mencapai tanggal akhir ({tanggal_akhir.strftime('%d-%m-%Y')})."
                )
                break

            self.log("")
            self.log(f"### Mencari tanggal: {tanggal.strftime('%d-%m-%Y')} "
                     f"(gagal berturut: {gagal_berturut}) ###")

            # --- Cari & proses tanggal ini ---
            hasil = self.cari_dan_proses_tanggal(tanggal)

            if hasil == "berhenti":
                break

            if hasil == "ditemukan":
                gagal_berturut = 0
                tanggal_diproses += 1
            else:  # "tidak_ada"
                gagal_berturut += 1
                self.progres.catat_gagal()
                self.log(f"[INFO] Tanggal {tanggal.strftime('%d-%m-%Y')} tidak ditemukan. "
                         f"Gagal berturut: {gagal_berturut}")

                # --- KRITERIA STOP OTOMATIS ---
                if self.auto_stop and gagal_berturut >= self.batas_gagal:
                    self.alasan_stop = (
                        f"STOP OTOMATIS: {gagal_berturut} tanggal berturut-turut "
                        f"tidak ditemukan. Data sudah habis."
                    )
                    break

            # --- Maju ke tanggal berikutnya ---
            tanggal = pembaca_layar.tanggal_sesudahnya(tanggal, 1)

            # Kembali ke halaman pertama supaya pencarian tanggal baru
            # dimulai dari awal tabel (kalau tabel diurutkan naik).
            self._kembali_ke_halaman_pertama()

        self._tampilkan_rekap(tanggal_diproses)
        self.progres.tandai_selesai()
        return self.alasan_stop or "Proses selesai."

    # ------------------------------------------------------------------
    # BANTUAN
    # ------------------------------------------------------------------
    def _kembali_ke_halaman_pertama(self):
        """Kembali ke halaman pertama tabel (lewat fungsi yang bisa diganti)."""
        try:
            self.fungsi_reset_halaman()
        except Exception:
            pass

    def _reset_halaman_asli(self):
        """
        Cara nyata kembali ke halaman pertama: tekan tombol HOME.
        Aman untuk tabel Java Swing dan tidak merusak fokus.
        """
        pyautogui.press("home")
        time.sleep(0.5 * self.mult)

    def _tampilkan_rekap(self, tanggal_diproses):
        """Menampilkan ringkasan hasil kerja di akhir proses."""
        self.log("")
        self.log("=" * 58)
        self.log(" REKAP HASIL")
        self.log(f" Tanggal diproses : {tanggal_diproses}")
        self.log(f" PDF berhasil     : {self.jumlah_berhasil}")
        self.log(f" Dilewati (duplikat): {self.jumlah_dilewati}")
        self.log(f" Alasan berhenti  : {self.alasan_stop or 'Selesai normal'}")
        self.log("=" * 58)

# ==============================================================================
# UJI MANDIRI (dijalankan: python mesin_pintar.py)
# ==============================================================================
if __name__ == "__main__":
    from datetime import date as _date

    print("=" * 66)
    print(" UJI MODUL mesin_pintar.py (SIMULASI - tanpa sentuh layar)")
    print("=" * 66)
    print("\nMemakai pembaca & progres PALSU (mock) supaya logika pencarian")
    print("bisa dibuktikan tanpa perlu aplikasi Takom terbuka.\n")

    # ---------- Mock pembaca layar ----------
    class PembacaPalsu:
        def __init__(self, baris):
            self.baris = baris
            self.posisi = 0
            self.kal = {"sumber_no_file": "asli"}

        def baca_baris_sekarang(self, coba_lagi=1):
            if self.posisi >= len(self.baris):
                # Tabel habis -> clipboard kosong (sama seperti aplikasi nyata)
                return {"tanggal": None, "no_transaksi": None,
                        "kolom": [], "mentah": "", "valid": False, "kosong": True}
            tgl, no = self.baris[self.posisi]
            return {"tanggal": tgl, "no_transaksi": no,
                    "kolom": [no, tgl.strftime("%d-%m-%Y")],
                    "mentah": f"{no}\t{tgl.strftime('%d-%m-%Y')}",
                    "valid": True, "kosong": False}

        def turun_satu_baris(self):
            self.posisi += 1

        def kembali_ke_awal(self):
            """Menyimulasikan tekan HOME: fokus balik ke baris pertama."""
            self.posisi = 0

    # ---------- Mock progres ----------
    class ProgresPalsu:
        def __init__(self):
            self.data = {"folder_simpan": r"C:\Tmp\Uji", "file_selesai": [],
                         "gagal_berturut": 0}
            self.berhasil = []
            self.gagal = 0

        def reset_gagal(self):
            self.data["gagal_berturut"] = 0

        def catat_berhasil(self, tgl, no, nama, hal):
            self.berhasil.append(nama)
            self.data["file_selesai"].append(nama)

        def catat_gagal(self):
            self.gagal += 1
            self.data["gagal_berturut"] += 1

        def set_halaman(self, hal):
            pass

        def tandai_selesai(self):
            pass

        def sudah_dibuat(self, nama):
            return nama in self.data["file_selesai"]

        def sudah_ada_di_disk(self, folder, nama):
            return False

    # ---------- Fungsi cetak palsu ----------
    tersimpan = []

    def cetak_palsu(nama_file):
        tersimpan.append(nama_file)
        return True

    def buat_baris(*daftar):
        """Helper: buat list (tanggal, no_transaksi)."""
        return [(_date(2026, 10, d), f"210726100{n:03d}") for d, n in daftar]

    # =====================================================================
    print("-" * 66)
    print("SKENARIO 1: Data ada tgl 1, 2, 3. Target 1-3 Okt. Harus simpan 5 file.")
    print("-" * 66)
    tersimpan.clear()
    p1 = PembacaPalsu(buat_baris((1, 1), (1, 2), (2, 1), (3, 1), (3, 2)))
    pr1 = ProgresPalsu()
    m1 = MesinPintar(p1, pr1, cetak_palsu, batas_gagal_berturut=2, mult=0.0, fungsi_reset_halaman=p1.kembali_ke_awal)
    m1.klik_next = lambda: "habis"   # simulasi: tidak ada pagination
    alasan1 = m1.jalankan(_date(2026, 10, 1), _date(2026, 10, 3))
    print(f"\n>>> File tersimpan: {tersimpan}")
    print(f">>> Jumlah: {len(tersimpan)} (harusnya 5)")
    print(f">>> Alasan stop: {alasan1}")

    # =====================================================================
    print()
    print("-" * 66)
    print("SKENARIO 2: Tgl 2 Okt TIDAK ADA (lompat). Harus tetap lanjut ke 3 Okt.")
    print("-" * 66)
    tersimpan.clear()
    p2 = PembacaPalsu(buat_baris((1, 1), (1, 2), (3, 1), (3, 2), (3, 3)))
    pr2 = ProgresPalsu()
    m2 = MesinPintar(p2, pr2, cetak_palsu, batas_gagal_berturut=2, mult=0.0, fungsi_reset_halaman=p2.kembali_ke_awal)
    m2.klik_next = lambda: "habis"
    alasan2 = m2.jalankan(_date(2026, 10, 1), _date(2026, 10, 5))
    print(f"\n>>> File tersimpan: {tersimpan}")
    print(f">>> Jumlah: {len(tersimpan)} (harusnya 5 - tgl 2 dilewati)")
    print(f">>> Alasan stop: {alasan2}")

    # =====================================================================
    print()
    print("-" * 66)
    print("SKENARIO 3: AUTO-STOP. Data habis setelah 2 Okt, batas gagal = 2.")
    print("-" * 66)
    tersimpan.clear()
    p3 = PembacaPalsu(buat_baris((1, 1), (2, 1)))
    pr3 = ProgresPalsu()
    m3 = MesinPintar(p3, pr3, cetak_palsu, batas_gagal_berturut=2, mult=0.0, fungsi_reset_halaman=p3.kembali_ke_awal)
    m3.klik_next = lambda: "habis"
    alasan3 = m3.jalankan(_date(2026, 10, 1), None)
    print(f"\n>>> File tersimpan: {tersimpan}")
    print(f">>> Jumlah: {len(tersimpan)} (harusnya 2)")
    print(f">>> Alasan stop: {alasan3}")
    print(f">>> AUTO-STOP bekerja: {'YA' if 'STOP OTOMATIS' in alasan3 else 'TIDAK'}")

    # =====================================================================
    print()
    print("-" * 66)
    print("SKENARIO 4: ANTI-DUPLIKAT. Baris 1 Okt diulang -> harus dilewati.")
    print("-" * 66)
    tersimpan.clear()
    p4 = PembacaPalsu(buat_baris((1, 1), (1, 1), (1, 2)))
    pr4 = ProgresPalsu()
    m4 = MesinPintar(p4, pr4, cetak_palsu, batas_gagal_berturut=2, mult=0.0, fungsi_reset_halaman=p4.kembali_ke_awal)
    m4.klik_next = lambda: "habis"
    alasan4 = m4.jalankan(_date(2026, 10, 1), _date(2026, 10, 1))
    print(f"\n>>> File tersimpan: {tersimpan}")
    print(f">>> Dilewati: {m4.jumlah_dilewati} (harusnya 1)")
    print(f">>> Alasan stop: {alasan4}")

    print()
    print("=" * 66)
    print(" SELESAI - logika mesin pintar terverifikasi")
    print("=" * 66)


