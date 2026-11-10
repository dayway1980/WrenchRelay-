import { z } from 'zod';

const id = z.string().regex(/^[A-Za-z0-9_.:-]{1,100}$/);
const epoch = z.number().int().nonnegative().max(8_640_000_000_000_000);
const quantity = z.number().int().positive().max(100_000);
const countMap = z.record(id, z.number().int().nonnegative().max(100_000));
const money = z.object({ minor: z.string().regex(/^\d{1,18}$/), currency: z.string().regex(/^[A-Z]{3}$/) }).strict();
const country = z.string().regex(/^[A-Z]{2}$/);
const coordinate = z.object({ lat: z.number().min(-90).max(90), lng: z.number().min(-180).max(180) }).strict();
const skills = z.record(id, z.number().min(0).max(1));
const language = z.string().min(2).max(35).refine(s => {
  try { return Intl.getCanonicalLocales(s).length === 1; } catch { return false; }
}).transform(s => Intl.getCanonicalLocales(s)[0]!);
const timeZone = z.string().max(100).refine(s => {
  try { new Intl.DateTimeFormat('en', { timeZone: s }); return true; } catch { return false; }
});
const leg = z.object({
  from: id, to: id, seconds: z.number().int().nonnegative().max(604800),
  meters: z.number().int().nonnegative().max(50_000_000), observedAt: epoch,
  transitCountries: z.array(country).min(1),
  approvedBorderDelaySeconds: z.number().int().nonnegative().max(604800),
}).strict();
export const DispatchInput = z.object({
  tenantId: id, now: epoch, maxSnapshotAgeMs: z.number().int().positive().max(300_000),
  maxRouteHorizonMs: z.number().int().positive().max(3_600_000),
  job: z.object({ id, country, timeZone, acceptedLanguages: z.array(language).min(1),
    requiredSkills: skills, parts: z.array(z.object({ sku: id, quantity }).strict()).max(100),
    windowStart: epoch, windowEnd: epoch, serviceSeconds: quantity,
    settlementCurrency: z.string().regex(/^[A-Z]{3}$/),
  }).strict(),
  technicians: z.array(z.object({ id, tenantId: id, version: z.number().int().nonnegative(),
    position: coordinate, observedAt: epoch, availableAt: epoch, shiftEnd: epoch,
    authorizedCountries: z.array(country).min(1), languages: z.array(language).min(1), skills,
    remainingKg: z.number().nonnegative(), remainingLiters: z.number().nonnegative(),
    onboard: countMap, dispatchFee: money,
  }).strict()).max(10_000),
  warehouses: z.array(z.object({ id, tenantId: id, version: z.number().int().nonnegative(), country,
    observedAt: epoch, readyAt: epoch, stock: countMap,
    skuInfo: z.record(id, z.object({ kg: z.number().nonnegative(), liters: z.number().nonnegative(), unitPrice: money }).strict()),
    pickupSeconds: z.number().int().nonnegative().max(86400),
  }).strict()).max(500),
  routes: z.array(leg).max(200_000),
  fx: z.array(z.object({ from: z.string().regex(/^[A-Z]{3}$/), to: z.string().regex(/^[A-Z]{3}$/),
    // Ratio converts minor units, including differing ISO currency exponents.
    numerator: z.string().regex(/^[1-9]\d{0,17}$/), denominator: z.string().regex(/^[1-9]\d{0,17}$/), observedAt: epoch,
  }).strict()).max(1000),
}).strict().superRefine((v, ctx) => {
  if (v.job.windowEnd < v.job.windowStart) ctx.addIssue({ code: 'custom', message: 'Reversed job window' });
  const endpoints = [v.job.id, ...v.technicians.map(t => t.id), ...v.warehouses.map(w => w.id)];
  if (new Set(endpoints).size !== endpoints.length)
    ctx.addIssue({ code: 'custom', message: 'Route endpoint IDs must be globally distinct' });
  if (new Set(v.job.parts.map(p => p.sku)).size !== v.job.parts.length)
    ctx.addIssue({ code: 'custom', message: 'Duplicate requested SKU' });
  const keys = v.routes.map(r => JSON.stringify([r.from, r.to]));
  if (new Set(keys).size !== keys.length) ctx.addIssue({ code: 'custom', message: 'Ambiguous route snapshot' });
  const fxKeys = v.fx.map(r => r.from + '/' + r.to);
  if (new Set(fxKeys).size !== fxKeys.length) ctx.addIssue({ code: 'custom', message: 'Ambiguous FX snapshot' });
});
export type DispatchRequest = z.infer<typeof DispatchInput>;
export interface Candidate {
  technicianId: string; technicianVersion: number; warehouseId: string | null; warehouseVersion: number | null;
  validUntil: number; finishAt: number; arriveAt: number; startAt: number; meters: number;
  costMinor: string; currency: string; pickup: Record<string, number>;
  quality: 'SNAPSHOT_RECOMMENDATION'; requiresAtomicReservation: true;
}
export function convertMinor(amount: bigint, numerator: bigint, denominator: bigint): bigint {
  if (amount < 0n || numerator <= 0n || denominator <= 0n) throw new Error('Invalid money ratio');
  return (amount * numerator + denominator - 1n) / denominator;
}
export function localTime(epochMs: number, zone: string): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: zone, dateStyle: 'medium', timeStyle: 'long' }).format(epochMs);
}
const lexical = (a: string, b: string): number => a < b ? -1 : a > b ? 1 : 0;
function compare(a: Candidate, b: Candidate): number {
  return a.finishAt - b.finishAt ||
    (BigInt(a.costMinor) < BigInt(b.costMinor) ? -1 : BigInt(a.costMinor) > BigInt(b.costMinor) ? 1 : 0) ||
    a.meters - b.meters || lexical(a.technicianId, b.technicianId) || lexical(a.warehouseId ?? '', b.warehouseId ?? '');
}
/** Exact lexicographic minimum for one job, at most one pickup, over supplied snapshots.
 * Earliest completion, then parts+dispatch fee, then meters and stable IDs.
 * This function authorizes no dispatch, stock reservation, payment or CMMS write.
 */
