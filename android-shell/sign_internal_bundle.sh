#!/usr/bin/env bash
# Run only on the isolated signing runner after compiled-bundle validation.
set -euo pipefail
export LC_ALL=C
umask 077

for name in INPUT_AAB PLAY_IDENTITY_FILE OUTPUT_DIRECTORY RUNNER_TEMP PLAY_PACKAGE PLAY_VERSION_CODE \
  PLAY_EXPECTED_CERT_SHA256 PLAY_OPERATOR_ACK ANDROID_SOURCE_COMMIT WORKFLOW_COMMIT \
  PLAY_UPLOAD_KEYSTORE_B64 PLAY_STORE_PASSWORD PLAY_KEY_PASSWORD PLAY_KEY_ALIAS; do
  if [[ -z "${!name:-}" ]]; then
    echo "::error::Required signing input is not configured: $name"
    exit 2
  fi
done

SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 - "$SCRIPT_DIRECTORY" <<'PY'
import os
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from verify_play_release import verify_saved_identity
verify_saved_identity(
    Path(os.environ["INPUT_AAB"]), Path(os.environ["PLAY_IDENTITY_FILE"]),
    os.environ["PLAY_PACKAGE"], os.environ["PLAY_VERSION_CODE"],
    os.environ["PLAY_EXPECTED_CERT_SHA256"], os.environ["PLAY_OPERATOR_ACK"],
    os.environ["ANDROID_SOURCE_COMMIT"], os.environ["WORKFLOW_COMMIT"],
)
PY

PRIVATE_DIRECTORY="$(mktemp -d "$RUNNER_TEMP/wrenchrelay-signing.XXXXXX")"
cleanup() { rm -rf -- "$PRIVATE_DIRECTORY"; }
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
KEYSTORE="$PRIVATE_DIRECTORY/upload-keystore"
SIGNED_AAB="$PRIVATE_DIRECTORY/internal-signed.aab"
printf '%s' "$PLAY_UPLOAD_KEYSTORE_B64" | base64 --decode > "$KEYSTORE"
chmod 600 "$KEYSTORE"

ACTUAL_FINGERPRINT="$(keytool -list -v -keystore "$KEYSTORE" \
  -alias "$PLAY_KEY_ALIAS" -storepass:env PLAY_STORE_PASSWORD \
  | awk '/SHA256:/ && !seen {print $2; seen=1}' | tr -d ':' | tr '[:upper:]' '[:lower:]')"
EXPECTED_FINGERPRINT="$(printf '%s' "$PLAY_EXPECTED_CERT_SHA256" \
  | tr -d '[:space:]:' | tr '[:upper:]' '[:lower:]')"
if [[ -z "$ACTUAL_FINGERPRINT" || "$ACTUAL_FINGERPRINT" != "$EXPECTED_FINGERPRINT" ]]; then
  echo "::error::Keystore certificate differs from the verified Play upload certificate"
  exit 2
fi

jarsigner -keystore "$KEYSTORE" -storepass:env PLAY_STORE_PASSWORD \
  -keypass:env PLAY_KEY_PASSWORD -signedjar "$SIGNED_AAB" "$INPUT_AAB" "$PLAY_KEY_ALIAS"
jarsigner -verify -strict -keystore "$KEYSTORE" -storepass:env PLAY_STORE_PASSWORD \
  "$SIGNED_AAB" "$PLAY_KEY_ALIAS" > "$PRIVATE_DIRECTORY/verification.txt"
grep -q 'jar verified' "$PRIVATE_DIRECTORY/verification.txt"

SIGNED_FINGERPRINT="$(keytool -printcert -jarfile "$SIGNED_AAB" \
  | awk '/SHA256:/ && !seen {print $2; seen=1}' | tr -d ':' | tr '[:upper:]' '[:lower:]')"
if [[ "$SIGNED_FINGERPRINT" != "$EXPECTED_FINGERPRINT" ]]; then
  echo "::error::Signed bundle certificate fingerprint mismatch"
  exit 2
fi

# Create deliverables only after successful strict signature verification.
mkdir -p -- "$OUTPUT_DIRECTORY"
cp -- "$SIGNED_AAB" "$OUTPUT_DIRECTORY/wrenchrelay-industrial-internal-SIGNED.aab"
cp -- "$PLAY_IDENTITY_FILE" "$OUTPUT_DIRECTORY/RELEASE_IDENTITY.json"
(
  cd -- "$OUTPUT_DIRECTORY"
  sha256sum wrenchrelay-industrial-internal-SIGNED.aab RELEASE_IDENTITY.json > SHA256SUMS.txt
)
echo "PASS: internal candidate signed and verified; no Play upload performed"

