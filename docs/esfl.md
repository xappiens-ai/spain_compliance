# Entidades sin fines lucrativos (ESFL): PGC, socios, donaciones y Modelo 182

Especificación para implementar en **Spain Compliance** (y qué reutilizar de ERPNext / Non Profit). Nada de esto está hecho salvo lo ya común del PGC mercantile (árbol 9 grupos, que también sirve de base estructural).

**Alcance general:** [alcance.md](alcance.md). **Plan de fases:** `/home/frappe/docs/spain-compliance-plan-desarrollo.md` (sección ESFL).

---

## 1. Contexto normativo (referencia de producto)

| Pieza | Norma / uso |
|-------|-------------|
| Plan de cuentas y cuentas anuales ESFL | RD **1491/2011** (adaptación del PGC a entidades sin fines lucrativos) y resoluciones de desarrollo |
| PGC mercantile (PYMES / Normal) | RD 1514/2007, RD 1515/2007 — ya priorizado en el roadmap general |
| Información de donativos | **Modelo 182** (declaración informativa de donaciones y aportaciones recibidas) |
| Deducción del donante | Ley 49/2002 y normas de desarrollo; certificado al donante (no confundir con 80G indio) |

La app no asesora fiscalmente: implementa estructuras de datos, plantillas e informes alineados con esos diseños; la configuración por compañía es opt-in.

---

## 2. Decisión de arquitectura

```
ERPNext
  ├── Contabilidad, Budget, Project, Cost Center, Subscription, Customer
  └── (opcional) app non_profit → Member, Membership, Donor, Donation

spain_compliance
  ├── PGC árbol 9 grupos (ya)
  ├── Plantilla / conversión PGC-PYMES | Normal | ESFL   ← datos versionados
  ├── Modelo de cuentas anuales según Company.modelo_cuentas_anuales
  ├── Registro fiscal / libros / modelos AEAT (roadmap)
  └── Módulo donaciones ES (certificado + 182) sobre Payment Entry /
      Sales Invoice / Donation (si Non Profit instalado)
```

**Reglas:**

1. **No** forkear Non Profit dentro de Spain Compliance.
2. Si el sitio tiene `non_profit`, los certificados/182 pueden leer `Donation` / `Donor` / `Member`.
3. Si no, la fuente mínima son **Customer** + **Payment Entry** / **Sales Invoice** con clasificación “donación / cuota” (Custom Fields en Company o en el documento).
4. Todo configurable por **Company** (`setup/custom_fields.py`); cero datos de un cliente concreto en el repo.

---

## 3. PGC-ESFL (plan de cuentas y cuentas anuales)

### 3.1 Qué hay hoy

- Conversión a árbol de **9 grupos** y subgrupos de 2 dígitos (núcleo común PGC / ESFL a nivel de estructura).
- Campo Company `modelo_cuentas_anuales`: `PYMES` | `Abreviado` | `Normal` (sin `ESFL`).
- Roadmap mercantile: plantillas con `account_number` oficiales y epígrafes de Balance/PyG PYMES → Abreviado → Normal.

### 3.2 Qué implementar

| Entrega | Descripción |
|---------|-------------|
| Valor `ESFL` en `modelo_cuentas_anuales` | Ampliar `MODELO_CUENTAS_OPTIONS` en `clasificacion.py` + campo Company. |
| Plantilla de cuentas ESFL | JSON/py versionado (`contabilidad/plantillas/esfl.py` o similar): grupos/cuentas propias del RD 1491/2011 (patrimonio neto de la entidad, ingresos por cuotas/donaciones/subvenciones, etc.), con `account_number`, `root_type`, `account_type`. |
| Instalación / conversión | Misma API que PYMES: solo compañías sin movimientos o conversión documentada; opt-in; idempotente; job en segundo plano. |
| Mapeo de cuentas anuales ESFL | Epígrafes oficiales ← prefijos/cuentas (datos versionados), informes Balance / resultado de ESFL (paralelos a Fase 2 mercantile). |
| Diagnóstico | Avisos si `modelo_cuentas_anuales = ESFL` y faltan cuentas típicas o hay mezcla inconsistente. |

### 3.3 Qué no hacer en la primera entrega ESFL

- Sustituir el PGC mercantile por ESFL en compañías ya convertidas sin confirmación.
- Mezclar epígrafes PYMES y ESFL en el mismo informe.
- Contabilidad de fondos / restricciones (si se pide después: dimensiones o subcuentas, no hardcode).

### 3.4 Orden sugerido respecto al roadmap general

1. Terminar plantilla **PGC-PYMES** (Fase 0.4) — reutilizable como base de números.
2. Añadir variante **ESFL** (cuentas + epígrafes) cuando haya demanda confirmada.
3. Cuentas anuales ESFL después o en paralelo a Fase 2 PYMES (misma infraestructura de informes).

---

## 4. Cuotas de socios (operativa)

### 4.1 Opción A — Sin Non Profit (mínima)

| Pieza | Uso |
|-------|-----|
| Customer | Socio / donante |
| Item / Subscription Plan | Tipo de cuota |
| Subscription + Auto Repeat / facturación | Cobro periódico |
| Sales Invoice + Payment Entry | Ingreso y cobro; cuenta 72x / 74x según plan PGC |

Spain Compliance: opcionalmente marcar en Company o en Item la naturaleza (`sc_naturaleza_ingreso`: cuota | donación | subvención | otro) para informes y 182.

### 4.2 Opción B — Con Non Profit

