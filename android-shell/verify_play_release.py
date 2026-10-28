#!/usr/bin/env python3
"""Fail-closed validation for owner-approved, internal-only Play signing builds.

This does not contact Play Console, authenticate a package, or publish an app.
The operator must compare the values against the actual Play Console release.
"""
import argparse
import re
import sys

ALLOWED_PACKAGES = frozenset({
    "com.wrenchrelay.industrial",
    "com.wrenchrelayllc.industrial",
})
ACK = "I_VERIFIED_PLAY_PACKAGE_VERSION_AND_UPLOAD_CERT"


def normalized_digest(value: str) -> str:
    digest = value.replace(":", "").replace(" ", "").lower().strip()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Upload-certificate fingerprint must be a SHA-256 digest")
    return digest


def validate(package: str, version_code: str, fingerprint: str, confirmation: str) -> str:
    if package not in ALLOWED_PACKAGES:
        raise ValueError("Package is not a documented WrenchRelay Industrial candidate")
    if not re.fullmatch(r"[1-9][0-9]{0,8}", version_code):
        raise ValueError("Version code must be a positive decimal integer")
    if not 1 <= int(version_code) <= 2100000000:
        raise ValueError("Version code outside Google Play supported range")
    if confirmation != ACK:
        raise ValueError("Operator must explicitly verify values in Play Console")
    return normalized_digest(fingerprint)


def self_test() -> None:
    good = "AA:" * 31 + "AA"
    assert validate("com.wrenchrelay.industrial", "1", good, ACK) == "aa" * 32
    assert validate("com.wrenchrelayllc.industrial", "123", "f" * 64, ACK) == "f" * 64
    bad = [
        ("com.wrenchrelay.industrial.evil", "1", good, ACK),
        ("com.wrenchrelay.industrial", "0", good, ACK),
        ("com.wrenchrelay.industrial", "-1", good, ACK),
        ("com.wrenchrelay.industrial", "2100000001", good, ACK),
        ("com.wrenchrelay.industrial", "1", "1234", ACK),
        ("com.wrenchrelay.industrial", "1", good, "not-confirmed"),
    ]
    for args in bad:
        try:
            validate(*args)
        except ValueError:
            continue
        raise AssertionError("Unsafe or incomplete release declaration was accepted")
    print("PASS: Play manual-release input safety tests")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--package", default="")
    parser.add_argument("--version-code", default="")
    parser.add_argument("--fingerprint", default="")
    parser.add_argument("--confirmation", default="")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
        else:
            validate(args.package, args.version_code, args.fingerprint, args.confirmation)
            print("PASS: structurally valid internal release declaration (Play identity must be verified by the operator)")
    except (ValueError, AssertionError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
