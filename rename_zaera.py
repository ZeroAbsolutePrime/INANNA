"""
Rename ZAERA → INANNA NAMMU across all project files.
Covers: display names, preferred names, auth references,
        documentation, tests, code comments.
"""
import json
from pathlib import Path

base = Path(r'C:\Users\Zohar\Dropbox\Windows11\REPOS\ABZU\INANNA')

# ── Simple string replacements (ordered: longer/specific first) ──────
REPLACEMENTS = [
    # Auth / login
    ('username: "INANNA NAMMU"',               'username: "INANNA NAMMU"'),
    ('username="INANNA NAMMU"',                'username="INANNA NAMMU"'),
    ('"username": "INANNA NAMMU"',             '"username": "INANNA NAMMU"'),
    ('seed_user("inanna_nammu"',               'seed_user("inanna_nammu"'),
    ('seed_user("INANNA NAMMU"',               'seed_user("INANNA NAMMU"'),
    ('get_by_username("INANNA NAMMU")',         'get_by_username("INANNA NAMMU")'),
    ('authenticate("INANNA NAMMU"',            'authenticate("INANNA NAMMU"'),
    ('issue("user_abc12345", "INANNA NAMMU"',   'issue("user_abc12345", "INANNA NAMMU"'),
    ('"username": "inanna_nammu"',             '"username": "inanna_nammu"'),
    # Display names
    ('display_name="INANNA NAMMU"',            'display_name="INANNA NAMMU"'),
    ('display_name = "INANNA NAMMU"',          'display_name = "INANNA NAMMU"'),
    ('"display_name": "INANNA NAMMU"',         '"display_name": "INANNA NAMMU"'),
    # Preferred name
    ('preferred_name="INANNA NAMMU"',          'preferred_name="INANNA NAMMU"'),
    ('"preferred_name": "INANNA NAMMU"',       '"preferred_name": "INANNA NAMMU"'),
    # Profile / session
    ('Active user: INANNA NAMMU',              'Active user: INANNA NAMMU'),
    ('Auto-login: INANNA NAMMU',               'Auto-login: INANNA NAMMU'),
    ('active_user="INANNA NAMMU',              'active_user="INANNA NAMMU'),
    ('active_user: str = "INANNA NAMMU',       'active_user: str = "INANNA NAMMU'),
    ('approved_by="INANNA NAMMU"',             'approved_by="INANNA NAMMU"'),
    ('approved_by = "INANNA NAMMU"',           'approved_by = "INANNA NAMMU"'),
    # Test assertions and strings
    ('record.username == "INANNA NAMMU"',      'record.username == "INANNA NAMMU"'),
    ('record.display_name == "INANNA NAMMU"',  'record.display_name == "INANNA NAMMU"'),
    ('"INANNA NAMMU", "Alice"',                '"INANNA NAMMU", "Alice"'),
    ('"INANNA NAMMU", "ETERNALOVE"',           '"INANNA NAMMU", "ETERNALOVE"'),
    ('("INANNA NAMMU", "ETERNALOVE")',         '("INANNA NAMMU", "ETERNALOVE")'),
    ('store.authenticate("INANNA NAMMU"',      'store.authenticate("INANNA NAMMU"'),
    ('token = store.issue',             'token = store.issue'),  # no-op (context varies)
    # Documentation prose
    ('INANNA NAMMU recognized',                'INANNA NAMMU recognized'),
    ('INANNA NAMMU (Guardian)',                'INANNA NAMMU (Guardian)'),
    ('INANNA NAMMU (guardian)',                'INANNA NAMMU (guardian)'),
    ("INANNA NAMMU's laptop",                  "INANNA NAMMU's laptop"),
    ("INANNA NAMMU's machine",                 "INANNA NAMMU's machine"),
    ("INANNA NAMMU's languages",               "INANNA NAMMU's languages"),
    ("INANNA NAMMU's session",                 "INANNA NAMMU's session"),
    ("INANNA NAMMU's profile",                 "INANNA NAMMU's profile"),
    ("INANNA NAMMU's communication",           "INANNA NAMMU's communication"),
    # Nix config
    ('users.users.inanna_nammu',               'users.users.inanna_nammu'),
    ('description = "INANNA NAMMU',           'description = "INANNA NAMMU'),
    ('home = "/home/inanna_nammu"',            'home = "/home/inanna_nammu"'),
    ('INANNA_SERVER_URL = "INANNA NAMMU"',     'INANNA_SERVER_URL = "INANNA NAMMU"'),
    # identity.py / state
    ('hostname="INANNA NAMMU"',                'hostname="INANNA NAMMU"'),
    ('"Hello INANNA NAMMU!',                   '"Hello INANNA NAMMU!'),
    ('"Hello, I am INANNA NAMMU"',             '"Hello, I am INANNA NAMMU"'),
    # Generic remaining ZAERA in strings (last, careful)
    ('Who is INANNA NAMMU',                    'Who is INANNA NAMMU'),
    ('ensure INANNA NAMMU',                    'ensure INANNA NAMMU'),
    ('for INANNA NAMMU',                       'for INANNA NAMMU'),
    # Doc prose remaining
    ('INANNA NAMMU configured',                'INANNA NAMMU configured'),
    ('INANNA NAMMU tests',                     'INANNA NAMMU tests'),
    ('INANNA NAMMU uses',                      'INANNA NAMMU uses'),
    ('INANNA NAMMU types',                     'INANNA NAMMU types'),
    ('INANNA NAMMU says',                      'INANNA NAMMU says'),
    ('INANNA NAMMU asks',                      'INANNA NAMMU asks'),
    ('for INANNA NAMMU specifically',          'for INANNA NAMMU specifically'),
    # Written by / Confirmed by
    ('Confirmed by: INANNA NAMMU',             'Confirmed by: INANNA NAMMU'),
    ('Guardian approval: INANNA NAMMU',        'Guardian approval: INANNA NAMMU'),
    ('INANNA NAMMU (Guardian)',                'INANNA NAMMU (Guardian)'),
]

TEXT_EXTS = {'.py', '.md', '.nix', '.txt', '.jsonl', '.sh', '.toml'}
JSON_EXTS  = {'.json'}

changed = []
errors  = []

for f in sorted(base.rglob('*')):
    if not f.is_file():
        continue
    # skip git internals
    if '.git' in f.parts:
        continue

    if f.suffix in TEXT_EXTS:
        try:
            src = f.read_text(encoding='utf-8', errors='replace')
            new = src
            for old, rep in REPLACEMENTS:
                new = new.replace(old, rep)
            if new != src:
                f.write_text(new, encoding='utf-8')
                changed.append(str(f.relative_to(base)))
        except Exception as e:
            errors.append(f'{f}: {e}')

    elif f.suffix in JSON_EXTS:
        try:
            src = f.read_text(encoding='utf-8', errors='replace')
            new = src
            for old, rep in REPLACEMENTS:
                new = new.replace(old, rep)
            if new != src:
                f.write_text(new, encoding='utf-8')
                changed.append(str(f.relative_to(base)))
        except Exception as e:
            errors.append(f'{f}: {e}')

print(f"Changed {len(changed)} files:")
for c in changed:
    print(f"  {c}")
if errors:
    print(f"\nErrors ({len(errors)}):")
    for e in errors:
        print(f"  {e}")
print("\nDone.")
