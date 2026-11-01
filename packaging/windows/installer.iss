; Установщик StungKir для Windows (Inno Setup 6). Файл в UTF-8 с BOM: в нём есть русские имена файлов.
; Собирается скриптом build-windows.ps1 после PyInstaller: берёт папку dist\StungKir.
#define AppName "StungKir"
#define AppVersion "1.1.0"
#define AppPublisher "KiriFesTung"

[Setup]
AppId={{6F1C2E4A-9B7D-4C1E-8A3F-5D2B7E9C4A10}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/KiriFestung/StungKir-notepad
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
OutputDir=..\..\dist
OutputBaseFilename=StungKir-Setup-{#AppVersion}
SetupIconFile=stungkir.ico
UninstallDisplayIcon={app}\StungKir.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\StungKir\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; лицензии и правовое - рядом с программой
Source: "..\..\LICENSE"; DestDir: "{app}\licenses"; DestName: "LICENSE-GPL3.txt"; Flags: ignoreversion
Source: "..\..\AUTHORS.md"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "..\..\docs\ПРАВОВОЕ.md"; DestDir: "{app}\licenses"; DestName: "LEGAL-ru.md"; Flags: ignoreversion
Source: "..\..\packaging\fonts\LICENSE-DejaVu.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "..\..\packaging\dictionaries\LICENSE-ru_RU.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion

[Registry]
; язык, выбранный в установщике, - программе (QSettings stungkir/stungkir): при первом запуске она не спросит
; второй раз. Выбор в «Настройках» программы важнее; при удалении подсказка убирается
Root: HKCU; Subkey: "Software\stungkir\stungkir"; ValueType: string; ValueName: "installer_language"; ValueData: "ru"; Languages: russian; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\stungkir\stungkir"; ValueType: string; ValueName: "installer_language"; ValueData: "en"; Languages: english; Flags: uninsdeletevalue

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\StungKir.exe"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\StungKir.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\StungKir.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

; Тексты (C:\Users\<имя>\StungKir) и копии (%APPDATA%\StungKir) при удалении не трогаются.
