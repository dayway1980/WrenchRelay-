# Main-Domain Source and Lead-Delivery Audit — November 9, 2026
**Status:** read-only audit complete; production change blocked pending actual source and delivery verification.## Public main site
- https://www.wrenchrelay.com/ loads and remains Automotive-first. Title: `Auto Repair Answering Service for Missed Calls | WrenchRelay`.
- Footer says `AzVaEnterprises LLC`, contrary to user-provided business name `WrenchRelay LLC`. This also appears at `/request-demo` and `/signup`. Do not silently modify signed legal documents; establish operator identity and exact deployable source first.
- Existing public content says $99/month for the first 200 handled calls, $0.50 per extra call, no setup fee, and 12-month founding price lock. These are marketing terms, NOT proof the live billing account, signed Stripe webhook, telephony routing, or fulfillment is operational.
- CTA `/signup` routes to `https://app.wrenchrelay.com/signup`; no payment or registration was attempted. Existing site continues to present a paid plan.
- Demo: `https://demo.wrenchrelay.com`; private-demo request form: `https://www.wrenchrelay.com/request-demo`; support: `https://app.wrenchrelay.com/contact?topic=support&source=marketing-footer`.
- Footer contains an ElevenLabs Grants link. Do not treat this as a confirmed endorsement, partner agreement, or grant award.

## Read-only lead-path audit
- `/request-demo`: publicly loads and has Contact name, Shop name, Business email and Phone as required fields, plus optional Website, Message and Company fax. The page says requests are manually reviewed before live demo invitations. Submission destination, backend persistence, actual notification routing and success/error behavior NOT tested. No automated email or access invitation confirmed.
- `app.wrenchrelay.com/contact`: publicly loads with topic, name, email, business, phone, message and optional fax. Privacy/sensitive-data notice present; dedicated Privacy/Terms links not visible. Submission and notification path NOT tested.
- `/signup`: loads, describes Founding Shop Plan, and links to app signup. Account creation, real Stripe account selection and fulfillment NOT tested.
- Neither main site nor support form visibly publishes `support@wrenchrelay.com`; this email is used only as `mailto:` on the separately hosted AppDeploy marketing site. Inbound mail delivery has NOT been verified.

## Email DNS evidence
- Domain DNS scan: Zoho MX hosts `mx.zoho.com`, `mx2.zoho.com`, `mx3.zoho.com`. This means mail is routed to Zoho, NOT to the connected Gmail inbox by default.
- Gmail search for recent mail **addressed to** `support@wrenchrelay.com` returned no results in the connected account. That is not a Zoho mailbox test and does not imply the address exists or receives messages.
- SPF `v=spf1 include:zohomail.com ~all`, DMARC `p=none` without rua reporting, and DKIM `zmail` reported as 1024-bit. Do not change auth records without sender inventory and signed-mail tests; changing DMARC now could block legitimate mail.
- Cloudflare connector showed a `wrenchrelay.com` zone in **pending** state, with saved website, Zoho MX, TXT, send-domain SES and other DNS records. This data is not a trustworthy authority to edit until authoritative nameservers and zone state are reconciled. Vercel separately reports apex A-record `216.150.1.1` and `216.150.16.1` with `misconfigured:false` on November 9. No DNS changed.

## Deployment source
- Vercel account has several similarly named projects (`wrenchrelay`, `wrench-relay`, `wrench-relay-production`, `wrenchrelay-industrial`). None of the first three lists `www.wrenchrelay.com` as an attached custom domain in project-domain results. The Industrial project lists `wrenchrelay.com` and `www` but a previous domain verification check described the .com domain as pending verification; project attachment is NOT evidence of production ownership/source.
- Vercel domain-to-project association lookup returned 403 from the selected team. Do not bypass permissions, merge an arbitrary repo, or repoint DNS.
- Original live marketing application could have a different deployment owner; exact build source is still unknown.
- AppDeploy demo/marketing properties are separately deployed and do NOT prove the existing public .com code has been updated.

## Acceptance steps before wider conversion campaign
1. Identify actual deployable source and deployment ID for `www.wrenchrelay.com` from authorized hosting configuration and inspect live build SHA/branch; preserve rollback version.
2. Verify whether `WrenchRelay LLC` is the contracted operator for the paid Automotive service; update footer, Privacy, Terms, signup and invoices consistently with reviewed legal ownership; remove misleading grants/endorsement language if not substantiated.
3. Confirm who administers the Zoho mailbox `support@wrenchrelay.com`; verify mailbox existence and mail forwarding. With explicit authorization, send one tagged internal test and confirm arrival plus reply path. Do not presume Gmail visibility.
4. Perform one synthetic form submission using noncustomer synthetic data with operator authorization; verify request persistence, owner notification, unsubscribe/privacy controls and response workflow. No actual customer details needed.
5. Confirm app signup, live Stripe account mapping, tax registration, signed webhook processing and entitlement provisioning in test mode, then controlled full-path pilot, before publishing paid activation promises.
6. Only then decide whether existing Automotive-first homepage should remain separate from the new Industrial-first `wrenchrelayllc.com` site. Do not risk both sites while choosing design/brand strategy.

**Changes made during this audit:** NONE to Vercel, Cloudflare, DNS, Zoho, Gmail, Stripe, Railway, the live main .com site, forms, production app, or paid accounts. This file is an internal review artifact.
