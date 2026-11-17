# 호랑이 모델·리깅 비교 시연

사용자 요청: 실제 적용 전에 리깅 개선을 시연하고, 워크래프트 3처럼 높은 사선 고정 시점에서 평가한다.

- 영상: `2026-11-14-tiger-rig-demo.mp4`, 1280×720, 24fps, 10초, 무음.
- 왼쪽: 실제 기존 Unity 호랑이 프리팹과 Walk / Attack / Heavy 클립.
- 오른쪽: 새 호랑이 메시와 23개 관절의 Blender 가중치 리그. 팔꿈치·무릎·발·목·턱·분절 꼬리를 추가했다. 몸통 무늬는 표면 곡률을 따라 배치했다.
- 0–3초 걷기, 3–6초 Q 할퀴기, 6–10초 E 포효. 동작을 천천히 비교하는 시연이며 실제 전투 재사용 시간·판정 시각을 나타내지 않는다.
- Q는 지지 다리를 유지하며 한 앞발을 들어 체중 이동·타격·복귀한다. E는 발 지지 후 가슴·목을 올리고 턱을 열며 돌아온다.

활성 프로젝트의 `Assets/Editor/TigerRigDemo.cs`와 `Assets/RigDemo/`에만 시연을 추가했다. 게임의 Zodiac 프리팹·전투 스크립트·서버·장면·카메라 설정은 이 시연 작업에서 변경하지 않았다. Unity 메뉴 `Warfront > Rig Demo > Compare Tiger Animations`에서 재생·정지·Q/E·뼈대 표시를 사용할 수 있다.

원본은 `Assets/RigDemo/Source~/TigerRigDemo.blend`, 교환 파일은 `Assets/RigDemo/Tiger/TigerRigDemo.fbx`, 텍스처는 `TigerPalette.png`다. Idle / Walk / QSkill / EUltimate 동작을 포함한 Generic 동물 리그이며 Humanoid Avatar가 아니다.

중요한 구현 한계: FBX 클립을 Unity에서 직접 재생할 때 단위/바인드 포즈 변환 문제가 발생했다. 이번 시연은 Blender의 실제 가중치 변형 결과를 `TigerPreview.bytes` 포즈 캐시로 내보내 Unity에서 재생한다. 이는 시각 평가용 재생 방식이며, 본 게임에 적용하기 전 FBX 리타기팅·스케일 및 실제 SkinnedMeshRenderer 재생 경로, 서버 판정 동기화를 별도로 마무리해야 한다. 캐시를 런타임 전투 리그로 간주하면 안 된다.

검증: Blender 원본 포즈와 Unity 비교 화면을 직접 확인했다. Q 지지 발 최대 이동 약 0.20mm, 공격 앞발 이동 약 0.822m, 240개 프레임의 관절 좌표 유한성 검사 통과. MP4 10초·1280×720 구조 검사와 디코딩한 Q 프레임 확인을 통과했다. 전체 게임 회귀 검증 또는 12종 캐릭터 적용 완료를 주장하지 않는다.

재생성 도구: `tools/build_tiger_rig_demo.py`, `tools/install_rig_demo.py`, `tools/encode_rig_demo_video.py`, `tools/verify_rig_demo.py`. 사용자 평가 전에는 본 게임으로 승격하지 않는다.
