# Read Frog for Safari on macOS

Technical companion to the [root README](../README.md): what the Safari port changes, how to build
and package it, how releases are signed, and what to verify before shipping.

## Build the extension

Build the extension from source with the repository's pnpm and Node versions:

```sh
pnpm install --frozen-lockfile
pnpm build:safari
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer bash scripts/test-safari-native.sh
```

The result is `.output/safari-mv3`. The build checks that its entry resources exist and that Chrome-only permissions did not leak into the Safari manifest.

## Create the macOS app

Install full Xcode, open it once to finish setup, and select it with `DEVELOPER_DIR` when your active developer directory points to Command Line Tools.

Safari only lists extensions whose host app carries an Apple-issued signature, so the signing mode decides whether the build is usable:

| `SAFARI_SIGNING`  | Result                                                                                                                                                       |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `identity`        | Signs with an Apple Development certificate and **no provisioning profile**. What releases use; Safari lists it, and there is no seven-day profile expiry.   |
| `adhoc`           | Local fallback. The app runs, but Safari hides the extension unless **Develop → Allow Unsigned Extensions** is enabled, which resets on every Safari launch. |
| `auto` / `manual` | Delegates to Xcode signing. Needs `SAFARI_TEAM_ID`, and `manual` also needs `SAFARI_PROFILE_SPECIFIER`.                                                      |

```sh
# Sign with a certificate already in the login keychain
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
SAFARI_SIGNING=identity \
SAFARI_SIGN_IDENTITY="Apple Development: you@example.com (XXXXXXXXXX)" \
pnpm package:safari

# Ad-hoc, for a quick local check only
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
SAFARI_SIGNING=adhoc \
pnpm package:safari
```

A personal-team Apple Development certificate works and is valid for a year. Signing it without a profile avoids the seven-day expiry that personal-team provisioning profiles carry. The machine must also have the **WWDR G3 intermediate** installed — without it, `security find-identity -p codesigning` reports zero valid identities even though the certificate is present:

```sh
curl -fsSL -o /tmp/AppleWWDRCAG3.cer https://www.apple.com/certificateauthority/AppleWWDRCAG3.cer
security add-certificates -k ~/Library/Keychains/login.keychain-db /tmp/AppleWWDRCAG3.cer
```

The app is `.safari/DerivedData/Build/Products/Release/Read Frog Safari.app`. Copy it into Applications, open it, and enable Read Frog in Safari's Extensions settings. Grant access to the websites you want to translate. Keep the same `SAFARI_BUNDLE_ID` across updates; the default is `app.readfrog.safari.local`. Increase `SAFARI_BUILD_NUMBER` for each installed update. Export your configuration before replacing a local development app: uninstalling or unregistering an extension can reset its local storage, including sign-in state.

## Release from GitHub Actions

`.github/workflows/release-safari.yml` builds and publishes the Safari app on a GitHub-hosted macOS runner, so no local Xcode install or manual upload is needed. Start it from **Actions → Release Safari → Run workflow**:

| Input     | Meaning                                                                  |
| --------- | ------------------------------------------------------------------------ |
| `version` | Exact `X.Y.Z` to release. Leave empty to bump `package.json` instead.    |
| `preview` | Preview number: `2` produces `safari-v1.55.0-preview.2`. Empty = stable. |
| `bump`    | `patch` / `minor` / `major` / `none`, used only when `version` is empty. |
| `publish` | Off builds and uploads a workflow artifact without tagging or releasing. |
| `draft`   | Publishes the release as a draft.                                        |

A publishing run builds the app, commits the version bump, creates the `safari-v*` tag, and attaches `Read-Frog-Safari-<version>.zip` plus its SHA-256 to the release. Release notes list the commits since the previous Safari tag and repeat the install steps.

Signing is driven by three repository secrets. With all three the build is signed with the Apple Development certificate and Safari lists the extension; with none it falls back to ad-hoc and Safari hides it:

- `SAFARI_CERT_P12` — base64 of an Apple Development `.p12`
- `SAFARI_CERT_PASSWORD` — password for that `.p12`
- `SAFARI_TEAM_ID` — Apple Developer team ID

No provisioning profile is used, which is what keeps personal-team certificates from expiring after seven days.

Optional build variables: repository variable `WXT_GOOGLE_CLIENT_ID` (or secret of the same name) enables Google sign-in and Google Drive; `SAFARI_BUNDLE_ID` overrides the default `app.readfrog.safari.local`. Keep the bundle ID stable across releases or Safari treats each build as a new extension and drops its stored configuration.

