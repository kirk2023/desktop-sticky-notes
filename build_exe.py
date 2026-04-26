"""
Build script - Package Sticky Notes into a single EXE file.

Output: output/desktop_sticky_notes.exe
(Always uses 'output' folder, never touches 'dist' or 'build')
"""

import os
import sys
import subprocess
import shutil
import time


def kill_old_process():
    """Kill any running instance."""
    try:
        subprocess.run(
            ['taskkill', '/F', '/IM', 'desktop_sticky_notes.exe'],
            capture_output=True, text=True, timeout=5
        )
        time.sleep(2)
    except Exception:
        pass


def build_exe():
    print()
    print("=" * 50)
    print("  Sticky Notes - Build Tool")
    print("=" * 50)
    print()

    # Step 1: Kill old process
    print("[1/2] Stopping old instances...")
    kill_old_process()
    print("  [OK]")
    print()

    # Step 2: Build
    dist_dir = 'output'
    print(f"[2/2] Building EXE -> {dist_dir}/")
    print()

    # Clean old build cache (not output)
    for d in ['build']:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
            except Exception:
                pass

    # Delete any leftover .spec file
    for f in os.listdir('.'):
        if f.endswith('.spec'):
            try:
                os.remove(f)
            except Exception:
                pass

    cmd = [
        sys.executable,
        '-m', 'PyInstaller',
        '--name=desktop_sticky_notes',
        '--onefile',
        '--windowed',
        '--noconfirm',
        '--distpath=output',
        '--workpath=build',
        '--specpath=.',
        '--hidden-import=PyQt5',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.QtWidgets',
        '--add-data=logo.png;.',
        '--add-data=logo.ico;.',
        'main.py',
    ]

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        exe_path = os.path.abspath('output/desktop_sticky_notes.exe')
        print()
        print("=" * 50)
        print("  BUILD SUCCESS!")
        print("=" * 50)
        print(f"  EXE: {exe_path}")
        print()
        print("  Tips:")
        print("  - First launch may take 5-10 seconds")
        print("  - Database will be created automatically")
        print("  - You can copy the EXE to any folder")
        print()
        print("  Auto starting...")
        subprocess.Popen([exe_path])
    else:
        print()
        print("BUILD FAILED! Check errors above.")

    # Cleanup spec file
    for f in os.listdir('.'):
        if f.endswith('.spec'):
            try:
                os.remove(f)
            except Exception:
                pass

    print()
    input("Press Enter to exit...")


if __name__ == "__main__":
    build_exe()
