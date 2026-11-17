; Windows installer for the `flet build windows` output, built in CI with Inno Setup 6:
;   iscc /DVersion=0.1.8 /DSource=build\windows /DExe=aprs-kiss.exe /DOut=dist packaging\windows\aprs-kiss.iss
; Installs for the current user only (no administrator rights needed), adds a Start menu entry,
; an optional desktop icon and an uninstaller in Settings › Apps.

#ifndef Version
  #define Version "0.0.0"
#endif
#ifndef Source
  #define Source "..\..\build\windows"
#endif
#ifndef Exe
  #define Exe "aprs-kiss.exe"
#endif
#ifndef Out
  #define Out "..\..\dist"
#endif

[Setup]
; Keep this AppId: it is how Windows recognises an update of the same app.
AppId={{6F2C8E1A-4B7D-4E93-9A51-3C0D7B2E8F14}
AppName=APRS & Packet
AppVersion={#Version}
AppVerName=APRS & Packet {#Version}
AppPublisher=Michal Šiman (OK1SIM)
AppPublisherURL=https://github.com/michalsiman/aprs-kiss-app
AppSupportURL=https://github.com/michalsiman/aprs-kiss-app/issues
AppUpdatesURL=https://github.com/michalsiman/aprs-kiss-app/releases
DefaultDirName={localappdata}\Programs\APRS & Packet
DefaultGroupName=APRS & Packet
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#Out}
OutputBaseFilename=aprs-kiss-{#Version}-windows-x64-setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#Exe}
UninstallDisplayName=APRS & Packet
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
LicenseFile=..\..\LICENSE

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
; Each one only if this Inno Setup has it; otherwise the installer stays in English for that language.
#if FileExists(CompilerPath + "Languages\Czech.isl")
Name: "cs"; MessagesFile: "compiler:Languages\Czech.isl"
#endif
#if FileExists(CompilerPath + "Languages\Danish.isl")
Name: "da"; MessagesFile: "compiler:Languages\Danish.isl"
#endif
#if FileExists(CompilerPath + "Languages\German.isl")
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
#endif
#if FileExists(CompilerPath + "Languages\Spanish.isl")
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
#endif
#if FileExists(CompilerPath + "Languages\French.isl")
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
#endif
#if FileExists(CompilerPath + "Languages\Italian.isl")
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"
#endif
#if FileExists(CompilerPath + "Languages\Norwegian.isl")
Name: "nb"; MessagesFile: "compiler:Languages\Norwegian.isl"
#endif
#if FileExists(CompilerPath + "Languages\BrazilianPortuguese.isl")
Name: "pt_BR"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
#endif
#if FileExists(CompilerPath + "Languages\Slovak.isl")
Name: "sk"; MessagesFile: "compiler:Languages\Slovak.isl"
#endif
#if FileExists(CompilerPath + "Languages\Slovenian.isl")
Name: "sl"; MessagesFile: "compiler:Languages\Slovenian.isl"
#endif
#if FileExists(CompilerPath + "Languages\Swedish.isl")
Name: "sv"; MessagesFile: "compiler:Languages\Swedish.isl"
#endif
#if FileExists(CompilerPath + "Languages\Ukrainian.isl")
Name: "uk"; MessagesFile: "compiler:Languages\Ukrainian.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#Source}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\APRS & Packet"; Filename: "{app}\{#Exe}"
Name: "{autodesktop}\APRS & Packet"; Filename: "{app}\{#Exe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#Exe}"; Description: "{cm:LaunchProgram,APRS & Packet}"; Flags: nowait postinstall skipifsilent
