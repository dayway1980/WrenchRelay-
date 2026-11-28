#!/usr/bin/env python3
"""Exercise the real client on a disposable emulator without account/plant data."""
import argparse, hashlib, json, re, subprocess, time
from pathlib import Path
import xml.etree.ElementTree as ET
PKG = "com.wrenchrelayllc.industrial"
def adb(*args):
    return subprocess.check_output(["adb", *args], text=True, stderr=subprocess.STDOUT)
def tree():
    adb("shell", "uiautomator", "dump", "/sdcard/wr-window.xml")
    xml = adb("shell", "cat", "/sdcard/wr-window.xml")
    return ET.fromstring(xml[xml.index("<"):])
def label(node):
    return node.get("text", "") or node.get("content-desc", "")
def find(fragment, timeout=25):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        for node in tree().iter("node"):
            if fragment.casefold() in label(node).casefold():
                return node
        time.sleep(1)
    raise AssertionError("Missing UI: " + fragment)
def tap(fragment):
    node = find(fragment)
    coords = list(map(int, re.findall(r"\d+", node.get("bounds", ""))))
    assert len(coords) == 4, node.attrib
    adb("shell", "input", "tap", str((coords[0]+coords[2])//2), str((coords[1]+coords[3])//2))
def shot(path):
    with open(path, "wb") as output:
        subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=output, check=True)
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--output", default="device-evidence")
    args = parser.parse_args()
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    apks = list(Path(args.artifacts).rglob("app-debug.apk"))
    ids = list(Path(args.artifacts).rglob("BUILD_IDENTITY.json"))
    assert len(apks) == 1 and len(ids) == 1, (apks, ids)
    identity = json.loads(ids[0].read_text())
    assert hashlib.sha256(apks[0].read_bytes()).hexdigest() == identity["apk"]["sha256"]
    assert identity["package"] == PKG
    adb("install", "-r", str(apks[0]))
    adb("shell", "am", "start", "-n", PKG + "/com.wrenchrelay.industrial.MainActivity")
    find("Speak note")
    find("Sign in", timeout=60)
    shot(output/"01-client-sign-in.png")
    tap("Privacy & account"); tap("About this app")
    find(PKG); find("QA debug build")
    shot(output/"02-client-identity.png")
    adb("shell", "input", "keyevent", "4")
    tap("Privacy & account"); tap("Read privacy policy")
    find("does not request microphone permission")
    shot(output/"03-client-privacy.png")
    adb("shell", "input", "keyevent", "4")
    tap("Speak note"); find("Tap a maintenance notes box")
    shot(output/"04-safe-dictation-prompt.png")
    adb("shell", "input", "keyevent", "4")
    assert adb("shell", "pidof", PKG).strip(), "Client process stopped"
    result = {"package": PKG, "apk_sha256": identity["apk"]["sha256"],
              "android_release": adb("shell","getprop","ro.build.version.release").strip(),
              "android_api": adb("shell","getprop","ro.build.version.sdk").strip(),
              "checks": ["install exact artifact", "launch real public sign-in", "native identity",
                         "in-app privacy", "speech refuses account/password field", "process alive"],
              "authenticated_workflow_tested": False, "speech_provider_audio_tested": False,
              "account_deletion_fulfillment_tested": False, "play_eligibility_verified": False}
    (output/"DEVICE_SMOKE.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
if __name__ == "__main__":
    main()
