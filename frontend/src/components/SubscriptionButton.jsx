import { useState } from "react";
import { Button } from "@/components/ui/button";
import { api, apiMessage } from "@/lib/api";

export default function SubscriptionButton({ planId = "pro_monthly", label = "Upgrade" }) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/billing/create-checkout", { plan_id: planId });
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      alert(apiMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button onClick={handleClick} disabled={loading}>
      {loading ? "Redirecting…" : label}
    </Button>
  );
}
