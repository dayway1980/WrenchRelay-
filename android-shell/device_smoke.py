#!/usr/bin/env python3
"""Exercise the real client on a disposable emulator without account/plant data."""
import argparse, hashlib, json, re, subprocess, time
from pathlib import Path
import xml.etree.ElementTree as ET

PKG = "com.wrenchrelayllc.industrial"
LAST_XML = ""

def adb(*args, timeout=30):
    return subprocess.check_output(["adb", *args], text=True,
                                   stderr=subprocess.STDOUT, timeout=timeout)

def tree():
    global LAST_XML
    # A failed dump can return exit 0 without writing a file while Android is busy.
    # Remove the prior capture so a retry cannot accidentally inspect stale UI.
    adb("shell", "rm", "-f", "/sdcard/wr-window.xml")
    result = adb("shell", "uiautomator", "dump", "--compressed", "/sdcard/wr-window.xml")
    if "ERROR" in result:
        raise RuntimeError(result.strip())
    xml = adb("shell", "cat", "/sdcard/wr-window.xml")
    root = ET.fromstring(xml[xml.index("<"):])
    LAST_XML = xml
    return root

def label(node):
    return node.get("text", "") or node.get("content-desc", "")

def find(fragment, timeout=60):
    end = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < end:
        try:
            for node in tree().iter("node"):
                if fragment.casefold() in label(node).casefold():
                    return node
            last_error = "UI captured; requested text absent"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                ET.ParseError, ValueError, RuntimeError) as error:
            last_error = str(error)[-300:]
        time.sleep(1)
    raise AssertionError("Missing UI: " + fragment + "; last inspection: " + last_error)

