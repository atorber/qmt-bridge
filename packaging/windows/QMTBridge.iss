; QMT Bridge — Inno Setup 安装脚本（由 build.ps1 调用）
; 需要 Inno Setup 6：https://jrsoftware.org/isinfo.php

#include "_version.iss"

#define MyAppName "QMT Bridge"
#define MyAppPublisher "QMT Bridge"
#define MyAppExeName "QMTBridge.exe"
#define MyAppURL "https://github.com/atorber/qmt-bridge"

[Setup]
AppId={{E2B8C4A1-9F3D-4E6B-8A21-7C4D91B0E8A3}-{#MyArchTag}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\QMT Bridge-{#MyArchTag}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed={#MyArchitecturesAllowed}
ArchitecturesInstallIn64BitMode={#MyArchitecturesInstallMode}
OutputDir=dist
OutputBaseFilename=QMTBridge-Setup-{#MyAppVersion}-{#MyArchTag}
SetupIconFile=qmt-bridge.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=no
CloseApplications=yes
MinVersion=10.0
LicenseFile=..\..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked
Name: "autostart"; Description: "开机时启动 QMT Bridge"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
Source: "dist\portable\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName} ({#MyArchTag})"; Filename: "{app}\{#MyAppExeName}"; Comment: "启动 QMT Bridge 控制面板"
Name: "{autodesktop}\{#MyAppName} ({#MyArchTag})"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "启动 QMT Bridge 控制面板"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "QMT Bridge {#MyArchTag}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动 QMT Bridge"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\runtime"
