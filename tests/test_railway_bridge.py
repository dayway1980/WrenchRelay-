"""Fail-closed routing contract for the temporary Railway gateway health probe."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "vercel.json"

class RailwayBridgeContract(unittest.TestCase):
    def test_probe_proxies_only_public_health_without_api_cutover(self):
        obj = json.loads(CONFIG.read_text(encoding="utf-8"))
        routes = obj["rewrites"]
        self.assertEqual(
            routes[0],
            {
                "source": "/__bridge/railway-health",
                "destination": "https://wrenchrelay-app-production.up.railway.app/api/health",
            },
        )
        self.assertEqual(routes[1:],
                         [
                             {"source": "/api", "destination": {"service": "api"}},
                             {"source": "/api/(.*)", "destination": {"service": "api"}},
                             {"source": "/(.*)", "destination": {"service": "web"}},
                         ])
        external = [r for r in routes if isinstance(r.get("destination"), str)
                    and r["destination"].startswith("https://")]
        self.assertEqual(len(external), 1)
        self.assertNotIn("mongodb", str(obj).lower())
        self.assertNotIn("sk_live_", str(obj).lower())

if __name__ == "__main__":
    unittest.main()
