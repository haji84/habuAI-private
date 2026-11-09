#!/usr/bin/env python3
"""Private, offline, authenticated Habu Library backup. Requires cryptography.

Usage:
  python habu_library_vault_tool.py create --source-dir ... --out ... --key-out ... --receipt-out ...
  python habu_library_vault_tool.py verify --vault ... --key ... [--source-dir ...]
  python habu_library_vault_tool.py restore --vault ... --key ... --target ...

Never copy real GPS source files, keys, manifests, or archive contents into public Git.
The key file is sensitive: keep it in access-controlled custody distinct from the vault.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import shutil
import tempfile
import zipfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VERSION = "habu-library-encrypted-raw-v1"
AAD = b"HABU-LIBRARY-VAULT-V1\x00"
MAX_ITEMS = 200
MAX_PER_ITEM = 12 * 1024 * 1024
MAX_TOTAL = 500 * 1024 * 1024


def failed(message):
    raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def clean_rel(name: str) -> str:
    if not name or "\\" in name or "\x00" in name or ":" in name or name.startswith("/") or any(v in ("", ".", "..") for v in name.split("/")):
        failed("UNSAFE_PATH")
    return name


def original_path(name: str) -> str:
    """Existing verified Library /ハブAI/Raw/2026/10 and /2026/11 paths."""
    if name.startswith("2026-11-"):
        folder = "2026/11"
    else:
        folder = "2026/10"
    return clean_rel(folder + "/" + name)


def make_header(archive_id: str, n: int) -> dict:
    return {"version": VERSION, "archive_id": archive_id,
            "algorithm": "AES-256-GCM", "items": n,
            "notes": "key_custody_outside_public_git"}


def load_key(path: Path, archive_id: str) -> bytes:
    source = path.resolve(strict=True)
    if not source.is_file() or source.stat().st_size > 4096:
        failed("BAD_KEY_FILE")
    meta = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(meta, dict) or set(meta) != {"version", "archive_id", "key_b64", "instructions"} or meta["version"] != VERSION or meta["archive_id"] != archive_id:
        failed("KEY_OR_ARCHIVE_MISMATCH")
    key = base64.b64decode(meta["key_b64"], validate=True)
    if len(key) != 32:
        failed("INVALID_AES_KEY")
    return key


def encrypted_payload(cipher: AESGCM, raw: bytes, archive_id: str, context: bytes) -> bytes:
    nonce = secrets.token_bytes(12)
    return nonce + cipher.encrypt(nonce, raw, AAD + archive_id.encode("ascii") + b"\x00" + context)


def decrypted_payload(cipher: AESGCM, data: bytes, archive_id: str, context: bytes) -> bytes:
    if len(data) < 12+16:
        failed("TRUNCATED_ENCRYPTED_PAYLOAD")
    return cipher.decrypt(data[:12], data[12:], AAD + archive_id.encode("ascii") + b"\x00" + context)


def create(source_dir: Path, archive: Path, key_file: Path, receipt: Path):
    source_dir = source_dir.resolve(strict=True)
    files = sorted(x for x in source_dir.iterdir() if x.is_file() and not x.is_symlink())
    if len(files) != 19:
        failed("EXPECTED_19_PRIVATE_SOURCE_FILES")
    sizes = [f.stat().st_size for f in files]
    if any(n <= 0 or n > MAX_PER_ITEM for n in sizes) or sum(sizes) > MAX_TOTAL:
        failed("SIZE_GATE")
    for p in [archive,key_file,receipt]:
        if p.exists() or p.is_symlink():
            failed("NO_OVERWRITE")
        if p.resolve().is_relative_to(source_dir):
            failed("OUTPUT_INSIDE_SOURCE")
    archive.parent.mkdir(parents=True, exist_ok=True)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    archive_id = secrets.token_hex(16)
    key = secrets.token_bytes(32)
    cipher = AESGCM(key)
    ledger = []
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
        for file in files:
            raw = file.read_bytes()
            digest = sha(raw)
            name = secrets.token_hex(16)+".enc"
            z.writestr(name, encrypted_payload(cipher, raw, archive_id, bytes.fromhex(digest)))
            ledger.append({"name": original_path(file.name), "sha256": digest,
                           "size": len(raw), "cipher": name})
        metadata = json.dumps({"version": VERSION, "archive_id": archive_id,
                               "files": ledger},ensure_ascii=False,sort_keys=True,
                              separators=(",", ":")).encode("utf-8")
        z.writestr("manifest.enc", encrypted_payload(cipher,metadata,archive_id,b"manifest"))
        z.writestr("header.json",json.dumps(make_header(archive_id,len(files)),sort_keys=True))
    os.chmod(archive,0o600)
    key_meta={"version":VERSION,"archive_id":archive_id,
              "key_b64":base64.b64encode(key).decode("ascii"),
              "instructions":"PRIVATE: keep offline and separately from encrypted archive; never post to GitHub, logs, or chat"}
    fd=os.open(key_file, os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as out:
        json.dump(key_meta,out,sort_keys=True)
    report=verify(archive,key_file,source_dir=source_dir)
    if report["verified_files"]!=len(files) or report["verified_bytes"]!=sum(sizes):
        failed("READBACK_MISMATCH")
    receipt.write_text(json.dumps({**report,"archive_sha256":sha(archive.read_bytes()),
                   "archive_size_bytes":archive.stat().st_size,"key_saved_outside_git":True,
                   "private_library_upload_confirmed":False},sort_keys=True,indent=2)+"\n",encoding="utf-8")
    os.chmod(receipt,0o600)
    return report


def verify(archive: Path, key_file: Path,source_dir: Path | None = None):
    with zipfile.ZipFile(archive,"r") as z:
        names=z.namelist()
        if len(names)>MAX_ITEMS+2 or len(set(names)) != len(names) or "header.json" not in names or "manifest.enc" not in names:
            failed("UNSAFE_ARCHIVE_STRUCTURE")
        header=json.loads(z.read("header.json"))
        if not isinstance(header,dict) or header.get("version")!=VERSION or header.get("algorithm")!="AES-256-GCM":
            failed("UNSUPPORTED_ARCHIVE")
        archive_id=header.get("archive_id")
        if not isinstance(archive_id,str) or len(archive_id)!=32 or any(c not in "0123456789abcdef" for c in archive_id):
            failed("INVALID_ARCHIVE_ID")
        key=load_key(key_file,archive_id)
        cipher=AESGCM(key)
        raw_manifest=decrypted_payload(cipher,z.read("manifest.enc"),archive_id,b"manifest")
        manifest=json.loads(raw_manifest)
        if manifest.get("version")!=VERSION or manifest.get("archive_id")!=archive_id or not isinstance(manifest.get("files"),list) or header.get("items")!=len(manifest["files"]):
            failed("BAD_MANIFEST")
        if len(manifest["files"])>MAX_ITEMS or not manifest["files"]:
            failed("MANIFEST_SIZE_GATE")
        expected_names={"header.json","manifest.enc"}
        seen_paths=set()
        total=0
        for entry in manifest["files"]:
            if not isinstance(entry,dict) or set(entry)!={"name","size","sha256","cipher"}:
                failed("BAD_ENTRY")
            path=clean_rel(entry["name"])
            if path in seen_paths or entry["cipher"] in expected_names:
                failed("DUPLICATE_ENTRY")
            seen_paths.add(path)
            digest=entry["sha256"]
            if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
                failed("BAD_DIGEST")
            if not isinstance(entry["size"],int) or not 0<entry["size"]<=MAX_PER_ITEM:
                failed("BAD_LENGTH")
            if not isinstance(entry["cipher"],str) or len(entry["cipher"])!=36 or not entry["cipher"].endswith(".enc"):
                failed("BAD_CIPHER_NAME")
            expected_names.add(entry["cipher"])
            if entry["cipher"] not in names:
                failed("MISSING_CIPHER")
            raw=decrypted_payload(cipher,z.read(entry["cipher"]),archive_id,bytes.fromhex(digest))
            if len(raw)!=entry["size"] or sha(raw)!=digest:
                failed("SOURCE_SHA_MISMATCH")
            if source_dir is not None:
                original=source_dir/Path(path).name
                if not original.is_file() or sha(original.read_bytes())!=digest:
                    failed("ORIGINAL_BYTE_MISMATCH")
            total+=len(raw)
            if total>MAX_TOTAL:
                failed("TOTAL_SIZE_GATE")
        if set(names)!=expected_names:
            failed("UNEXPECTED_CIPHER_ENTRY")
    return {"version":VERSION,"archive_id":archive_id,"result":"VERIFIED_AUTHENTICATED_AES256_GCM",
            "verified_files":len(manifest["files"]),"verified_bytes":total,
            "byte_exact_originals":source_dir is not None}


def restore(archive:Path,key_file:Path,target:Path):
    if target.exists() or target.is_symlink():
        failed("NO_OVERWRITE_TARGET")
    verify(archive,key_file)
    target.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix=".habu_restore_",dir=target.parent))
    os.chmod(stage,0o700)
    try:
        with zipfile.ZipFile(archive) as z:
            header=json.loads(z.read("header.json"))
            aid=header["archive_id"]
            cipher=AESGCM(load_key(key_file,aid))
            manifest=json.loads(decrypted_payload(cipher,z.read("manifest.enc"),aid,b"manifest"))
            for entry in manifest["files"]:
                clean_rel(entry["name"])
                dest=stage/entry["name"]
                if not dest.resolve().is_relative_to(stage) or dest.exists():
                    failed("RESTORE_PATH_INVALID")
                dest.parent.mkdir(parents=True,exist_ok=True)
                raw=decrypted_payload(cipher,z.read(entry["cipher"]),aid,bytes.fromhex(entry["sha256"]))
                fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,"wb") as out:
                    out.write(raw)
                    out.flush()
                    os.fsync(out.fileno())
                if sha(dest.read_bytes())!=entry["sha256"]:
                    failed("RESTORE_DIGEST_FAILURE")
        stage.rename(target)
    except BaseException:
        shutil.rmtree(stage,ignore_errors=True)
        raise
    return {"result":"RESTORED_ONLY_TO_NEW_PRIVATE_DIRECTORY","files":len(manifest["files"])}


def cli():
    p=argparse.ArgumentParser(description="Habu authenticated private Library backup")
    sub=p.add_subparsers(dest="action",required=True)
    x=sub.add_parser("create");x.add_argument("--source-dir",type=Path,required=True);x.add_argument("--out",type=Path,required=True);x.add_argument("--key-out",type=Path,required=True);x.add_argument("--receipt-out",type=Path,required=True)
    x=sub.add_parser("verify");x.add_argument("--vault",type=Path,required=True);x.add_argument("--key",type=Path,required=True);x.add_argument("--source-dir",type=Path)
    x=sub.add_parser("restore");x.add_argument("--vault",type=Path,required=True);x.add_argument("--key",type=Path,required=True);x.add_argument("--target",type=Path,required=True)
    args=p.parse_args()
    if args.action=="create": result=create(args.source_dir,args.out,args.key_out,args.receipt_out)
    elif args.action=="verify":result=verify(args.vault,args.key,args.source_dir)
    else:result=restore(args.vault,args.key,args.target)
    # No positions, file names, original hashes, keys, or decrypted content in stdout.
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    cli()
