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

# The converter's target layout changes between Xcode releases: Debug and
# Release alone already account for two settings per target, and newer versions
# add targets. Rewrite relative to the app identifier the converter chose so
# extra targets keep distinct identifiers instead of collapsing into one.
original_ids = sorted(set(re.findall(r'PRODUCT_BUNDLE_IDENTIFIER = "?([^";]+)"?;', text)))
if not original_ids:
    raise SystemExit("No PRODUCT_BUNDLE_IDENTIFIER settings found in the converter project")

# The app identifier is the longest prefix of the extension identifier, so a
# shorter test or helper target cannot be mistaken for the containing app.
extension_ids = [candidate for candidate in original_ids if candidate.endswith(".Extension")]
prefixes = [
    candidate
    for candidate in original_ids
    if any(extension.startswith(f"{candidate}.") for extension in extension_ids)
]
base_id = max(prefixes, key=len) if prefixes else min(original_ids, key=len)


def remap(old: str) -> str:
    if old == base_id:
        return bundle_id
    if old.startswith(base_id):
        return f"{bundle_id}{old[len(base_id):]}"
    return f"{bundle_id}.{old.rsplit('.', 1)[-1]}"


mapping = {old: remap(old) for old in original_ids}


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
