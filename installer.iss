[Setup]
AppId={{B7A3C1D2-5E4F-4A6B-9C8D-1F2E3A4B5C6D}
AppName=EduManager
AppVersion=1.0.0
AppPublisher=EduManager

DefaultDirName={autopf}\EduManager
DefaultGroupName=EduManager

OutputDir=installer_output
OutputBaseFilename=EduManager_Setup

SetupIconFile=assets\EduManager_fixed.ico

UninstallDisplayIcon={app}\EduManager_fixed.ico

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"

[Dirs]
Name: "{app}\data"
Name: "{app}\data\backups"
Name: "{app}\exports"
Name: "{app}\exports\bulletins"
Name: "{app}\exports\emplois_du_temps"
Name: "{app}\exports\excel"

[Files]
Source: "dist\EduManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\EduManager_fixed.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\EduManager"; Filename: "{app}\EduManager.exe"; IconFilename: "{app}\EduManager_fixed.ico"; IconIndex: 0
Name: "{group}\Désinstaller EduManager"; Filename: "{uninstallexe}"
Name: "{autodesktop}\EduManager"; Filename: "{app}\EduManager.exe"; IconFilename: "{app}\EduManager_fixed.ico"; IconIndex: 0; Tasks: desktopicon

[Run]
Filename: "{app}\EduManager.exe"; Description: "Lancer EduManager"; Flags: nowait postinstall skipifsilent