#!/usr/bin/env python3
"""
Install jamdict-data on Windows by automatically downloading the source distribution,
patching the Windows file-lock bug in setup.py (WinError 32 on unlinking open .xz file),
and installing via pip.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

JAMDICT_DATA_SDIST_URL = (
    "https://files.pythonhosted.org/packages/97/a5/075928aed2b3b70459fc1db396397dfa6714d266c143c51af9b648551a4e/jamdict_data-1.5.tar.gz"
)


def is_jamdict_data_installed() -> bool:
    try:
        import jamdict_data  # noqa: F401
        return True
    except ImportError:
        return False


def install_fixed_jamdict_data() -> None:
    if is_jamdict_data_installed():
        print("[jamdict-data] Already installed. Skipping.")
        return

    print("[jamdict-data] Detected missing jamdict-data. Preparing Windows-compatible installation...")
    temp_dir = tempfile.mkdtemp(prefix="jamdict_install_")
    try:
        tar_path = os.path.join(temp_dir, "jamdict_data.tar.gz")
        print(f"[jamdict-data] Downloading from {JAMDICT_DATA_SDIST_URL} ...")
        urllib.request.urlretrieve(JAMDICT_DATA_SDIST_URL, tar_path)

        print("[jamdict-data] Extracting package...")
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(temp_dir)

        pkg_dir = os.path.join(temp_dir, "jamdict_data-1.5")
        setup_py = os.path.join(pkg_dir, "setup.py")
        if not os.path.isfile(setup_py):
            raise FileNotFoundError(f"Could not find setup.py in {pkg_dir}")

        print("[jamdict-data] Patching Windows file-lock bug in setup.py...")
        with open(setup_py, "r", encoding="utf-8") as f:
            content = f.read()

        # Fix: Ensure lzma file is closed before attempting os.unlink, and guard against Windows file lock errors
        old_pattern = """        with lzma.open(ZIPPED_DB) as f:
            db_content = f.read()
            with open(TARGET_DB, "wb") as out:
                out.write(db_content)
            # delete the xz file
            os.unlink("jamdict_data/jamdict.db.xz")"""

        new_pattern = """        with lzma.open(ZIPPED_DB) as f:
            db_content = f.read()
        with open(TARGET_DB, "wb") as out:
            out.write(db_content)
        try:
            os.unlink(ZIPPED_DB)
        except Exception:
            pass"""

        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
        else:
            # Fallback replacement if formatting differs slightly
            content = content.replace(
                'os.unlink("jamdict_data/jamdict.db.xz")',
                'pass  # Patched for Windows'
            )

        with open(setup_py, "w", encoding="utf-8") as f:
            f.write(content)

        print("[jamdict-data] Installing patched package...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_dir, "--no-build-isolation"])
        print("[jamdict-data] Successfully installed jamdict-data!")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    install_fixed_jamdict_data()