export function matchDispatch(raw: unknown): { best: Candidate | null; considered: number; rejected: string[] } {
  const v = DispatchInput.parse(raw);
  const fresh = (at: number): boolean => at <= v.now && v.now - at <= v.maxSnapshotAgeMs;
  const routes = new Map(v.routes.map(r => [JSON.stringify([r.from, r.to]), r]));
  const fx = new Map(v.fx.map(r => [r.from + '/' + r.to, r]));
  const rejected: string[] = [];
  let best: Candidate | null = null; let considered = 0;
  for (const t of v.technicians) {
    if (t.tenantId !== v.tenantId || !fresh(t.observedAt) || !t.authorizedCountries.includes(v.job.country) ||
        !v.job.acceptedLanguages.some(l => t.languages.includes(l)) ||
        !Object.entries(v.job.requiredSkills).every(([s, level]) => (Object.hasOwn(t.skills, s) ? t.skills[s]! : 0) >= level)) {
      rejected.push(t.id + ':identity_freshness_country_language_or_skill'); continue;
    }
    const departure = Math.max(v.now, t.availableAt);
    if (departure - v.now > v.maxRouteHorizonMs) { rejected.push(t.id + ':traffic_horizon'); continue; }
    const missing: Record<string, number> = Object.create(null) as Record<string, number>;
    for (const p of v.job.parts) {
      const onboard = Object.hasOwn(t.onboard, p.sku) ? t.onboard[p.sku]! : 0;
      const n = Math.max(0, p.quantity - onboard);
      if (n > 0) missing[p.sku] = n;
    }
    const options: Array<DispatchRequest['warehouses'][number] | null> =
      Object.keys(missing).length === 0 ? [null] : v.warehouses;
    let feasible = false;
    for (const w of options) {
      let validUntil = Math.min(v.now + 15000, t.observedAt + v.maxSnapshotAgeMs);
      function price(m: z.infer<typeof money>): bigint | null {
        if (m.currency === v.job.settlementCurrency) return BigInt(m.minor);
        const r = fx.get(m.currency + '/' + v.job.settlementCurrency);
        if (!r || !fresh(r.observedAt)) return null;
        validUntil = Math.min(validUntil, r.observedAt + v.maxSnapshotAgeMs);
        return convertMinor(BigInt(m.minor), BigInt(r.numerator), BigInt(r.denominator));
      }
      function route(from: string, to: string): z.infer<typeof leg> | null {
        const r = routes.get(JSON.stringify([from, to]));
        if (!r || !fresh(r.observedAt) || !r.transitCountries.every(c => t.authorizedCountries.includes(c))) return null;
        validUntil = Math.min(validUntil, r.observedAt + v.maxSnapshotAgeMs);
        return r;
      }
      const fee = price(t.dispatchFee); if (fee === null) continue;
      let arriveAt: number; let meters = 0; let cost = fee;
      if (w) {
        if (w.tenantId !== v.tenantId || !fresh(w.observedAt) || !t.authorizedCountries.includes(w.country)) continue;
        validUntil = Math.min(validUntil, w.observedAt + v.maxSnapshotAgeMs);
        let kg = 0; let liters = 0; let valid = true;
        for (const [sku, n] of Object.entries(missing)) {
          const info = Object.hasOwn(w.skuInfo, sku) ? w.skuInfo[sku] : undefined;
          const stock = Object.hasOwn(w.stock, sku) ? w.stock[sku]! : 0;
          if (!info || stock < n) { valid = false; break; }
          const unit = price(info.unitPrice);
          if (unit === null) { valid = false; break; }
          kg += info.kg * n; liters += info.liters * n; cost += unit * BigInt(n);
        }
        if (!valid || kg > t.remainingKg || liters > t.remainingLiters) continue;
        const a = route(t.id, w.id); const b = route(w.id, v.job.id);
        if (!a || !b) continue;
        const pickupAt = Math.max(departure + (a.seconds + a.approvedBorderDelaySeconds) * 1000, w.readyAt) + w.pickupSeconds * 1000;
        if (pickupAt - v.now > v.maxRouteHorizonMs) continue;
        arriveAt = pickupAt + (b.seconds + b.approvedBorderDelaySeconds) * 1000;
        meters = a.meters + b.meters;
      } else {
        const r = route(t.id, v.job.id); if (!r) continue;
        arriveAt = departure + (r.seconds + r.approvedBorderDelaySeconds) * 1000; meters = r.meters;
      }
      const startAt = Math.max(arriveAt, v.job.windowStart);
      const finishAt = startAt + v.job.serviceSeconds * 1000;
      if (finishAt > v.job.windowEnd || finishAt > t.shiftEnd || validUntil <= v.now) continue;
      const candidate: Candidate = { technicianId: t.id, technicianVersion: t.version, warehouseId: w?.id ?? null,
        warehouseVersion: w?.version ?? null, validUntil, arriveAt, startAt, finishAt, meters,
        costMinor: cost.toString(), currency: v.job.settlementCurrency, pickup: { ...missing },
        quality: 'SNAPSHOT_RECOMMENDATION', requiresAtomicReservation: true };
      feasible = true; considered++;
      if (!best || compare(candidate, best) < 0) best = candidate;
    }
    if (!feasible) rejected.push(t.id + ':fx_parts_route_capacity_or_schedule');
  }
  return { best, considered, rejected };
}

