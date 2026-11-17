# AutonomePay design system: "settlement desk ledger"

**Who and what:** a judge or fintech engineer verifying that an AI negotiator stays within merchant policy. The UI should feel like precise, auditable paperwork, not a neon AI dashboard.

## Tokens (`frontend/src/styles/index.css`, mapped in `tailwind.config.js`)
- **Surfaces:** one warm hue, lightness only: `paper` (page) → `sheet` (panels) → `sheet-raised` (slips, popovers, dialogs). `well` is for inset inputs, slightly darker than its surroundings.
- **Text tiers:** `ink`, `ink-2`, `ink-3` (all ≥ 4.5:1 on `sheet` in both modes), plus `ink-4` (disabled or decorative only).
- **Borders:** `border-rule/10` standard, `/15` emphasis, `/20` dashed slip divider.
- **Colour:** one accent, `accent` (ink blue), used for primary actions, focus rings, user bubbles and meters.
- **Status (reserved, never decorative):** `settled` / `caution` (+ `caution-ink` for text) / `void`. These are validated with dataviz `validate_palette.js` in both modes. Always pair them with an icon and a label.

## Type and spacing
- **Fonts:** Geist (UI) and Geist Mono (ids, raw JSON). Use `.num` (tabular figures) only in aligned columns; hero and stat values use proportional figures.
- **Scale (ratio 1.25):** 12 · 14 · 16 · 18 · 22 · 28 · 36, plus a 52 px hero (one per view). 12 px is the minimum.
- **Spacing:** 4 px base, workbench density. Panel padding 16, header 12×16, section gap 12 (24 on benchmark).
- **Radius:** `control` 6, `panel` 10, `dialog` 14. Stamps use 4.
- **Depth:** borders plus tonal surfaces only. One ring shadow on dialogs. No glass, no glows.

## Signature components
- **SettlementSlip:** receipt layout. Original → concession or held → **net payable (22 px)**, then bounds meters, guardrail notes, and the Pay link or "awaiting consent" footer.
- **Stamp:** uppercase, 1.5 px border, −1° rotation. `within` / `corrected` / `blocked`.
- **BoundsMeter:** `role="meter"`, track at accent /15, fill accent (caution when corrected).
- **AuditRail:** numbered vertical timeline: triage → policy → offer → guardrails → payment tool.
- **CaseLedger:** 50 buttons, outcome as colour + icon + legend count. ResultsTable is the table view.

## Layout
- **Sandbox:** ≥1280 px `300 | 1fr | 380`; 768–1279 px chat plus a 340 px tabbed side column; <768 px a Chat · Case · Audit segmented control. The shell is `h-dvh`; panels scroll internally.
- **Benchmark:** page scroll. The table shows at ≥1024 px (Turns and Latency at ≥1280 px); cards below that.

## Interaction
- Native `<button>`, `<a>`, `<dialog>` and `<details>`. Segmented = `role="tablist"` with arrow keys.
- **Motion:** 150–200 ms `ease-out` (`cubic-bezier(.23,1,.32,1)`). The stamp/dialog entrance is scale .96→1. No perpetual animation except loading skeletons and the typing dots. `prefers-reduced-motion` is honoured globally.
- **Touch:** controls are ≥ 44 px below 768 px. Inputs use 16 px text on mobile so iOS doesn't zoom.
