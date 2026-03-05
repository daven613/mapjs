#!/usr/bin/env python3
"""
Merge all torah_N_packages.json files into a single packageData.js file
for use in the Torah Map Explorer search app.
"""
import json
import os
import glob

def main():
    review_dir = os.path.dirname(os.path.abspath(__file__)) + '/review'

    # Collect all confirmed package files (not new_packages or additions)
    patterns = [
        os.path.join(review_dir, 'torah_*_packages.json'),
        os.path.join(review_dir, 'lm2', 'torah_*_packages.json'),
    ]

    all_packages = []
    seen_torahs = set()

    for pattern in patterns:
        for filepath in sorted(glob.glob(pattern)):
            # Skip new_packages files
            if 'new_packages' in os.path.basename(filepath):
                continue

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    raw = f.read()

                # Fix unescaped quotes inside JSON strings (Hebrew abbreviation marks like נ"ל)
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    # Replace unescaped inner quotes: find quotes that are clearly
                    # inside strings (preceded and followed by non-JSON-structural chars)
                    import re
                    # Strategy: fix quotes between Hebrew letters (abbreviation marks)
                    fixed = re.sub(r'(?<=[\u0590-\u05FF])"(?=[\u0590-\u05FF])', '\\"', raw)
                    # Also fix quotes between Hebrew and Latin in the same context
                    fixed = re.sub(r'(?<=[\u0590-\u05FF])"(?=[A-Za-z ])', '\\"', fixed)
                    fixed = re.sub(r'(?<=[A-Za-z])"(?=[\u0590-\u05FF])', '\\"', fixed)
                    # Fix patterns like ל' (letter + quote + space/comma/period)
                    fixed = re.sub(r"(?<=[\u0590-\u05FF])'(?=[\s,.\)])", "'", fixed)
                    try:
                        data = json.loads(fixed)
                    except json.JSONDecodeError:
                        # More aggressive: escape ALL internal quotes in string values
                        # by parsing line-by-line between known JSON structural quotes
                        fixed2 = re.sub(r'(?<=[a-z,\w\s])"(?=[a-z,\w\s])', '\\"', fixed)
                        data = json.loads(fixed2)

                packages = data.get('packages', [])
                for pkg in packages:
                    torah_ref = pkg.get('torah_ref')
                    if torah_ref is not None:
                        seen_torahs.add(torah_ref)
                    all_packages.append(pkg)

            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: skipping {filepath}: {e}")

    # Sort by torah_ref then id
    all_packages.sort(key=lambda p: (p.get('torah_ref', 0), p.get('id', 0)))

    # Write as a JS global variable
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'packageData.js')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('// Auto-generated package data - do not edit manually\n')
        f.write('var packageData = ')
        json.dump(all_packages, f, ensure_ascii=False, indent=None)
        f.write(';\n')

    print(f"Generated {output_path}")
    print(f"  {len(all_packages)} packages from {len(seen_torahs)} Torahs")
    print(f"  File size: {os.path.getsize(output_path) / 1024:.1f} KB")

if __name__ == '__main__':
    main()
