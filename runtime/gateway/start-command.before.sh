sh -c 'echo WR_GATEWAY_CANONICAL_V6; mkdir -p /tmp/voice /tmp/public/delete-account /tmp/public/privacy-android; cat > /tmp/public/delete-account/index.html <<"HTML"
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Delete WrenchRelay account & data</title><style>body{font-family:system-ui,-apple-system,sans-serif;background:#07111f;color:#edf6ff;margin:0;padding:32px}main{max-width:760px;margin:auto;background:#0d1b2a;padding:28px;border-radius:18px;border:1px solid #25415f}h1{margin-top:0}a.button{display:inline-block;padding:13px 18px;border-radius:10px;background:#eaf6ff;color:#07111f;text-decoration:none;font-weight:800}p,li{line-height:1.55;color:#cbd9e7}.small{font-size:13px;color:#9fb2c4}@media print{.nav,.actions{display:none!important}body{background:#fff;color:#111}.hero,.section,.proof{padding:28px 24px}.machine,.card,.proof,.cta{box-shadow:none;background:#fff;color:#111;border-color:#bbb}.lead,.muted,.card p,.truth,.cta span,footer{color:#333}.kicker,.num{color:#17617d}.proofwrap{padding:0}.hero{grid-template-columns:1fr 1fr}.gwPrintBreak{break-before:page}}
</style></head><body><main><h1>Delete your WrenchRelay account & data</h1><p>WrenchRelay LLC provides this page for users of the WrenchRelay Industrial Android app and web service to request deletion of their account and associated WrenchRelay data.</p><h2>How to request deletion</h2><ol><li>Use the button below from the email address associated with your WrenchRelay account.</li><li>Keep the subject line <strong>WrenchRelay account deletion request</strong>.</li><li>We will verify the request before deleting the account and associated work-order/account data.</li></ol><p><a class="button" href="mailto:support@wrenchrelay.app?subject=WrenchRelay%20account%20deletion%20request&body=Please%20delete%20my%20WrenchRelay%20account%20and%20associated%20data.%0A%0AAccount%20email%3A%20">Request account deletion</a></p><h2>What is deleted</h2><p>After verification, WrenchRelay deletes the app account and associated account/work-order data under WrenchRelay&#39;s control, except information that must be retained for legitimate security, fraud-prevention, legal, tax, or regulatory reasons. Any required retention is limited to that purpose.</p><p class="small">Operator: WrenchRelay LLC · Contact: support@wrenchrelay.app · Privacy: <a href="/privacy" style="color:#9fd4ff">wrenchrelayllc.com/privacy</a></p></main></body></html>
HTML
cat > /tmp/public/privacy-android/index.html <<"HTML"
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>WrenchRelay Industrial Android Privacy</title><style>body{font-family:system-ui,-apple-system,sans-serif;background:#07111f;color:#edf6ff;margin:0;padding:32px}main{max-width:820px;margin:auto;background:#0d1b2a;padding:28px;border-radius:18px;border:1px solid #25415f}h1,h2{color:#fff}p,li{line-height:1.58;color:#cbd9e7}a{color:#9fd4ff}</style></head><body><main><h1>WrenchRelay Industrial Android Privacy</h1><p><strong>Operator:</strong> WrenchRelay LLC · <strong>Contact:</strong> support@wrenchrelay.app</p><p>This notice applies to the WrenchRelay Industrial Android app distributed through Google Play.</p><h2>Information WrenchRelay processes</h2><ul><li>Account information such as the email address used to sign in or register.</li><li>Maintenance information you choose to enter, including equipment observations, measurements, fault codes, actions, handoff notes, and work-order content.</li><li>Recognized text returned by the device speech-recognition service when you use the native Speak button.</li><li>Technical service information needed to operate, secure, and troubleshoot the service.</li></ul><h2>Voice input</h2><p>The Google Play build launches the Android device&#39;s speech-recognition activity. Audio may be processed by the speech-recognition provider configured on the device under that provider&#39;s terms and privacy practices. WrenchRelay receives the recognized text returned by that service; the WrenchRelay Android app does not request the RECORD_AUDIO permission and does not receive or store the raw microphone audio from that native Speak flow.</p><h2>Payments</h2><p>The Google Play build is consumption-only and does not offer purchases or subscription changes inside the Android app. Payment-card data for WrenchRelay web checkout is handled by Stripe when web checkout is enabled and is not stored by the Android app.</p><h2>CMMS and external systems</h2><p>External CMMS data is transmitted only when a connector is configured and verified for the relevant workflow.</p><h2>Retention and deletion</h2><p>Account and work-order data is retained as needed to provide and secure the service. You may request deletion of your WrenchRelay account and associated data at <a href="/delete-account">wrenchrelayllc.com/delete-account</a>. After verification, WrenchRelay deletes data under its control except information that must be retained for legitimate security, fraud-prevention, legal, tax, or regulatory reasons, limited to those purposes.</p><h2>Safety</h2><p>WrenchRelay is maintenance documentation and decision-support software. Users remain responsible for safe work, approvals, lockout/tagout, electrical safety, OEM requirements, site procedures, and human verification before consequential action.</p><p><a href="/">Return to WrenchRelay</a></p></main></body></html>
HTML

 mkdir -p /tmp/public/giant-wheel; cat > /tmp/public/giant-wheel/index.html <<"GWHTML"
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hybrid Wheel Press | Indexed Rotary Compression Molding</title>
<meta name="description" content="Hybrid Wheel Press is a pre-prototype WrenchRelay LLC rotary compression-molding concept using indexed removable cassettes around one dedicated high-force forming station.">
<link rel="canonical" href="https://www.wrenchrelayllc.com/hybrid-wheel-press">
<meta property="og:type" content="website">
<meta property="og:title" content="Hybrid Wheel Press | Indexed Rotary Compression Molding">
<meta property="og:description" content="A pre-prototype WrenchRelay LLC press architecture designed to keep the high-force station focused on forming while compatible process steps happen elsewhere.">
<meta property="og:url" content="https://www.wrenchrelayllc.com/hybrid-wheel-press">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="Hybrid Wheel Press | Indexed Rotary Compression Molding">
<meta name="twitter:description" content="Hybrid Wheel Press: a pre-prototype indexed-cassette rotary compression-molding architecture from WrenchRelay LLC.">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage","name":"Hybrid Wheel Press","url":"https://www.wrenchrelayllc.com/hybrid-wheel-press","description":"Pre-prototype indexed-cassette rotary compression-molding press concept from WrenchRelay LLC.","about":{"@type":"Thing","name":"Hybrid Wheel Press rotary compression-molding platform"},"publisher":{"@type":"Organization","name":"WrenchRelay LLC","url":"https://www.wrenchrelayllc.com"}}</script>
<style>
:root{--bg:#081019;--panel:#101a24;--line:#293744;--text:#eef6fb;--muted:#9aabb8;--cyan:#69d7ff;--cyan2:#bceeff}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:inherit;text-decoration:none}.nav{height:72px;display:flex;align-items:center;justify-content:space-between;padding:0 clamp(20px,5vw,72px);border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(8,16,25,.92);backdrop-filter:blur(14px);z-index:10}.brand{font-weight:900;letter-spacing:-.03em}.brand span{color:var(--cyan)}.brand small{font-size:10px;color:#8092a0;letter-spacing:.14em;margin-left:8px}.navlinks{display:flex;gap:12px;align-items:center}.navlinks a{font-size:13px;padding:9px 13px;border:1px solid #354654;border-radius:999px}.navlinks span{font-size:11px;letter-spacing:.14em;color:#8092a0}.hero{max-width:1240px;margin:auto;display:grid;grid-template-columns:1.08fr .92fr;gap:70px;align-items:center;padding:94px clamp(22px,5vw,72px) 80px}.kicker{display:block;color:var(--cyan);font-size:11px;font-weight:900;letter-spacing:.17em;margin-bottom:18px}.hero h1{font-size:clamp(64px,9vw,118px);line-height:.86;letter-spacing:-.065em;margin:0}.hero h2{font-size:clamp(29px,3.3vw,50px);line-height:1.02;letter-spacing:-.04em;margin:26px 0 20px}.lead{font-size:18px;line-height:1.68;color:#afbdc9;max-width:760px}.badges{display:flex;flex-wrap:wrap;gap:10px;margin:26px 0}.badges span{font-size:11px;font-weight:800;border:1px solid #314452;background:#111d27;padding:8px 11px;border-radius:999px;color:#cbd8e1}.actions{display:flex;gap:12px;flex-wrap:wrap;margin:30px 0}.primary,.secondary{padding:14px 18px;border-radius:12px;font-size:14px;font-weight:900}.primary{background:var(--cyan);color:#061018}.secondary{border:1px solid #3c4f5d;color:#eef7fc}.truth{font-size:13px;line-height:1.55;color:#8193a1;border-left:3px solid #385466;padding-left:14px}.machine{background:linear-gradient(180deg,#111c26,#0b1219);border:1px solid #2d3b47;border-radius:26px;padding:22px;box-shadow:0 36px 90px rgba(0,0,0,.35)}.machinehead{display:flex;justify-content:space-between;align-items:center}.machinehead span{font-size:10px;letter-spacing:.18em;color:#6e8293}.machinehead b{font-size:14px}.machine svg{width:100%;height:auto;margin-top:8px}.machine>p{text-align:center;color:#607383;font-size:11px;margin:0}.station rect{fill:#17232d;stroke:#435260;stroke-width:1.5}.station text{fill:#cbd8e1;font-size:13px;font-weight:900;letter-spacing:.06em}.press rect{fill:#103245;stroke:var(--cyan)}.press text{fill:var(--cyan2)}.svgsmall{fill:#75899a;font-size:12px;font-weight:700;letter-spacing:.18em}.svgbig{fill:#eef7fc;font-size:21px;font-weight:900;letter-spacing:.08em}.section{max-width:1240px;margin:auto;padding:78px clamp(22px,5vw,72px)}.divider{border-top:1px solid #1f2c37}.section h2{font-size:clamp(32px,4vw,58px);line-height:1.04;letter-spacing:-.04em;margin:0 0 18px}.muted{color:#93a5b4;line-height:1.66}.thesishead{display:grid;grid-template-columns:.64fr 1.36fr;gap:50px}.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:44px}.card{background:#0f1821;border:1px solid #263541;border-radius:18px;padding:24px}.num{font-size:12px;font-weight:900;color:var(--cyan)}.card h3{font-size:19px;margin:18px 0 10px}.card p{margin:0;color:#93a5b4;line-height:1.65}.proofwrap{max-width:1240px;margin:auto;padding:0 clamp(22px,5vw,72px)}.proof{padding:76px clamp(22px,4vw,60px);background:#0b141c;border:1px solid #22303c;border-radius:34px}.proofhead{max-width:860px}.proofgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:40px}.proofgrid b{display:flex;width:34px;height:34px;align-items:center;justify-content:center;background:#163142;color:#70dcff;border-radius:10px}.proofgrid h3{margin:16px 0 10px}.partnerintro{max-width:850px}.partnergrid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:40px}.cta{margin-top:34px;border:1px solid #315064;background:linear-gradient(100deg,#102634,#0d1720);border-radius:20px;padding:24px 28px;display:flex;justify-content:space-between;align-items:center;gap:20px}.cta div{display:flex;flex-direction:column;gap:5px}.cta b{font-size:24px}.cta span{color:#8fa3b3}.cta a{background:var(--cyan);color:#061018;font-weight:900;padding:13px 16px;border-radius:12px}footer{max-width:1240px;margin:auto;padding:26px clamp(22px,5vw,72px) 42px;border-top:1px solid #26333e;display:flex;justify-content:space-between;gap:24px;color:#687b8b;font-size:12px}@media(max-width:900px){.hero{grid-template-columns:1fr;gap:38px;padding-top:62px}.machine{max-width:620px}.thesishead{grid-template-columns:1fr}.grid3,.proofgrid{grid-template-columns:1fr 1fr}.partnergrid{grid-template-columns:1fr 1fr}.navlinks span{display:none}.cta{flex-direction:column;align-items:flex-start}}@media(max-width:620px){.nav{height:64px}.navlinks a{display:none}.hero{padding-top:50px}.hero h1{font-size:64px}.grid3,.proofgrid,.partnergrid{grid-template-columns:1fr}.proofwrap{padding:0}.proof{border-radius:0;border-left:0;border-right:0}.cta a{width:100%;text-align:center}footer{flex-direction:column}}
</style></head>
<body>
<header class="nav"><a class="brand" href="https://www.wrenchrelayllc.com"><span>Wrench</span>Relay <small>LLC</small></a><div class="navlinks"><span>INDUSTRIAL INNOVATION</span><a href="https://www.wrenchrelayllc.com">WrenchRelay AI</a></div></header>
<main><section class="hero"><div><span class="kicker">PRE-PROTOTYPE • ROTARY COMPRESSION-MOLDING EQUIPMENT</span><h1>Hybrid Wheel Press</h1><h2>Keep the press pressing.</h2><p class="lead">Hybrid Wheel Press is a proposed indexed-cassette architecture that concentrates the high-force forming event at one dedicated station while loading, dwell/cooling, ejection and reset can occur elsewhere when the selected material process permits.</p><div class="badges"><span>WrenchRelay LLC</span><span>Invented by David Day</span><span>Iowa, USA</span><span>Pre-prototype</span></div><div class="actions"><a class="primary" href="mailto:dayway1980@gmail.com?subject=Hybrid%20Wheel%20Press%20Engineering%20Partnership&body=I%20am%20interested%20in%20discussing%20the%20Hybrid%20Wheel%20Press.%0A%0AOrganization%3A%0ARole%3A%0AInterest%3A%20engineering%20%2F%20prototype%20funding%20%2F%20composite%20process%20%2F%20launch%20application%0A">Discuss a build partnership</a><a class="secondary" href="#proof">See what we must prove ↓</a><button class="secondary" type="button" onclick="window.print()" style="background:transparent;cursor:pointer">Print / save brief</button></div><p class="truth"><b>Built for serious diligence, not hype.</b> Current stage is pre-prototype. No production throughput gain, physical validation, customer commitment or commercial performance result is claimed yet.</p><p class="truth"><b>Non-confidential preview:</b> detailed geometry, load paths, cassette interfaces and implementation details are reserved for controlled technical diligence and NDA discussions.</p></div>
<div class="machine"><div class="machinehead"><span>CONCEPT ARCHITECTURE</span><b>Indexed cassette loop</b></div><svg viewBox="0 0 520 520" role="img" aria-label="Conceptual circular cassette platform with one forming station and parallel process stations"><defs><linearGradient id="ring" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#dfe7ef"/><stop offset="100%" stop-color="#8d9aa8"/></linearGradient></defs><circle cx="260" cy="260" r="176" fill="none" stroke="url(#ring)" stroke-width="34"/><circle cx="260" cy="260" r="102" fill="#0f1720" stroke="#34414f" stroke-width="2"/><text x="260" y="248" text-anchor="middle" class="svgsmall">INDEXED</text><text x="260" y="278" text-anchor="middle" class="svgbig">CASSETTES</text><g class="station press"><rect x="206" y="28" width="108" height="68" rx="14"/><text x="260" y="57" text-anchor="middle">FORM</text><text x="260" y="79" text-anchor="middle">HIGH FORCE</text></g><g class="station"><rect x="385" y="115" width="108" height="64" rx="14"/><text x="439" y="143" text-anchor="middle">DWELL</text><text x="439" y="164" text-anchor="middle">/ COOL</text></g><g class="station"><rect x="388" y="340" width="108" height="64" rx="14"/><text x="442" y="368" text-anchor="middle">EJECT</text><text x="442" y="389" text-anchor="middle">/ RESET</text></g><g class="station"><rect x="28" y="340" width="108" height="64" rx="14"/><text x="82" y="368" text-anchor="middle">LOAD</text><text x="82" y="389" text-anchor="middle">/ PREP</text></g><g class="station"><rect x="27" y="115" width="108" height="64" rx="14"/><text x="81" y="143" text-anchor="middle">INDEX</text><text x="81" y="164" text-anchor="middle">/ VERIFY</text></g><path d="M260 108 A152 152 0 0 1 402 206" fill="none" stroke="#69d7ff" stroke-width="5" stroke-linecap="round"/><path d="M407 314 A152 152 0 0 1 300 407" fill="none" stroke="#69d7ff" stroke-width="5" stroke-linecap="round"/><path d="M205 404 A152 152 0 0 1 112 300" fill="none" stroke="#69d7ff" stroke-width="5" stroke-linecap="round"/></svg><p>Conceptual workflow only — not a production-machine rendering.</p></div></section>
<section class="section divider"><div class="thesishead"><span class="kicker">THE CORE IDEA</span><h2>Use the expensive high-force resource for the one job only it can do.</h2></div><div class="grid3"><article class="card"><span class="num">01</span><h3>Conventional sequence</h3><p>Load → close → form → dwell/cool → open → eject → reset. One press can remain occupied while the surrounding cycle finishes.</p></article><article class="card"><span class="num">02</span><h3>Hybrid Wheel approach</h3><p>Move removable cassettes through indexed stations so the high-force forming event is concentrated at one dedicated position while compatible surrounding operations proceed elsewhere.</p></article><article class="card"><span class="num">03</span><h3>Decision rule</h3><p>If measured part quality, safety, repeatability, maintainability and economics do not justify the added cassette and indexing complexity, the concept does not advance.</p></article></div></section>
<section class="section divider"><div class="thesishead"><span class="kicker">WHO THIS IS FOR</span><h2>We are looking for builders, process experts and launch partners who can make the concept harder to fool.</h2></div><div class="grid3"><article class="card"><span class="num">ENGINEERING</span><h3>Machine builder / integrator</h3><p>Help size the reaction structure, locking, indexing, hydraulics, controls and safeguarding — then price a representative prototype honestly.</p><p><a class="secondary" href="mailto:dayway1980@gmail.com?subject=Hybrid%20Wheel%20Press%20-%20Engineering%20Partner">Engineering discussion →</a></p></article><article class="card"><span class="num">PROCESS</span><h3>Composite molding expert</h3><p>Define the material, tooling, thermal and dwell constraints that determine whether operations can actually separate from the high-force station.</p><p><a class="secondary" href="mailto:dayway1980@gmail.com?subject=Hybrid%20Wheel%20Press%20-%20Composite%20Process%20Partner">Process discussion →</a></p></article><article class="card"><span class="num">PILOT</span><h3>Strategic prototype / launch partner</h3><p>Bring a suitable first application, purchasing criteria and a real-world baseline so the prototype answers commercial questions as well as engineering ones.</p><p><a class="secondary" href="mailto:dayway1980@gmail.com?subject=Hybrid%20Wheel%20Press%20-%20Prototype%20or%20Launch%20Partner">Pilot discussion →</a></p></article></div></section>
<div class="proofwrap"><section class="proof" id="proof"><div class="proofhead"><span class="kicker">PLANNED ACCEPTANCE EVIDENCE — TESTS NOT YET PERFORMED</span><h2>Build the evidence before the full machine.</h2><p class="muted">The first development program is designed to falsify the hardest assumptions quickly and economically.</p></div><div class="proofgrid"><article class="card"><b>A</b><h3>Load path</h3><p>Representative high-force reaction structure, cassette restraint, stiffness and deflection.</p></article><article class="card"><b>B</b><h3>Lock + index</h3><p>Mechanical lock/unlock, repeatable registration, settle time and fatigue behavior.</p></article><article class="card"><b>C</b><h3>Thermal + process</h3><p>Dwell/cooling behavior, tooling interface and representative composite-part quality.</p></article><article class="card"><b>D</b><h3>Controls + safety</h3><p>PLC state machine, permissives, interlocks, fault recovery and safe indexed movement.</p></article><article class="card"><b>E</b><h3>Cycle timeline</h3><p>Instrumented timing against a defined conventional-process baseline.</p></article><article class="card"><b>F</b><h3>Economics</h3><p>Real fabrication, maintenance and operating costs before any scale-up claim.</p></article></div></section></div>
<section class="section"><div class="partnerintro"><span class="kicker">THE ASK</span><h2>Help us turn one strong manufacturing thesis into measured physical evidence.</h2><p class="muted">Hybrid Wheel Press is being advanced as a WrenchRelay LLC industrial equipment initiative. The immediate goal is not a production-machine promise; it is a scoped, instrumented prototype program with clear acceptance tests and go/no-go gates.</p></div><div class="partnergrid"><article class="card"><h3>Equipment engineering</h3><p>Mechanical, structural, hydraulic, controls and machinery-safety design.</p></article><article class="card"><h3>Composite process</h3><p>Material, tooling, thermal cycle, dwell requirements and part validation.</p></article><article class="card"><h3>Prototype funding</h3><p>Representative build, instrumentation, test execution and engineering diligence.</p></article><article class="card"><h3>Launch application</h3><p>A suitable first part, pilot environment, purchasing criteria and service pathway.</p></article></div><div class="cta"><div><b>Hybrid Wheel Press</b><span>WrenchRelay LLC • Invented by David Day • Iowa, USA</span></div><a href="mailto:dayway1980@gmail.com?subject=Hybrid%20Wheel%20Press%20Development%20Partnership&body=I%20would%20like%20to%20discuss%20a%20confidential%20Hybrid%20Wheel%20Press%20development%20conversation.%0A%0AOrganization%3A%0ARole%3A%0AWhat%20we%20could%20contribute%3A%0A">Start a confidential discussion →</a></div><section class="section divider"><div class="partnerintro"><span class="kicker">TECHNICAL DILIGENCE FAQ</span><h2>The questions a serious partner should ask first.</h2></div><div class="grid3"><article class="card"><h3>Is it proven?</h3><p>No. It is deliberately presented as pre-prototype. The next phase exists to prove or kill the key assumptions with instrumentation and representative hardware.</p></article><article class="card"><h3>Where could it fail?</h3><p>Load-path stiffness, cassette restraint, indexing repeatability, thermal/dwell requirements, fault recovery, maintainability and the cost of added handling complexity.</p></article><article class="card"><h3>What makes a useful first meeting?</h3><p>Bring one suitable part/process, the conventional cycle baseline, the material constraints and the engineering capabilities you can contribute. We will focus on falsifiable next steps.</p></article></div></section>
</section></main>
<footer><span>Hybrid Wheel Press • A WrenchRelay LLC industrial equipment initiative</span><span>Pre-prototype • Non-confidential preview • Former working name: Giant Wheel</span></footer></body></html>
GWHTML

printf "%s" "$WR_VOICE_APP_JS_B64" | base64 -d > /tmp/voice/app.js; cat >> /tmp/voice/app.js <<WR_VOICE_AUDIO_PATCH
/* WrenchRelay LLC: reversible browser speech-output patch. Does not alter
   authentication, work-order approvals, API requests, payments, or storage. */
(function () {
  "use strict";
  if (typeof window === "undefined" || typeof beginVoiceSession !== "function" ||
      typeof render !== "function" || typeof startRecognizer !== "function" ||
      typeof stopVoiceSession !== "function") return;
  const originalBegin = beginVoiceSession;
  const originalStart = startRecognizer;
  const originalStop = stopVoiceSession;
  const originalRender = render;
  const originalSetup = setupVoiceSessionUI;
  function speakMaintenanceReply(message) {
    if (!voiceSession.armed || voiceSession.muted) return false;
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) return false;
    const text = String(message || "").trim();
    if (!text) return false;
    const utterance = new window.SpeechSynthesisUtterance(text.slice(0, 700));
    utterance.lang = String(locale).toLowerCase().startsWith("es") ? "es-ES" : "en-US";
    utterance.rate = 1.0;
    utterance.onend = () => {
      if (voiceSession.armed && !voiceSession.muted) scheduleVoiceRestart(250);
    };
    utterance.onerror = () => {
      if (voiceSession.armed && !voiceSession.muted) scheduleVoiceRestart(250);
    };
    try {
      voiceSession.recognizer?.abort();
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
      return true;
    } catch (error) {
      console.warn("WrenchRelay speech output unavailable", error);
      if (voiceSession.armed && !voiceSession.muted) scheduleVoiceRestart(250);
      return false;
    }
  }
  startRecognizer = function (...args) {
    if (voiceSession.assistantSpeaking) return;
    return originalStart.apply(this, args);
  };
  beginVoiceSession = async function (...args) {
    const wasArmed = voiceSession.armed;
    const result = await originalBegin.apply(this, args);
    if (!wasArmed && voiceSession.armed) {
      speakMaintenanceReply(String(locale).toLowerCase().startsWith("es")
        ? "Hola. Soy WrenchRelay. Cuéntame qué sucedió con el equipo."
        : "WrenchRelay ready. Tell me what happened with the equipment.");
    }
    return result;
  };
  render = function (workOrder, ...args) {
    const result = originalRender.call(this, workOrder, ...args);
    if (voiceSession.armed && !voiceSession.muted && workOrder?.next_question) {
      speakMaintenanceReply(workOrder.next_question);
    }
    return result;
  };
  stopVoiceSession = function (...args) {
    try { window.speechSynthesis?.cancel(); } catch (_) {}
    return originalStop.apply(this, args);
  };
  setupVoiceSessionUI = function (...args) {
    const result = originalSetup.apply(this, args);
    const mainButton = document.getElementById("voice");
    if (mainButton) mainButton.onclick = beginVoiceSession;
    const controls = document.getElementById("wrVoiceSecondary");
    if (controls && !document.getElementById("wrVoiceRepeat")) {
      const repeat = document.createElement("button");
      repeat.id = "wrVoiceRepeat";
      repeat.type = "button";
      repeat.textContent = "Repeat reply";
      repeat.style.cssText = "flex:1;min-height:42px";
      repeat.onclick = () => speakMaintenanceReply(
        current?.next_question ||
        (String(locale).toLowerCase().startsWith("es")
          ? "Cuéntame qué sucedió con el equipo."
          : "Tell me what happened with the equipment.")
      );
      controls.appendChild(repeat);
    }
    return result;
  };
})();
WR_VOICE_AUDIO_PATCH
cat >> /tmp/voice/app.js <<WR_VOICE_BUTTON_BINDING_PATCH
/* WrenchRelay: existing HTML voice control buttons must be bound. */
(function () {
  "use strict";
  const previousSetup = setupVoiceSessionUI;
  const previousStop = stopVoiceSession;
  setupVoiceSessionUI = function (...args) {
    const result = previousSetup.apply(this, args);
    const mute = document.getElementById("wrVoiceMute");
    const end = document.getElementById("wrVoiceEnd");
    if (mute) {
      mute.type = "button";
      mute.onclick = toggleVoiceMute;
    }
    if (end) {
      end.type = "button";
      end.onclick = () => stopVoiceSession();
    }
    return result;
  };
  stopVoiceSession = function (...args) {
    const result = previousStop.apply(this, args);
    voiceSession.assistantSpeaking = false;
    voiceSession.lastAssistantText = "";
    return result;
  };
})();
WR_VOICE_BUTTON_BINDING_PATCH
cat >> /tmp/voice/app.js <<WR_VOICE_MUTE_PATCH
/* WrenchRelay browser voice safety: Mute also silences playback. */
(function () {
  "use strict";
  const previousToggleVoiceMute = toggleVoiceMute;
  toggleVoiceMute = function (...args) {
    const wasMuted = voiceSession.muted;
    const result = previousToggleVoiceMute.apply(this, args);
    if (!wasMuted && voiceSession.muted) {
      try { window.speechSynthesis?.cancel(); } catch (_) {}
      voiceSession.assistantSpeaking = false;
      voiceSession.lastAssistantText = "";
      clearTimeout(voiceSession.restartTimer);
      setVoiceState("muted");
    }
    return result;
  };
  const previousSetupVoiceUI = setupVoiceSessionUI;
  setupVoiceSessionUI = function (...args) {
    const result = previousSetupVoiceUI.apply(this, args);
    const mute = document.getElementById("wrVoiceMute");
    if (mute) mute.onclick = () => toggleVoiceMute();
    return result;
  };
})();
WR_VOICE_MUTE_PATCH

cat >> /tmp/voice/app.js <<WR_BRAND_PATCH
/* WrenchRelay LLC branding correction; limited to the website footer. */
(function () {
  "use strict";
  function correctOperator() {
    var footer = document.querySelector("footer");
    if (!footer) return;
    if (footer.textContent && footer.textContent.indexOf("AzVa Enterprises LLC") >= 0) {
      footer.textContent = footer.textContent.replace("AzVa Enterprises LLC", "WrenchRelay LLC");
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", correctOperator);
  } else {
    correctOperator();
  }
  var footer = document.querySelector("footer");
  if (footer) {
    new MutationObserver(correctOperator).observe(footer, {childList:true, subtree:true, characterData:true});
  }
  function showProductLinks() {
    var nav = document.querySelector("header nav");
    if (!nav) return;
    var links = [
      {href:"/industrial",text:"Industrial"},
      {href:"/automotive",text:"Automotive"}
    ];
    links.forEach(function (link) {
      if (Array.prototype.some.call(nav.querySelectorAll("a"), function (el) { return el.getAttribute("href") === link.href; })) return;
      var a = document.createElement("a");
      a.href = link.href;
      a.textContent = link.text;
      a.style.cssText = "font-weight:700;white-space:nowrap";
      nav.insertBefore(a, nav.querySelector("a[href*=terms]") || nav.firstChild);
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", showProductLinks);
  } else {
    showProductLinks();
  }
})();
WR_BRAND_PATCH

mkdir -p /tmp/public/automotive
cat > /tmp/public/automotive/index.html <<WR_AUTOMOTIVE_HTML
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WrenchRelay Automotive | Shop Pilot</title>
<meta name="description" content="WrenchRelay Automotive is preparing an automotive missed-call intake and service follow-up pilot. Request participation and product updates.">
<style>body{margin:0;background:#0b1520;color:#ecf6ff;font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}header,main,footer{max-width:840px;margin:auto;padding:28px 22px}header{border-bottom:1px solid #263e50;font-weight:750}.eyebrow{letter-spacing:.16em;text-transform:uppercase;color:#7ed7f8;font-size:12px;font-weight:800}h1{font-size:clamp(2.6rem,7vw,4.5rem);line-height:1.07;letter-spacing:-.04em;margin:22px 0}p{color:#b9c8d7;max-width:680px}.panel{background:#132434;padding:24px;border-radius:18px;border:1px solid #29475e;margin:30px 0}.cta{display:inline-block;padding:13px 20px;border-radius:10px;background:#8cdefc;color:#071522;font-weight:800;text-decoration:none}.secondary{display:inline-block;margin-left:14px;color:#9ad5ef}footer{font-size:13px;color:#8fa5b9;border-top:1px solid #263e50}a{color:#a6e6ff}</style>
</head>
<body>
<header><a href="/" style="text-decoration:none;color:inherit">WrenchRelay LLC</a></header>
<main>
<p class="eyebrow">Automotive shops • early engineering pilot</p>
<h1>Catch more service opportunities when the shop cannot answer.</h1>
<p>WrenchRelay Automotive is being developed to support missed-call intake, customer follow-up and clearer service histories. The live automated phone-answering and payment workflows are <strong>not yet commissioned</strong>.</p>
<section class="panel"><h2>Request a pilot conversation</h2>
<p>Tell us your shop name, location, and what missed calls cost your operation. This is a no-obligation interest request, not an active subscription.</p>
<a class="cta" href="mailto:dayway1980@gmail.com?subject=WrenchRelay%20Automotive%20Pilot%20Inquiry&amp;body=Shop%20name%3A%0ALocation%3A%0AContact%3A%0AMissed-call%20needs%3A%0A">Email your interest</a>
<a class="secondary" href="/">Industrial WrenchRelay</a>
</section>
<p>No validated call-routing results, unattended customer acquisition, integrations, or automated billing are claimed for the Automotive pilot.</p>
</main>
<footer>WrenchRelay LLC • Automotive pilot information • <a href="/privacy">Privacy</a></footer>
</body></html>
WR_AUTOMOTIVE_HTML
cat >> /tmp/voice/app.js <<WR_BILLING_READINESS_PATCH
/* WrenchRelay production: fail-closed checkout control until the API enables Stripe. */
(function () {
  "use strict";
  function checkoutReadiness() {
    var button = document.getElementById("checkout");
    if (!button) return;
    button.dataset.billingReady = "no";
    button.disabled = true;
    button.setAttribute("aria-disabled", "true");
    button.title = "Checking secure billing readiness";
    button.addEventListener("click", function (event) {
      if (button.dataset.billingReady !== "yes") {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    }, true);
    var notice = document.createElement("p");
    notice.id = "wrBillingReadinessNotice";
    notice.setAttribute("role", "status");
    notice.style.cssText = "font-size:0.85rem;margin:0.8rem 0;color:inherit";
    button.parentNode.appendChild(notice);
    notice.textContent = "Checking secure billing readiness...";
    fetch("/api/config", {cache: "no-store", credentials: "same-origin"})
      .then(function (response) {
        if (!response.ok) throw new Error("Billing readiness check unavailable");
        return response.json();
      })
      .then(function (config) {
        if (config && config.stripe_enabled === true && config.billing_commissioned === true) {
          button.dataset.billingReady = "yes";
          button.disabled = false;
          button.removeAttribute("aria-disabled");
          button.title = "Open secure checkout";
          notice.textContent = "";
        } else {
          button.title = "Billing is temporarily unavailable";
          notice.textContent = "Online subscriptions are temporarily unavailable. Contact support@wrenchrelay.app for assistance.";
        }
      })
      .catch(function () {
        button.title = "Billing verification unavailable";
        notice.textContent = "Online subscriptions cannot be verified right now. Contact support@wrenchrelay.app for assistance.";
      });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", checkoutReadiness, {once: true});
  } else {
    checkoutReadiness();
  }
})();
WR_BILLING_READINESS_PATCH

# Materialize the reviewed search-visibility files before Caddy starts.
mkdir -p /tmp/public/search-visibility || exit 1
cat > /tmp/public/search-visibility/industrial.html <<'"'"'WR_SEARCH_STATIC_0_20261028'"'"' || exit 1
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Industrial Maintenance Documentation &amp; Handoffs | WrenchRelay</title>
<meta name="description" content="Explore the WrenchRelay Industrial pilot for technician notes, maintenance work-order drafts and shift handoffs, with human review before action.">
<link rel="canonical" href="https://www.wrenchrelayllc.com/industrial">
<style>
body{margin:0;background:#0b1520;color:#ecf6ff;font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}header,main,footer{max-width:840px;margin:auto;padding:28px 22px}header{border-bottom:1px solid #263e50;display:flex;justify-content:space-between;align-items:center;gap:20px}nav{display:flex;gap:20px;flex-wrap:wrap}.brand{font-weight:750;text-decoration:none;color:inherit}.eyebrow{letter-spacing:.16em;text-transform:uppercase;color:#7ed7f8;font-size:12px;font-weight:800}h1{font-size:clamp(2.6rem,7vw,4.5rem);line-height:1.07;letter-spacing:-.04em;margin:22px 0}h2{line-height:1.2}p,li{color:#b9c8d7}.panel{background:#132434;padding:24px;border-radius:18px;border:1px solid #29475e;margin:30px 0}.cta{display:inline-block;padding:13px 20px;border-radius:10px;background:#8cdefc;color:#071522;font-weight:800;text-decoration:none}.secondary{display:inline-block;margin:14px 0 0;color:#9ad5ef}a{color:#a6e6ff}a:focus-visible{outline:3px solid #8cdefc;outline-offset:5px}footer{font-size:13px;color:#8fa5b9;border-top:1px solid #263e50}@media(min-width:620px){.secondary{margin:0 0 0 18px}}@media(max-width:480px){header{align-items:flex-start;flex-direction:column}}
</style>
</head>
<body>
<header><a class="brand" href="/">WrenchRelay LLC</a><nav aria-label="Main navigation"><a href="/automotive">Automotive</a><a href="/privacy">Privacy</a></nav></header>
<main>
<p class="eyebrow">Industrial maintenance • engineering pilot</p>
<h1>Keep the knowledge behind the repair.</h1>
<p>Technician conversations contain details the next shift needs: what happened, what was checked, what changed and how the result was verified. WrenchRelay Industrial is being developed to turn those notes into clearer maintenance records and handoffs.</p>
<section class="panel" aria-labelledby="workflow-title">
<h2 id="workflow-title">From technician notes to a reviewable record</h2>
<ul><li>Capture equipment observations, fault codes, measurements and repair context in voice or text.</li><li>Organize work-order drafts, troubleshooting context and shift handoffs.</li><li>Keep observed facts, suggested checks and unresolved questions clear.</li><li>Review and approve the record before action or entry into an official maintenance system.</li></ul>
</section>
<section aria-labelledby="review-title"><h2 id="review-title">Your team stays responsible for the work</h2><p>Follow site procedures, lockout/tagout, OEM guidance and qualified-person requirements. Every output needs human verification. CMMS integration and production acceptance depend on the specific pilot; discuss your workflow with us.</p></section>
<section class="panel" aria-labelledby="pilot-title"><h2 id="pilot-title">Discuss an Industrial pilot</h2><p>Tell us about your equipment, maintenance records and shift-handoff challenges. We can discuss the workflow and the evidence needed to evaluate a pilot.</p><a class="cta" href="mailto:dayway1980@gmail.com?subject=WrenchRelay%20Industrial%20Pilot%20Inquiry&amp;body=Company%3A%0AEquipment%20or%20process%3A%0AMaintenance%20documentation%20needs%3A%0AContact%3A%0A">Request a pilot conversation</a><a class="secondary" href="/">Open maintenance workspace</a></section>
</main>
<footer>WrenchRelay LLC • Industrial pilot information • <a href="/automotive">Automotive</a> • <a href="/privacy">Privacy</a></footer>
</body>
</html>
WR_SEARCH_STATIC_0_20261028
cat > /tmp/public/search-visibility/automotive.html <<'"'"'WR_SEARCH_STATIC_1_20261028'"'"' || exit 1
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WrenchRelay Automotive | Shop Pilot</title>
<meta name="description" content="WrenchRelay Automotive is preparing an automotive missed-call intake and service follow-up pilot. Request participation and product updates.">
<style>body{margin:0;background:#0b1520;color:#ecf6ff;font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}header,main,footer{max-width:840px;margin:auto;padding:28px 22px}header{border-bottom:1px solid #263e50;font-weight:750}.eyebrow{letter-spacing:.16em;text-transform:uppercase;color:#7ed7f8;font-size:12px;font-weight:800}h1{font-size:clamp(2.6rem,7vw,4.5rem);line-height:1.07;letter-spacing:-.04em;margin:22px 0}p{color:#b9c8d7;max-width:680px}.panel{background:#132434;padding:24px;border-radius:18px;border:1px solid #29475e;margin:30px 0}.cta{display:inline-block;padding:13px 20px;border-radius:10px;background:#8cdefc;color:#071522;font-weight:800;text-decoration:none}.secondary{display:inline-block;margin-left:14px;color:#9ad5ef}footer{font-size:13px;color:#8fa5b9;border-top:1px solid #263e50}a{color:#a6e6ff}</style>
<link rel="canonical" href="https://www.wrenchrelayllc.com/automotive">
</head>
<body>
<header><a href="/" style="text-decoration:none;color:inherit">WrenchRelay LLC</a></header>
<main>
<p class="eyebrow">Automotive shops • early engineering pilot</p>
<h1>Catch more service opportunities when the shop cannot answer.</h1>
<p>WrenchRelay Automotive is being developed to support missed-call intake, customer follow-up and clearer service histories. The live automated phone-answering and payment workflows are <strong>not yet commissioned</strong>.</p>
<section class="panel"><h2>Request a pilot conversation</h2>
<p>Tell us your shop name, location, and what missed calls cost your operation. This is a no-obligation interest request, not an active subscription.</p>
<a class="cta" href="mailto:dayway1980@gmail.com?subject=WrenchRelay%20Automotive%20Pilot%20Inquiry&amp;body=Shop%20name%3A%0ALocation%3A%0AContact%3A%0AMissed-call%20needs%3A%0A">Email your interest</a>
<a class="secondary" href="/industrial">Industrial WrenchRelay</a>
</section>
<p>No validated call-routing results, unattended customer acquisition, integrations, or automated billing are claimed for the Automotive pilot.</p>
</main>
<footer>WrenchRelay LLC • Automotive pilot information • <a href="/privacy">Privacy</a></footer>
</body></html>
WR_SEARCH_STATIC_1_20261028
cat > /tmp/public/search-visibility/robots.txt <<'"'"'WR_SEARCH_STATIC_2_20261028'"'"' || exit 1
User-agent: *
Allow: /
Sitemap: https://www.wrenchrelayllc.com/sitemap.xml
WR_SEARCH_STATIC_2_20261028
cat > /tmp/public/search-visibility/sitemap.xml <<'"'"'WR_SEARCH_STATIC_3_20261028'"'"' || exit 1
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.wrenchrelayllc.com/</loc></url>
  <url><loc>https://www.wrenchrelayllc.com/industrial</loc></url>
  <url><loc>https://www.wrenchrelayllc.com/automotive</loc></url>
  <url><loc>https://www.wrenchrelayllc.com/hybrid-wheel-press</loc></url>
</urlset>
WR_SEARCH_STATIC_3_20261028
cat > /tmp/Caddyfile <<"CADDY"
{
  admin off
}
:8000 {
  route {
    # Search-visibility repair: only the two requested public hosts.
    @llcHome {
      host wrenchrelayllc.com www.wrenchrelayllc.com
      path /
    }
    header @llcHome Link "<https://www.wrenchrelayllc.com/>; rel=\"canonical\""
    @llcRobots {
      host wrenchrelayllc.com www.wrenchrelayllc.com
      path /robots.txt
    }
    handle @llcRobots {
      header Content-Type "text/plain; charset=utf-8"
      header Cache-Control "public, max-age=300"
      root * /tmp/public/search-visibility
      file_server
    }
    @llcSitemap {
      host wrenchrelayllc.com www.wrenchrelayllc.com
      path /sitemap.xml
    }
    handle @llcSitemap {
      header Content-Type "application/xml; charset=utf-8"
      header Cache-Control "public, max-age=300"
      root * /tmp/public/search-visibility
      file_server
    }
    @llcIndustrial {
      host wrenchrelayllc.com www.wrenchrelayllc.com
      path /industrial /industrial/
    }
    handle @llcIndustrial {
      header Content-Type "text/html; charset=utf-8"
      header Cache-Control "no-store"
      root * /tmp/public/search-visibility
      rewrite * /industrial.html
      file_server
    }
    @llcAutomotive {
      host wrenchrelayllc.com www.wrenchrelayllc.com
      path /automotive /automotive/
    }
    handle @llcAutomotive {
      header Content-Type "text/html; charset=utf-8"
      header Cache-Control "no-store"
      root * /tmp/public/search-visibility
      rewrite * /automotive.html
      file_server
    }
    handle /health {
      respond "voice-v6-health" 200
    }
    handle /voice-version {
      respond "voice-session-v8-play-ready" 200
    }
    handle /robots.txt {
      header Content-Type "text/plain; charset=utf-8"
      respond "User-agent: *\nAllow: /\nSitemap: https://www.wrenchrelayllc.com/sitemap.xml\n" 200
    }
    handle /favicon.ico {
      respond "" 204
    }
    handle /delete-account {
      header Content-Type "text/html; charset=utf-8"
      header Cache-Control "no-store"
      root * /tmp/public/delete-account
      rewrite * /index.html
      file_server
    }
    handle /automotive {
      header Content-Type "text/html; charset=utf-8"
      header Cache-Control "no-store"
      root * /tmp/public/automotive
      rewrite * /index.html
      file_server
    }
    handle /privacy-android {
      header Content-Type "text/html; charset=utf-8"
      header Cache-Control "no-store"
      root * /tmp/public/privacy-android
      rewrite * /index.html
      file_server
    }
    handle /sitemap.xml {
      header Content-Type "application/xml; charset=utf-8"
      respond "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n  <url><loc>https://www.wrenchrelayllc.com/</loc></url>\n  <url><loc>https://www.wrenchrelayllc.com/hybrid-wheel-press</loc></url>\n</urlset>\n" 200
    }
    handle /press {
      redir /hybrid-wheel-press 308
    }
    handle /giant-wheel {
      redir /hybrid-wheel-press 308
    }
    handle /giant-wheel/* {
      redir /hybrid-wheel-press 308
    }
    handle /hybrid-wheel-press* {
      header Content-Type "text/html; charset=utf-8"
      header Cache-Control "public, max-age=300"
      root * /tmp/public/giant-wheel
      rewrite * /index.html
      file_server
    }
    handle /app.js {
      header Content-Type "application/javascript; charset=utf-8"
      header Cache-Control "no-store, max-age=0"
      root * /tmp/voice
      file_server
    }
    @legacywww host www.wrenchrelay.com
    handle @legacywww {
      redir https://wrenchrelayllc.com{uri} 308
    }
    handle {
      @api host api.wrenchrelay.com api.wrenchrelay.app
      header @api X-Robots-Tag "noindex, nofollow"
      @owned host wrenchrelay.app www.wrenchrelay.app industrial.wrenchrelay.com automotive.wrenchrelay.com industrial.wrenchrelay.app automotive.wrenchrelay.app cutover.wrenchrelay.com cutover2.wrenchrelay.com verify.wrenchrelay.com verify2.wrenchrelay.com railway-origin.wrenchrelay.com landing.wrenchrelay.com
      redir @owned https://wrenchrelayllc.com{uri} 308
      @stripeLegacyWebhook path /api/billing/webhook
      rewrite @stripeLegacyWebhook /api/stripe/webhook
      @authpaths path /login /signup /register /industrial
      rewrite @authpaths /
      reverse_proxy wrenchrelay-production.railway.internal:8080 wrenchrelay-recovery.railway.internal:8080 {
        lb_policy first
        health_uri /api/health
        health_interval 10s
        health_timeout 8s
        fail_duration 30s
        max_fails 2
        lb_try_duration 5s
        lb_try_interval 250ms
      }
    }
  }
}
CADDY
printf %s "$WR_SAVE_GUARDED_APP_JS_00$WR_SAVE_GUARDED_APP_JS_01" | base64 -d > /tmp/voice/app.js || exit 1; exec caddy run --config /tmp/Caddyfile --adapter caddyfile'
