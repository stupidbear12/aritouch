; AirTouch Interactive System Installer

#define MyAppName "AirTouch"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "승규"
#define MyAppExeName "main.exe"

[Setup]
; 고유 ID (변경하지 마세요)
AppId={{F8A3B2C1-D4E5-4F67-8901-234567890ABC}}
; 앱 정보
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/
AppSupportURL=https://github.com/
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; 출력 설정
OutputDir=..\output
OutputBaseFilename=AirTouch_Setup_v{#MyAppVersion}
; 압축
Compression=lzma2/max
SolidCompression=yes
; Windows 10+ 필수
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; 권한 (관리자 불필요)
PrivilegesRequired=lowest
; UI
WizardStyle=modern
DisableProgramGroupPage=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면 바로가기 만들기"; GroupDescription: "추가 옵션:"

[Files]
; 메인 실행 파일
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 시작 메뉴
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\제거하기"; Filename: "{uninstallexe}"
; 바탕화면
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 설치 완료 후 실행
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} 실행"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  MsgBox('AirTouch 인터랙티브 시스템을 설치합니다.' + #13#10 + #13#10 + 
         '설치 후 웹캠 권한이 필요합니다.', mbInformation, MB_OK);
end;