Workflows copied into a fork start disabled: open **Actions** once and approve running them. The upstream `Release Extension` workflow can be disabled from the Actions tab; it only publishes Chrome, Edge and Firefox zips and conflicts with the Safari release numbering.

The packaging script pins the bundle identifiers the Xcode 27 converter rewrites, re-adds the entitlements that converter no longer emits, keeps app and extension versions aligned with the manifest, and defaults the macOS deployment target to 14.0. Override `SAFARI_MACOS_TARGET` if needed. Runtime verification has been performed on Safari 27/macOS 27; earlier versions and iOS are not certified by this work.

## Safari behavior

- Safari uses a nonpersistent background page and has no Chrome `offscreen` API. Speech uses the existing Edge TTS HTTP service, then decodes and plays audio in the page through Web Audio. The click handler resumes audio before asynchronous synthesis begins, respecting Safari's user-gesture requirement. Playback is scoped to the current page; Chrome and Firefox retain their existing background/offscreen playback.
- Page translation, selection translation, input injection, popup and options UI use the existing extension code.
- Account sign-in uses the official Read Frog website. Safari can omit website session cookies from extension requests even with host access and `credentials: "include"`. Account requests therefore run in an isolated extension script on an official website tab, with response bytes streamed over a private extension port. Returning to the extension refreshes its account state. When no official tab is open, signed-in requests use the containing App’s narrowly scoped native HTTP handler with fresh cookies from the current Safari cookie store. This path buffers responses (up to 8 MiB) before returning them; opening the official website enables incremental streaming for hosted account APIs. Native requests use an ephemeral session without a separate cookie jar, reject redirects, and apply server cookie refresh/logout back to Safari. Background requests never create or reopen website tabs. Explicit Log in and Web App actions still open the website. Cookies are not copied into extension storage. Other providers keep their normal network route.
- Google Drive sign-in uses a dedicated Safari tab to complete the same Google OAuth flow as Chrome. The callback must match the tab, exact registered origin/path and a random login state. Closing the sign-in tab cancels the attempt; timeout and navigation failure remove its listeners. Local configuration import/export and backups remain available.
- Safari has no `sidePanel` API, so its permission and manifest entry are excluded. The floating button's panel action falls back to page translation on Safari and the option is hidden from settings; the subtitles sidebar has no Safari host yet. The normal floating translation button remains available.
- Xcode's converter may warn about `type`, `persistent`, and `world`. These are retained for the background-page and main-world content-script behavior; verify runtime behavior on each supported Safari release instead of removing them blindly.

## Google Drive configuration

Use the same `WXT_GOOGLE_CLIENT_ID` used for the upstream Chrome release. It is a public application identifier, not a user's Google password or access token. The upstream release pipeline injects it when building; a local source build can put it in the ignored `.env.safari.local` file. Installing an already configured Safari app does not require each user to create a Google Cloud project.

Safari defaults to the upstream Chrome extension's registered callback, `https://modkelfkcfjpgbfmnbnllalkiogfofhb.chromiumapp.org/`. If your own OAuth client registers a different HTTPS callback, set `WXT_GOOGLE_REDIRECT_URL` too. Keep client and callback paired: Google rejects an unregistered redirect. The Safari flow opens the real Google website in a regular tab, and observes only the tab it created. It does not embed Google's login page, request a client secret, use a local callback server, or add native messaging permissions.

Using the same upstream client preserves the Google application identity and requested scopes (`drive.appdata` and `userinfo.email`). It also keeps the current Chrome token behavior: the access token is used until near expiry, then a new sign-in flow runs. User authorization stays in extension-local storage. A separate Google Cloud project would represent a different application and should not be assumed to share the upstream app's backups.

## Validation

```sh
SKIP_FREE_API=true pnpm test
pnpm lint
pnpm fmt:check
pnpm build:safari
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer bash scripts/test-safari-native.sh
```

In Safari, verify page translation and restoration, selected-text streaming translation, the settings page, provider connection testing, input replacement on a test page, Google Drive upload/download readback, video subtitle translation during playback, and speech completion (not just a successful synthesis response). API availability requires a working provider; an HTTP success with empty model output is not sufficient proof.

References: [Apple's Safari extension overview](https://developer.apple.com/safari/extensions/), [WebKit's Manifest V3 support](https://webkit.org/blog/12445/new-webkit-features-in-safari-15-4/), and [WXT browser targets](https://wxt.dev/guide/essentials/target-different-browsers).
