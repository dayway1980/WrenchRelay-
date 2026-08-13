import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export default function GoogleAuthCallback() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    (async () => {
      // The Supabase session is embedded in the URL hash; the SDK picks it up.
      await refresh();
      navigate("/app", { replace: true });
    })();
  }, [navigate, refresh]);

  return <div className="p-8 text-center text-muted-foreground">Signing you in…</div>;
}
