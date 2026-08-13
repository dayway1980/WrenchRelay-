import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { api, apiMessage } from "@/lib/api";

const statuses = ["All", "Draft", "InReview", "Approved", "Submitted", "Completed"];
export default function ProductionWorkOrdersPage() {
  const { session } = useAuth(); const orgId = session?.organizations?.[0]?.id; const [items, setItems] = useState([]); const [filter, setFilter] = useState("All"); const [search, setSearch] = useState(""); const [error, setError] = useState("");
  useEffect(() => { if (orgId) api.get("/work-orders", { params: { organization_id: orgId } }).then((r) => setItems(r.data)).catch((e) => setError(apiMessage(e))); }, [orgId]);
  const visible = items.filter((wo) => (filter === "All" || wo.status === filter) && `${wo.work_order_number} ${wo.title} ${wo.problem || ""}`.toLowerCase().includes(search.toLowerCase()));
  return <AppShell title="Work Orders"><div className="toolbar"><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search work orders" data-testid="production-wo-search" /><Link to="/work-orders/new" className="button button-orange">New Work Order</Link></div><div className="status-tabs">{statuses.map((status) => <button key={status} onClick={() => setFilter(status)} className={filter === status ? "active" : ""} data-testid={`wo-filter-${status}`}>{status}</button>)}</div>{error && <p className="form-error">{error}</p>}<div className="table-panel">{visible.map((wo) => <Link key={wo.id} to={`/work-orders/${wo.id}?organization_id=${orgId}`} className="table-row table-link"><strong>{wo.work_order_number}</strong><span>{wo.asset_name || wo.asset_id || "Unassigned asset"}</span><span>{wo.status}</span><span>{wo.maintenance_type || "\u2014"}</span></Link>)}{!visible.length && <p className="empty-state">No work orders match this view.</p>}</div></AppShell>;
}
