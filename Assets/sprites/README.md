# WARFRONT 16비트 픽셀 아트

2026-11-05, 기본 내장 `image_gen`으로 생성한 프로젝트 에셋이다. 원본 PNG는 이 폴더에 보관하고 Unity 실행용 복사본은 `C:/Users/good6/WarfrontMVP/Assets/Resources/Sprites/`에 설치했다.

| 파일 | 구성 | 용도 |
|---|---|---|
| `warfront-characters-v1.png` | 1536×1024 RGBA, 3열×2행, 셀512×512 | 위: 아군 돌격·수호·지원 / 아래: 적군 돌격·수호·지원 |
| `warfront-terrain-v1.png` | 1254×1254 RGB, 2열×2행, 셀627×627 | 위: 풀·콘크리트 / 아래: 자갈·철판 |

픽셀 경계를 보존하기 위해 Point 필터, 밉맵 끔, 비압축, NPOT 크기 유지, 최대2048로 임포트한다. 캐릭터 PNG의 알파를 그대로 사용한다. 파일을 덮어쓰지 않고 새 스타일은 `-v2`처럼 버전을 올려 저장한다.

`Assets/script/PixelArtView.cs`가 이미지를 한 번 로드하고 UV로 셀을 선택한다. 캐릭터는 좌우 반전을 지원하는 정지 포즈다. AI·온라인 거점 대전, 무료 조작 안내, 생존·폭탄 회피의 플레이어, 훈련장 바닥에 연결했다. 전투 좌표·충돌 크기·입력·서버 판정·순위 규칙은 변경하지 않았다. 기존 군사 기지 로비 배경은 보존했다.

## 생성 프롬프트

도구: 기본 내장 `image_gen` (CLI/API 키 경로 사용 안 함).

### 캐릭터 — transparent_background=true

Create a production game sprite atlas for WARFRONT, a fictional military base combat game. 16-bit retro pixel art, true crisp square pixel clusters, SNES era overhead 3/4 top-down view. ONE transparent PNG atlas, landscape 3 columns by 2 rows of exactly equal size cells, no gutters except transparent padding within each cell. Six separate full-body small soldier sprites, each exactly centered in its own cell, consistent feet baseline, consistent scale, facing right/down-right with weapon ready. Top row LEFT blue-team assault rifle soldier with olive helmet and teal-blue shoulder plates, CENTER blue-team bulky guardian with heavier helmet armor and compact shield, RIGHT blue-team support medic with small backpack and cyan medical cross. Bottom row same three roles in same columns but enemy team with muted brick-red shoulder plates and charcoal uniforms. Uniform cohesive military olive, navy-shadow, desaturated teal, warm sand highlights, muted red enemy accents. Chibi tactical proportions, helmet-covered face, readable silhouette at 48 screen pixels tall, 2-pixel dark outlines, at most about 24 palette colors, no gradients, no antialias, no smooth painting, no 3D render. Each figure occupies central 60 percent of its cell width and 72 percent height with completely transparent margins, zero overlap into adjacent cells. Minimal small dark pixel contact shadow only underneath feet, transparent rest of background, no ground rectangles, no text, no letters, no grid, no labels, no watermarks. This is a usable game asset sheet, not a mockup.

### 지형 — transparent_background=false

WARFRONT usable seamless military-base ground terrain tileset, unified 16-bit retro pixel art, SNES overhead top-down game, crisp square pixels and limited muted olive/teal/slate/sand palette matching small military soldiers. One opaque square image, EXACTLY 2 by 2 equally sized quadrants with no gaps or border and no labels. TOP LEFT: seamless desaturated olive grass soil texture, very low contrast tiny pixel tufts. TOP RIGHT: seamless dark gray blue concrete slabs, subtle pixel cracks and fine gritty speckles, continuous at opposite edges. BOTTOM LEFT: seamless warm gray-brown gravel and compact dirt, tiny sparse stone clusters. BOTTOM RIGHT: seamless dark desaturated teal steel deck panels with small rivets, subtle surface detail. Each quadrant is an independent repeatable square tile filling its entire quadrant; no margins, no enclosing frame. Ground textures only, absolutely no characters, no trees, no props, no buildings, no text, no perspective horizon, no dramatic lighting, no gradients, no smooth rendered textures, no big objects, no floor markings. These are background tiles which must remain visually quiet behind combat and UI. All quadrants same lighting, same low contrast, clean pixel clusters with about 24 colors total.
