# SpiderFoot fork evaluation and roadmap

*Assessed 2026-10-01.*

Upstream SpiderFoot ([smicallef/spiderfoot](https://github.com/smicallef/spiderfoot)) has had no commits since 6 November 2023 (v4.0.0, `0f815a2`), and SpiderFoot HX has been discontinued (spiderfoot.net/hx now redirects to Intel 471). This document records why this repository (6sp33d/spiderfoot) is our base rather than the most active public fork, [poppopjmp/spiderfoot](https://github.com/poppopjmp/spiderfoot), and what we plan to do next.

## Decision

**Build on this repository** (upstream 4.0.0 plus our fixes). **Use poppopjmp/spiderfoot as a source of individual module improvements, not as a base.**

## Comparison

| | 6sp33d/spiderfoot (upstream 4.0.0 + Phase 1) | poppopjmp/spiderfoot v6.1.0 |
|---|---|---|
| Relationship to upstream | Same history; Phase 1 commits on top | Fork of upstream; about 5,600 commits on top; core rewritten |
| Last commit | This branch (upstream: Nov 2023) | 2 Jun 2026 (about 4 months before this assessment) |
| Maintainers | Our team | Effectively one person, plus AI-agent commits |
| Python code (excluding tests) | About 60k lines | About 216k lines, plus a 44k-line React/TS frontend and a Go CLI |
| Runtime needed for a scan | One process, SQLite (`sf.py -s` or `sf.py -l`) | FastAPI plus PostgreSQL at minimum; default compose has 23 services |
| Direct dependencies | 26 | 60 (192 resolved, about 390 MB venv) |
| Unit tests | 1,530 pass on Python 3.10–3.14 | 8,635 pass (3.12) |
| Known dependency advisories | 0 (was 26 before Phase 1) | 20 in 6 packages; upper-bound pins block the fixes |
| Security scans in CI | pip-audit blocking, bandit high/high blocking, CodeQL | pip-audit and Trivy non-blocking (`\|\| true`, `exit-code: 0`) |
| Web authentication | On by default (Phase 1) | On by default (JWT), with the defects listed below |
| Modules | 233 | 309 (95 added, 19 upstream modules removed) |
| Community | Private team fork | 197 stars, 30 forks; open issues include the Docker build failing (#386) |

Measurements were taken by installing and running both codebases in this session. The poppopjmp figures are for commit `4b53ca6` (tag v6.1.0).

## Why not poppopjmp/spiderfoot as the base

We verified each of the following in its code; none require unusual configuration.

1. **Critical authentication bypass via SAML.**
   - `AuthService.process_saml_response` (`spiderfoot/auth/service.py`, around line 1389) decodes and parses the SAML response without checking its signature. The code comment reads "real impl would validate signature".
   - The public `POST /api/auth/sso/saml/acs/{provider_id}` route (`spiderfoot/auth/routes.py`, around line 900) then looks up the user by the email in the assertion and issues access and refresh tokens.
   - An unsigned, forged assertion naming `admin@spiderfoot.local` was accepted. The only precondition is that an admin has enabled any SAML provider.
2. **Roles are not enforced.**
   - `require_permission` is used on only 14 of the 33 routes in `auth/routes.py`.
   - None of the 384 route handlers in `spiderfoot/api/routers/` (39 modules) check permissions. They only check that the caller is logged in, so a "viewer" can start or delete scans and change configuration.
3. **The insecure quick start is the documented path.**
   - The README says to `cp .env.example .env`. That file sets `SF_ADMIN_PASSWORD=admin`, `SF_JWT_SECRET=change-me-in-production-please` and `POSTGRES_PASSWORD=changeme`.
   - The startup check refuses these values only when `SF_ENV=production`, which compose does not set.
4. **Stubs are advertised as features.**
   - `sfp_whatsapp`, `sfp_instagram`, `sfp_reddit`, `sfp_telegram`, `sfp_rubika` and `sfp_soroush` have empty `handleEvent` methods. `sfp_whatsapp` is still described as monitoring WhatsApp.
   - `recon/dns_stealth.py` returns fake IP addresses derived from an MD5 hash.
   - `notifications/rules.py` marks notifications as delivered without sending them.
   - `plugins/marketplace.py` seeds fabricated download counts and ratings.
5. **Duplication and dead code.**
   - There are two SSO stacks, both mounted, and two `AuthConfig` classes.
   - There are five `CircuitBreaker`, three `RateLimiter` and at least four webhook/notification implementations.
   - About 5,500 lines are referenced only by tests.
6. **Heavy to operate.**
   - PostgreSQL is mandatory ("Only PostgreSQL is supported"), and single-process mode was removed in v6.0.0.
   - `python sfapi.py --help` crashes without a database.
   - `openai` and `telethon` are required dependencies, but `openai` is never imported and `telethon` is only imported by a stub module.
7. **High maintenance risk.**
   - The project has a bus factor of one.
   - February 2026 alone had 666 commits (+320k/−154k lines) and 403 distinct version strings.
   - There have been gaps of 202 days and then 4 months with no commits.
8. **It cannot be merged.**
   - The core (`sf.py`, `sfwebui.py`, `sfscan.py`, `sflib.py`, `spiderfoot/db.py`) has been deleted and rewritten, and the SQLite database is not migrated.
   - Adopting it would mean taking ownership of a 216k-line platform that we did not write and that already has the critical defects above.
9. **Licensing needs care.** `modules/sfp_deepinfo.py` carries a "Licence: GPL" header inside an otherwise MIT project.

What poppopjmp did well, and what we should reuse:

- It curated modules for dead services.
- It migrated `sfp_virustotal` to the v3 API.
- It added useful new data sources and tool wrappers.

Its plugin API is still close to upstream: 232 of upstream's 233 modules load on its core. So individual modules can be ported back (MIT) with a mechanical adaptation (`SpiderFootAsyncPlugin` → `SpiderFootPlugin`, `self.fetch_url` → `self.sf.fetchUrl`).

## Why this repository

- It is small and comprehensible, runs as a single process, and installs and passes its tests on Python 3.10–3.14.
- Its problems were known and bounded. Phase 1 (below) fixed the critical ones in about a dozen focused commits.
- Upstream's design (SQLite, `sf.py -s` for scripted runs, `sfcli.py`, correlation rules) is what most SpiderFoot users already know.

## Phase 1: done on this branch

Platform:

- **Dependencies:** floors raised to advisory-free versions, so pip-audit is clean.
  - cryptography 3.4 → 50
  - pyOpenSSL 21 → 26
  - lxml 4 → 6
  - PyPDF2 → pypdf
  - networkx 3, python-docx and python-pptx 1.x
  - `ipaddr` and `pygexf` dropped (unused)
- **Python:** 3.10 or newer is now required. CI tests 3.11–3.14.
- **Tests:** fixed the exit hang and the parallel database race in the test suite. Test and lint tooling updated.
- **CI:**
  - Current GitHub Actions.
  - New `Security` workflow: pip-audit blocking, bandit high/high blocking, weekly schedule.
  - Dependabot for pip, Actions and Docker.
  - CodeQL v3.
- **Docker:** images built on `python:3.12-slim-bookworm` (was Alpine 3.12/3.13, end of life), running as non-root. The full image's broken tool installs are fixed.

Security:

- **Authentication by default:** a random `admin` password is generated into `passwd` (mode 0600) on first start. `--insecure-no-auth` restores the old behaviour.
- **CSRF protection:** every state-changing endpoint is POST-only and requires a random per-process token. `sfcli.py` sends the token automatically.
- **Output escaping:** Mako templates escape all output, which closes the reflected and stored XSS.
- **Export sanitisation:** CSV exports neutralise spreadsheet formulas, and Excel exports store them as text.
- **`/query`** runs on a read-only database connection.

Bug fixes:

- **`fetchUrl()` no longer raises TypeError on network errors.** Any connection reset or timeout used to abort the calling module.
- **`sfcli.py -e FILE` works again.** It crashed before running any command.
- **`removeUrlCreds`** now redacts `Key=`/`PASSWORD=` regardless of case.
- **SpiderFoot HX advertising** has been removed from the UI footer.

## Roadmap

### Phase 2: security and reliability follow-ups

- **Proper user accounts.** Replace HTTP Digest auth and the plaintext `passwd` file with hashed passwords (argon2 or bcrypt), session login and per-user accounts.
- **Drop `'unsafe-inline'` from the CSP** by moving inline `<script>` blocks and `onClick` handlers into static JS.
- **Stop HTML-escaping on input** (`cleanUserInput`) now that output is escaped. Values such as `<` are currently stored as `&lt;`.
- **Sanitise `Content-Disposition` filenames** built from scan names.
- **Restrict the `sfp_tool_*` executable-path options**, for example to a configured allow-list, so a settings change cannot point a module at an arbitrary binary.
- **Fix the scan hang:** if a scan exits before its main loop (for example, with no valid modules), its thread pool is never shut down.
- **Add request timeouts in `sfcli.py`** (bandit B113).
- **Migrate to `netaddr` 1.x** (`IPAddress.is_private()` was removed) **and `secure` 1.x**.

### Phase 3: module health

- **Remove or repair modules for services that are gone or changed.** Verify each before removing it. Candidates:

  | Status | Modules |
  |---|---|
  | Gone | `sfp_threatcrowd`, `sfp_crobat_api`, `sfp_dnsgrep`, `sfp_fsecure_riddler`, `sfp_crxcavator`, `sfp_spyonweb`, `sfp_punkspider`, `sfp_onioncity`, `sfp_jsonwhoiscom` |
  | Retired API | `sfp_bingsearch`, `sfp_bingsharedip` (Bing Search APIs retired August 2025) |
  | Absorbed or paywalled | `sfp_riskiq`, `sfp_dnsdb`, `sfp_robtex`, `sfp_twitter` |
  | Removed by poppopjmp | `sfp_threatjammer`, `sfp_psbdmp`, `sfp_trashpanda`, `sfp_clearbit`, `sfp_bitcoinabuse`, `sfp_phishstats`, `sfp_abusix` |

- **Add a scheduled live smoke-test workflow** that runs each keyless module, plus keyed modules using repository secrets, against known targets and reports which ones broke.
- **Port from poppopjmp, in priority order, each with unit tests:**
  1. `sfp_virustotal` (v3 API; the v2 API is deprecated)
  2. Keyless or free sources: `sfp_internetdb` (Shodan InternetDB), `sfp_rapiddns`, `sfp_hudsonrock`
  3. Widely used keyed sources: `sfp_criminalip`, `sfp_netlas`, `sfp_leakcheck`, `sfp_validin`, `sfp_fofa`, `sfp_zoomeye`, `sfp_hunterhow`, `sfp_bevigil`, `sfp_whoisxmlapi`
  4. Tool wrappers: `sfp_tool_amass`, `sfp_subfinder`, `sfp_httpx`, `sfp_tool_dnsx`, `sfp_tool_naabu`, `sfp_tool_katana`, `sfp_tool_gau`, `sfp_tool_waybackurls`, and the updated `sfp_nmap`/`sfp_nuclei`
- **Do not port:**
  - the stub modules (`sfp_whatsapp`, `sfp_instagram`, `sfp_reddit`, `sfp_telegram`, `sfp_rubika`, `sfp_soroush`)
  - `sfp_deepinfo` (GPL header)
  - the pseudo-modules `sfp__ai_threat_intel`, `sfp__security_hardening` and `sfp_performance_optimizer`

### Phase 4: features HX users relied on

- **A token-authenticated JSON REST API** alongside the existing UI.
- **Scheduled re-scans** with result diffs (attack-surface monitoring), plus notifications by email or webhook.
- **Releases:**
  - semantic versions starting at 4.1.0, with a changelog
  - signed container images published to GHCR
  - a monthly release cadence

### Project hygiene

- Protect `master`: require the Tests, Security and CodeQL checks, and at least one review.
- Add CODEOWNERS. Have at least two maintainers with merge rights.
- Add a `SECURITY.md` with a private reporting address and supported versions.
- Triage Dependabot PRs weekly.
- Review poppopjmp's module changes quarterly for further fixes worth porting.
