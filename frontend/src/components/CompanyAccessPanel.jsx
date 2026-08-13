import { useEffect, useState } from "react";
import { CreditCard, Users } from "lucide-react";
import { api, apiMessage } from "@/lib/api";

export default function CompanyAccessPanel({ organizationId }) {
  const [data, setData] = useState({ active_members: 0, seat_count: 1, plan: "Starter", billing_status: "Test mode" });
  const [message, setMessage] = useState("");
  useEffect(() => { if (organizationId) api.get(`/auth/organizations/${organizationId}/seats`).then((response) => setData(response.data)); }, [organizationId]);
  const save = async () => { try { const response = await api.put(`/auth/organizations/${organizationId}/seats`, data); setData({ ...data, ...response.data }); setMessage("Seat allocation saved for this organization."); } catch (requestError) { setMessage(apiMessage(requestError)); } };
  return <section className="settings-section company-access-panel" data-testid="company-access-panel"><p className="eyebrow">Company access</p><h2>Seats & licensing</h2><div className="seat-stat"><Users size={20} /><strong data-testid="active-technician-count">{data.active_members}</strong><span>active team members</span></div><label>Plan<select value={data.plan} onChange={(event) => setData({ ...data, plan: event.target.value })} data-testid="subscription-plan-select"><option>Starter</option><option>Professional</option><option>Enterprise</option></select></label><label>Technician seats<input type="number" min="1" value={data.seat_count} onChange={(event) => setData({ ...data, seat_count: Number(event.target.value) })} data-testid="seat-count-input" /></label><button className="button button-orange" onClick={save} data-testid="save-seat-count-button"><CreditCard size={16} />Save test subscription</button>{message && <p className="status-note" data-testid="seat-status-message">{message}</p>}</section>;
}
