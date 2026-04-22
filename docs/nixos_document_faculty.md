# NixOS Document Faculty Dependencies

Cycle 8 Phase 8.4 adds direct-reader document support to INANNA NYX.
The Python-side runtime depends on five document libraries, and the
application-side export path depends on LibreOffice.

## Python packages installed in this phase

The following command completed successfully on the active workstation:

```powershell
py -3 -m pip install python-docx python-pptx openpyxl pymupdf odfpy --break-system-packages
```

Installed successfully:

- `python-docx==1.2.0`
- `python-pptx==1.0.2`
- `openpyxl==3.1.5`
- `pymupdf==1.27.2.2`
- `odfpy==1.4.1`

No fallback to `pypdf` was required.

## NixOS equivalents

Use these equivalents in a NixOS shell, dev environment, or system package set:

- `python-docx` -> `python3Packages.python-docx`
- `python-pptx` -> `python3Packages.python-pptx`
- `openpyxl` -> `python3Packages.openpyxl`
- `pymupdf` -> `python3Packages.pymupdf`
- `odfpy` -> `python3Packages.odfpy`
- LibreOffice CLI export -> `libreoffice`

Example `mkShell` fragment:

```nix
pkgs.mkShell {
  packages = with pkgs; [
    libreoffice
    (python3.withPackages (ps: with ps; [
      python-docx
      python-pptx
      openpyxl
      pymupdf
      odfpy
    ]))
  ];
}
```

## Format coverage

Direct read support in Phase 8.4:

- `.txt`
- `.md`
- `.rst`
- `.log`
- `.docx`
- `.odt`
- `.pdf`
- `.xlsx`
- `.xls`
- `.ods`
- `.csv`

Direct write support in Phase 8.4:

- `.txt`
- `.md`
- `.docx`

Export support in Phase 8.4:

- any LibreOffice-openable source document to `.pdf` via `soffice --headless --convert-to pdf`
