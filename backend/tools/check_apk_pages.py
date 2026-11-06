"""Check ARM64 ELF load alignment in a built APK (not a device smoke test)."""
import argparse
import json
import struct
from pathlib import Path
import zipfile


def inspect(apk):
    libraries = []
    with zipfile.ZipFile(apk) as archive:
        for name in archive.namelist():
            if not name.startswith("lib/arm64-v8a/") or not name.endswith(".so"):
                continue
            data = archive.read(name)
            if data[:6] != b"\x7fELF\x02\x01":
                raise ValueError(f"Expected little-endian ELF64: {name}")
            offset = struct.unpack_from("<Q", data, 32)[0]
            entry_size, count = struct.unpack_from("<HH", data, 54)
            if entry_size < 56:
                raise ValueError(f"Invalid ELF program header size: {name}")
            loads = []
            for i in range(count):
                header = offset + i * entry_size
                if struct.unpack_from("<I", data, header)[0] == 1:
                    file_offset, address = struct.unpack_from("<QQ", data, header + 8)
                    alignment = struct.unpack_from("<Q", data, header + 48)[0]
                    loads.append(alignment >= 16384 and (address - file_offset) % 16384 == 0)
            libraries.append({"library": name, "load_segments": len(loads),
                              "elf_16kb_aligned": bool(loads) and all(loads)})
    if not libraries:
        raise ValueError("APK contains no ARM64 native libraries")
    return {"apk": str(apk), "elf_16kb_aligned": all(x["elf_16kb_aligned"] for x in libraries),
            "libraries": libraries,
            "scope": "ELF segments only; APK zip alignment and execution on a 16KB device require separate checks"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = inspect(args.apk)
    output = json.dumps(result, indent=2)
    if args.report:
        args.report.write_text(output, encoding="utf-8")
    print(output)
    raise SystemExit(0 if result["elf_16kb_aligned"] else 1)
