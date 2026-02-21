; Inno Setup script for PlaudPilot
; Produces a Setup.exe installer for Windows
;
; Prerequisites:
;   1. Build with:  pyinstaller --clean --noconfirm build\PlaudPilot_installer.spec
;   2. Then compile this .iss with Inno Setup 6+
;
; The onedir build produces uncompressed files in dist\PlaudPilot\, allowing
; LZMA2 solid compression here to achieve ~50-60% smaller installers vs
; wrapping a pre-compressed onefile EXE.

[Setup]
AppName=PlaudPilot
AppVersion=1.1.0
AppPublisher=PlaudPilot
DefaultDirName={autopf}\PlaudPilot
DefaultGroupName=PlaudPilot
OutputDir=..\dist
OutputBaseFilename=PlaudPilot_Setup
Compression=lzma2/ultra64
SolidCompression=yes
LZMANumBlockThreads=4
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\PlaudPilot\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PlaudPilot"; Filename: "{app}\PlaudPilot.exe"
Name: "{autodesktop}\PlaudPilot"; Filename: "{app}\PlaudPilot.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\PlaudPilot.exe"; Description: "Launch PlaudPilot"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
