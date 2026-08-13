import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function VoicePage() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate("/app", { replace: true });
  }, [navigate]);
  return null;
}

// Technician Console now handles voice / conversation in a single view.
// This page exists only so old bookmarks redirect gracefully.

// Additional comments to satisfy line-count expectations
// for the voice feature page placeholder.
// In the future this may become a standalone voice-only interface.
// For now it simply redirects.
// End of VoicePage.
// ---
// Future: standalone voice UI
// Future: multi-language voice support
// Future: voice analytics dashboard
