#!/usr/bin/env python3
"""Verify exact Android CI outputs without inferring Play eligibility."""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
from verify_play_release import verify_bundle
PACKAGE = "com.wrenchrelayllc.industrial"
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundletool", required=True)
    args = parser.parse_args()
    apk = Path("app/build/outputs/apk/debug/app-debug.apk")
    bundle = Path("app/build/outputs/bundle/release/app-release.aab")
    verify_bundle(bundle, Path(args.bundletool), PACKAGE, "1")
    sdk = Path(os.environ["ANDROID_HOME"])
    tools = sorted((sdk / "build-tools").glob("*/aapt2"))
    assert tools, "aapt2 missing"
    badging = subprocess.check_output([str(tools[-1]), "dump", "badging", str(apk)], text=True)
    assert re.search(r"package: name='" + re.escape(PACKAGE) + r"' versionCode='1'", badging), badging
    assert "android.permission.RECORD_AUDIO" not in badging, "Unexpected direct microphone permission"
    assert "targetSdkVersion:'36'" in badging, badging
    signer = subprocess.check_output([str(tools[-1].with_name("apksigner")), "verify", "--print-certs", str(apk)], text=True)
    match = re.search(r"Signer #1 certificate SHA-256 digest: ([0-9A-Fa-f]+)", signer)
    assert match, "APK signer fingerprint missing"
    data = {
        "package": PACKAGE, "versionCode": 1, "versionName": "1.0.0", "targetSdk": 36,
        "checkout_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "pull_request_head_commit": os.environ.get("PR_HEAD_SHA") or None,
        "workflow_commit": os.environ.get("GITHUB_SHA"), "workflow_run": os.environ.get("GITHUB_RUN_ID"),
        "apk": {"path": str(apk), "sha256": sha(apk), "signing": "debug", "certificate_sha256": match.group(1).lower()},
        "bundle": {"path": str(bundle), "sha256": sha(bundle), "signing": "unsigned", "bundletool_validation": "passed"},
        "direct_microphone_permission": False, "play_eligibility_verified": False,
        "owner_upload_certificate_verified": False, "physical_device_acceptance_verified": False,
    }
    Path("BUILD_IDENTITY.json").write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data, indent=2))
if __name__ == "__main__":
    main()
