# Alcance: qué hace ERPNext, qué hace Spain Compliance, qué no

Referencia para producto, preventa e implementación. Evita reinventar en la app lo que ya cubre ERPNext, y deja claro qué es cumplimiento español vs operativa genérica.

**Relacionado:** [esfl.md](esfl.md) (entidades sin fines lucrativos, socios, donaciones, Modelo 182), [desarrollo.md](desarrollo.md), plan interno `/home/frappe/docs/spain-compliance-plan-desarrollo.md`.

---

## Principio

| Capa | Responsabilidad |
|------|-----------------|
| **ERPNext** | Contabilidad de partida doble, facturación, cobros/pagos, centros de coste, dimensiones, presupuestos analíticos, proyectos, suscripciones, CRM. |
| **Spain Compliance** | Adaptación al PGC español, correlatividad y series, registro fiscal / libros / modelos AEAT, UI `/contabilidad`, controles fiscales ES. |
| **Non Profit** (app Frappe, opcional) | Socios, cuotas, donantes y donaciones *genéricos* (certificados tipo 80G India; no sirve tal cual para España). |
| **A medida / fase ESFL** | PGC-ESFL (RD 1491/2011), certificados de donación españoles, Modelo 182, listados de socios si el estándar no basta. |

Spain Compliance **no** sustituye el Desk ni duplica DocTypes de asiento, factura o presupuesto de ERPNext.

---

## Matriz por tema (preguntas habituales)

### 1. Mapa de cuentas / PGC

| Afirmación frecuente | Realidad | Dónde |
|----------------------|----------|--------|
| «El mapa no está adaptado al PGC» | Cierto para el plan *Standard* de ERPNext. | ERPNext de fábrica |
| Árbol de 9 grupos, `root_type` por cuenta, conversión | Hecho | Spain Compliance (`plan_contable`, override `Account`, parches Balance/PyG) |
| Plantilla PGC completa al crear compañía (números oficiales) | Roadmap (Fase 0.4) | Spain Compliance |
| Cuentas anuales oficiales PYMES / Abreviado / Normal | Roadmap (Fase 2) | Spain Compliance |
| **PGC-ESFL (RD 1491/2011)** | No implementado | Spain Compliance — ver [esfl.md](esfl.md) |
| Subcuenta 430/400/410 por tercero | Hecho (opt-in) | Spain Compliance |

### 2. Partida doble y automatismos contables

| Afirmación frecuente | Realidad | Dónde |
|----------------------|----------|--------|
| «No comprueba partida doble» | **Falso.** `Journal Entry` exige Debe = Haber; no se presenta con diferencia. | ERPNext |
| «Trata todas las cuentas por igual» | Parcialmente cierto en el sentido *español*: no valida naturaleza PGC (p. ej. no impedir un debe “raro” en una 438). Sí distingue `root_type` / `account_type` para el mayor y los estados. | ERPNext + SC (PGC) |
| «No hay rutinas automatizadas» | **Falso.** Facturas, abonos, cobros, pagos, notas de crédito, cierre de periodo, nóminas (HRMS), stock, etc. generan `GL Entry`. | ERPNext |
| Libros legales, liquidaciones AEAT, asiento de liquidación IVA | Roadmap / en curso | Spain Compliance |

**No implementar** en Spain Compliance un “validador de partida doble” propio: ya existe. Sí, si hace falta, avisos de *clasificación fiscal* o cuentas fuera de grupo PGC (diagnóstico).

### 3. Cuotas de socios / donaciones / MOD182

| Necesidad | Estado | Dónde |
|-----------|--------|--------|
| Cuotas periódicas facturables | Disponible sin módulo “Socios” | ERPNext: **Subscription** + **Customer** (+ CRM) |
| Ficha de socio / tipo de cuota / capítulos | App opcional | **Non Profit**: `Member`, `Membership`, `Membership Type`, `Chapter` |
| Donante y donación | App opcional | Non Profit: `Donor`, `Donation` |
| Certificado fiscal de donación (España) y **Modelo 182** | No hay (el 80G de Non Profit es India) | Spain Compliance — [esfl.md](esfl.md) |

Spain Compliance **no** debe reinventar el padrón de socios si Non Profit o Suscripciones bastan; sí el **cumplimiento fiscal español** sobre esas operaciones.

### 4. Presupuestos generales y analítica

| Necesidad | Estado | Dónde |
|-----------|--------|--------|
| Presupuesto por **centro de coste** (analítica) + cuentas de gasto | Nativo | ERPNext DocType **Budget** (`budget_against` = Cost Center) |
| Presupuesto por **proyecto** + cuentas de gasto | Nativo | Budget (`budget_against` = Project) |
| Solo analítica sin cuenta | No: las líneas de Budget son `Budget Account` (cuenta contable). La analítica es el *against*; el detalle es cuenta (y opcionalmente distribución mensual). | ERPNext |
| Otras dimensiones (área, subvención, actividad…) | Nativo | **Accounting Dimension** + informes; Budget se puede ampliar a dimensiones en versiones recientes según configuración |
| “Presupuestos” en la SPA `/contabilidad` | Hoy lista de **presupuestos de venta** (Quotation), no Budget contable | SPA — no confundir en preventa |

**No implementar** un motor de presupuestos contables en Spain Compliance. Documentar y, si se pide en la SPA, exponer el DocType **Budget** (y Cost Center / Project), no Quotation.

### 5. Proyectos + presupuesto + contabilidad

| Necesidad | Estado | Dónde |
|-----------|--------|--------|
| Imputar proyecto / CC en facturas y asientos | Nativo | ERPNext (Accounting Dimensions) |
| Presupuesto del proyecto y control de exceso (Stop / Warn) | Nativo | Budget against Project |
| Costes e ingresos del proyecto | Nativo | Project + GL / informes de costes |
| Integración “completa” PGC + analítica + proyecto | Configuración + uso; no es un hueco de SC | ERPNext (+ árbol PGC de SC) |

---

## Qué sí / no meter en el repo `spain_compliance`

**Sí (producto genérico):**

- PGC mercantile (árbol, plantillas PYMES/Normal, cuentas anuales).
- PGC-ESFL como *variante* de plantilla y de modelo de cuentas anuales (datos versionados, opt-in en Company).
- Registro fiscal, libros, modelos AEAT (303, 347, 182 cuando se priorice, etc.).
- Certificados / listados fiscales españoles ligados a documentos ERPNext o Non Profit, sin hardcodear una entidad concreta.

**No:**

- Duplicar Journal Entry, Budget, Project, Subscription.
- Certificados 80G / lógica India de Non Profit.
- Nombres de compañías, series o cuentas de un cliente concreto.

---

## Respuestas cortas para preventa

1. **¿PGC?** Con Spain Compliance, árbol PGC y roadmap PYMES/Normal. **ESFL** = fase documentada, no disponible aún.
2. **¿Partida doble y asientos automáticos?** Sí en ERPNext; SC añade el marco español.
3. **¿Socios?** Suscripciones y/o Non Profit; **182 y certificados ES** = desarrollo SC (o proyecto a medida acotado).
4. **¿Presupuesto con analítica?** Sí: Budget + Cost Center / Project + cuentas.
5. **¿Proyectos con presupuesto y contabilidad?** Sí, nativo ERPNext.
