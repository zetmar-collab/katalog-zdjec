; =============================================================================
; Inno Setup 6.x — skrypt instalatora dla „Katalog Zdjęć" (Windows)
; Wymagania: Inno Setup 6.x (https://jrsoftware.org/isinfo.php)
;            + pliki EXE zbudowane przez PyInstaller (dist\KatalogZdjec\)
;
; Kompilacja:  iscc installer_windows.iss
;              lub otwórz ten plik w Inno Setup IDE i kliknij Build
; =============================================================================

#define MyAppName      "Katalog Zdjęć"
#define MyAppVersion   "1.0"
#define MyAppPublisher "Marek Zettel"
#define MyAppURL       "https://zetmar.net.pl"
#define MyAppExeName   "KatalogZdjec.exe"
#define MyAppExeDir    "dist\KatalogZdjec"

; --------------------------------------------------------------------------- ;
[Setup]
; UWAGA: AppId jednoznacznie identyfikuje aplikację. Nie zmieniaj go po wydaniu!
AppId={{F3A2B1C0-D4E5-4F60-9ABC-DEF012345678}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Katalog instalacji
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Plik wyjściowy
OutputDir=dist\installer
OutputBaseFilename=KatalogZdjec_Instalator_v{#MyAppVersion}

; Kompresja
Compression=lzma2/ultra64
SolidCompression=yes

; Styl
WizardStyle=modern
WizardResizable=yes

; Wymagany system
MinVersion=10.0

; Instalacja dla bieżącego użytkownika (unika ostrzeżenia o userappdata)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Ikona instalatora (opcjonalna)
; SetupIconFile=assets\icon.ico

; --------------------------------------------------------------------------- ;
[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

; --------------------------------------------------------------------------- ;
[Tasks]
Name: "desktopicon"; \
    Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; \
    Flags: unchecked

Name: "quicklaunchicon"; \
    Description: "Utwórz ikonę na &pasku szybkiego uruchamiania"; \
    GroupDescription: "{cm:AdditionalIcons}"; \
    Flags: unchecked; Check: not IsAdminInstallMode

; --------------------------------------------------------------------------- ;
[Files]
; Wszystkie pliki zbudowane przez PyInstaller
Source: "{#MyAppExeDir}\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; --------------------------------------------------------------------------- ;
[Icons]
; Menu Start
Name: "{group}\{#MyAppName}"; \
    Filename: "{app}\{#MyAppExeName}"

; Odinstalowanie
Name: "{group}\Odinstaluj {#MyAppName}"; \
    Filename: "{uninstallexe}"

; Skrót na pulpicie (opcjonalny)
Name: "{autodesktop}\{#MyAppName}"; \
    Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

; Pasek szybkiego uruchamiania (opcjonalny)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; \
    Filename: "{app}\{#MyAppExeName}"; \
    Tasks: quicklaunchicon

; --------------------------------------------------------------------------- ;
[Run]
; Uruchom po instalacji (opcjonalne)
Filename: "{app}\{#MyAppExeName}"; \
    Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent

; --------------------------------------------------------------------------- ;
[UninstallDelete]
; Usuń bazę danych i logi pozostawione przez aplikację
Type: files; Name: "{app}\*.log"
