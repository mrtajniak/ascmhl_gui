# ASC MHL Creator GUI
## What is that?
ASC MHL Creator GUI is a user-friendly graphical interface for generating ASC Media Hash List (MHL) files, built on top of the asc/mhl core engine. Designed to simplify the creation process for users who prefer a visual workflow, this tool offers an accessible way to maintain data integrity and traceability in media production pipelines.

Key Features:
- ASC MHL Creation: Easily generate ASC-compliant MHL files to ensure reliable file transfer verification and media archiving.
- Author Information: Optionally embed detailed author metadata to maintain traceability and accountability.
- Identity Export/Import: Define and export/import identity profiles including name, email, role, phone number, and location, streamlining repeat use and ensuring consistency across projects.

Whether you’re a Digital Imaging Technician, editor, or archivist, ASC MHL Creator GUI provides a clean and intuitive interface for professional-grade MHL generation without the need to interact with command-line tools.

## Requierments
1. Python 3.13 or later
2. ASCMHL from [HERE](https://github.com/ascmitc/mhl)

## How to install
1. Downlod windows release provided in the releases tab
2. Add ASCMHL that you installed to your system PATH
3. Install requiered packages by running `pip install -r requirements.txt`
4. Run `ASCMHLCreatorGUI.exe`
5. Enjoy easy MHL creation with simple GUI

## Compliance: 
[![Build](https://github.com/mrtajniak/ascmhl_gui/actions/workflows/main.yml/badge.svg?branch=main)](https://github.com/mrtajniak/ascmhl_gui/actions/workflows/main.yml)
[![CodeQL](https://github.com/mrtajniak/ascmhl_gui/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/mrtajniak/ascmhl_gui/actions/workflows/github-code-scanning/codeql)