Usar `Member`, `Membership`, `Membership Type` (y `Chapter` si aplica). La facturación/cobro sigue enlazando a Customer/Payment según la app.

Spain Compliance **no** duplica esos DocTypes; documenta la integración y, si hace falta, Custom Fields ES (`sc_*`) vía `setup/custom_fields.py` solo si Non Profit está instalado (hooks defensivos: `frappe.get_installed_apps()`).

### 4.3 Fuera de alcance producto (salvo encargo)

Portal de alta de socio, votaciones, censos electorales, carnés, etc.

---

## 5. Donaciones, certificados y Modelo 182

### 5.1 Hueco actual

- Non Profit trae **Tax Exemption 80G Certificate** (India). No usar para España.
- Spain Compliance roadmap AEAT (Fases 3–7) no incluye aún el **182**.

### 5.2 Modelo de datos propuesto (Spain Compliance)

DocTypes propios (nombres orientativos; prefijo/módulo Contabilidad):

1. **`Certificado Donacion`** (o `SC Certificado Donacion`)
   - Compañía, ejercicio, donante (link Customer / Donor), NIF, nombre, domicilio.
   - Importe, fecha de donación, naturaleza (dineraria / especie), finalidad, deducible (sí/no).
   - Documento origen (Payment Entry / Sales Invoice / Donation).
   - Número de certificado (serie Company), PDF printable.
   - Estado: Borrador / Emitido / Anulado.

2. **`Registro Modelo 182`** (filas congeladas al “generar periodo”, análogas a `Registro Fiscal IVA`)
   - Una fila por donante × clave de declaración del diseño de registro vigente.
   - Campos alineados al diseño AEAT del 182 (NIF, NIF del declarante, importe, clave, % deducción si aplica, etc. — numeración y longitudes anotadas en código con versión del diseño).

Custom Fields en Company (sección Contabilidad España o subsección Donaciones):

- Activar certificados / 182 (check).
- Serie de certificados.
- Datos del declarante ya previstos para otros modelos (NIF, contacto).
- Régimen Ley 49/2002 (sí/no) informativo.

### 5.3 Flujo

```
Donación cobrada (Payment Entry / Donation / SI)
        → (opcional) emitir Certificado Donacion
        → al cierre del ejercicio / generación 182:
              materializar Registro Modelo 182
        → informe + exportación fichero AEAT (Fase 7 genérica)
```

### 5.4 Informes SPA / Desk

- Listado de donaciones del ejercicio (filtro compañía, donante, origen).
- Emisión / reimpresión de certificado.
- Borrador Modelo 182 con casillas/columnas del diseño; “ver documentos” por fila.
- Export Excel y, cuando exista infraestructura Fase 7, fichero de presentación.

### 5.5 Tests

Solo datos ficticios en `sc-test.localhost`. Cubrir: alta donación → certificado → fila 182; anulación; compañía sin opción activa (no crear nada); sitio sin `non_profit` (fuente Payment Entry).

---

## 6. Presupuestos y proyectos en ESFL

No es código Spain Compliance: es **configuración ERPNext**.

Recomendación de implantación para asociaciones/fundaciones:

| Uso | Configuración |
|-----|----------------|
| Presupuesto por área / programa | Cost Center (árbol) + Budget against Cost Center + cuentas 6xx |
| Presupuesto por proyecto / subvención | Project + Budget against Project; dimensión “Subvención” si hace falta |
| Seguimiento | Informes de Budget Variance; GL filtrado por CC/Project |
| Contabilidad general | Plan PGC o PGC-ESFL en la misma compañía |

Si la SPA debe mostrar “presupuestos generales”, añadir ruta al DocType **Budget** (no confundir con Quotation “Presupuestos” de venta).

---

## 7. Criterios de aceptación (resumen)

### PGC-ESFL

- [ ] Company puede elegir modelo ESFL.
- [ ] Instalar/convertir plantilla ESFL crea cuentas con número y `root_type` correctos.
- [ ] Balance / resultado ESFL cuadran y usan epígrafes del RD 1491/2011 (datos versionados).
- [ ] Compañía PYMES/Normal intacta.

### Socios

- [ ] Documentado: camino Subscription y camino Non Profit.
- [ ] Sin DocTypes “Socio” duplicados en SC salvo que Non Profit no baste y se decida lo contrario por escrito.

### 182 / certificados

- [ ] Certificado emitible desde cobro/donación clasificada.
- [ ] Generación 182 idempotente por ejercicio; anulación coherente.
- [ ] Export según diseño de registro (cuando Fase 7 esté lista).
- [ ] Sin lógica 80G.

### Presupuestos / proyectos

- [ ] Preventa y docs apuntan a Budget + Cost Center/Project.
- [ ] SPA no presenta Quotation como presupuesto contable (renombrar o añadir Budget).

---

## 8. Orden de implementación recomendado

| Prioridad | Entrega | Dependencias |
|-----------|---------|--------------|
| P0 | Documentación alcance + esta spec (este doc) | — |
| P1 | Clarificar SPA: Budget vs Quotation | Solo frontend |
| P2 | Plantilla PGC-PYMES (roadmap general) | Fase 0.4 |
| P3 | Certificado donación + registro/listado 182 | Clasificación ingreso; infra informes |
| P4 | Plantilla + cuentas anuales ESFL | P2 + infra Fase 2 |
| P5 | Fichero AEAT 182 | Fase 7 |

P3 puede adelantarse a P4 si el cliente ESFL prioriza Hacienda (182) sobre el plan de cuentas estricto RD 1491/2011 (en muchos casos operan con PGC-PYMES adaptado).
