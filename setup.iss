#define MyAppName      "DMF Engine"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "DMF Automacao"
#define MyAppExeName   "DMF Engine.exe"
#define MyAppID        "B4A2F8E1-3C7D-4F9A-82BE-1D5E6F0A3C9B"
#define DistDir        "dist\DMF Engine"

[Setup]
AppId={{{#MyAppID}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\DMF Engine
DefaultGroupName={#MyAppName}
OutputDir=dist\installer
OutputBaseFilename=Setup_DMF_Engine_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
PrivilegesRequired=admin
; Icone do instalador (mesmo do app)
SetupIconFile=dmf_engine\ui\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "ptBR"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na &Área de Trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
; Copia tudo do dist gerado pelo PyInstaller
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";   Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar";    Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName} agora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove logs e config gerados em runtime dentro da pasta de instalação
Type: files; Name: "{app}\dmf_engine.log"
Type: files; Name: "{app}\dmf_engine_errors.log"
