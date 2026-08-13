import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AppShell from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { api, apiMessage } from "@/lib/api";

export default function AssetDetailPage() {
  const { assetId } = useParams(); const { session } = useAuth(); const orgId = session?.organizations?.[0]?.id; const [data, setData] = useState(null); const [error, setError] = useState("");
  useEffect(() => { if (orgId) api.get(`/assets/${assetId}`, { params: { organization_id: orgId } }).then((r) => setData(r.data)).catch((e) => setError(apiMessage(e))); }, [assetId, orgId]);
  if (!data) return <AppShell title="Asset"><p className="loading-state">Loading asset\u2026</p>{error && <p className="form-error">{error}</p>}</AppShell>;
  const { asset, work_orders: workOrders } = data; const similar = workOrders.reduce((counts, item) => ({ ...counts, [item.maintenance_type || "Unspecified"]: (counts[item.maintenance_type || "Unspecified"] || 0) + 1 }), {});
  return <AppShell title={asset.asset_name}><section className="settings-section"><p className="eyebrow">{asset.asset_number}</p><h2>{asset.asset_name}</h2><p>{asset.facility || asset.site || "Facility not provided"} \u00b7 {asset.area || asset.location || "Location not provided"}</p><p>{asset.manufacturer || "Manufacturer not provided"} \u00b7 {asset.model || "Model not provided"} \u00b7 {asset.serial || "Serial not provided"}</p><span className="status-badge">{asset.criticality} criticality</span></section><section className="settings-section"><h2>Similar issues</h2>{Object.entries(similar).map(([type, count]) => <p key={type}>{type}: {count} related work orders</p>)}</section><section className="settings-section"><h2>Work order history</h2>{workOrders.map((wo) => <Link className="table-row table-link" key={wo.id} to={`/work-orders/${wo.id}?organization_id=${orgId}`}><strong>{wo.work_order_number}</strong><span>{wo.title}</span><span>{wo.status}</span></Link>)}</section></AppShell>;
}
