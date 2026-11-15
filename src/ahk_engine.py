#!/usr/bin/env python3
"""
AutoHotkey (.ahk v1/v2 minimal) to Python/xdotool translator & runner
Supports: Click, MouseMove, Sleep, Send, Loop, Break, Variables
"""
import sys
import os
import re
import time
import subprocess

def run_ahk(script_content, target_display=":2", stop_check=None):
    env = os.environ.copy()
    env["DISPLAY"] = target_display

    lines = script_content.splitlines()
    
    # Simple AST / instruction list
    instructions = []
    for raw_line in lines:
        line = re.sub(r';.*$', '', raw_line).strip()
        if not line:
            continue
        
        # Click x, y
        m = re.match(r'^Click(?:\s*,\s*(\d+)\s*,\s*(\d+))?', line, re.I)
        if m:
            x, y = m.group(1), m.group(2)
            instructions.append(('CLICK', int(x) if x else None, int(y) if y else None))
            continue
            
        # MouseMove x, y
        m = re.match(r'^MouseMove\s*,\s*(\d+)\s*,\s*(\d+)', line, re.I)
        if m:
            instructions.append(('MOUSEMOVE', int(m.group(1)), int(m.group(2))))
            continue

        # Sleep ms
        m = re.match(r'^Sleep\s*,\s*(\d+)', line, re.I)
        if m:
            instructions.append(('SLEEP', int(m.group(1))))
            continue

        # Send keys
        m = re.match(r'^Send(?:\s*,\s*|\s+)(.+)', line, re.I)
        if m:
            keys = m.group(1).strip()
            instructions.append(('SEND', keys))
            continue
            
        # Loop start
        m = re.match(r'^Loop(?:\s*,\s*(\d+)|\s+(\d+))?\s*\{?', line, re.I)
        if m:
            count = m.group(1) or m.group(2)
            instructions.append(('LOOP_START', int(count) if count else None))
            continue

        if line == '}':
            instructions.append(('LOOP_END',))
            continue

    def execute_block(instrs, loop_count=None):
        runs = 0
        while True:
            if stop_check and stop_check():
                break
            for inst in instrs:
                if stop_check and stop_check():
                    break
                op = inst[0]
                if op == 'CLICK':
                    if inst[1] is not None and inst[2] is not None:
                        subprocess.run(["xdotool", "mousemove", str(inst[1]), str(inst[2]), "click", "1"], env=env)
                    else:
                        subprocess.run(["xdotool", "click", "1"], env=env)
                elif op == 'MOUSEMOVE':
                    subprocess.run(["xdotool", "mousemove", str(inst[1]), str(inst[2])], env=env)
                elif op == 'SLEEP':
                    time.sleep(inst[1] / 1000.0)
                elif op == 'SEND':
                    key_str = inst[1]
                    # Parse {Space}, {Enter}, etc
                    keys = re.findall(r'\{([A-Za-z0-9_]+)\}|([^{}\s]+)', key_str)
                    for braced, plain in keys:
                        k = braced or plain
                        if k.lower() == 'space':
                            k = 'space'
                        subprocess.run(["xdotool", "key", k], env=env)
            runs += 1
            if loop_count is not None and runs >= loop_count:
                break
            if loop_count is None and not any(i[0] == 'LOOP_START' for i in instrs):
                break

    # If there's an outer loop, handle it
    execute_block(instructions, loop_count=None)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            code = f.read()
        disp = sys.argv[2] if len(sys.argv) > 2 else ":2"
        run_ahk(code, disp)
