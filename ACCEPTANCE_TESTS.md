# WrenchRelay Production Acceptance Tests

A release is not complete merely because `/api/health` is green. Every release must pass the product tests below.

## A. Build and infrastructure

- Docker build completes from repository root.
- Container starts with `uvicorn production:app`.
- `/api/health` returns HTTP 200.
- MongoDB is reachable.
- No secrets appear in build logs or source.
- Railway health check is `/api/health`, sleeping disabled, restart policy ON_FAILURE.

## B. Public routing

- `https://wrenchrelay.com` loads the WrenchRelay choice page over valid HTTPS.
- `https://www.wrenchrelay.com` loads the same entry experience.
- `https://app.wrenchrelay.com` loads the application entry.
- `https://industrial.wrenchrelay.com` preselects Industrial.
- `https://automotive.wrenchrelay.com` preselects Automotive.
- `https://api.wrenchrelay.com/api/health` returns HTTP 200 JSON.
- No domain points to stale Vercel, Workers, Emergent preview, or other obsolete deployment targets.

## C. Choice and onboarding

- First-time root visitor sees Industrial vs Automotive before auth.
- Choice persists through auth and reload.
- User can switch modes from the app.
- Industrial and Automotive copy/prompts differ appropriately.

## D. Authentication

- New password account can register.
- Existing password account can log in.
- Logout clears the HttpOnly session cookie.
- Protected endpoints return 401 without a valid session.
- Google button appears when `GOOGLE_CLIENT_ID` is configured.
- Google sign-in accepts only verified Google identity tokens.
- Session cookie is Secure, HttpOnly, SameSite=Lax.

## E. Brava lifetime entitlement

- A qualifying `@bravatile.com` account receives `pro_lifetime`.
- Pro Lifetime UI is visible after login.
- Brava account is not sent to Stripe checkout.
- Explicit addresses in `BRAVA_LIFETIME_EMAILS` also receive lifetime access.

## F. AI tools

Test with a safe, fictional maintenance scenario. Never use a live hazardous task as an acceptance test.

- Work Order produces factual CMMS-ready text and omits unknown facts.
- Troubleshoot produces ranked checks and separates facts from hypotheses.
- Handoff produces current state, findings, risks, remaining work, next check.
- Industrial output references appropriate machine/control domains when relevant.
- Automotive output references appropriate vehicle diagnostic domains when relevant.
- Safety prompt never recommends bypassing guards, LOTO, interlocks, airbags, high-voltage protections, or safety systems.
- 12 personalities are selectable and influence communication style without changing facts.
- English and Spanish selection is passed to AI requests.

## G. Voice

- Browser with Web Speech API can capture a spoken note.
- Unsupported browsers degrade to typed input without blocking the app.
- Voice greeting attempts on entry and can be disabled.
- Generated output is not automatically treated as verified because it was spoken aloud.

## H. Work-order history

- Generated result can be saved.
- Saved record reappears after reload/login.
- History is isolated by user.
- Search returns only the logged-in user's matching records.

## I. Billing

- Starter checkout uses the configured Starter Stripe price.
- Pro checkout uses the configured Pro Stripe price.
- Successful checkout returns to WrenchRelay.
- Stripe webhook signature verification is required.
- Completed checkout updates the user plan.
- Subscription deletion returns a non-Brava account to Free.
- Billing portal opens only for a customer with a Stripe customer ID.
- No full payment-card data is stored by WrenchRelay.

## J. Legal and safety

Direct routes must load:

- `/terms`
- `/privacy`
- `/safety`
- `/billing`

Signup and checkout include appropriate consent/disclosure language. Safety warning is visible inside the working app.

## K. Security regression

- Secret scan returns zero obvious committed credentials.
- `test_reports/` artifacts are not committed.
- Security headers include nosniff, frame denial, referrer policy, permissions policy, and HSTS.
- CORS is restricted to WrenchRelay production origins.
- No production secret is exposed to the browser bundle.

## Release rule

A failing item in sections A, B, D, E, F, I, or K blocks production release. Other failures require an explicit recorded decision before release.
