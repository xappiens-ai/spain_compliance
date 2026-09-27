# Cómo se mantiene y publica esta app

## Dos repositorios, una historia

| Repositorio | Papel |
|---|---|
| GitLab interno de Xappiens | **Canónico.** Aquí se hace el desarrollo diario y aquí está la rama que corre en el ERP de Xappiens. |
| [GitHub `xappiens-ai/spain_compliance`](https://github.com/xappiens-ai/spain_compliance) | **Público.** Es de donde instalan Frappe Cloud y `bench get-app`. Recibe la misma historia que GitLab. |

Ambos contienen los mismos commits. GitHub no es un fork ni una copia editada: se actualiza con cada push a GitLab que sea publicable. Si encuentras diferencias entre los dos, GitLab es el que vale.

## Ramas

| Rama pública (GitHub) | Frappe / ERPNext |
|---|---|
| `version-15` | v15 |

Sigue la convención de Frappe (`version-N`) para que Frappe Cloud y `bench get-app --branch version-15` funcionen sin explicaciones. Internamente la rama puede tener otro nombre; el contenido es el mismo.

## Dónde se prueba

La app se desarrolla y se prueba en un ERPNext **en producción** (el de Xappiens). Eso condiciona cómo se escribe el código:

- **Nada específico de una empresa** en el repo: ni nombres de compañía, ni abreviaturas, ni nombres de cuentas, ni series concretas, ni dominios. Todo lo que dependa de la empresa vive en campos de `Company` (`spain_compliance/setup/custom_fields.py`) y cada sitio los rellena a su gusto.
- **Los patches y hooks de instalación deben ser idempotentes** y no hacer nada en sitios donde no aplican. Se ejecutan en producción con cada `bench migrate`.
- Cualquier cambio en `install.py`, `setup/custom_fields.py`, `hooks.py` o `patches.txt` se comprueba además con una **instalación en un sitio nuevo y vacío** (`bench new-site … --install-app spain_compliance`) antes de publicarlo.

## Qué pasa con cada cambio

1. Commit en la rama canónica.
2. Push a GitLab.
3. Push a GitHub, rama `version-15`.
4. En el ERP de referencia: `bench migrate` si hay patches o campos nuevos, `clear-cache`, `bench restart`. Si cambió `frontend/`, antes `yarn build` con Node 22.

## Versiones

`spain_compliance/__init__.py` lleva `__version__`. Se sube cuando hay cambios que afecten a la instalación o a la base de datos, y el commit correspondiente queda etiquetado en GitHub.

## Contribuciones externas

Se aceptan issues y pull requests en GitHub. Los PR aceptados se integran primero en GitLab y vuelven a GitHub en el siguiente push, para que ambos sigan con la misma historia.
