#ifndef MyVersion
  #define MyVersion "1.0.0"
#endif
[Setup]
AppId={{3F8C1A9D-6B2E-4D7F-A5C3-9E1B2D4F6A80}
AppName=Lector Libre
AppVersion={#MyVersion}
AppPublisher=Facundo Luzardo
DefaultDirName={localappdata}\Programs\LectorLibre
DefaultGroupName=Lector Libre
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=LectorLibre-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\LectorLibre.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
AppMutex=LectorLibreMutex
CloseApplications=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"
Name: "autostart"; Description: "Iniciar Lector Libre con Windows"

[Files]
Source: "dist\LectorLibre\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\Lector Libre"; Filename: "{app}\LectorLibre.exe"; AppUserModelID: "FacundoLuzardo.LectorLibre"
Name: "{autodesktop}\Lector Libre"; Filename: "{app}\LectorLibre.exe"; AppUserModelID: "FacundoLuzardo.LectorLibre"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "LectorLibre"; ValueData: """{app}\LectorLibre.exe"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\LectorLibre.exe"; Description: "Abrir Lector Libre"; Flags: nowait postinstall skipifsilent
Filename: "{app}\LectorLibre.exe"; Flags: nowait runasoriginaluser; Check: WizardSilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM LectorLibre.exe"; Flags: runhidden; RunOnceId: "KillApp"
