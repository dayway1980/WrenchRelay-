#!/usr/bin/env python3
"""Validate internal signing inputs and the compiled bundle, without Play access."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ALLOWED_PACKAGES = frozenset({
    "com.wrenchrelay.industrial",
    "com.wrenchrelayllc.industrial",
})
ACK = "I_VERIFIED_PLAY_PACKAGE_VERSION_AND_UPLOAD_CERT"
BUNDLETOOL_SHA256 = "a099cfa1543f55593bc2ed16a70a7c67fe54b1747bb7301f37fdfd6d91028e29"
ANDROID_VERSION = "{http://schemas.android.com/apk/res/android}versionCode"


def file_digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def normalized_digest(value: str) -> str:
    digest = value.replace(":", "").replace(" ", "").lower().strip()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Upload-certificate fingerprint must be a SHA-256 digest")
    return digest


def validate(package: str, version_code: str, fingerprint: str, confirmation: str) -> str:
    if package not in ALLOWED_PACKAGES:
        raise ValueError("Package is not a documented WrenchRelay Industrial candidate")
    if not re.fullmatch(r"[1-9][0-9]{0,9}", version_code):
        raise ValueError("Version code must be a positive decimal integer")
    if not 1 <= int(version_code) <= 2100000000:
        raise ValueError("Version code outside Google Play supported range")
    if confirmation != ACK:
        raise ValueError("Operator must explicitly verify values in Play Console")
    return normalized_digest(fingerprint)


def source_commit(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("Source/workflow identity must be a full lowercase Git commit SHA")
    return value


def compiled_identity(manifest: str, package: str, version_code: str) -> tuple[str, int]:
    if len(manifest) > 1024 * 1024 or re.search(r"<!\s*(DOCTYPE|ENTITY)", manifest, re.I):
        raise ValueError("Unexpected compiled manifest document")
    try:
        root = ET.fromstring(manifest)
    except ET.ParseError as exc:
        raise ValueError("Compiled manifest is not valid XML") from exc
    if root.tag != "manifest":
        raise ValueError("Compiled manifest root is missing")
    actual_package = root.get("package")
    actual_version = root.get(ANDROID_VERSION)
    if actual_package != package or actual_version != version_code:
        raise ValueError("Compiled App Bundle package/version differs from verified Play inputs")
    return actual_package, int(actual_version)


def ensure_unsigned_bundle(bundle: Path) -> None:
    with zipfile.ZipFile(bundle) as archive:
        for entry in archive.namelist():
            name = entry.upper()
            if name.startswith("META-INF/") and name.endswith((".RSA", ".DSA", ".EC", ".SF")):
                raise ValueError("Expected an unsigned bundle; pre-existing signature found")


def identity_record(bundle: Path, package: str, version_code: str, fingerprint: str,
                    confirmation: str, source: str, workflow: str) -> dict:
    digest = validate(package, version_code, fingerprint, confirmation)
    ensure_unsigned_bundle(bundle)
    return {
        "package": package,
        "versionCode": int(version_code),
        "sourceCommit": source_commit(source),
        "workflowCommit": source_commit(workflow),
        "bundleSha256": file_digest(bundle),
        "uploadCertificateSha256": digest,
        "track": "NOT_UPLOADED",
    }


def verify_bundle(bundle: Path, bundletool: Path, package: str, version_code: str) -> None:
    if file_digest(bundletool) != BUNDLETOOL_SHA256:
        raise ValueError("Google bundletool checksum mismatch")
    ensure_unsigned_bundle(bundle)
    common = ["java", "-jar", str(bundletool)]
    subprocess.run(common + ["validate", f"--bundle={bundle}"],
                   check=True, capture_output=True, text=True, timeout=120)
    result = subprocess.run(common + ["dump", "manifest", f"--bundle={bundle}"],
                            check=True, capture_output=True, text=True, timeout=120)
    compiled_identity(result.stdout, package, version_code)


def verify_saved_identity(bundle: Path, identity_file: Path, package: str, version_code: str,
                          fingerprint: str, confirmation: str, source: str, workflow: str) -> None:
    expected = identity_record(bundle, package, version_code, fingerprint, confirmation, source, workflow)
    if json.loads(identity_file.read_text()) != expected:
        raise ValueError("Unsigned bundle or release identity changed after compiled validation")


def self_test() -> None:
    good = "AA:" * 31 + "AA"
    assert validate("com.wrenchrelay.industrial", "1", good, ACK) == "aa" * 32
    assert validate("com.wrenchrelayllc.industrial", "2100000000", "f" * 64, ACK) == "f" * 64
    assert source_commit("a" * 40) == "a" * 40
    manifest = ('<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
                'package="com.wrenchrelay.industrial" android:versionCode="1"/>')
    assert compiled_identity(manifest, "com.wrenchrelay.industrial", "1") == (
        "com.wrenchrelay.industrial", 1)
    bad = [
        ("com.wrenchrelay.industrial.evil", "1", good, ACK),
        ("com.wrenchrelay.industrial", "0", good, ACK),
        ("com.wrenchrelay.industrial", "-1", good, ACK),
        ("com.wrenchrelay.industrial", "2100000001", good, ACK),
        ("com.wrenchrelay.industrial", "0001", good, ACK),
        ("com.wrenchrelay.industrial", "1", "1234", ACK),
        ("com.wrenchrelay.industrial", "1", good, "not-confirmed"),
    ]
    for args in bad:
        try:
            validate(*args)
        except ValueError:
            continue
        raise AssertionError("Unsafe or incomplete release declaration was accepted")
    print("PASS: Play signing input and compiled-manifest safety tests")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    for field in ("package", "version-code", "fingerprint", "confirmation", "source-commit",
                  "workflow-commit", "bundle", "bundletool", "identity-output"):
        parser.add_argument("--" + field, default="")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        validate(args.package, args.version_code, args.fingerprint, args.confirmation)
        source_commit(args.source_commit)
        if bool(args.bundle) != bool(args.bundletool):
            raise ValueError("Bundle and pinned bundletool must be supplied together")
        if args.identity_output and not args.bundle:
            raise ValueError("An identity record requires compiled-bundle validation")
        if args.bundle:
            bundle = Path(args.bundle)
            verify_bundle(bundle, Path(args.bundletool), args.package, args.version_code)
            record = identity_record(bundle, args.package, args.version_code, args.fingerprint,
                                     args.confirmation, args.source_commit, args.workflow_commit)
            if args.identity_output:
                Path(args.identity_output).write_text(json.dumps(record, indent=2) + "\n")
            print("PASS: compiled unsigned bundle matches verified release inputs")
        else:
            print("PASS: structural inputs only; Play Console identity still requires owner verification")
    except (ValueError, OSError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

