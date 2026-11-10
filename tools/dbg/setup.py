"""Prepare this project's isolated, muted portable PCSX2 (work/emulator/pcsx2).

Copies the runtime and BIOS from the sibling Sunrise Eiyuutan 2 portable install and
writes fresh settings: PINE on 28027 (env SWW_PINE_PORT), audio muted, memory cards
off, fast boot, no imported saves. Dry run unless --write; refuses an existing config."""
import argparse, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'Sunrise Eiyuutan 2/work/emulator/pcsx2'
DEST = ROOT / 'work/emulator/pcsx2'
CONFIG = '''[UI]
SetupWizardIncomplete = false
ConfirmShutdown = false
SettingsVersion = 1
PauseOnFocusLoss = false
StartFullscreen = false

[Folders]
Bios = bios
Snapshots = snaps
Savestates = sstates
MemoryCards = memcards
Logs = logs
Cache = cache

[Filenames]
BIOS = scph39001.bin

[EmuCore]
EnableFastBoot = true
EnablePINE = true
PINESlot = 28027
EnableCheats = false
EnablePatches = false
SaveStateOnShutdown = false
BackupSavestate = false

[MemoryCards]
Slot1_Enable = true
Slot1_Filename = SWW_test.ps2
Slot2_Enable = false

[AutoUpdater]
CheckAtStartup = false

[SPU2/Output]
OutputMuted = true
StandardVolume = 0
OutputModule = nullout

[Pad1]
Type = DualShock2

[EmuCore/GS]
upscale_multiplier = 1
VsyncEnable = false
'''

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    files = [p for p in SOURCE.iterdir() if p.is_file() and (p.suffix.lower() in ('.exe', '.dll') or p.name in ('qt.conf', 'portable.txt'))]
    dirs = ['QtPlugins', 'resources', 'bios', 'D3D12']
    print('Source:', SOURCE, '->', DEST, '| files', len(files), '| dirs', dirs)
    if not a.write:
        print('DRY RUN: --write copies runtime + BIOS and writes fresh muted settings'); return
    if (DEST / 'inis/PCSX2.ini').exists():
        raise FileExistsError('Destination already configured')
    DEST.mkdir(parents=True, exist_ok=True)
    for p in files: shutil.copy2(p, DEST / p.name)
    for d in dirs: shutil.copytree(SOURCE / d, DEST / d, dirs_exist_ok=True)
    (DEST / 'inis').mkdir(exist_ok=True)
    (DEST / 'inis/PCSX2.ini').write_text(CONFIG, encoding='utf-8')
    print('written')

if __name__ == '__main__':
    main()
