"""Start/stop only this project's portable PCSX2. --run is required for mutations."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[2]
EMU=ROOT/'work/emulator/pcsx2'
EXE=EMU/'pcsx2-qt.exe'


def pids():
    cmd="Get-CimInstance Win32_Process -Filter \"Name='pcsx2-qt.exe'\" | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"
    result=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,check=True)
    items=json.loads(result.stdout) if result.stdout.strip() else []
    if isinstance(items,dict):items=[items]
    return [p['ProcessId'] for p in items if p.get('ExecutablePath') and os.path.normcase(p['ExecutablePath'])==os.path.normcase(str(EXE))]


def stop():
    for pid in pids():subprocess.run(['taskkill','/PID',str(pid),'/F'],capture_output=True,check=True)
    deadline=time.time()+20
    while pids():
        if time.time()>deadline:raise TimeoutError('Project emulator did not exit')
        time.sleep(.2)


def start(iso,state=None):
    if pids():raise RuntimeError('Project emulator already running; stop it explicitly first')
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    args=[str(EXE),'-batch','-portable']
    if state:
        saved=Path(state).resolve()
        if not saved.is_file():raise FileNotFoundError(saved)
        args+=['-statefile',str(saved)]
    args+=['--',str(Path(iso).resolve())]
    return subprocess.Popen(args,cwd=EMU,startupinfo=si)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=['status','start','stop'])
    ap.add_argument('iso',nargs='?');ap.add_argument('--state');ap.add_argument('--run',action='store_true');args=ap.parse_args()
    print('Project executable:',EXE,'PIDs:',pids())
    if args.action=='status':return
    if not args.run:print('DRY RUN: --run performs',args.action,'ISO:',args.iso,'state:',args.state);return
    if args.action=='stop':stop()
    else:
        if not args.iso:raise ValueError('Explicit ISO required')
        print('Started PID',start(args.iso,args.state).pid)


if __name__=='__main__':main()
