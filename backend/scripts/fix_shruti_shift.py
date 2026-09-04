#!/usr/bin/env python3
"""
Fix the Shruti naming shift in shruti_mapping.py and raga_mapping.py.

Why this script exists
----------------------
The SHRUTI_NAMES list currently has incorrect names for indices 9-15:
  index 9  has ratio 729/512 (≈372 Hz) which is Tivra Ma  — NOT Pa
  index 10 has ratio 3/2     (≈392 Hz) which is Pa
  … etc.

SWARA_MAP in raga_mapping.py maps swara names to integer indices and those
integers are used throughout RAGA_DATABASE.  Since the old names were wrong,
the old SWARA_MAP had 'Pa' → 9 (which is Tivra Ma's bin), causing every
raga that uses Pa, Dha, or Ni to point at the wrong frequency.

The fix:
  1. Rename SHRUTI_NAMES[9:16] to the correct musicological labels.
  2. Update SWARA_MAP: 'Tivra Ma'→9, 'Pa'→10, 'Dha1'→11, 'Dha2'→12,
     'Ni1'→13, 'Ni2'→14, 'Ni3'→15
  3. In every raga entry, increment integers 9-14 by +1 so they point
     to the new (correct) frequency index.  Integers 0-8 and 15+ are
     unaffected.
"""
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SHRUTI_FILE = BACKEND / 'ml_engine' / 'shruti_mapping.py'
RAGA_FILE   = BACKEND / 'ml_engine' / 'raga_mapping.py'

# ── Step 1: Fix SHRUTI_NAMES in shruti_mapping.py ────────────────────────────
OLD_NAMES = [
    "'Shruti 10 (Pa)'",
    "'Shruti 11 (Dha1)'",
    "'Shruti 12 (Dha2)'",
    "'Shruti 13 (Ni1)'",
    "'Shruti 14 (Ni2)'",
    "'Shruti 15 (Ni3)'",
]
NEW_NAMES = [
    "'Shruti 10 (Tivra Ma)'",
    "'Shruti 11 (Pa)'",
    "'Shruti 12 (Dha1)'",
    "'Shruti 13 (Dha2)'",
    "'Shruti 14 (Ni1)'",
    "'Shruti 15 (Ni2)'",
]

shruti_src = SHRUTI_FILE.read_text()
for old, new in zip(OLD_NAMES, NEW_NAMES):
    assert old in shruti_src, f'Expected to find {old} in shruti_mapping.py'
    shruti_src = shruti_src.replace(old, new, 1)

# Also fix the ratio comment on index 9 row
# S10 was labelled "Pa" in the comment, should be "Tivra Ma"
shruti_src = shruti_src.replace(
    '# S10 Pa      — 372.51 Hz',
    '# S10 Tivra Ma — 372.51 Hz',
)
# Fix subsequent comment labels too
comment_fixes = [
    ('# S11 Dha1    — 392.44 Hz', '# S11 Pa       — 392.44 Hz'),
    ('# S12 Dha2    — 413.43 Hz', '# S12 Dha1     — 413.43 Hz'),
    ('# S13 Ni1     — 418.60 Hz', '# S13 Dha2     — 418.60 Hz'),
    ('# S14 Ni2     — 436.05 Hz', '# S14 Ni1      — 436.05 Hz'),
    ('# S15 Ni3     — 441.49 Hz', '# S15 Ni2      — 441.49 Hz'),
    ('# S16 Sa\'     — 465.11 Hz', '# S16 Ni3      — 465.11 Hz'),
]
for old_c, new_c in comment_fixes:
    if old_c in shruti_src:
        shruti_src = shruti_src.replace(old_c, new_c, 1)

SHRUTI_FILE.write_text(shruti_src)
print(f'✓ {SHRUTI_FILE.name} — names corrected')

# ── Step 2: Fix SWARA_MAP and RAGA_DATABASE in raga_mapping.py ───────────────
raga_src = RAGA_FILE.read_text()

# 2a. Update SWARA_MAP definition
OLD_SWARA_MAP = (
    "    'Ma1': 6, 'Ma2': 7, 'Ma3': 8, 'Pa': 9, 'Dha1': 10, 'Dha2': 11,\n"
    "    'Ni1': 12, 'Ni2': 13, 'Ni3': 14,"
)
NEW_SWARA_MAP = (
    "    'Ma1': 6, 'Ma2': 7, 'Ma3': 8, 'Tivra Ma': 9, 'Pa': 10,\n"
    "    'Dha1': 11, 'Dha2': 12, 'Ni1': 13, 'Ni2': 14, 'Ni3': 15,"
)
assert OLD_SWARA_MAP in raga_src, 'SWARA_MAP section not found as expected'
raga_src = raga_src.replace(OLD_SWARA_MAP, NEW_SWARA_MAP, 1)

# 2b. Update swara_names lookup dict inside detect_raga()
OLD_SWARA_NAMES = (
    "        0: 'Sa', 1: 'Re1', 2: 'Re2', 3: 'Ga1', 4: 'Ga2', 5: 'Ga3',\n"
    "        6: 'Ma1', 7: 'Ma2', 8: 'Ma3', 9: 'Pa', 10: 'Dha1', 11: 'Dha2',\n"
    "        12: 'Ni1', 13: 'Ni2', 14: 'Ni3',"
)
NEW_SWARA_NAMES = (
    "        0: 'Sa', 1: 'Re1', 2: 'Re2', 3: 'Ga1', 4: 'Ga2', 5: 'Ga3',\n"
    "        6: 'Ma1', 7: 'Ma2', 8: 'Ma3', 9: 'Tivra Ma', 10: 'Pa',\n"
    "        11: 'Dha1', 12: 'Dha2', 13: 'Ni1', 14: 'Ni2', 15: 'Ni3',"
)
assert OLD_SWARA_NAMES in raga_src, 'swara_names dict not found as expected'
raga_src = raga_src.replace(OLD_SWARA_NAMES, NEW_SWARA_NAMES, 1)

