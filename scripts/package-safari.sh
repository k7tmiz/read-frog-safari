#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# DEVELOPER_DIR can select Xcode without changing the machine-wide xcode-select.
: "${DEVELOPER_DIR:=$(xcode-select -p)}"
export DEVELOPER_DIR
xcrun --find safari-web-extension-converter >/dev/null
pnpm build:safari
mkdir -p .safari
project_root=$(mktemp -d "$PWD/.safari/project.XXXXXX")
app_name="Read Frog Safari"
bundle_id="${SAFARI_BUNDLE_ID:-app.readfrog.safari.local}"
xcrun safari-web-extension-converter "$PWD/.output/safari-mv3" \
  --project-location "$project_root" --app-name "$app_name" \
  --bundle-identifier "$bundle_id" --macos-only --swift --copy-resources \
  --no-open --no-prompt

# Xcode 27's converter can rewrite the containing app ID independently of its
# extension. Pin both generated target IDs so installation preserves extension data.
python3 scripts/fix-safari-project.py "$project_root/$app_name" "$bundle_id"

signing_mode="${SAFARI_SIGNING:-}"
if [[ -z "$signing_mode" ]]; then
  if [[ -n "${SAFARI_SIGN_IDENTITY:-}" ]]; then signing_mode=identity
  elif [[ -n "${SAFARI_TEAM_ID:-}" ]]; then signing_mode=auto
  else signing_mode=none; fi
fi

signing=(CODE_SIGNING_ALLOWED=NO)
case "$signing_mode" in
  auto)
    : "${SAFARI_TEAM_ID:?SAFARI_SIGNING=auto needs SAFARI_TEAM_ID}"
    signing=(CODE_SIGN_STYLE=Automatic CODE_SIGN_IDENTITY="Apple Development"
      DEVELOPMENT_TEAM="$SAFARI_TEAM_ID" -allowProvisioningUpdates)
    ;;
  manual)
    : "${SAFARI_TEAM_ID:?SAFARI_SIGNING=manual needs SAFARI_TEAM_ID}"
    : "${SAFARI_PROFILE_SPECIFIER:?SAFARI_SIGNING=manual needs SAFARI_PROFILE_SPECIFIER}"
    signing=(CODE_SIGN_STYLE=Manual CODE_SIGN_IDENTITY="Apple Development"
      DEVELOPMENT_TEAM="$SAFARI_TEAM_ID"
      PROVISIONING_PROFILE_SPECIFIER="$SAFARI_PROFILE_SPECIFIER")
    ;;
  identity)
    # An Apple Development certificate without a provisioning profile, which is
    # what the Safari port's preview builds use: Safari only lists extensions
    # from Apple-signed host apps, and a profile would add a 7-day expiry.
    : "${SAFARI_SIGN_IDENTITY:?SAFARI_SIGNING=identity needs SAFARI_SIGN_IDENTITY}"
    ;;
  adhoc | none) ;;
  *)
    printf 'Unknown SAFARI_SIGNING=%s (expected auto, manual, identity, adhoc or none)\n' \
      "$signing_mode" >&2
    exit 2
    ;;
esac

xcodebuild -project "$project_root/$app_name/$app_name.xcodeproj" \
  -scheme "$app_name" -configuration Release \
  -derivedDataPath "$PWD/.safari/DerivedData" \
  -destination "generic/platform=macOS" \
  CURRENT_PROJECT_VERSION="${SAFARI_BUILD_NUMBER:-1}" \
  MACOSX_DEPLOYMENT_TARGET="${SAFARI_MACOS_TARGET:-14.0}" "${signing[@]}" build
app_path="$PWD/.safari/DerivedData/Build/Products/Release/$app_name.app"

# The converter writes one entitlements file per target. Signing with them keeps
# App Sandbox whether the signature is ad-hoc or a developer certificate.
app_entitlements=$(find "$project_root/$app_name" -type f -name "*.entitlements" \
  ! -name "*Extension*" | head -n1 || true)
extension_entitlements=$(find "$project_root/$app_name" -type f -name "*.entitlements" \
  -name "*Extension*" | head -n1 || true)

sign_target() {
  local target="$1" entitlements="$2"
  local args=(--force --sign "$sign_identity" --timestamp=none)
  [[ -n "$entitlements" ]] && args+=(--entitlements "$entitlements")
  codesign "${args[@]}" "$target"
}

sign_identity=""
if [[ "$signing_mode" == "adhoc" ]]; then sign_identity="-"; fi
if [[ "$signing_mode" == "identity" ]]; then sign_identity="$SAFARI_SIGN_IDENTITY"; fi

if [[ -n "$sign_identity" ]]; then
  for appex in "$app_path"/Contents/PlugIns/*.appex; do
    [[ -e "$appex" ]] || continue
    sign_target "$appex" "$extension_entitlements"
  done
  sign_target "$app_path" "$app_entitlements"
fi

if [[ "$signing_mode" != "none" ]]; then
  codesign --verify --strict "$app_path"
  for appex in "$app_path"/Contents/PlugIns/*.appex; do
    [[ -e "$appex" ]] || continue
    codesign --verify --strict "$appex"
  done
fi

printf '\nSafari app: %s (signing: %s)\n' "$app_path" "$signing_mode"
