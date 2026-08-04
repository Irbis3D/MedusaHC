#!/usr/bin/env python3
# Post-process gcode:
# 1) After each tool call Tn:
#    - Find the first *relevant* move (G0/G1), ignoring E-only extrusion moves (G1 E...).
#    - If that first relevant move is Z-only (G0/G1 Z... without X/Y/E),
#      then find the next XY-only move (G0/G1 with X or Y, without Z/E).
#      Swap those two move lines and transfer F from Z-move to XY-move (only if XY has no F).

import re
import sys
from pathlib import Path

TOOL_RE = re.compile(r'^\s*T(\d+)\s*(?:;.*)?$', re.IGNORECASE)

# Move commands: G0 or G1
MOVE_RE = re.compile(r'^\s*G0\b|^\s*G1\b', re.IGNORECASE)
G1_RE   = re.compile(r'^\s*G1\b', re.IGNORECASE)

F_RE = re.compile(r'(?<![A-Z])F\s*([-+]?\d*\.?\d+)', re.IGNORECASE)

def strip_comment_keep(line: str):
    if ';' in line:
        a, b = line.split(';', 1)
        return a.rstrip(), ';' + b
    return line.rstrip('\n'), ''

def strip_comment(line: str) -> str:
    return line.split(';', 1)[0].strip()

def has_axis(cmd: str, axis: str) -> bool:
    return re.search(rf'(?<![A-Z]){axis}\s*[-+]?\d*\.?\d+', cmd, re.IGNORECASE) is not None

def is_e_only_move(cmd: str) -> bool:
    return (G1_RE.match(cmd)
            and has_axis(cmd, 'E')
            and not has_axis(cmd, 'X')
            and not has_axis(cmd, 'Y')
            and not has_axis(cmd, 'Z'))

def is_z_only_move(cmd: str) -> bool:
    return (MOVE_RE.match(cmd)
            and has_axis(cmd, 'Z')
            and not has_axis(cmd, 'X')
            and not has_axis(cmd, 'Y')
            and not has_axis(cmd, 'E'))

def is_xy_only_move(cmd: str) -> bool:
    return (MOVE_RE.match(cmd)
            and (has_axis(cmd, 'X') or has_axis(cmd, 'Y'))
            and not has_axis(cmd, 'Z')
            and not has_axis(cmd, 'E'))

def extract_F(code: str):
    m = F_RE.search(code)
    return m.group(1) if m else None

def remove_first_F(code: str) -> str:
    return re.sub(r'\s*(?<![A-Z])F\s*[-+]?\d*\.?\d+', '', code, count=1, flags=re.IGNORECASE).strip()

def add_F(code: str, fval: str) -> str:
    return f"{code.strip()} F{fval}"

def transfer_F(z_line: str, xy_line: str):
    z_code, z_cmt = strip_comment_keep(z_line)
    xy_code, xy_cmt = strip_comment_keep(xy_line)

    zF = extract_F(z_code)
    xyF = extract_F(xy_code)

    if zF and not xyF:
        z_code2 = remove_first_F(z_code)
        xy_code2 = add_F(xy_code, zF)

        z_out = z_code2 + ((' ' + z_cmt.strip()) if z_cmt else '') + "\n"
        xy_out = xy_code2 + ((' ' + xy_cmt.strip()) if xy_cmt else '') + "\n"
        return z_out, xy_out

    return z_line, xy_line

def process(lines) -> bool:
    changed = False

    i = 0
    while i < len(lines):
        cmd_i = strip_comment(lines[i])
        if not TOOL_RE.match(cmd_i):
            i += 1
            continue

        z_idx = None
        xy_idx = None
        first_relevant_move_found = False

        j = i + 1
        while j < len(lines):
            c = strip_comment(lines[j])

            if TOOL_RE.match(c):
                break

            if not first_relevant_move_found and is_e_only_move(c):
                j += 1
                continue

            if not first_relevant_move_found and MOVE_RE.match(c):
                first_relevant_move_found = True
                if is_z_only_move(c):
                    z_idx = j
                else:
                    z_idx = None
                    break
                j += 1
                continue

            if z_idx is not None and xy_idx is None and is_xy_only_move(c):
                xy_idx = j
                break

            j += 1

        if z_idx is None or xy_idx is None:
            i += 1
            continue

        new_z, new_xy = transfer_F(lines[z_idx], lines[xy_idx])
        if new_z != lines[z_idx] or new_xy != lines[xy_idx]:
            lines[z_idx], lines[xy_idx] = new_z, new_xy
            changed = True

        lines[z_idx], lines[xy_idx] = lines[xy_idx], lines[z_idx]
        changed = True

        i = xy_idx + 1

    return changed

def main():
    if len(sys.argv) < 2:
        raise SystemExit("Expected gcode filepath as last argument")

    gcode_path = Path(sys.argv[-1].strip('"'))
    if not gcode_path.is_file():
        raise SystemExit(f"Gcode file not found: {gcode_path}")

    lines = gcode_path.read_text(encoding="utf-8", errors="ignore").splitlines(True)
    changed = process(lines)
    if changed:
        gcode_path.write_text("".join(lines), encoding="utf-8")

if __name__ == "__main__":
    main()