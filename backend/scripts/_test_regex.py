"""Test the FILE_SCHEMA regex against actual STP file content."""
import re

# Current regex (from step_parser.py)
old_re = re.compile(r"FILE_SCHEMA\(\(\s*'([^']+)'\s*\)\)\s*;", re.IGNORECASE)

# Fixed regex with optional whitespace before (
new_re = re.compile(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'\s*\)\s*\)\s*;", re.IGNORECASE)

test = "FILE_SCHEMA (('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF { 1 0 10303 442 1 1 4 }'));"

m1 = old_re.search(test)
print(f"Old regex match: {m1}")

m2 = new_re.search(test)
print(f"New regex match: {m2}")
if m2:
    print(f"  group(1) = {m2.group(1)}")

# Also test multi-line version (FILE_SCHEMA on one line, value on next)
test2 = """FILE_SCHEMA (('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF { 1 0 10303 442 1
 1 4 }'));"""
m3 = new_re.search(test2)
print(f"\nMulti-line match: {m3}")
if m3:
    print(f"  group(1) = {m3.group(1)}")
