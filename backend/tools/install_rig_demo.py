"""Only installs the isolated Editor demo and its own RigDemo assets."""
from pathlib import Path
import shutil
import tempfile

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'backend/unity-rig-demo/Assets'
TARGET=Path('C:/Users/good6/WarfrontMVP/Assets').resolve()
for source in SOURCE.rglob('*'):
    if not source.is_file():continue
    relative=source.relative_to(SOURCE)
    if source.suffix=='.blend': relative=Path('RigDemo/Source~')/source.name
    destination=(TARGET/relative).resolve()
    if not destination.is_relative_to(TARGET):raise RuntimeError('Outside active Assets')
    if not (relative.as_posix().startswith('RigDemo/') or relative.as_posix()=='Editor/TigerRigDemo.cs'):
        raise RuntimeError('Unexpected demo path')
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,destination)
frames=ROOT/'backend/docs/superpowers/artifacts/tiger-rig-demo-frames'
frames.mkdir(parents=True,exist_ok=True)
Path(tempfile.gettempdir(),'warfront-rig-demo-v8.request').write_text(str(frames),encoding='utf-8')
print('Installed isolated Editor demo, Blender source, FBX and UV PNG. Production scripts/assets untouched.')
