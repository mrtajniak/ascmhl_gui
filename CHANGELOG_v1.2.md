# ASC MHL Creator GUI v1.2 Changelog

## New Features
- Added automatic ASC MHL installation using pip if not detected on system.
- Added real-time status and feedback updates for all ASC MHL installation, checking, and update operations.
- Added update check for ASC MHL using pip and a visible update button if a new version is available.
- Added export/import of user identity data in XML format in the Info tab.
- Added feedback label in Info tab for export/import status.
- Added clear button to Info tab to clear all fields.
- Added clear button to Log tab to clear logs.
- Added progress bar for activity indication.
- Added argument summary after MHL creation job.

## Improvements
- Improved UI responsiveness by running long operations in a separate thread.
- Improved status label and feedback label font size and style for better visibility.
- Improved Info tab layout and usability.
- Improved error handling and user feedback for all operations.
- Optimized code structure and reduced redundant lines.

## Bug Fixes
- Fixed window freezing during ASC MHL installation and checking.
- Fixed premature or misleading status messages during ASC MHL check/install.
- Fixed Info tab fields not appearing or clearing as expected.
- Fixed UI elements not being enabled/disabled correctly during processing.

## Other
- Updated displayed ASC MHL Creator GUI version to 1.2.
- Updated .gitignore and requirements.txt for better project hygiene.
