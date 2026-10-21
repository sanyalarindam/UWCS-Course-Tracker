#ifndef AppVersion
#define AppVersion "0.2.0"
#endif
[Setup]
AppId={{B721937E-4EC9-49F2-86D7-28847AF839A2}
AppName=CS Tracker
AppVersion={#AppVersion}
AppPublisher=CS Tracker contributors
AppPublisherURL=https://github.com/sanyalarindam/UWCS-Course-Tracker
DefaultDirName={localappdata}\Programs\CS Tracker
DefaultGroupName=CS Tracker
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=CS-Tracker-Setup-{#AppVersion}-Windows-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\.local-data\build-tools\app.ico
UninstallDisplayIcon={app}\CS Tracker.exe
CloseApplications=yes
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "..\dist\CS Tracker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\.local-data\build-tools\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
[Icons]
Name: "{group}\CS Tracker"; Filename: "{app}\CS Tracker.exe"
Name: "{autodesktop}\CS Tracker"; Filename: "{app}\CS Tracker.exe"; Tasks: desktopicon
[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Checking Microsoft Edge WebView2 Runtime..."; Flags: waituntilterminated
Filename: "{app}\CS Tracker.exe"; Description: "Open CS Tracker"; Flags: nowait postinstall skipifsilent
; User data in LocalAppData/UWCS Tracker is intentionally preserved on uninstall.
