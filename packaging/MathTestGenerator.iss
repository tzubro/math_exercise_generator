#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#define AppName "Math Test Generator"
#define AppPublisher "Math Test Generator"

[Setup]
AppId={{61A4C0B9-E52E-4D47-91CA-EEBB934B6310}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\MathTestGenerator
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=MathTestGenerator-Setup-{#AppVersion}-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
Uninstallable=yes

[Files]
Source: "..\dist\MathTestGenerator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\MathTestGenerator.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\MathTestGenerator.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\MathTestGenerator.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
