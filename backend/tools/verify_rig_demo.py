"""Prototype geometry/foot-contact and encoded-video structural checks."""
from pathlib import Path
import struct
import math

root=Path(__file__).resolve().parents[1]
cache=root/'unity-rig-demo/Assets/RigDemo/Tiger/TigerPreview.bytes'
with cache.open('rb') as f:
    assert f.read(4)==b'TRD1'
    vertices,indices,bones,frames,fps=struct.unpack('<iiiif',f.read(20))
    assert bones==23 and frames==240 and fps==24
    f.seek(vertices*8+indices*4,1)
    names=[]
    for _ in range(bones):names.append(f.read(64).rstrip(b'\0').decode());f.read(4)
    positions=[]
    for frame in range(frames):
        f.seek(vertices*24,1)
        values=struct.unpack('<'+'f'*(bones*3),f.read(bones*12))
        assert all(math.isfinite(v) for v in values)
        positions.append({name:values[i*3:i*3+3] for i,name in enumerate(names)})
    def distance(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
    support=('FrontLPaw','HindLPaw','HindRPaw')
    drift=max(distance(positions[n][name],positions[84][name]) for n in range(84,131) for name in support)
    # Sub-frame quaternion interpolation may introduce sub-millimetre drift.
    assert drift<.001,drift
    swing=max(distance(positions[n]['FrontRPaw'],positions[84]['FrontRPaw']) for n in range(84,131))
    assert swing>.3,swing
movie=root/'docs/superpowers/artifacts/2026-11-14-tiger-rig-demo.mp4'
data=movie.read_bytes()
def boxes(start,end):
    while start+8<=end:
        length,kind=struct.unpack_from('>I4s',data,start)
        if not length:break
        payload=start+8
        if kind==b'mvhd':
            scale,duration=struct.unpack_from('>II',data,payload+12)
            assert abs(duration/scale-10)<.1
        if kind==b'tkhd':
            width,height=struct.unpack_from('>II',data,start+length-8)
            assert (width/65536,height/65536)==(1280,720)
        if kind in (b'moov',b'trak',b'mdia'):boxes(payload,start+length)
        start+=length
boxes(0,len(data))
print(f'PASS: 23 source bones; 240 frames; Q support-paw drift {drift:.8f}; striking-paw travel {swing:.3f}; MP4 1280x720 / 10 seconds / {len(data)} bytes')
