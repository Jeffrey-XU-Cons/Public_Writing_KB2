#!/usr/bin/env python3
"""Find and fix YAML fields where double-quoted strings close early due to embedded ASCII quotes."""
import re

filepath = "D:/projects/Public_Writing_KB/02_rules/content_quality/quality_rules.yaml"

with open(filepath, encoding='utf-8') as f:
    lines = f.readlines()

problems = []
for i, line in enumerate(lines):
    s = line.strip()
    if not s or s.startswith('#') or s.endswith('|') or s.endswith('>'):
        continue
    colon_pos = s.find(': ')
    if colon_pos == -1:
        continue
    val = s[colon_pos+2:]
    if not val.startswith('"'):
        continue
    # scan through the quoted value
    inner = val[1:]  # skip opening quote
    j = 0
    closed_at = -1
    while j < len(inner):
        c = inner[j]
        if c == '\\':
            j += 2
            continue
        if c == '"':
            closed_at = j
            break
        j += 1
    if closed_at != -1 and closed_at < len(inner) - 1:
        remaining = inner[closed_at+1:].strip()
        if remaining:
            problems.append((i+1, line.rstrip(), val, colon_pos))

print(f"Found {len(problems)} problematic lines:")
for lineno, text, val, cp in problems:
    print(f"  Line {lineno}: {text[:100]}")
print()

# Fix: convert problematic double-quoted values to single-quoted
fixed_lines = list(lines)
for lineno, text, val, cp in problems:
    idx = lineno - 1
    line = lines[idx]
    # Extract the indent + key + ': '
    prefix_match = re.match(r'^(\s*)(\w[\w_]*): ', line)
    if not prefix_match:
        print(f"  SKIP line {lineno}: can't parse")
        continue
    indent = prefix_match.group(1)
    key = prefix_match.group(2)
    # Extract the full value content (strip outer quotes)
    # The value starts with " - find the actual full content without YAML delimiters
    # Since it's broken, reconstruct by removing the outer " at start and end
    raw_val = val
    # Strip surrounding quotes if they exist
    if raw_val.startswith('"') and raw_val.endswith('"'):
        inner_content = raw_val[1:-1]
    else:
        # Value ends mid-stream - take everything between first and last "
        first_q = raw_val.index('"')
        last_q = raw_val.rindex('"')
        inner_content = raw_val[first_q+1:last_q]
    # Escape single quotes in the content
    escaped = inner_content.replace("'", "''")
    new_line = f"{indent}{key}: '{escaped}'\n"
    fixed_lines[idx] = new_line
    print(f"  Fixed line {lineno}:")
    print(f"    OLD: {line.rstrip()[:90]}")
    print(f"    NEW: {new_line.rstrip()[:90]}")

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print(f"\nDone. Fixed {len(problems)} lines.")
