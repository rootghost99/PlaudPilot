; Inno Setup script for PlaudTranscriber
; Produces a Setup.exe installer for Windows

[Setup]
AppName=PlaudTranscriber
AppVersion=1.0.0
AppPublisher=PlaudTranscriber
DefaultDirName={autopf}\PlaudTranscriber
DefaultGroupName=PlaudTranscriber
OutputDir=..\dist
OutputBaseFilename=PlaudTranscriber_Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\PlaudTranscriber.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\PlaudTranscriber"; Filename: "{app}\PlaudTranscriber.exe"
Name: "{autodesktop}\PlaudTranscriber"; Filename: "{app}\PlaudTranscriber.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\PlaudTranscriber.exe"; Description: "Launch PlaudTranscriber"; Flags: nowait postinstall skipifsilent
