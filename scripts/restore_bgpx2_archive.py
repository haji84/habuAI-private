from __future__ import annotations
import argparse, base64, hashlib, json, lzma, struct
from datetime import datetime, timezone
from pathlib import Path

def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _read_uv(data: bytes, pos: int) -> tuple[int, int]:
    n = 0
    shift = 0
    while True:
        b = data[pos]
        pos += 1
        n |= (b & 127) << shift
        if not (b & 128):
            return n, pos
        shift += 7

def _unzz(n: int) -> int:
    return (n >> 1) ^ -(n & 1)

def _decstr(value: int, scale: int) -> str:
    neg = value < 0
    digits = str(abs(value))
    if scale:
        digits = digits.zfill(scale + 1)
        digits = digits[:-scale] + "." + digits[-scale:]
    return ("-" if neg else "") + digits

def _decode_dec(data: bytes, count: int) -> list[str]:
    out = []
    pos = 0
    previous = 0
    previous_scale = None
    for _ in range(count):
        scale = data[pos]
        pos += 1
        code, pos = _read_uv(data, pos)
        if code & 1:
            value = _unzz(code >> 1)
        else:
            value = previous + _unzz(code >> 1)
        out.append(_decstr(value, scale))
        previous = value
        previous_scale = scale
    if pos != len(data):
        raise ValueError("decimal stream trailing bytes")
    return out

def _decode_time(data: bytes, count: int) -> list[str]:
    out = []
    pos = 0
    previous = None
    for index in range(count):
        code, pos = _read_uv(data, pos)
        millis = code if index == 0 else previous + _unzz(code)
        sec, milli = divmod(millis, 1000)
        dt = datetime.fromtimestamp(sec, tz=timezone.utc)
        out.append(dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{milli:03d}Z")
        previous = millis
    if pos != len(data):
        raise ValueError("time stream trailing bytes")
    return out

def restore(parts_dir: Path, manifest_path: Path, output: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    part_files = sorted(parts_dir.glob("part_*.b64"))
    if len(part_files) != manifest["part_count"]:
        raise ValueError("part count mismatch")
    encoded = "".join(p.read_text(encoding="ascii").strip() for p in part_files)
    compressed = base64.b64decode(encoded, validate=True)
    if len(compressed) != manifest["xz_size_bytes"] or _sha(compressed) != manifest["xz_sha256"]:
        raise ValueError("xz mismatch")
    payload = lzma.decompress(compressed)
    if len(payload) != manifest["payload_size_bytes"] or _sha(payload) != manifest["payload_sha256"]:
        raise ValueError("payload mismatch")
    if not payload.startswith(b"BGPX2"):
        raise ValueError("bad BGPX2 magic")

    pos = 5
    blocks = []
    for _ in range(13):
        size = struct.unpack(">I", payload[pos:pos + 4])[0]
        pos += 4
        blocks.append(payload[pos:pos + size])
        pos += size
    if pos != len(payload):
        raise ValueError("payload trailing bytes")

    pre, post, meta_b, tids_b, lat_b, lon_b, ele_b, time_b, hdop_b, vdop_b, speed_b, course_b, rel_b = blocks
    meta = json.loads(meta_b.decode("utf-8"))
    row_count = meta["rows"]
    templates = meta["templates"]
    if len(tids_b) != row_count:
        raise ValueError("template id count mismatch")

    tids = list(tids_b)
    lat = _decode_dec(lat_b, row_count)
    lon = _decode_dec(lon_b, row_count)
    ele = _decode_dec(ele_b, row_count)
    times = _decode_time(time_b, row_count)
    hdop = _decode_dec(hdop_b, row_count)
    vdop = _decode_dec(vdop_b, row_count)

    counts = {
        name: sum(name in templates[tid] for tid in tids)
        for name in ("speed", "course", "rel_alt")
    }
    values = {
        "speed": _decode_dec(speed_b, counts["speed"]),
        "course": _decode_dec(course_b, counts["course"]),
        "rel_alt": _decode_dec(rel_b, counts["rel_alt"]),
    }
    offsets = {name: 0 for name in values}

    raw = bytearray(pre)
    indent = meta["indent"]
    newline = meta["newline"]
    for index, tid in enumerate(tids):
        inner = ""
        for name in templates[tid]:
            value = values[name][offsets[name]]
            offsets[name] += 1
            inner += f"<gom:{name}>{value}</gom:{name}>"
        line = (
            f'{indent}<trkpt lat="{lat[index]}" lon="{lon[index]}"><ele>{ele[index]}</ele>'
            f"<time>{times[index]}</time><hdop>{hdop[index]}</hdop><vdop>{vdop[index]}</vdop>"
            f"<extensions>{inner}</extensions></trkpt>{newline}"
        )
        raw.extend(line.encode("utf-8"))
    raw.extend(post)
    restored = bytes(raw)

    if len(restored) != manifest["raw_size_bytes"] or _sha(restored) != manifest["raw_sha256"]:
        raise ValueError("restored raw GPX mismatch")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(restored)
    return {
        "byte_exact": True,
        "raw_sha256": _sha(restored),
        "raw_size_bytes": len(restored),
        "part_count": len(part_files),
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parts-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(restore(args.parts_dir, args.manifest, args.output), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
