"""Keep the existing host app; require a reviewed source hash before integration."""
import hashlib
import importlib.util
import os
import sys
from pathlib import Path
from integration import install


def load_application():
    root = Path(os.environ["WR_PAYMENTS_HOST_ROOT"]).resolve(strict=True)
    sys.path.insert(0, str(root))
    spec = importlib.util.find_spec("backend.app")
    expected = os.environ.get("WR_PAYMENTS_HOST_SHA256", "")
    if not spec or not spec.origin or Path(spec.origin).resolve() != (root/"backend"/"app.py").resolve() or len(expected) != 64:
        raise RuntimeError("A reviewed host source hash is required")
    if hashlib.sha256(Path(spec.origin).read_bytes()).hexdigest() != expected:
        raise RuntimeError("Host source differs from the reviewed billing integration")
    import backend.app as host
    install(host)
    return host.app


if __name__ == "__main__":
    # No shell expansion or credentials on the process command line.
    import uvicorn
    uvicorn.run(load_application(), host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
