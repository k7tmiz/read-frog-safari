<div align="center">

# Read Frog Safari

**An unofficial macOS Safari build of [Read Frog](https://github.com/mengxi-ream/read-frog)**

[![Latest release](https://img.shields.io/github/v/release/k7tmiz/read-frog-safari?filter=safari-v*&style=flat-square&label=Safari%20release&color=brightgreen&labelColor=black)](../../releases)
[![License](https://img.shields.io/github/license/k7tmiz/read-frog-safari?style=flat-square&labelColor=black)](./LICENSE)
[![macOS](https://img.shields.io/badge/macOS-14%2B-black?style=flat-square&logo=apple&labelColor=black)](#requirements)

[Download](../../releases) · [Safari technical notes](./readmes/README.safari.md) · [Upstream project](https://github.com/mengxi-ream/read-frog) · [Agent workflow](./AGENTS.md)

</div>

> **This is not the official Read Frog repository.**
> It is a personal fork that packages the upstream extension as a native Safari host app for
> macOS. Chrome, Edge and Firefox builds, the website, accounts and support all belong to the
> [upstream project](https://github.com/mengxi-ream/read-frog) — please do not report Safari-port
> problems there. Issues are disabled on this fork.

## What this fork adds

Read Frog itself is upstream's work. This repository keeps the extension source tracking
`mengxi-ream/read-frog` and adds only the macOS Safari host:

| Area         | What is different here                                                                                                                                                           |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Packaging    | Swift host app generated with `safari-web-extension-converter`, built as a universal binary                                                                                      |
| Manifest     | `sidePanel`, `offscreen` and `identity` are dropped; a nonpersistent background page replaces the service worker                                                                 |
| Account      | Session requests go through the containing app's native `SafariWebExtensionHandler` or an official-website tab, because Safari withholds website cookies from extension requests |
| Google Drive | OAuth runs in a dedicated Safari tab instead of `browser.identity`                                                                                                               |
| Speech       | Edge TTS audio is decoded and played with Web Audio in the page, inside the click gesture                                                                                        |
| Releases     | Built, signed and published by GitHub Actions on a macOS runner                                                                                                                  |

Every release notes the upstream version it contains. See
[`readmes/README.safari.md`](./readmes/README.safari.md) for the full technical account.

## Install

1. Download the latest [`safari-v*` release](../../releases) and unzip it.
2. Quit Safari, then replace `Read Frog Safari.app` in **Applications** with the new copy.
3. Open the app once, then enable **Read Frog** in **Safari → Settings → Extensions** and grant
   access to the websites you want to translate.

Keep the same bundle identifier (`app.readfrog.safari.local`) across updates: Safari keys
extension storage on it. Do not uninstall the old extension first — removing it can reset its
local storage, including configured providers and sign-in state. If Gatekeeper blocks the app,
right-click it and choose **Open**.

## Requirements

- macOS 14 or later, Safari 17 or later
- Apple silicon or Intel (the app is a universal binary)
- Development targets macOS 27 / Safari 27; older versions are not certified

## Build from source

Requires Node 26, pnpm 12 and full Xcode:

```sh
pnpm install --frozen-lockfile
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer pnpm package:safari
```

The app lands in `.safari/DerivedData/Build/Products/Release/Read Frog Safari.app`. Two checks run
along the way: `build:safari` verifies the Safari manifest and its entry resources, and
`package:safari` pins the bundle identifiers the Xcode converter tends to rewrite.

Signing is controlled by `SAFARI_SIGNING`:

- `identity` — sign with an Apple Development certificate, no provisioning profile (what the
  preview builds use)
- `adhoc` — local fallback; **Safari does not list extensions from ad-hoc host apps**
- `auto` / `manual` — delegate to Xcode signing; needs a team and, for `manual`, a profile

## Release pipeline

Releases are produced by [`.github/workflows/release-safari.yml`](./.github/workflows/release-safari.yml),
never by uploading a local build.

1. **Actions → Release Safari → Run workflow**
2. Choose a version (or leave it empty to bump), an optional preview number, and whether to publish
3. The runner builds and signs the app, commits the version bump, tags `safari-v*`, and attaches
   the zip plus its SHA-256 to the release

Repository secrets: `SAFARI_CERT_P12` (base64 `.p12`), `SAFARI_CERT_PASSWORD`, `SAFARI_TEAM_ID`.
Without them the workflow still runs but produces an ad-hoc build that Safari will not list.
The workflow commits to `main`, so pull with `--rebase` before pushing locally after a release.

## Limitations

- **No side panel.** Safari has no `sidePanel` API. The floating button's panel action falls back to
  page translation and the option is hidden in settings; the subtitles sidebar has no Safari host.
- **Built-in AI providers are Chrome-only.** Selecting one on Safari fails with a provider error;
  use a hosted or local provider instead.
- **Speech playback is page-scoped.** Chrome and Firefox keep playing across navigation; Safari's
  Web Audio path stops when the page does.
- **Unsigned builds are invisible to Safari.** Only Apple-signed host apps appear in
  Settings → Extensions, which is why releases carry a signing certificate.

## Staying in sync with upstream

```sh
git fetch upstream --tags
git merge upstream/main
```

`upstream` points at `mengxi-ream/read-frog`. Conflicts concentrate in the files the port touches;
[`AGENTS.md`](./AGENTS.md) lists them and the validation to run before pushing.

## Documentation

| File                                                     | Purpose                                                                             |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| [`readmes/README.safari.md`](./readmes/README.safari.md) | Safari behaviour, account/Google Drive transports, packaging and validation details |
| [`AGENTS.md`](./AGENTS.md)                               | Repository layout, upstream syncing, signing and release conventions                |
| `readmes/README.<locale>.md`                             | Upstream product documentation in other languages, unchanged                        |

## Credits and license

Read Frog is built by [mengxi-ream](https://github.com/mengxi-ream) and its contributors. The Safari
port in this repository started from [noahhhi/read-frog](https://github.com/noahhhi/read-frog) and
is maintained here independently.

Licensed under the [GNU General Public License v3.0](./LICENSE), the same license as upstream.
