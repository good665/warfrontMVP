"""640px rendered item icons -> 32x32 pixel icons (same grid as the code-drawn ones in SquadGearHud.SquadItemIcon).

uv run --no-project --with pillow python -X utf8 pixelize_item_icons.py <render_dir> <out_dir>
Copy the results (not long_whip: a hairline, the game draws its own) into Resources/ZodiacItems/Icons with Point filter.
"""
import sys, os
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
GRID, BODY, COLORS = 32, 28, 10
for name in sorted(os.listdir(src)):
    if not name.endswith('.png'): continue
    im = Image.open(os.path.join(src, name)).convert('RGBA')
    im = im.crop(im.getchannel('A').point(lambda a: 255 if a > 40 else 0).getbbox())
    side = max(im.size); sq = Image.new('RGBA', (side, side)); sq.paste(im, ((side-im.width)//2, (side-im.height)//2))
    small = sq.resize((BODY, BODY), Image.BOX)
    alpha = small.getchannel('A').point(lambda a: 255 if a >= 110 else 0)
    rgb = small.convert('RGB').quantize(COLORS, method=Image.Quantize.MEDIANCUT).convert('RGB')
    body = Image.merge('RGBA', (*rgb.split(), alpha))
    out = Image.new('RGBA', (GRID, GRID)); out.paste(body, ((GRID-BODY)//2, (GRID-BODY)//2))
    px = out.load(); ink = (24, 18, 28, 255)  # 1 px dark rim so the sprite reads on any slot colour
    solid = {(x, y) for x in range(GRID) for y in range(GRID) if px[x, y][3]}
    for x, y in solid:
        for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
            if 0 <= nx < GRID and 0 <= ny < GRID and (nx, ny) not in solid: px[nx, ny] = ink
    out.save(os.path.join(dst, name))
    print(name, len(solid))
# preview sheet, 8x nearest
names = sorted(n for n in os.listdir(dst) if n.endswith('.png'))
sheet = Image.new('RGBA', (len(names)*GRID*4, GRID*4), (60, 52, 70, 255))
for i, n in enumerate(names):
    t = Image.open(os.path.join(dst, n)).resize((GRID*4, GRID*4), Image.NEAREST); sheet.alpha_composite(t, (i*GRID*4, 0))
sheet.save(os.path.join(dst, '_sheet.png'))
