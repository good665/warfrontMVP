# WARFRONT UI 위젯 적용

생성한 `warfront-ui-widgets-v1.png`를 활성 `C:/Users/good6/WarfrontMVP/Assets/Resources/Sprites/`에서 사용한다.

- `WidgetArtView.cs`: 원본 PNG의 버튼 3종·패널·체력 프레임·아이콘 12종을 한 번 잘라 캐시한다. 원본 픽셀 좌표를 사용하며, 버튼/패널은 테두리를 보존하는 9-slice로 그린다.
- 공통 IMGUI 버튼, 공통 패널, 로비 건물 이름판·하단 출격 버튼·재화 아이콘, 주간 훈련 카드·아이콘, 기존 군단 체력바에 연결한다.
- `PixelArtImport.cs`: Point 필터, 비압축, 밉맵 끔, 위젯 Read/Write와 입력 알파 보존. 임포터 버전을 올려 이미 추가된 PNG도 다시 임포트한다.
- 기존 캐릭터·바닥 픽셀 이미지와 군사 기지 배경을 유지한다. 클릭 영역·문구·화면 전환·서버/전투 규칙은 유지한다.
- 텍스처 누락 시 기존 버튼/패널 표시를 사용한다. 생성 텍스처와 스킨은 컴포넌트 종료 시 해제한다.

검증 기록은 `validation/ui-widgets-2026-11-06/`에 보관한다. Android/iOS 빌드와 실기기 검증은 이번 적용 범위에 포함하지 않는다.

활성 런타임 C# 컴파일 오류 0, 기존 미사용 필드 경고 1. 임시 프로젝트와 활성 Unity Editor에서 위젯 16 + 기존 픽셀 이미지 5 + 게임 회귀 184 = 205개 검사가 통과했다. 활성 파일과 검증한 소스의 해시 일치를 확인했다.

`Warfront > Preview UI Widgets`에서 서버에 요청하지 않는 미리보기를 열 수 있다. `Warfront > Run UI Widget Checks`에서 검사를 다시 실행할 수 있다. 미리보기 창은 열렸으나 컴퓨터 제어의 캡처에 창 내용이 노출되지 않아 시각적 배치 검증은 미완료다. 현재 편집기의 Untitled 씬은 변경하지 않았다. 실제 게임은 기존 `Assets/Scenes/SampleScene.unity`를 열어 실행한다.
