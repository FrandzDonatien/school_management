#define MyAppName "EduManager"
#define MyAppVersion "5.0.0"
#define MyAppPublisher "EduManager"
#define MyAppExeName "EduManager.exe"
#define MyAppIcon "assets\EduManager_fixed.ico"

[Setup]
AppId={{B7A3C1D2-5E4F-4A6B-9C8D-1F2E3A4B5C6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppCopyright=Copyright (C) 2026 EduManager

DefaultDirName={autopf}\EduManager
DefaultGroupName=EduManager
DisableProgramGroupPage=yes

OutputDir=installer_output
OutputBaseFilename=EduManager_Setup_{#MyAppVersion}

SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\EduManager_fixed.ico

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; Langue de l'assistant
ShowLanguageDialog=no

; Droits d'installation
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Informations de désinstallation
Uninstallable=yes

; Réglages de l'assistant
WizardSizePercent=100
WizardResizable=no

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; \
    Description: "Créer un raccourci sur le Bureau"; \
    GroupDescription: "Raccourcis supplémentaires :"; \
    Flags: unchecked

[Dirs]
Name: "{localappdata}\EduManager"
Name: "{localappdata}\EduManager\data"
Name: "{localappdata}\EduManager\data\backups"
Name: "{localappdata}\EduManager\exports"
Name: "{localappdata}\EduManager\exports\bulletins"
Name: "{localappdata}\EduManager\exports\emplois_du_temps"
Name: "{localappdata}\EduManager\exports\excel"

[Files]
Source: "dist\EduManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\EduManager_fixed.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\EduManager"; \
    Filename: "{app}\EduManager.exe"; \
    IconFilename: "{app}\EduManager_fixed.ico"; \
    IconIndex: 0

Name: "{group}\Désinstaller EduManager"; \
    Filename: "{uninstallexe}"

Name: "{autodesktop}\EduManager"; \
    Filename: "{app}\EduManager.exe"; \
    IconFilename: "{app}\EduManager_fixed.ico"; \
    IconIndex: 0; \
    Tasks: desktopicon

[Run]
Filename: "{app}\EduManager.exe"; \
    Description: "Lancer EduManager"; \
    Flags: nowait postinstall skipifsilent