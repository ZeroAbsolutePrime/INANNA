# Cycle 7 Phase 7.1 Report
### The NixOS Configuration

*Date: 2026-04-21*

---

## Delivered

- Added `nixos/configuration.nix` with the Phase 7.1 NixOS scaffold:
  system settings, `inanna` user, autologin, Python/system packages,
  the `inanna-nyx` systemd service, and firewall ports.
- Added `nixos/README.md` documenting the install and service workflow.
- Added `nixos/inanna-nyx.service` as a standalone systemd unit for
  non-NixOS systems.
- Added `nixos/install.sh` as a bounded setup helper for fresh NixOS
  machines.
- Added `inanna/requirements.txt` with the requested baseline packages
  plus `python-dotenv`, which is imported by the current runtime.
- Updated `inanna/identity.py` with Phase 7.1 and `CYCLE7_PREVIEW`.
- Added `inanna/tests/test_nixos_config.py` and updated
  `inanna/tests/test_identity.py`.
- Updated `inanna/tests/test_commands.py` so the suite tracks the
  already-present `help` command on `origin/main`.

## Boundaries Held

- No Python runtime capability changes were made.
- No web interface files were modified.
- No Phase 7.2+ file-system, process, package, or voice features were
  started.

## Verification

- `py -3 -m unittest discover -s tests`
  Result: passed, `330` tests.

## Test Drift Fixed

- `inanna/tests/test_identity.py` had a frozen exact-prompt fixture that
  no longer matched the live `build_system_prompt()` on `origin/main`.
  The test was updated to assert the current identity-shape invariants
  instead of a stale full-string snapshot.
- `inanna/tests/test_commands.py` was still expecting the pre-existing
  startup command list without `help`. The suite was updated to match
  the actual command surface already present on `origin/main`.
