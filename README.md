<div align="center">
  <img src="spain_compliance/public/images/logo.svg" width="72" alt="Spain Compliance" />
  <h1>Spain Compliance</h1>
  <p>Spanish accounting and compliance for <a href="https://github.com/frappe/erpnext">ERPNext</a>.</p>
  <p><i>Contabilidad española para ERPNext: Plan General Contable, series de facturas rectificativas, estados de cobro e interfaz de contabilidad.</i></p>
</div>

---

## Features

### Plan General Contable (PGC) tree
ERPNext organises the chart of accounts by `root_type` (Asset, Liability, Equity, Income, Expense). The Spanish PGC organises it by **nature** into groups 1–9, and a single group mixes asset and liability accounts (430 *Clientes* vs 438 *Anticipos de clientes*, 470 vs 475 *Hacienda Pública*, 570 *Caja* vs 521 *Deudas a corto plazo*).

Spain Compliance lets each account keep **its own** `root_type` regardless of its parent group, and patches ERPNext's Balance Sheet / Profit and Loss so they still balance:

- Company checkbox **Plan General Contable (árbol de 9 grupos)**.
- One-click conversion of an existing company chart to the 9-group tree (*Company → Contabilidad España → Convertir plan a PGC*): creates groups 1–9 and the two-digit subgroups, re-parents numbered accounts by prefix, deletes (or disables and re-parents) the leftover ERPNext standard accounts.
- Financial statements include the full PGC hierarchy for PGC companies; non-PGC companies are untouched.

### Dedicated series for credit notes (facturas rectificativas)
Spanish invoicing rules require rectifying invoices to use their own series. ERPNext copies the original invoice's series when creating a return. Configure **Serie de facturas rectificativas** on the Company (e.g. `{company_abbr}.R.YY.{#####}`) and every credit note created from the ordinary series is moved to it automatically, both server-side and in the form.

`{company_abbr}` resolves to the Company abbreviation when the invoice is named, so you can also use it in the ordinary series (e.g. `{company_abbr}.F.YY.{#####}`). It is not a stored field: ERPNext already uses that name internally.

### Collection statuses: *Dudoso Cobro* and *Pérdida*
Two extra values on the native `Sales Invoice.status` field (no custom column), with buttons on the invoice form and preserved across ERPNext's automatic status recalculation while the invoice is outstanding. Optionally, invoices overdue by *N* months (Company → **Meses hasta Dudoso Cobro**) are moved to *Dudoso Cobro* by a daily job. Disabled (0) by default.

### Contabilidad UI
A [frappe-ui](https://github.com/frappe/frappe-ui) single-page app at `/contabilidad` (Apps screen → *Contabilidad*): dashboard with billing, cash-flow and receivables, and list views for invoices, payments, journal entries, parties, items and tax templates built on ERPNext DocTypes. Compliance sections (SII, Verifactu, tax forms) are placeholders for upcoming work.

## Compatibility

| Branch       | Frappe / ERPNext |
|--------------|------------------|
| `version-15` | v15              |

Requires **ERPNext** (installed automatically as a dependency). Building the UI requires **Node.js ≥ 20.11** (frappe-ui / Vite 5). On Frappe Cloud, select Node 20 or 22 in your bench *Dependencies*.

## Installation

### Frappe Cloud
Install from the Marketplace, or add `https://github.com/xappiens-ai/spain_compliance` (branch `version-15`) as a custom app to your bench.

### Self-hosted bench

```bash
bench get-app --branch version-15 https://github.com/xappiens-ai/spain_compliance
bench --site <site> install-app spain_compliance
```

`bench build` runs the frontend build through the root `package.json` (`yarn build`).

## Configuration

Everything is configured per **Company**, section *Contabilidad España*:

| Field | Purpose |
|-------|---------|
| Plan General Contable (árbol de 9 grupos) | Enable per-account `root_type` and the PGC-aware financial statements. Set automatically by the conversion button. |
| Serie de facturas rectificativas | Naming series forced on credit notes. Empty = ERPNext default behaviour. |
| Meses hasta Dudoso Cobro | Months after due date before an unpaid invoice becomes *Dudoso Cobro*. 0 = off. |

Access to `/contabilidad` is granted to *Accounts User*, *Accounts Manager* and *System Manager*.

## Documentation (Spanish)

- [docs/series-facturas-abono.md](docs/series-facturas-abono.md) — series de facturas y rectificativas
- [docs/desarrollo.md](docs/desarrollo.md) — arquitectura y directrices de desarrollo
- [docs/publicacion.md](docs/publicacion.md) — cómo se mantiene y publica la app (GitLab canónico, GitHub público)

## Development

```bash
# Frontend (Node 22 recommended, see .nvmrc)
cd apps/spain_compliance/frontend
yarn
yarn dev      # Vite dev server proxied to your bench
yarn build    # → spain_compliance/public/frontend + www/contabilidad.html (both gitignored)

# Backend
bench --site <site> migrate
bench --site <site> clear-cache && bench restart
```

Pre-commit (ruff, prettier, eslint): `pre-commit install`.

## Maintenance and publishing

The app is developed by [Xappiens](https://xappiens.com) against a production ERPNext and versioned in Xappiens' internal GitLab; this GitHub repository is the public distribution channel and receives the same code on every release. Details in [docs/publicacion.md](docs/publicacion.md).

## Contributing

Issues and pull requests are welcome. Please keep changes generic (no site-specific account names, series or credentials) and follow [docs/desarrollo.md](docs/desarrollo.md).

## License

[MIT](license.txt) © Xappiens and contributors.
