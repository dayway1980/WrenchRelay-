"""Regression checks use disposable test keys; they never access owner credentials."""
import base64
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import verify_play_release as gate

HERE = Path(__file__).resolve().parent
PACKAGE = "com.wrenchrelay.industrial"
SOURCE = "a" * 40
WORKFLOW = "b" * 40
MANIFEST = ('<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
            'package="com.wrenchrelay.industrial" android:versionCode="1"/>')


class ReleaseGateTests(unittest.TestCase):
    def test_valid_package_and_version_boundaries(self):
        for package in gate.ALLOWED_PACKAGES:
            for version in ("1", "2100000000"):
                self.assertEqual(gate.validate(package, version, "AA:" * 31 + "AA", gate.ACK), "aa" * 32)

    def test_rejects_invalid_version_codes(self):
        for value in ("0", "-1", "01", "2100000001", "1.0", "1\n", "１", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                gate.validate(PACKAGE, value, "f" * 64, gate.ACK)

    def test_rejects_wrong_package_fingerprint_and_ack(self):
        cases = [
            ("com.wrenchrelay.industrial.evil", "1", "f" * 64, gate.ACK),
            (PACKAGE, "1", "g" * 64, gate.ACK),
            (PACKAGE, "1", "f" * 63, gate.ACK),
            (PACKAGE, "1", "f" * 64, ""),
        ]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                gate.validate(*args)

    def test_requires_immutable_source_not_branch_or_expression(self):
        self.assertEqual(gate.source_commit(SOURCE), SOURCE)
        for value in ("main", "a" * 7, "A" * 40, SOURCE + "\n", "$(false)", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                gate.source_commit(value)

    def test_compiled_manifest_matches_both_expected_fields(self):
        self.assertEqual(gate.compiled_identity(MANIFEST, PACKAGE, "1"), (PACKAGE, 1))

    def test_ignoring_gradle_package_override_fails_closed(self):
        with self.assertRaises(ValueError):
            gate.compiled_identity(MANIFEST, "com.wrenchrelayllc.industrial", "1")

    def test_ignoring_gradle_version_override_fails_closed(self):
        with self.assertRaises(ValueError):
            gate.compiled_identity(MANIFEST, PACKAGE, "2")

    def test_malformed_or_ambiguous_manifest_rejected(self):
        documents = [
            "<manifest", "<other/>", "<manifest package='com.wrenchrelay.industrial'/>",
            '<!DOCTYPE manifest [<!ENTITY x "x">]>' + MANIFEST,
            MANIFEST.replace('android:versionCode="1"', 'versionCode="1"'),
        ]
        for document in documents:
            with self.subTest(document=document), self.assertRaises(ValueError):
                gate.compiled_identity(document, PACKAGE, "1")

    def test_preexisting_bundle_signature_rejected(self):
        for name in ("META-INF/OLD.RSA", "meta-inf/old.sf", "META-INF/OLD.EC", "META-INF/OLD.DSA"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                bundle = Path(directory) / "signed.aab"
                with zipfile.ZipFile(bundle, "w") as archive:
                    archive.writestr(name, "test")
                with self.assertRaises(ValueError):
                    gate.ensure_unsigned_bundle(bundle)

    def test_dependency_checksum_failure_precedes_java_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            tool = Path(directory) / "bundletool.jar"
            tool.write_bytes(b"incorrect tool")
            with mock.patch.object(gate.subprocess, "run") as java:
                with self.assertRaises(ValueError):
                    gate.verify_bundle(Path("does-not-exist.aab"), tool, PACKAGE, "1")
                java.assert_not_called()

    def test_compiled_validation_error_is_not_ignored(self):
        with mock.patch.object(gate, "file_digest", return_value=gate.BUNDLETOOL_SHA256), \
             mock.patch.object(gate, "ensure_unsigned_bundle"), \
             mock.patch.object(gate.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "java")):
            with self.assertRaises(subprocess.CalledProcessError):
                gate.verify_bundle(Path("candidate.aab"), Path("bundletool.jar"), PACKAGE, "1")


@unittest.skipUnless(shutil.which("keytool") and shutil.which("java"), "Java test tools unavailable")
class SigningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix="play-signing-tests-")
        cls.addClassCleanup(cls.workspace.cleanup)
        cls.root = Path(cls.workspace.name)
        cls.binaries = cls.root / "bin"
        cls.binaries.mkdir()
        cls.real_jarsigner = shutil.which("jarsigner")
        if cls.real_jarsigner:
            cls.signer_command = [cls.real_jarsigner]
        else:
            cls.signer_command = [shutil.which("java"), "-m", "jdk.jartool/sun.security.tools.jarsigner.Main"]
        wrapper = cls.binaries / "jarsigner"
        import shlex
        wrapper.write_text("#!/usr/bin/env bash\nexec " + shlex.join(cls.signer_command) + ' "$@"\n')
        wrapper.chmod(0o700)
        cls.password = secrets.token_urlsafe(24)
        cls.keystore = cls.root / "disposable-test-only.p12"
        tool_env = dict(os.environ, TEST_STORE_PASSWORD=cls.password, LC_ALL="C")
        subprocess.run([
            "keytool", "-genkeypair", "-alias", "test-only", "-keyalg", "RSA", "-keysize", "2048",
            "-validity", "3650", "-dname", "CN=Disposable workflow regression key",
            "-storetype", "PKCS12", "-keystore", str(cls.keystore),
            "-storepass:env", "TEST_STORE_PASSWORD", "-keypass:env", "TEST_STORE_PASSWORD",
        ], check=True, capture_output=True, text=True, env=tool_env, timeout=30)
        listed = subprocess.run([
            "keytool", "-list", "-v", "-alias", "test-only", "-keystore", str(cls.keystore),
            "-storepass:env", "TEST_STORE_PASSWORD",
        ], check=True, capture_output=True, text=True, env=tool_env, timeout=30)
        cls.fingerprint = re.search(r"SHA256:\s*([A-F0-9:]+)", listed.stdout).group(1)
        cls.base64_key = base64.b64encode(cls.keystore.read_bytes()).decode()

    def setUp(self):
        self.case = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(self.case.cleanup)
        self.directory = Path(self.case.name)
        self.bundle = self.directory / "unsigned.aab"
        with zipfile.ZipFile(self.bundle, "w") as archive:
            archive.writestr("test-payload.txt", "Cryptographic shell test; not an Android release")
        self.identity = self.directory / "identity.json"
        self.output = self.directory / "output"
        self.env = dict(
            os.environ, PATH=str(self.binaries) + os.pathsep + os.environ["PATH"],
            INPUT_AAB=str(self.bundle), PLAY_IDENTITY_FILE=str(self.identity),
            OUTPUT_DIRECTORY=str(self.output), RUNNER_TEMP=str(self.directory),
            PLAY_PACKAGE=PACKAGE, PLAY_VERSION_CODE="1",
            PLAY_EXPECTED_CERT_SHA256=self.fingerprint, PLAY_OPERATOR_ACK=gate.ACK,
            ANDROID_SOURCE_COMMIT=SOURCE, WORKFLOW_COMMIT=WORKFLOW,
            PLAY_UPLOAD_KEYSTORE_B64=self.base64_key, PLAY_STORE_PASSWORD=self.password,
            PLAY_KEY_PASSWORD=self.password, PLAY_KEY_ALIAS="test-only",
        )
        self.save_identity()

    def save_identity(self):
        record = gate.identity_record(
            self.bundle, PACKAGE, "1", self.env["PLAY_EXPECTED_CERT_SHA256"], gate.ACK, SOURCE, WORKFLOW)
        self.identity.write_text(json.dumps(record))

    def run_signing(self):
        result = subprocess.run(
            ["bash", str(HERE / "sign_internal_bundle.sh")],
            env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(list(self.directory.glob("wrenchrelay-signing.*")), [])
        self.assertNotIn(self.password, result.stdout + result.stderr)
        self.assertNotIn(self.base64_key, result.stdout + result.stderr)
        return result

    def assert_blocked(self):
        result = self.run_signing()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.output.exists())
        return result

    def test_success_has_matching_signature_checksums_and_no_private_key_files(self):
        result = self.run_signing()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            {p.name for p in self.output.iterdir()},
            {"wrenchrelay-industrial-internal-SIGNED.aab", "RELEASE_IDENTITY.json", "SHA256SUMS.txt"})
        for line in (self.output / "SHA256SUMS.txt").read_text().splitlines():
            digest, filename = line.split(maxsplit=1)
            self.assertEqual(gate.file_digest(self.output / filename), digest)
        self.assertEqual(json.loads((self.output / "RELEASE_IDENTITY.json").read_text())["track"], "NOT_UPLOADED")

    def test_wrong_certificate_blocked_and_key_cleaned(self):
        self.env["PLAY_EXPECTED_CERT_SHA256"] = "0" * 64
        self.save_identity()
        self.assert_blocked()

    def test_wrong_password_blocked_and_key_cleaned(self):
        self.env["PLAY_STORE_PASSWORD"] = "intentionally-invalid-test-password"
        self.assert_blocked()

    def test_bad_base64_blocked_and_partial_key_cleaned(self):
        self.env["PLAY_UPLOAD_KEYSTORE_B64"] = "invalid-base64!"
        self.assert_blocked()

    def test_changed_bundle_blocked_before_key_creation(self):
        with zipfile.ZipFile(self.bundle, "a") as archive:
            archive.writestr("changed.txt", "changed after validation")
        self.assertIn("changed after", self.assert_blocked().stderr)

    def test_changed_identity_blocked_before_key_creation(self):
        record = json.loads(self.identity.read_text())
        record["sourceCommit"] = "c" * 40
        self.identity.write_text(json.dumps(record))
        self.assert_blocked()

    def test_missing_credentials_blocked(self):
        self.env["PLAY_UPLOAD_KEYSTORE_B64"] = ""
        self.assert_blocked()

    def test_signature_verification_failure_leaves_no_output_or_key(self):
        failbin = self.directory / "failbin"
        failbin.mkdir()
        import shlex
        wrapper = failbin / "jarsigner"
        wrapper.write_text(
            '#!/usr/bin/env bash\nif [[ "$1" == "-verify" ]]; then exit 9; fi\nexec '
            + shlex.join(self.signer_command) + ' "$@"\n')
        wrapper.chmod(0o700)
        self.env["PATH"] = str(failbin) + os.pathsep + self.env["PATH"]
        self.assert_blocked()


if __name__ == "__main__":
    unittest.main()

