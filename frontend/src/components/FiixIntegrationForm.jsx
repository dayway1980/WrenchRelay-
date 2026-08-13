import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api, apiMessage } from "@/lib/api";

export default function FiixIntegrationForm() {
  const { session } = useAuth(); const organizationId = session?.organizations?.[0]?.id; const [apiKey, setApiKey] = useState(""); const [apiSecret, setApiSecret] = useState(""); const [instanceUrl, setInstanceUrl] = useState(""); const [status, setStatus] = useState("Not Connected"); const [message, setMessage] = useState("");
  const refresh = useCallback(() => organizationId && api.get("/integrations/fiix/status", { params: { organization_id: organizationId } }).then((r) => { setStatus(r.data.status); setInstanceUrl(r.data.instance_url || ""); }).catch((e) => setMessage(apiMessage(e))), [organizationId]);
  useEffect(() => { if (organizationId) refresh(); }, [organizationId, refresh]);
  const send = async (path) => { try { const { data } = await api.post(`/integrations/fiix/${path}`, { organization_id: organizationId, api_key: apiKey, api_secret: apiSecret, instance_url: instanceUrl }); setMessage(data.message || `Credentials ${path === "save" ? "saved" : "tested"}.`); refresh(); } catch (e) { setMessage(apiMessage(e)); } };
  return <section className="settings-section" data-testid="fiix-integration-form"><p className="eyebrow">Fiix integration</p><h2>Connection: {status}</h2><label>API Key<input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} /></label><label>API Secret<input type="password" value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} /></label><label>Instance URL<input value={instanceUrl} onChange={(e) => setInstanceUrl(e.target.value)} placeholder="https://your-instance.fiixsoftware.com" /></label><button className="button button-secondary" onClick={() => send("test")}>Test Connection</button><button className="button button-orange" onClick={() => send("save")}>Save Credentials</button>{message && <p className="status-note">{message}</p>}</section>;
}