def tap(fragment):
    node = find(fragment)
    coords = list(map(int, re.findall(r"\d+", node.get("bounds", ""))))
    assert len(coords) == 4, node.attrib
    adb("shell", "input", "tap", str((coords[0]+coords[2])//2), str((coords[1]+coords[3])//2))

def shot(path):
    with open(path, "wb") as output:
        subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=output, check=True, timeout=20)


SITE_HOST = "wrenchrelayllc.com"
NETWORK_ERROR_MARKERS = (
    "could not load",
    "check your connection",
    "err_name_not_resolved",
    "webpage not available",
)

def has_text(root, fragment):
    needle = fragment.casefold()
    return any(needle in label(node).casefold() for node in root.iter("node"))

def network_error_visible(root):
    blob = " ".join(label(node) for node in root.iter("node")).casefold()
    return any(marker in blob for marker in NETWORK_ERROR_MARKERS)

def tap_node(node):
    coords = list(map(int, re.findall(r"\d+", node.get("bounds", ""))))
    assert len(coords) == 4, node.attrib
    adb("shell", "input", "tap", str((coords[0]+coords[2])//2), str((coords[1]+coords[3])//2))

def tap_retry(root):
    """Tap the in-app Retry control. Prefer the lower button (error overlay over toolbar)."""
    retries = [node for node in root.iter("node") if "retry" in label(node).casefold()]
    if not retries:
        return False
    def top(node):
        coords = list(map(int, re.findall(r"\d+", node.get("bounds", ""))))
        return coords[1] if len(coords) == 4 else 0
    tap_node(max(retries, key=top))
    return True

def probe_site():
    """Check from the emulator that wrenchrelayllc.com resolves and accepts TCP/443."""
    scripts = (
        "toybox timeout 6 sh -c 'echo | toybox nc -w 5 %s 443' >/dev/null 2>&1 && echo REACHABLE" % SITE_HOST,
        "toybox wget -T 5 -O /dev/null https://%s/ >/dev/null 2>&1 && echo REACHABLE" % SITE_HOST,
        "ping -c 1 -W 3 %s >/dev/null 2>&1 && echo DNS_ONLY" % SITE_HOST,
    )
    notes = []
    for script in scripts:
        try:
            out = adb("shell", "sh", "-c", script, timeout=15)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            notes.append((getattr(error, "output", None) or str(error))[-120:].strip())
            continue
        if "REACHABLE" in out:
            return "REACHABLE"
        if "DNS_ONLY" in out:
            notes.append("DNS_ONLY")
        elif out.strip():
            notes.append(out.strip()[-120:])
    return "; ".join(note for note in notes if note) or "unreachable"

def wait_until_site_reachable(timeout=120):
    end = time.monotonic() + timeout
    last = ""
    while time.monotonic() < end:
        last = probe_site()
        if last == "REACHABLE":
            return last
        time.sleep(2)
    raise AssertionError(
        "emulator could not resolve and reach https://%s:443; last probe: %s" % (SITE_HOST, last)
    )

def wait_for_sign_in(timeout=120):
    """Wait for the live sign-in page. If the native load-error screen appears, tap Retry."""
    end = time.monotonic() + timeout
    last_error = ""
    last_retry_at = 0
    retried = 0
    while time.monotonic() < end:
        try:
            root = tree()
            if has_text(root, "Sign in"):
                return
            if network_error_visible(root):
                last_error = "native network-error screen visible"
                if time.monotonic() - last_retry_at >= 8:
                    if tap_retry(root):
                        retried += 1
                        last_retry_at = time.monotonic()
                        last_error += "; tapped Retry (%s)" % retried
            else:
                last_error = "UI captured; Sign in absent"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                ET.ParseError, ValueError, RuntimeError) as error:
            last_error = str(error)[-300:]
        time.sleep(2)
    raise AssertionError("Missing UI: Sign in; last inspection: " + last_error)

def diagnostics(output):
    for filename, args in (
        ("activity.txt", ("shell", "dumpsys", "activity", "activities")),
        ("logcat.txt", ("logcat", "-d", "-t", "250")),
    ):
        try:
            (output/filename).write_text(adb(*args))
        except (subprocess.SubprocessError, OSError):
            pass
    if LAST_XML:
        (output/"last-window.xml").write_text(LAST_XML)
    try:
        shot(output/"failure.png")
    except (subprocess.SubprocessError, OSError):
        pass

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
    result = {
        "package": PKG, "apk_sha256": identity["apk"]["sha256"],
        "checkout_commit": identity["checkout_commit"], "checks": [],
        "authenticated_workflow_tested": False, "speech_provider_audio_tested": False,
        "account_deletion_fulfillment_tested": False, "play_eligibility_verified": False,
    }
    try:
        result["android_release"] = adb("shell", "getprop", "ro.build.version.release").strip()
        result["android_api"] = adb("shell", "getprop", "ro.build.version.sdk").strip()
        for key in ("window_animation_scale", "transition_animation_scale", "animator_duration_scale"):
            adb("shell", "settings", "put", "global", key, "0")
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
        adb("shell", "wm", "dismiss-keyguard")
        adb("install", "-r", str(apks[0]), timeout=60)
        result["checks"].append("install exact artifact")
        result["site_probe"] = wait_until_site_reachable()
        result["checks"].append("emulator reached wrenchrelayllc.com")
        adb("shell", "am", "start", "-W", "-n", PKG + "/com.wrenchrelay.industrial.MainActivity")
        find("Speak note")
        wait_for_sign_in()
        result["checks"].append("launch real public sign-in")
        shot(output/"01-client-sign-in.png")
        tap("Privacy & account"); tap("About this app")
        find(PKG); find("QA debug build")
        result["checks"].append("native identity")
        shot(output/"02-client-identity.png")
        adb("shell", "input", "keyevent", "4")
        tap("Privacy & account"); tap("Read privacy policy")
        find("does not request microphone permission")
        result["checks"].append("in-app privacy")
        shot(output/"03-client-privacy.png")
        adb("shell", "input", "keyevent", "4")
        tap("Speak note"); find("Tap a maintenance notes box")
        result["checks"].append("speech refuses account/password field")
        shot(output/"04-safe-dictation-prompt.png")
        adb("shell", "input", "keyevent", "4")
        assert adb("shell", "pidof", PKG).strip(), "Client process stopped"
        result["checks"].append("process alive")
        result["result"] = "passed"
    except Exception as error:
        result["result"] = "failed"
        result["failure"] = str(error)
        diagnostics(output)
        raise
    finally:
        (output/"DEVICE_SMOKE.json").write_text(json.dumps(result, indent=2)+"\n")
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
