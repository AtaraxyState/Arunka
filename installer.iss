; Arunka — Windows Installer
; Requires Inno Setup 6: https://jrsoftware.org/isinfo.php
; Build: open this file in Inno Setup Compiler and click Compile
; Output: installer/ArunkaSetup.exe

#define AppName    "Arunka"
#define AppVersion "1.0.0"
#define AppPublisher "Studio Nyx"
#define AppURL     "https://studio-nyx.com"
#define AppExe     "Arunka.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=ArunkaSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Require Windows 10+
MinVersion=10.0
; Request admin rights (needed to install to Program Files)
PrivilegesRequired=admin
; Nice installer icon (optional — comment out if no icon)
; SetupIconFile=assets\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "Create a &desktop shortcut";    GroupDescription: "Additional shortcuts:"; Flags: checked
Name: "startmenuicon";  Description: "Create a &Start Menu shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checked

[Files]
; Main executable (built by PyInstaller)
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

; Assets — templates + nav JSON files (user-generated, keep on update)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs; \
  Excludes: "*.pyc"

; Config
Source: "config\settings.yaml"; DestDir: "{app}\config"; Flags: ignoreversion onlyifdoesntexist

[Icons]
; Desktop shortcut
Name: "{userdesktop}\{#AppName}";       Filename: "{app}\{#AppExe}"; \
  Tasks: desktopicon; Comment: "Epic Seven Bot"

; Start Menu
Name: "{group}\{#AppName}";             Filename: "{app}\{#AppExe}"; \
  Tasks: startmenuicon
Name: "{group}\Uninstall {#AppName}";   Filename: "{uninstallexe}"

[Run]
; Offer to launch after install
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove generated files on uninstall
Type: filesandordirs; Name: "{app}\assets\templates"
Type: files;          Name: "{app}\assets\nav_points.json"
Type: files;          Name: "{app}\assets\nav_routes.json"

[Code]
// Warn user if Epic Seven doesn't appear to be installed
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpWelcome then begin
    MsgBox(
      'Welcome to Arunka Setup!' + #13#10 + #13#10 +
      'Make sure Epic Seven is installed and has been run at least once before using Arunka.' + #13#10 + #13#10 +
      'After installing, open Arunka and go to the Calibration tab to set up your templates.',
      mbInformation, MB_OK
    );
  end;
end;
