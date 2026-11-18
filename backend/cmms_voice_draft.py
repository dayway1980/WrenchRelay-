"""Vendor-neutral, deterministic voice-to-CMMS draft contract.

No external CMMS write is performed here. Only technician-confirmed values
are eligible for an approved connector command.
"""
from dataclasses import dataclass, field
from typing import Any

FIELDS = ("asset_id", "work_order_id", "complaint", "symptoms",
          "measurements", "actions_taken", "parts_used",
          "verification", "machine_status", "downtime_minutes")


@dataclass
class VoiceWorkDraft:
    organization_id: str
    user_id: str
    fields: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, str] = field(default_factory=dict)
    revision: int = 0
    approved_revision: int | None = None

    def add_technician_fact(self, key: str, value: Any) -> None:
        if key not in FIELDS:
            raise ValueError("Unsupported CMMS field")
        if not isinstance(value, (str, int, float)) or not str(value).strip():
            raise ValueError("A nonempty, explicit technician fact is required")
        self.fields[key] = value
        self.provenance[key] = "technician_confirmed"
        self.revision += 1
        self.approved_revision = None

    def missing(self) -> list[str]:
        required = ("asset_id", "complaint", "actions_taken", "verification")
        return [key for key in required if not self.fields.get(key)]

    def approve(self, *, actor_id: str, revision: int) -> None:
        if actor_id != self.user_id:
            raise PermissionError("Only the draft owner may approve")
        if revision != self.revision:
            raise ValueError("Draft changed; review again")
        if self.missing():
            raise ValueError("Required work-order facts are missing")
        self.approved_revision = revision

    def connector_payload(self, *, organization_id: str, actor_id: str,
                          capability: str) -> dict[str, Any]:
        if organization_id != self.organization_id or actor_id != self.user_id:
            raise PermissionError("Organization or user mismatch")
        if capability != "work_orders:write":
            raise PermissionError("Connector does not permit work-order writes")
        if self.approved_revision != self.revision:
            raise PermissionError("Technician approval required")
        return {"organization_id": self.organization_id,
                "actor_id": actor_id,
                "revision": self.revision,
                "fields": dict(self.fields),
                "provenance": dict(self.provenance)}