# 2c. In RAGA_DATABASE, increment every integer in range [9, 14] that appears
#     inside swaras/arohana/avarohana/vadi/samvadi fields.
#     Strategy: work only on lines that contain those field names, and only
#     on the integer portion of those lines.
#
#     We process the file line by line.  For lines that are raga data lines
#     (identified by field keywords), we replace bare integers 9-14 with +1.
#
#     Crucially we must NOT touch integers ≥15 (they are either already
#     correct upper-octave indices like 15-21, or 0-8 which are unaffected).
#     We also must NOT touch integers in comments or non-raga lines.

RAGA_FIELDS = {'swaras', 'arohana', 'avarohana', 'vadi', 'samvadi'}

def shift_raga_line(line):
    """Increment integers 9-14 in a raga data line."""
    # Replace \b9\b, \b10\b, ... \b14\b with value+1.
    # Process in descending order to avoid double-substitution
    # (e.g., 9→10 then 10→11 would incorrectly bump the original 10).
    result = line
    for old_val in range(14, 8, -1):  # 14 down to 9
        new_val = old_val + 1
        # Only match bare integers (not part of larger numbers)
        result = re.sub(
            r'(?<!\d)' + str(old_val) + r'(?!\d)',
            str(new_val),
            result,
        )
    return result

lines = raga_src.split('\n')
new_lines = []
in_raga_db = False  # track when we're inside RAGA_DATABASE = [...]

for line in lines:
    stripped = line.strip()

    # Detect entry / exit of the RAGA_DATABASE block
    if 'RAGA_DATABASE = [' in line:
        in_raga_db = True
    # The database ends at the closing ']' on its own line
    if in_raga_db and stripped == ']':
        in_raga_db = False

    if in_raga_db:
        # Only rewrite lines that are actual raga field lines
        if any(f"'{fld}'" in line or f'"{fld}"' in line for fld in RAGA_FIELDS):
            line = shift_raga_line(line)

    new_lines.append(line)

raga_src = '\n'.join(new_lines)

RAGA_FILE.write_text(raga_src)
print(f'✓ {RAGA_FILE.name} — SWARA_MAP, swara_names, and RAGA_DATABASE indices updated')

# ── Step 3: Validate ──────────────────────────────────────────────────────────
# Re-import the fixed modules and run basic sanity checks.
import importlib, sys

# Force fresh import (modules may be cached from a previous run in the same process)
for mod in ['ml_engine.shruti_mapping', 'ml_engine.raga_mapping']:
    sys.modules.pop(mod, None)

sys.path.insert(0, str(BACKEND))
from ml_engine.shruti_mapping import SHRUTI_NAMES, SHRUTI_FREQUENCIES, SHRUTI_RATIOS
from ml_engine.raga_mapping import SWARA_MAP, RAGA_DATABASE

# Check index 10 is now Pa (ratio 3/2)
pa_freq = SHRUTI_FREQUENCIES[SHRUTI_NAMES[10]]
assert abs(pa_freq - 392.44) < 1.0, f'Pa freq wrong: {pa_freq}'
print(f'  SHRUTI_NAMES[10] = {SHRUTI_NAMES[10]}  freq = {pa_freq} Hz  ✓')

# Check index 9 is now Tivra Ma
tivra_ma_freq = SHRUTI_FREQUENCIES[SHRUTI_NAMES[9]]
expected_tivra = round(261.626 * 729 / 512, 2)
assert abs(tivra_ma_freq - expected_tivra) < 0.5, f'Tivra Ma freq wrong: {tivra_ma_freq}'
print(f'  SHRUTI_NAMES[9]  = {SHRUTI_NAMES[9]}  freq = {tivra_ma_freq} Hz  ✓')

# Check SWARA_MAP
assert SWARA_MAP['Pa'] == 10,       f"SWARA_MAP['Pa'] = {SWARA_MAP['Pa']}, expected 10"
assert SWARA_MAP['Ni2'] == 14,      f"SWARA_MAP['Ni2'] = {SWARA_MAP['Ni2']}, expected 14"
assert SWARA_MAP['Ni3'] == 15,      f"SWARA_MAP['Ni3'] = {SWARA_MAP['Ni3']}, expected 15"
pa_idx   = SWARA_MAP['Pa']
ni2_idx  = SWARA_MAP['Ni2']
ni3_idx  = SWARA_MAP['Ni3']
print(f'  SWARA_MAP Pa={pa_idx}, Ni2={ni2_idx}, Ni3={ni3_idx}  ✓')

# No raga should reference an out-of-range index
for raga in RAGA_DATABASE:
    rname = raga['name']
    for field in ('swaras', 'arohana', 'avarohana'):
        for idx in raga[field]:
            assert idx <= 21, f'{rname}.{field} has out-of-range index {idx}'
    assert raga['vadi'] <= 21,    f'{rname} vadi={raga["vadi"]} out of range'
    assert raga['samvadi'] <= 21, f'{rname} samvadi={raga["samvadi"]} out of range'

print(f'  All {len(RAGA_DATABASE)} ragas validated — no out-of-range indices  ✓')
print('\nAll checks passed.')
