import { useLocation } from "react-router-dom";

const CONTENT = {
  "/privacy": { title: "Privacy Policy", body: "WrenchRelay collects only the data necessary to operate the service. We do not sell personal information. Data is stored securely in SOC-2 compliant infrastructure. For questions contact privacy@wrenchrelay.com." },
  "/terms": { title: "Terms of Service", body: "By using WrenchRelay you agree to these terms. The service is provided as-is. We reserve the right to modify or discontinue features with notice. Abuse of the platform may result in account termination." },
  "/support": { title: "Support", body: "Email support@wrenchrelay.com or use the in-app chat. We aim to respond within 24 hours on business days." },
  "/data-deletion": { title: "Data Deletion", body: "To request deletion of your data, email privacy@wrenchrelay.com with your account email. We will process requests within 30 days as required by applicable law." },
};

export default function LegalPage() {
  const { pathname } = useLocation();
  const page = CONTENT[pathname] || { title: "Not Found", body: "" };
  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <h1 className="text-3xl font-bold mb-6">{page.title}</h1>
      <p className="text-muted-foreground leading-relaxed">{page.body}</p>
    </div>
  );
}
