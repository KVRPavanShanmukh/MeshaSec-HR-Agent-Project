[Setup]
AppId={{75E9637D-7556-4D97-9A7D-A17A9E40F510}}
AppName=MESHASEC AI HR Interview Agent
AppVersion=2.0.0
AppPublisher=MESHASEC
DefaultDirName={localappdata}\Programs\MESHASEC AI HR Interview Agent
DefaultGroupName=MESHASEC AI HR Interview Agent
OutputDir=..\installer_output
OutputBaseFilename=MESHASEC_AI_HR_Agent_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\AI HR Agent.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\AI HR Agent.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MESHASEC AI HR Interview Agent"; Filename: "{app}\AI HR Agent.exe"
Name: "{autodesktop}\MESHASEC AI HR Interview Agent"; Filename: "{app}\AI HR Agent.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AI HR Agent.exe"; Description: "Launch MESHASEC AI HR Interview Agent"; Flags: nowait postinstall skipifsilent


