"""Launch the existing 125 MHz real-time application or perform offline checks."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / 'board/runtime/frame_retire_125'


def start_commands(boot_id):
    return [
        [sys.executable, '-u', str(RUNTIME / '01_load_identity.py'), '--cold-boot', boot_id],
        [sys.executable, '-u', str(RUNTIME / '11_live_ui_touch.py'), '--boot', boot_id,
         '--cold-session-confirmed'],
    ]


def load_precheck():
    spec = importlib.util.spec_from_file_location('pq_board_precheck', ROOT / 'board/precheck.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description='125 MHz实时采集、事件、模型、HDMI及PC共享显示')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--check', action='store_true', help='离线文件、固件及合同检查；不访问硬件')
    modes.add_argument('--precheck', action='store_true', help='板端只读环境初筛；不加载固件')
    modes.add_argument('--plan', action='store_true', help='仅显示原启动链，不执行命令')
    args = parser.parse_args()
    if args.plan:
        print(json.dumps(dict(mode='REALTIME_FRAME_RETIRE_125', commands=start_commands('<current_boot_id>'),
            interpreter='Both original stages use this same Python interpreter',
            prerequisite='Full power cycle and no other PL/Reader/video owner in this boot',
            execution='NOT_RUN'), ensure_ascii=False, indent=2))
        return
    if args.check:
        runpy.run_path(str(ROOT / 'tools/verify_package.py'), run_name='__main__')
        return
    if not sys.platform.startswith('linux'):
        raise SystemExit('应用和环境初筛在PYNQ板端Linux执行；电脑使用 --check 或 --plan。')
    # Same offline identity checks before any board-side action.
    runpy.run_path(str(ROOT / 'tools/verify_package.py'), run_name='__main__')
    report = load_precheck().collect()
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if not report['ready_for_original_startup']:
        raise SystemExit('环境初筛未通过；按列出的项目处理，不加载固件、不自动重试。')
    if args.precheck:
        return
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text(encoding='utf-8').strip()
    first, second = start_commands(boot_id)
    print('即将按原流程执行固件身份加载和实时入口；须已完整断电冷启动，且本boot无其他硬件程序。', flush=True)
    subprocess.run(first, cwd=RUNTIME, check=True)
    # Reuse the original owner process and its signal/buffer handling; no shell
    # pipeline, extra Reader, hidden background service or automatic reset.
    os.chdir(RUNTIME)
    os.execv(sys.executable, second)


if __name__ == '__main__':
    main()
