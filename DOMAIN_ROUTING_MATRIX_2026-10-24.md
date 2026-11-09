# WrenchRelay host routing — verification and change control (2026-10-24)

## Key architectural fact

**Vercel is connected to the WrenchRelay source repo and builds production/preview deployments; Railway is also hosting the live production gateway and Python backend.** A domain attached to Vercel is NOT necessarily pointing to Vercel. Domain source of truth is the authoritative DNS provider. Do not change route destinations without validating the selected deployment and confirming ownership.

| Hostname / service | Verified configuration | Status/action |
| --- | --- | --- |
| `www.wrenchrelayllc.com` | Railway `wrenchrelay-app` custom domain verified, TLS valid; Vercel `wrenchrelay-industrial` project also has this custom domain assigned and verified | **Do not assume Vercel serves it**; DNS response and end-to-end frontend smoke required before an intentional Vercel cutover |
| `wrenchrelayllc.com` | Railway domain verified with valid certificate; Vercel project has an apex redirect to `www.wrenchrelayllc.com` | Preserve both until the authoritative DNS behavior is confirmed and reviewed |
| `wrenchrelay.app` | Namecheap BasicDNS nameservers; Railway CNAME `kjjvxxet.up.railway.app` reported propagated but ownership is unverified, certificate issuing | Add Railway-issued ownership verification TXT at Namecheap, then recheck Railway status |
| `www.wrenchrelay.app` | Railway CNAME `8vlew8az.up.railway.app` reported propagated; ownership unverified and certificate issuing | Add Railway-issued ownership verification TXT at Namecheap |
| `wrenchrelay.com` and `www.wrenchrelay.com` | Nameservers reported `kelly.ns.cloudflare.com`, `koa.ns.cloudflare.com`; connected Cloudflare account returned no manageable matching zone. Public `www` site showed a different automotive call-intake product branded `AzVaEnterprises LLC` | **Do not repoint, take ownership of, or overwrite these hosts without proving company/domain ownership and intended use** |
| `app.wrenchrelay.com` | Publicly serves a separate WrenchRelay shop-admin login; Railway's custom-domain claim is unverified and routing record does not match | **Preserve current portal**; investigate authorized owners and product separation before any DNS change |
| `press.wrenchrelayllc.com` | Assigned and verified in Vercel `wrenchrelay-industrial` | Smoke-test the page before considering it a production release |
| Railway backend | `wrenchrelay-production` with `/api/health` healthcheck, image-based start command and mounted data | Preserve until GitHub source parity and data backup are proven |

### Minimal Namecheap-only actions for .app, without switching hosting

The following values were read from Railway's domain-status API. **Reread them before using in case Railway has rotated the challenge.**

1. For zone `wrenchrelay.app`, add TXT with Host `_railway-verify` and Value `railway-verify=0e4c20bee0eb48a1fb53122316378a26d02430e80a3734ff2129b3d448e5b873`.
2. For the same zone, add TXT with Host `_railway-verify.www` and Value `railway-verify=36cd4451fa3001d7308e1f3da452fc787828fbb4b962bc75edf5f392dbb511cd`.
3. Keep current CNAMEs, MX, SPF/DKIM/DMARC, and unrelated TXT records as-is. Do not add Vercel routing records for these two hosts simultaneously.
4. Recheck each custom domain's `verified=true` and valid TLS certificate via Railway. Confirm browser HTTPS and redirects with real requests before announcing a fix.

### If WrenchRelay LLC should use Vercel for the customer website

1. Designate `www.wrenchrelayllc.com` as the landing-page frontend and keep Railway behind the API gateway. Choose the frontend routing rules and test the production `wrenchrelay-industrial` Vercel deployment on its default `.vercel.app` hostname first.
2. Verify the published app accurately identifies **WrenchRelay LLC** and implements choice-first Industrial/Automotive navigation, auth, voice, privacy/account deletion, and fail-closed checkout. Do not use the separate `wrenchrelay.com` shop portal as acceptance evidence.
3. Confirm Vercel's project-specific DNS values and establish rollback targets at Namecheap. Changing DNS cuts traffic between providers; it should happen only after positive end-to-end tests, backup, and explicit approval.
4. Change only the appropriate Namecheap host record to Vercel's designated target; do not change nameservers or replace the whole zone.
5. Verify DNS propagation, TLS, redirect loops, signup/login, backend API connectivity, persistence, and telemetry. Roll back the single DNS record if a test fails.

### Current tool access limitation

ChatGPT can read/update Railway and Vercel project configuration and GitHub source, but the connected **Namecheap tool only checks domain availability**, not DNS. Current Cloudflare connection did not have access to the `wrenchrelay.com` zone. Therefore DNS changes must be made by the authorized registrar/zone administrator. No DNS mutation was performed by this PR.

### Gate before production release

Live environment configurations include image-based launch commands with customer application code held in Railway variables. Do **not** attach the GitHub repository to that production service or swap code based solely on Vercel READY/build checks or source CI. First prove the actual runtime app's behavior against the new build in isolation.
