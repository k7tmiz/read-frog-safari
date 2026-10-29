"""Configure converter-generated Safari identifiers and native account transport."""
import pathlib
import json
import re
import sys
import shutil

project, bundle_id = pathlib.Path(sys.argv[1]), sys.argv[2]
if not re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", bundle_id):
    raise SystemExit("Invalid Safari bundle identifier")
pbxproj = next(project.glob("*.xcodeproj/project.pbxproj"))
text = pbxproj.read_text()

original_ids = sorted(set(re.findall(r'PRODUCT_BUNDLE_IDENTIFIER = "?([^";]+)"?;', text)))
if not original_ids:
    raise SystemExit("No PRODUCT_BUNDLE_IDENTIFIER settings found in the converter project")

# Xcode 27's converter can rewrite the containing app identifier independently of
# the extension: with --bundle-identifier app.readfrog.safari.local it emits
# app.readfrog.safari.Read-Frog-Safari for the app but keeps
# app.readfrog.safari.local.Extension. Anchor on the extension identifier, which
# the converter does respect, and derive the app identifier from it.
extension_ids = [candidate for candidate in original_ids if candidate.endswith(".Extension")]
extension_id = extension_ids[0] if extension_ids else None
remaining = [candidate for candidate in original_ids if candidate not in extension_ids]

prefixes = [
    candidate for candidate in remaining if extension_id and extension_id.startswith(f"{candidate}.")
]
app_id = max(prefixes, key=len) if prefixes else min(remaining, key=len)


def remap(old: str) -> str:
    if extension_id and old == extension_id:
        return f"{bundle_id}.Extension"
    if old == app_id:
        return bundle_id
    if extension_id and old.startswith(f"{extension_id}."):
        return f"{bundle_id}.Extension{old[len(extension_id):]}"
    if old.startswith(f"{app_id}."):
        return f"{bundle_id}{old[len(app_id):]}"
    return f"{bundle_id}.{old.rsplit('.', 1)[-1]}"


mapping = {old: remap(old) for old in original_ids}
duplicates = {value for value in mapping.values() if list(mapping.values()).count(value) > 1}
if duplicates:
    raise SystemExit(f"Bundle identifier rewrite collides: {sorted(duplicates)} ({mapping})")


def substitute(match):
    return f'PRODUCT_BUNDLE_IDENTIFIER = "{mapping[match.group(1).strip(chr(34))]}";'


text, count = re.subn(r"PRODUCT_BUNDLE_IDENTIFIER = ([^;]+);", substitute, text)

assigned = set(re.findall(r'PRODUCT_BUNDLE_IDENTIFIER = "([^"]+)";', text))
if bundle_id not in assigned or f"{bundle_id}.Extension" not in assigned:
    raise SystemExit(
        f"Converter did not produce the expected app + extension pair: {sorted(assigned)} "
        f"(from {original_ids})"
    )
print(f"Bundle identifiers: {mapping} ({count} settings)")

manifest = next(project.glob("* Extension/Resources/manifest.json"))
version = json.loads(manifest.read_text())["version"]
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    raise SystemExit(f"Unsupported Safari version: {version}")
text = re.sub(r"MARKETING_VERSION = [^;]+;", f"MARKETING_VERSION = {version};", text)
text = re.sub(r"\s*ENABLE_OUTGOING_NETWORK_CONNECTIONS = YES;", "", text)
text = text.replace(
    "ENABLE_APP_SANDBOX = YES;",
    "ENABLE_APP_SANDBOX = YES;\n\t\t\t\tENABLE_OUTGOING_NETWORK_CONNECTIONS = YES;",
)
pbxproj.write_text(text)

# Replace the converter echo handler (which logs payloads) with the narrowly
# scoped account transport. Credentials must never enter unified logging.
handlers = list(project.glob("* Extension/SafariWebExtensionHandler.swift"))
if len(handlers) != 1:
    raise SystemExit(f"Expected one SafariWebExtensionHandler.swift, found {len(handlers)}")
shutil.copyfile(
    pathlib.Path(__file__).resolve().parent.parent / "native/safari/SafariWebExtensionHandler.swift",
    handlers[0],
)