const MatrixElement = z.object({ originIndex: z.number().int().nonnegative(), destinationIndex: z.number().int().nonnegative(),
  status: z.object({code: z.number().int().optional()}).passthrough().optional(),
  condition: z.string().optional(), distanceMeters: z.number().int().nonnegative().optional(), duration: z.string().optional(),
}).passthrough();
/** Matrix does not prove transit countries/customs permissions. Independent approval is required. */
export function normalizeGoogleMatrix(raw: unknown, origins: readonly string[], destinations: readonly string[], observedAt: number,
  compliance: ReadonlyMap<string, { transitCountries: string[]; approvedBorderDelaySeconds: number }>): DispatchRequest['routes'] {
  const cells = z.array(MatrixElement).parse(raw); const result: DispatchRequest['routes'] = []; const seen = new Set<string>();
  for (const cell of cells) {
    if ((cell.status?.code ?? 0) !== 0 || cell.condition !== 'ROUTE_EXISTS' || cell.distanceMeters === undefined || !cell.duration) continue;
    const from = origins[cell.originIndex]; const to = destinations[cell.destinationIndex];
    const duration = /^(\d+(?:\.\d+)?)s$/.exec(cell.duration);
    if (!from || !to || !duration?.[1]) throw new Error('Invalid matrix cell');
    const key = JSON.stringify([from, to]); if (seen.has(key)) throw new Error('Duplicate matrix cell'); seen.add(key);
    const approval = compliance.get(key); if (!approval) continue;
    result.push(leg.parse({from, to, meters:cell.distanceMeters, seconds:Math.ceil(Number(duration[1])), observedAt, ...approval}));
  }
  return result;
}
