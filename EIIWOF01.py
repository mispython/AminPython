#!/usr/bin/env python3
"""EIIWOF01 — Copy fail asal PIBB ke folder BACKUP dan WOFF."""

from pathlib import Path
import shutil

SOURCE = Path("/exdwh/host/ln/npl_hp_sasdata/pibb")
BACKUP = SOURCE / "backup"
WOFF = SOURCE / "woff"


def main():
    BACKUP.mkdir(exist_ok=True)
    WOFF.mkdir(exist_ok=True)

    # Copy fail sahaja; tidak termasuk subfolder.
    for file in SOURCE.iterdir():
        if file.is_file():
            shutil.copy2(file, BACKUP / file.name)
            shutil.copy2(file, WOFF / file.name)
            print(f"Copied: {file.name}")

    print("EIIWOF01 selesai.")


if __name__ == "__main__":
    main()
