# WrenchRelay dual-product staging prototype

**State: isolated prototype only.** Added under `prototypes/`, deliberately outside `src/`, `web/`, `frontend/`, and the production Python backend. Do not merge/deploy as customer code until release gates are met.

This is an original implementation of the concept explored by Netlify deploy `6aa7defb0a05494ec36321cd`. Netlify records say the September 14, 2026 deploy is TanStack Start / agent-runner with no linked Git commit. **This repository has not been shown to be the deploy source, and the preview could not be inspected end to end.** This folder is not a source-port of the original page.

## Try the prototype locally

From this folder run `python3 -m http.server 8765`, then open `http://localhost:8765/`. It is a static HTML/CSS/JS page. There are no framework dependencies. It contains only fictional sample information.

## Safety boundaries

- No real data input, outbound API requests, external scripts, cookies, trackers, calls, Stripe, booking, CMMS, payments or customer-facing features.
- CSP restricts connections and forbids forms.
- The Automotive concept is framed as **missed-call intake**, not a proven calling integration.
- The Industrial concept is framed as **structured maintenance handoff**, not proven CMMS writeback or diagnosis.
- Human review is mandatory; sample text is not repair or safety authorization.

## Gate to deployment

1. Identify actual production marketing source, live routes, Netlify source provenance, and provider accounts.
2. Audit original Netlify preview visual design, CTAs, network traffic, cookies, forms, analytics and mobile behavior using a real browser.
3. Confirm approved brand/legal operator. Current historic sources disagree (God's Plan LLC / AzVaEnterprises LLC / WrenchRelay LLC). Do not claim one without evidence.
4. Verify billing and phone-routing readiness and published privacy/terms before adding any signup/payment or lead-capture links.
5. Verify accessibility, safety claims, and manual demo acceptance with approved target.
6. Plan rollback and obtain owner approval before live publication, domain changes, costs, outbound calls or production app writes.

The separate `dayway1980/WrenchRelay-website` repository is an operations-only control repo; its draft PR #4 tracks the plan. It must not be connected as a production website source.
