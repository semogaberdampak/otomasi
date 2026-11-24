"""Rilis satu perintah.

Pemakaian:
    python rilis.py patch     # 1.0.0 -> 1.0.1  (perbaikan kecil)
    python rilis.py minor     # 1.0.0 -> 1.1.0  (fitur baru)
    python rilis.py major     # 1.0.0 -> 2.0.0  (perubahan besar)
    python rilis.py patch --tanpa-build   # lewati build exe & upload

Yang dilakukan:
  1. Naikkan nomor di versi.py
  2. Tulis entri CHANGELOG.md dari pesan commit sejak rilis sebelumnya
  3. Commit "Rilis vX.Y.Z" + git tag vX.Y.Z, lalu push
  4. Build exe (PyInstaller) dan, bila GitHub CLI `gh` ada, unggah ke Releases
"""

import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSI_PY = ROOT / "versi.py"
CHANGELOG = ROOT / "CHANGELOG.md"


def jalankan(*perintah, cek=True):
    hasil = subprocess.run(
        perintah, cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    if cek and hasil.returncode != 0:
        sys.exit(f"Gagal: {' '.join(perintah)}\n{hasil.stderr or hasil.stdout}")
    return hasil.stdout.strip()


def versi_sekarang():
    return re.search(r'__versi__ = "([^"]+)"', VERSI_PY.read_text("utf-8")).group(1)


def naikkan(versi, jenis):
    a, b, c = (int(x) for x in versi.split("."))
    return {
        "major": f"{a + 1}.0.0",
        "minor": f"{a}.{b + 1}.0",
        "patch": f"{a}.{b}.{c + 1}",
    }[jenis]


def catatan_commit():
    tag_terakhir = jalankan("git", "describe", "--tags", "--abbrev=0", cek=False)
    rentang = f"{tag_terakhir}..HEAD" if tag_terakhir else "HEAD"
    log = jalankan("git", "log", rentang, "--pretty=%s")
    baris = [b for b in log.splitlines() if b and not b.startswith("Rilis v")]
    return baris or ["Perbaikan dan penyempurnaan."]


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("major", "minor", "patch"):
        sys.exit(__doc__)
    jenis, tanpa_build = sys.argv[1], "--tanpa-build" in sys.argv

    if jalankan("git", "status", "--porcelain", "--untracked-files=no"):
        sys.exit("Ada perubahan yang belum di-commit. Commit dulu, lalu jalankan lagi.")

    lama = versi_sekarang()
    baru = naikkan(lama, jenis)
    catatan = catatan_commit()

    # 1. versi.py
    VERSI_PY.write_text(
        VERSI_PY.read_text("utf-8").replace(
            f'__versi__ = "{lama}"', f'__versi__ = "{baru}"'
        ),
        encoding="utf-8",
    )

    # 2. CHANGELOG.md (entri terbaru di atas)
    entri = f"## [{baru}] - {date.today():%Y-%m-%d}\n" + "\n".join(
        f"- {c}" for c in catatan
    )
    isi = CHANGELOG.read_text("utf-8")
    titik = isi.index("## [")
    CHANGELOG.write_text(isi[:titik] + entri + "\n\n" + isi[titik:], encoding="utf-8")

    # 3. commit + tag + push
    jalankan("git", "add", "versi.py", "CHANGELOG.md")
    jalankan("git", "commit", "-m", f"Rilis v{baru}")
    jalankan("git", "tag", "-a", f"v{baru}", "-m", f"Versi {baru}")
    jalankan("git", "push", "origin", "HEAD", "--follow-tags")
    print(f"Versi {lama} -> {baru} tercatat dan di-push.")

    # 4. build + upload
    if tanpa_build:
        return
    print("Membangun exe (PyInstaller)...")
    jalankan(sys.executable, "-m", "PyInstaller", "--noconfirm", "AutomasiNota.spec")
    exe = ROOT / "dist" / "AutomasiNota.exe"
    if not exe.exists():
        sys.exit("Build selesai tapi dist/AutomasiNota.exe tidak ditemukan.")
    if shutil.which("gh"):
        jalankan(
            "gh", "release", "create", f"v{baru}", str(exe),
            "--title", f"v{baru}", "--notes", "\n".join(f"- {c}" for c in catatan),
        )
        print(f"Rilis v{baru} dipublikasikan di GitHub Releases.")
    else:
        print(
            "GitHub CLI (gh) tidak ditemukan. Unggah dist/AutomasiNota.exe secara "
            f"manual ke GitHub > Releases > tag v{baru}."
        )


if __name__ == "__main__":
    main()
