from pathlib import Path
import subprocess, sys

# Search all Python files for verify_connection definition
repo = Path(r'C:\Users\Zohar\Dropbox\Windows11\REPOS\ABZU\INANNA\inanna')
results = []
for f in repo.rglob('*.py'):
    try:
        text = f.read_text(encoding='utf-8')
        if 'def verify_connection' in text:
            lines = text.splitlines()
            for i, l in enumerate(lines):
                if 'def verify_connection' in l:
                    # Get context
                    ctx = lines[i:i+20]
                    results.append(f"\n=== {f.relative_to(repo)} line {i+1} ===")
                    results.extend(ctx)
    except:
        pass

out = Path(r'C:\Users\Zohar\Dropbox\Windows11\REPOS\ABZU\INANNA\inanna\vc_found.txt')
out.write_text('\n'.join(results), encoding='utf-8')
print(f"Found in {len([r for r in results if r.startswith('===')])} files")
