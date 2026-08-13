/**
 * VendorAdSlot — Placeholder component for future vendor/partner advertisements.
 *
 * Right now it renders nothing visible (returns null). When the ads module is
 * activated in a future release, this component will fetch and display
 * contextual ads from partnered maintenance-supply vendors.
 *
 * Props:
 *   slot  — identifier for the ad placement (e.g. "sidebar-top")
 *   size  — optional size hint ("banner" | "square")
 */
export default function VendorAdSlot({ slot, size = "banner" }) {
  // TODO: wire to ads backend once vendor partnerships are signed.
  // The component is mounted in key pages so placements are pre-registered
  // for analytics even before ads go live.
  return null;
}

// Future: fetch from /api/ads?slot=X
// Future: impression tracking pixel
// Future: click-through attribution
// Future: A/B test different creative sizes
// Future: fallback to house ads when no vendor fill
