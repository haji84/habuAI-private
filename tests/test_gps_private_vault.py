"""Privacy migration tests use a synthetic ephemeral Git repo only.

Never archive any owner original from CI or print exact observed coordinates,
filenames, private key material or raw source content to GitHub Actions.
"""
from pathlib import Path
import base64
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import gps_private_vault as vault


@unittest.skipUnless(shutil.which("git"), "git required")
class EncryptedMigrationFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="habu-migration-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "public-repo"
        self.repo.mkdir()
        self.private = self.root / "outside-git"
        self.private.mkdir()
        subprocess.run(["git","init","-q"],cwd=self.repo,check=True,capture_output=True)
        subprocess.run(["git","config","user.name","Synthetic Test"],cwd=self.repo,check=True)
        subprocess.run(["git","config","user.email","synthetic@example.invalid"],cwd=self.repo,check=True)
        self.original = {
            "data/raw/habu_logs/2026/synthetic-owner-raw.txt":
              "SYNTHETIC owner log, no real sightings\n",
            "data/raw/gpx_archives/synthetic-archive.txt":
              "SYNTHETIC LOCATIONS data encoded by original tooling\n",
            "data/raw/gpx/synthetic.gpx":
              "<gpx><trkpt lat='28.123456789' lon='129.345678901'/></gpx>",
            "data/processed/individuals/synthetic.csv":
              "gps,sex\n28.123456789 129.345678901,F\n",
            "data/raw/habu_owner_nights/2026/2026-11-08.json":
              '{"night":"2026-11-08","capture_count":3,"owner_confirmed":true}\n",
        }
        for name, content in self.original.items():
            path = self.repo / name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content,encoding="utf-8")
        subprocess.run(["git","add","."],cwd=self.repo,check=True)
        subprocess.run(["git","commit","-q","-m","synthetic first"],cwd=self.repo,check=True)
        self.passphrase = "synthetic-local-migration-password-very-long"

    def test_inventory_and_ciphertext_recovery_are_byte_exact(self):
        original_tree = subprocess.check_output(["git","rev-parse","HEAD"],cwd=self.repo)
        head,items = vault.inventory(self.repo)
        self.assertEqual(len(items),4)
        self.assertEqual(head,original_tree.decode().strip())
        self.assertNotIn("capture_count",str([s.path for s in items]))
        target = self.private/"vault"
        receipt = vault.archive(self.repo,target,self.passphrase)
        self.assertEqual(receipt["sources"],4)
        self.assertEqual(receipt["status"],"VERIFIED_ENCRYPTED_ONLY")
        self.assertEqual(vault.verify(target,self.passphrase)["sources"],4)
        self.assertEqual(len([p for p in target.iterdir() if p.suffix==".enc"]),5)
        all_bytes = b"".join(p.read_bytes() for p in target.iterdir())
        self.assertNotIn(b"synthetic-owner-raw.txt",all_bytes)
        self.assertNotIn(b"129.345678901",all_bytes)
        self.assertNotIn(self.passphrase.encode(),all_bytes)
        self.assertNotIn(b"synthetic.gpx",all_bytes)
        restored = self.private/"restore"
        report = vault.restore(target,restored,self.passphrase)
        self.assertEqual(report["status"],"RESTORED_TO_PRIVATE_LOCATION")
        for key,original in self.original.items():
            if key.startswith("data/raw/habu_owner_nights/"):
                self.assertFalse((restored/key).exists())
            else:
                self.assertEqual((restored/key).read_text(encoding="utf-8"),original)
        self.assertEqual(subprocess.check_output(["git","rev-parse","HEAD"],cwd=self.repo),original_tree)
        self.assertEqual(subprocess.check_output(["git","status","--porcelain"],cwd=self.repo),b"")
        with self.assertRaises(vault.VaultError):
            vault.restore(target,restored,self.passphrase)
        with self.assertRaises(vault.VaultError):
            vault.archive(self.repo,self.repo/"data"/"private-copy",self.passphrase)

    def test_wrong_password_and_tampering_never_change_sources(self):
        target = self.private / "vault"
        vault.archive(self.repo,target,self.passphrase)
        with self.assertRaises((vault.VaultError,ValueError)):
            vault.verify(target,"different-password-thats-long-enough")
        part = next(p for p in target.iterdir() if p.name not in ("manifest.enc","package.json"))
        before=part.read_bytes()
        corrupt=bytearray(before)
        corrupt[-1]^=1
        part.write_bytes(corrupt)
        with self.assertRaises((vault.VaultError,ValueError)):
            vault.verify(target,self.passphrase)
        with self.assertRaises((vault.VaultError,ValueError)):
            vault.restore(target,self.private/"destination-not-created",self.passphrase)
        self.assertFalse((self.private/"destination-not-created").exists())
        self.assertTrue((self.repo/"data/raw/habu_logs/2026/synthetic-owner-raw.txt").is_file())
        part.write_bytes(before)
        self.assertEqual(vault.verify(target,self.passphrase)["sources"],4)

    def test_existing_plaintext_output_or_git_internal_destination_fails_closed(self):
        dest=self.private/"existing"
        dest.mkdir()
        with self.assertRaises(vault.VaultError):
            vault.archive(self.repo,dest,self.passphrase)
        with self.assertRaises(vault.VaultError):
            vault.archive(self.repo,self.repo/".git"/"unsafe-copy",self.passphrase)
        with self.assertRaises(vault.VaultError):
            vault.password_key("short",b"a"*16)

    def test_deleted_historical_source_is_not_mistaken_for_clean_history(self):
        orphaned="data/raw/gpx/old-only-in-history.gpx"
        out=self.repo/orphaned
        out.write_text("synthetic deleted track original",encoding="utf-8")
        subprocess.run(["git","add","."],cwd=self.repo,check=True)
        subprocess.run(["git","commit","-q","-m","historical only"],cwd=self.repo,check=True)
        out.unlink()
        subprocess.run(["git","add","-u"],cwd=self.repo,check=True)
        subprocess.run(["git","commit","-q","-m","remove from HEAD"],cwd=self.repo,check=True)
        _,snapshot=vault.inventory(self.repo)
        self.assertNotIn(orphaned,[x.path for x in snapshot])
        # Current-tree archive is explicitly NOT a complete historical purge.
        history=subprocess.check_output(["git","rev-list","--objects","--all"],cwd=self.repo)
        self.assertIn(orphaned.encode(),history)
        history_candidate=vault.history_candidates(self.repo)
        self.assertGreaterEqual(history_candidate["historical_paths_absent_from_current"],1)
        self.assertFalse(history_candidate["all_remote_forks_clones_and_PR_refs_audited"])
        self.assertEqual(vault.archive(self.repo,self.private/"vault",self.passphrase)["sources"],4)


if __name__=="__main__":
    unittest.main()
