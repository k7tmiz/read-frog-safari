# AGENTS.md

## What this repository is

A Safari port of [read-frog](https://github.com/mengxi-ream/read-frog). `origin` is
`k7tmiz/read-frog-safari`; the Safari work started from `noahhhi/read-frog` and now tracks the
upstream project directly.

- `origin` — this fork. `main` is the only branch that ships.
- `upstream` — `mengxi-ream/read-frog`. Source of feature updates.
- Safari release tags look like `safari-v1.54.2-preview.2`, separate from upstream `v*` tags.

## Syncing upstream

```sh
git fetch upstream --tags
git merge upstream/main
```

Conflicts concentrate in the files the port touches:

- `src/hooks/use-text-to-speech.tsx` — keep upstream's `runPlayback` / `isSuperseded` / `quiet`
  structure and re-route playback through Safari's `WebAudioPlaybackController`.
- `src/utils/orpc/background-client.ts` — keep both upstream's header builder and `safariApiFetch`.
- `wxt.config.ts` — keep both the Safari manifest hook and upstream's build hooks.

After merging, run the full validation below before pushing. Do not drop a Safari branch of a
conflict just to make the merge apply.

## Validation

```sh
pnpm install --frozen-lockfile
SKIP_FREE_API=true pnpm test
pnpm type-check
pnpm fmt:check
pnpm build:safari                 # manifest + entry resources checked
```

Packaging needs full Xcode, and `xcode-select` points at Command Line Tools on this machine:

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer pnpm package:safari
```

`package:safari` signing modes via `SAFARI_SIGNING`:

- `identity` (default here when `SAFARI_SIGN_IDENTITY` is set) — sign the app and its extension
  with an Apple Development certificate and **no provisioning profile**. This is what the preview
  builds use; a profile would expire after seven days on a personal team.
- `adhoc` — unsigned-ish fallback. Safari does **not** list extensions from ad-hoc host apps.
- `auto` / `manual` — let Xcode sign; needs a team and, for `manual`, a profile.

## Releasing

`.github/workflows/release-safari.yml` builds, signs and publishes on a GitHub-hosted macOS
runner. Start it from **Actions → Release Safari → Run workflow**.

- Inputs: `version` (empty = bump), `preview` (empty = stable), `bump`, `publish`, `draft`.
- Secrets: `SAFARI_CERT_P12` (base64 `.p12`), `SAFARI_CERT_PASSWORD`, `SAFARI_TEAM_ID`. Without
  them the workflow falls back to an ad-hoc build.
- A publishing run commits the version bump to `main`, tags `safari-v*`, and attaches the zip plus
  its SHA-256. Pull with `--rebase` before pushing locally after a release.
- The upstream `Release Extension` workflow is disabled on this fork; it only publishes Chrome,
  Edge and Firefox zips and would fight the Safari tag scheme.

Requirements for Safari to list an extension: the host app must carry an Apple-issued signature.
A personal-team Apple Development certificate is enough, but the machine also needs the
**WWDR G3 intermediate** (`https://www.apple.com/certificateauthority/AppleWWDRCAG3.cer`) or
`security find-identity -p codesigning` reports zero valid identities.

## Safari platform notes

- No `sidePanel`, `offscreen`, `identity` or `tabCapture`. The manifest hook drops `side_panel`
  and the side panel entry falls back to page translation; speech plays through Web Audio in the
  content script because Safari has no offscreen document.
- Account requests do not rely on extension host permissions; they run through the containing
  app's native handler or an official-website tab, so `hasAccountHostPermission()` reports granted
  on Safari.
- Xcode 27's `safari-web-extension-converter` rewrites the containing app identifier while keeping
  the extension identifier, and no longer emits `.entitlements` files. `scripts/fix-safari-project.py`
  and `scripts/package-safari.sh` compensate; do not "simplify" either back to fixed counts or to
  the Xcode defaults.
- The converter warns about `type`, `persistent`, `world` and `match_origin_as_fallback`. They are
  intentional for the background page and main-world content scripts.

## Testing Notes

- `src/utils/host/translate/api/__tests__/free-api.test.ts` depends on live external translation services.
- When running tests locally as an AI agent, set `SKIP_FREE_API=true`.
- If `SKIP_FREE_API=true` is set, treat `free-api.test.ts` as intentionally skipped during local validation.

## PR Notes

- PR titles must use conventional commit format, such as `fix(subtitles): ...`; avoid extra prefixes like `[codex]`.
- User-facing fixes and features should include a `.changeset/*.md` file for `@read-frog/extension` unless the change intentionally does not need a release. use conventional commit format for the changeset content.
