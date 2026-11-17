# WarfrontMVP 레트로 판타지 에셋

적용 프로젝트: `C:\Users\good6\WarfrontMVP` (Unity 6000.3.23f1)

## 산출물

- `Assets/Resources/RetroFantasy/Models`: Kenney Retro Fantasy Kit의 원본 FBX 모듈 16종. 건물·지붕·탑·계단·나무·울타리·상자·통·장애물.
- `Assets/Resources/RetroFantasy/Textures`, `Materials`: 원본 픽셀 텍스처와 URP 재질, 자체 생성 잔디 텍스처. 나무는 알파 클리핑 적용.
- `Assets/Resources/RetroFantasy/Hero/Adventurer.prefab`: 자체 제작 검·방패 모험가. 1,672 정점, 836 삼각형, 18개 본, 정규화된 스킨 웨이트, UV 팔레트 텍스처.
- `Idle`, `Walk`, `Attack`, `Dodge` 클립. Generic 스켈레톤과 legacy Animation 컴포넌트 사용. Humanoid Avatar 또는 FBX 캐릭터/Blender 원본을 제공하는 형식은 아님.
- `Assets/Editor/RetroAdventurerBuilder.cs`: 캐릭터 메시·UV PNG·리그·클립·프리팹 재생성 원본. `Warfront > Retro Fantasy > Build Adventurer`에서 실행.
- 개인 제작 스킬: `C:\Users\good6\.codex\skills\unity-retro-fantasy\SKILL.md`. 사용 예: `$unity-retro-fantasy로 방패와 갑옷을 개선해줘`.

## 연결

3D 스톤헤이븐 마을 메인화면에서 길드/사냥터, 유적, 대장간/장비, 여관/파티, 기록관/퀘스트로 이동한다. 별도 카메라와 RenderTexture로 실제 메시를 표시한다. 기존 URP의 기본 2D 렌더러를 유지하고 새 3D 카메라용 Forward Renderer를 추가했다. 사용자 씬과 ProjectSettings는 수정하지 않았다.

MMORPG 플레이어와 적을 실제 스킨 모델로 표시하며 서버 좌표·충돌·입력·보상 규칙은 유지한다. 55도 직교 투영을 기존 GUI 조준 좌표와 일치시켰다. 병과 색상 변경과 피격 점멸을 유지하며 퇴장한 배우와 생성 자원을 정리한다.

## 검증

- 미구현 프리팹 검사 실패를 확인한 후 제작. 본/바인드 포즈/정규화 가중치/UV/재질 및 네 클립의 실제 BakeMesh 정점 변형 검사 통과.
- 실제 환경 메시, 재질 연결, 이름표 경계·겹침, 서버 좌표 투영 오차 1px 이내, 배우 정리, 병과 변경·피격 표시 검사 통과.
- 기존 Unity 검사 219개 통과: MMO 3, 모션 6, 통신 암호 마우스 5, 위젯 16, 픽셀 아트 5, 성장/기존 시뮬레이션 184.
- 실제 Unity Play에서 마을, 장비 패널, 서버 사냥터의 플레이어·적 모델 확인. 별도 Play 프레임 카메라 검사로 실제 텍스처 표시 확인.
- 에셋 생성 직후 단일 수동 render request는 SRP 초기화 전이라 잘못된 표면/빈 출력이 발생했다. 시각 증거는 실제 Play 프레임과 활성 Editor 화면을 기준으로 삼았다.
- 기존 SampleScene의 missing script 경고와 Unity AI Assistant 구독 오류는 이 변경에서 수정하지 않았다. Android 기기 빌드는 실행하지 않았다.

검증 로그: `%TEMP%/warfront-retro-final.log`, `%TEMP%/warfront-retro-live-final.log`. 기존 파일 백업은 워크스페이스 `.tools/fantasy-town/backup-20261107-052353`, 재질 백업은 `.tools/fantasy-town/final-backup`에 보관했다.

## 출처

환경 모델·원본 텍스처: [Kenney Retro Fantasy Kit](https://kenney.nl/assets/retro-fantasy-kit), 동봉 CC0 라이선스는 `Assets/Resources/RetroFantasy/Kenney-License.txt`에 보존. 캐릭터·팔레트·잔디·리깅·동작·조립 코드는 이번에 자체 제작했으며 Kenney 제공 캐릭터로 표기하지 않는다.
