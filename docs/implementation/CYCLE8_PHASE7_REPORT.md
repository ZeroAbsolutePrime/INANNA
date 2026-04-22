# Cycle 8 Phase 8.7 - NixOS Backend

## Deliverables

- `nixos/client.nix` created
- `nixos/server.nix` created
- `nixos/configuration.nix` updated for single-machine development parity
- `nixos/README.md` updated for the two-machine architecture
- `core/desktop_faculty.py` updated with Linux display-server detection and Linux app normalization

## AT-SPI2 Packages Used

The NixOS declarations use:

- `at-spi2-core`
- `python311Packages.pyatspi`

Package naming can vary slightly across nixpkgs revisions, especially for Python accessibility bindings, so `pyatspi` availability should be verified against the exact channel in use.

## Wayland vs X11 Detection

`LinuxAtspiBackend` now uses `_detect_display_server()`:

- returns `wayland` when `WAYLAND_DISPLAY` is set or `XDG_SESSION_TYPE=wayland`
- otherwise returns `x11`

`type_text()` now prefers `ydotool` on Wayland and `xdotool` on X11, with fallback to the opposite tool if the preferred binary is missing.

## Platform Selection Logic

Confirmed unchanged:

- `platform.system() == "Windows"` -> `WindowsMCPBackend`
- `platform.system() == "Linux"` -> `LinuxAtspiBackend`
- anything else -> `FallbackBackend`

The tests were written to match this existing implementation rather than forcing a different selection pattern.

## pyatspi Availability Note

The Python-side Linux backend depends on `python311Packages.pyatspi`. This package exists in many nixpkgs revisions, but if a target channel lacks it, an overlay or alternative packaging path may be required. The code and tests keep `pyatspi` optional at import time and surface a clean error when it is unavailable.
