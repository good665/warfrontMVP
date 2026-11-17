# 팔다리 확대와 이동 속도 조정

- 영웅 이동 175 → 245, 활 사용 중 이동 110 → 160.
- 동료/일반 분대 155 → 215, 정찰병 210 → 290. 봇 경로 예측도 245로 동기화.
- Walk 재생 속도 0.65와 기존 클립/전환/포물선 표현 유지.
- 활성 Unity 프로젝트의 `Assets/script/SquadLimbProportions.cs`는 팔·다리 길이를 18%, 두께를 12% 확대한다. 애니메이션이 스케일을 덮어쓰므로 LateUpdate에서 적용한다.
- 리그 루트는 0.032 올려 길어진 다리의 지면 접촉을 보정하며 매 프레임 이전 보정을 복구한다. 활 손 위치 갱신 전에 적용한다.
- `RetroFantasyScene.Actor`에서 분대 캐릭터 생성 시에만 컴포넌트를 부착한다.
- 백업: `%TEMP%/warfront-stride-proportions/backup/RetroFantasyScene.cs`.

## 검증

- 이동/충돌/전투 48개 및 봇/분대 24개 통과.
- Unity `StrideProportionChecks` PASS: Human/Orc 팔다리 크기, 걷기 회전 유지, 높이 보정 비누적, 애니메이션 샘플 후 크기 유지. `GentleArcheryChecks`도 PASS.
- Unity 렌더링 이미지 `%TEMP%/warfront-archery-0.400.png`를 열어 확대된 캐릭터의 걷기 포즈를 확인했다.
- 실행 중 스크립트 리로드 후 기존 씬 객체 참조가 깨지는 현상이 보여 Play 모드를 종료하고 검증했다. 변경된 코드는 다음 Play 시작부터 생성되는 캐릭터에 적용된다.
