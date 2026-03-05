#!/usr/bin/env python3
"""Generate _visualizer_manifest.json for the Torah Package Visualizer."""
import json, glob, os, re

REVIEW_DIR = os.path.dirname(os.path.abspath(__file__))
manifest = {"files": []}

def extract_torah_num(filename):
    m = re.search(r'torah_(\d+)_', filename)
    return int(m.group(1)) if m else None

def extract_type(filename):
    if '_new_packages' in filename: return 'new_packages'
    if '_packages' in filename: return 'packages'
    if '_additions' in filename: return 'additions'
    return None

# LM1: data/review/torah_*_{packages,additions,new_packages}.json
for f in sorted(glob.glob(os.path.join(REVIEW_DIR, 'torah_*_*.json'))):
    basename = os.path.basename(f)
    num = extract_torah_num(basename)
    ftype = extract_type(basename)
    if num is None or ftype is None:
        continue
    manifest["files"].append({
        "path": basename,
        "volume": "lm1",
        "torah_num": num,
        "type": ftype
    })

# LM2 (our branch): data/review/lm2/torah_*_*.json
for f in sorted(glob.glob(os.path.join(REVIEW_DIR, 'lm2', 'torah_*_*.json'))):
    basename = os.path.basename(f)
    num = extract_torah_num(basename)
    ftype = extract_type(basename)
    if num is None or ftype is None:
        continue
    manifest["files"].append({
        "path": "lm2/" + basename,
        "volume": "lm2",
        "torah_num": num,
        "type": ftype
    })

# LM2 (main-deploy): data/review/lm2-main-deploy/torah_*_*.json
for f in sorted(glob.glob(os.path.join(REVIEW_DIR, 'lm2-main-deploy', 'torah_*_*.json'))):
    basename = os.path.basename(f)
    num = extract_torah_num(basename)
    ftype = extract_type(basename)
    if num is None or ftype is None:
        continue
    manifest["files"].append({
        "path": "lm2-main-deploy/" + basename,
        "volume": "lm2-md",
        "torah_num": num,
        "type": ftype
    })

out_path = os.path.join(REVIEW_DIR, '_visualizer_manifest.json')
with open(out_path, 'w') as f:
    json.dump(manifest, f, indent=2)

print(f"Generated {out_path}")
print(f"  LM1: {sum(1 for x in manifest['files'] if x['volume']=='lm1')} files")
print(f"  LM2 (ours): {sum(1 for x in manifest['files'] if x['volume']=='lm2')} files")
print(f"  LM2 (main-deploy): {sum(1 for x in manifest['files'] if x['volume']=='lm2-md')} files")
print(f"  Total: {len(manifest['files'])} files")
