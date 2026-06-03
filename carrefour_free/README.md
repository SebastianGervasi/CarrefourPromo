# Monitor Carrefour — Versión 100% Gratuita

Corre en **GitHub Actions** (gratis) y manda reportes por **Gmail** (gratis).
Sin servidores, sin costos, sin tarjeta de crédito.

---

## Cómo funciona

```
GitHub Actions (cron diario)
  → Instala Chrome headless
  → Entra a carrefour.com.ar/descuentos-bancarios
  → Compara con el día anterior
  → Te manda email con los cambios
```

---

## Setup — 10 minutos, una sola vez

### Paso 1 — Crear el repositorio en GitHub

1. Andá a https://github.com/new
2. Nombre: `carrefour-monitor` (puede ser privado ✅)
3. Crealo vacío (sin README)
4. Subí estos archivos manteniendo la estructura:

```
carrefour-monitor/
├── monitor.py
└── .github/
    └── workflows/
        └── monitor.yml
```

Podés subirlos desde la interfaz web de GitHub arrastrando los archivos,
o con git:

```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/TU_USUARIO/carrefour-monitor.git
git push -u origin main
```

---

### Paso 2 — Configurar App Password de Gmail

> Necesitás esto para que GitHub Actions pueda mandar emails desde tu cuenta.

1. Andá a https://myaccount.google.com/security
2. Activá **Verificación en 2 pasos** (si no la tenés)
3. Buscá **Contraseñas de aplicaciones**
4. Creá una nueva → nombre: "Carrefour Monitor"
5. Copiá los 16 caracteres que aparecen (ej: `abcd efgh ijkl mnop`)

---

### Paso 3 — Agregar los Secrets en GitHub

En tu repo de GitHub:
**Settings → Secrets and variables → Actions → New repository secret**

Crear estos 3 secrets:

| Nombre | Valor |
|--------|-------|
| `GMAIL_SENDER` | tu_email@gmail.com |
| `GMAIL_PASSWORD` | el App Password de 16 chars |
| `GMAIL_RECIPIENT` | donde querés recibir el reporte (puede ser el mismo Gmail) |

---

### Paso 4 — Primer test manual

1. En tu repo → pestaña **Actions**
2. Clic en **Monitor Carrefour Descuentos Bancarios**
3. Clic en **Run workflow** → **Run workflow**
4. Esperá ~2 minutos
5. Revisá tu email 📬

Si el workflow se pone verde ✅ → todo funciona. A partir de ahí corre solo.

---

## Horario de ejecución

Por defecto corre a las **9:00 AM hora Argentina** todos los días.

Para cambiar el horario, editá esta línea en `monitor.yml`:

```yaml
- cron: "0 12 * * *"   # 12:00 UTC = 9:00 AM Argentina
```

Convertidor de zonas: https://crontab.guru

Ejemplos:
- 7:00 AM ARG → `"0 10 * * *"`
- 8:00 AM ARG → `"0 11 * * *"`
- 6:00 PM ARG → `"0 21 * * *"`

---

## Qué recibís por email

**Primer día:** listado completo de todas las promociones encontradas.

**Días siguientes sin cambios:**
```
✅ SIN CAMBIOS respecto al relevamiento anterior.
Promociones activas: 12
```

**Cuando hay cambios:**
```
⚠️ SE DETECTARON CAMBIOS

── NUEVAS PROMOCIONES (2) ──
➕ Banco Galicia | 20% de descuento | Martes y jueves...
➕ BBVA | 15% reintegro | Viernes...

── PROMOCIONES ELIMINADAS (1) ──
➖ Banco Nación | 10% descuento | Lunes...

── DETALLE DEL DIFF ──
- Banco Nación: descuento lunes 10%
+ Banco Galicia: descuento martes y jueves 20%
```

---

## Límites de GitHub Actions (plan gratuito)

| Recurso | Límite | Tu uso |
|---------|--------|--------|
| Minutos/mes | 2.000 | ~60 (30 días × 2 min) |
| Repos privados | ilimitados | 1 |
| Storage cache | 10 GB | < 1 MB |

Sobra ampliamente. ✅

---

## Problemas frecuentes

**El workflow falla con error de email**
→ Verificá que el App Password sea correcto (sin espacios)
→ Asegurate de que la verificación en 2 pasos esté activa

**"Host not in allowlist"**
→ El sitio de Carrefour puede estar bloqueando el scraping
→ Abrí un issue en el repo o contactame para actualizar el script

**No llega el email**
→ Revisá la carpeta Spam
→ En Gmail, buscá emails de tu propia dirección

**Quiero monitorear otro supermercado también**
→ Duplicá el archivo `monitor.yml` con otro nombre y otra URL en `monitor.py`
