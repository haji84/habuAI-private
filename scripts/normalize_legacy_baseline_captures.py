#!/usr/bin/env python3
"""Normalize Habu capture events from the immutable legacy baseline field log."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST=timezone(timedelta(hours=9))
DT_RE=re.compile(r"^(20\d{2})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$")
COUNT_RE=re.compile(r"^(\d+)匹$")
LAT_RE=re.compile(r"^2[6789]\.\d+$")
LON_RE=re.compile(r"^12[89]\.\d+$")
WETNESS=("ソークド(水跳ね)","ウェット","ウエット","湿り","ドライ")
SIZE_MAP={
    "ハブ捕獲極小":"極小",
    "ハブ捕獲小":"小",
    "ハブ捕獲中":"中",
    "ハブ捕獲大":"大",
}

def operational_night(dt: datetime) -> str:
    return (dt.astimezone(JST)-timedelta(hours=7)).date().isoformat()

def blocks(text: str) -> list[tuple[datetime,list[str]]]:
    lines=text.splitlines()
    out=[]
    i=0
    while i<len(lines):
        m=DT_RE.match(lines[i].strip())
        if not m:
            i+=1
            continue
        y,mo,d,hh,mm,ss=m.groups()
        dt=datetime(int(y),int(mo),int(d),int(hh),int(mm),int(ss or 0),tzinfo=JST)
        block=[lines[i].rstrip("\r")]
        j=i+1
        while j<len(lines) and not DT_RE.match(lines[j].strip()):
            block.append(lines[j].rstrip("\r"))
            j+=1
        out.append((dt,block))
        i=j
    return out

def _coords(lines: list[str]) -> tuple[float|None,float|None]:
    lat=lon=None
    for line in lines:
        s=line.strip()
        if LAT_RE.match(s):
            try:
                v=float(s)
                if 27.0 <= v <= 29.5: lat=v
            except ValueError:
                pass
        elif LON_RE.match(s):
            try:
                v=float(s)
                if 128.0 <= v <= 131.0: lon=v
            except ValueError:
                pass
    return lat,lon

def parse_captures(text: str, source_sha256: str) -> list[dict]:
    rows=[]
    ordinal=0
    for dt,block in blocks(text):
        stripped=[x.strip() for x in block]
        if "捕獲" not in stripped:
            continue
        if not any("ハブ捕獲" in x for x in stripped):
            continue
        lat,lon=_coords(block)
        count=1
        for x in stripped:
            m=COUNT_RE.match(x)
            if m:
                count=int(m.group(1))
                break
        size_note=next((x for x in stripped if x.startswith("ハブ捕獲") and x!="ハブ捕獲"),"")
        size_class=SIZE_MAP.get(size_note,"")
        wetness=next((w for w in WETNESS if w in stripped),"")
        coord_indexes=[i for i,x in enumerate(stripped) if LAT_RE.match(x) or LON_RE.match(x)]
        before_coord=min(coord_indexes) if coord_indexes else len(stripped)
        excluded={"捕獲",""}
        excluded.update(WETNESS)
        descriptive=[
            x for x in stripped[1:before_coord]
            if x not in excluded
            and not x.startswith("ハブ捕獲")
            and not COUNT_RE.match(x)
            and not x.startswith("鹿児島県")
            and x!="日本"
        ]
        place=""
        behavior=""
        microhabitat=""
        for x in descriptive:
            if "瀬戸内町" in x or "県道" in x or "国道" in x:
                place=x
        nonplace=[x for x in descriptive if x!=place]
        if nonplace:
            behavior=nonplace[0]
        if len(nonplace)>1:
            microhabitat=" | ".join(nonplace[1:])
        ordinal+=1
        raw_text="\n".join(block).rstrip()+"\n"
        raw_sha=hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        rows.append({
            "event_id":f"LEGACY-CAP-{dt:%Y%m%d-%H%M}-{ordinal:03d}",
            "operational_date":operational_night(dt),
            "event_time_local":dt.isoformat(),
            "event_place":place,
            "event_type":"capture",
            "species":"ハブ",
            "event_count":count,
            "latitude":lat if lat is not None else "",
            "longitude":lon if lon is not None else "",
            "size_note":size_note,
            "size_class_legacy":size_class,
            "surface":wetness,
            "behavior_note":behavior,
            "microhabitat_note":microhabitat,
            "source_file_sha256":source_sha256,
            "source_block_sha256":raw_sha,
            "source_status":"raw_log_reparsed",
        })
    return rows

def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    if not rows: return
    with path.open("w",encoding="utf-8-sig",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def normalize(path: Path, root: Path) -> dict:
    raw=path.read_bytes()
    source_sha=hashlib.sha256(raw).hexdigest()
    text=raw.decode("utf-8-sig")
    rows=parse_captures(text,source_sha)
    by_night=defaultdict(list)
    for row in rows:
        by_night[row["operational_date"]].append(row)
    for night,night_rows in sorted(by_night.items()):
        year=night[:4]
        write_csv(root/"data"/"processed"/"capture_events"/year/f"{night}.csv",night_rows)
        individuals=[]
        for row in night_rows:
            for idx in range(1,int(row["event_count"])+1):
                individuals.append({
                    "individual_id":f"{row['event_id']}-{idx:02d}",
                    "event_id":row["event_id"],
                    "individual_index":idx,
                    "operational_date":night,
                    "event_time_local":row["event_time_local"],
                    "size_note":row["size_note"],
                    "source_status":"raw_log_reparsed",
                })
        write_csv(root/"data"/"processed"/"individuals"/year/f"{night}.csv",individuals)
    total_individuals=sum(int(r["event_count"]) for r in rows)
    summary={
        "schema_version":"legacy-baseline-capture-reparse-v1",
        "source_path":str(path.relative_to(root)),
        "source_sha256":source_sha,
        "capture_events":len(rows),
        "capture_individuals":total_individuals,
        "coordinate_complete_events":sum(bool(r["latitude"]) and bool(r["longitude"]) for r in rows),
        "operational_nights":{
            night:{
                "capture_events":len(night_rows),
                "capture_individuals":sum(int(r["event_count"]) for r in night_rows),
            }
            for night,night_rows in sorted(by_night.items())
        },
        "night_boundary":"07:00 Asia/Tokyo; timestamps 00:00-06:59 belong to previous operational date",
    }
    out=root/"evidence"/"legacy"/"habuAI-public"/"baseline_capture_reparse_summary.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return summary

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--input",type=Path,default=Path("data/raw/habu_logs/baseline_through_2026-08-27.txt"))
    args=ap.parse_args()
    root=args.repo_root.resolve()
    inp=args.input if args.input.is_absolute() else root/args.input
    print(json.dumps(normalize(inp,root),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
