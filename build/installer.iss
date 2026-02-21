; Inno Setup script for PlaudPilot
; Produces a Setup.exe installer for Windows

[Setup]
AppName=PlaudPilot
AppVersion=1.1.0
AppPublisher=PlaudPilot
DefaultDirName={autopf}\PlaudPilot
DefaultGroupName=PlaudPilot
OutputDir=..\dist
OutputBaseFilename=PlaudPilot_Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\PlaudPilot.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\PlaudPilot"; Filename: "{app}\PlaudPilot.exe"
Name: "{autodesktop}\PlaudPilot"; Filename: "{app}\PlaudPilot.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\PlaudPilot.exe"; Description: "Launch PlaudPilot"; Flags: nowait postinstall skipifsilent
