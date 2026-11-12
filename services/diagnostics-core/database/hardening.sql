-- WrenchRelay Diagnostics Core hardening layer.
-- Apply after the Prisma migration has created the tables.

BEGIN;

-- Raw evidence and generated inferences are append-only scientific records.
CREATE OR REPLACE FUNCTION wrenchrelay_reject_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'WrenchRelay evidence records are append-only; create a superseding record instead';
END;
$$;

DROP TRIGGER IF EXISTS observation_immutable_update ON observations;
CREATE TRIGGER observation_immutable_update
BEFORE UPDATE OR DELETE ON observations
FOR EACH ROW EXECUTE FUNCTION wrenchrelay_reject_mutation();

DROP TRIGGER IF EXISTS evidence_span_immutable_update ON evidence_spans;
CREATE TRIGGER evidence_span_immutable_update
BEFORE UPDATE OR DELETE ON evidence_spans
FOR EACH ROW EXECUTE FUNCTION wrenchrelay_reject_mutation();

DROP TRIGGER IF EXISTS inference_evidence_immutable_update ON inference_evidence;
CREATE TRIGGER inference_evidence_immutable_update
BEFORE UPDATE OR DELETE ON inference_evidence
FOR EACH ROW EXECUTE FUNCTION wrenchrelay_reject_mutation();

DROP TRIGGER IF EXISTS provenance_edge_immutable_update ON provenance_edges;
CREATE TRIGGER provenance_edge_immutable_update
BEFORE UPDATE OR DELETE ON provenance_edges
FOR EACH ROW EXECUTE FUNCTION wrenchrelay_reject_mutation();

-- Human approval records cannot be edited into a different decision after the fact.
DROP TRIGGER IF EXISTS human_approval_immutable_update ON human_approvals;
CREATE TRIGGER human_approval_immutable_update
BEFORE UPDATE OR DELETE ON human_approvals
FOR EACH ROW EXECUTE FUNCTION wrenchrelay_reject_mutation();

-- PostgreSQL permits duplicate NULL values in composite UNIQUE constraints.
-- This partial index guarantees one global translation per namespace/key/locale.
CREATE UNIQUE INDEX IF NOT EXISTS translation_global_unique
ON translation_bindings (namespace, key, locale)
WHERE "tenantId" IS NULL;

-- Basic data-quality guards.
ALTER TABLE inferences
  ADD CONSTRAINT inference_confidence_range
  CHECK (confidence >= 0.0 AND confidence <= 1.0);

ALTER TABLE inferences
  ADD CONSTRAINT inference_unknown_probability_range
  CHECK ("unknownMechanismProbability" >= 0.0 AND "unknownMechanismProbability" <= 1.0);

ALTER TABLE inference_evidence
  ADD CONSTRAINT inference_evidence_contribution_range
  CHECK (contribution >= -1.0 AND contribution <= 1.0);

COMMIT;
