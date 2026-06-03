"""
Monitor de Promociones Bancarias — Carrefour Argentina
Versión 100% gratuita: sin IA, comparación de texto pura.
Diseñado para correr en GitHub Actions.
"""

import os
import json
import hashlib
import datetime
import difflib
import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL = "https://www.carrefour.com.ar/descuentos-bancarios"
SNAPSHOT_FILE = Path("data/latest_snapshot.json")

# Credenciales desde variables de entorno (GitHub Secrets)
GMAIL_SENDER    = os.environ["GMAIL_SENDER"]
GMAIL_PASSWORD  = os.environ["GMAIL_PASSWORD"]
GMAIL_RECIPIENT = os.environ["GMAIL_RECIPIENT"]


# ──────────────────────────────────────────────
#  SCRAPING
# ──────────────────────────────────────────────

def scrape() -> tuple[str, list[str]]:
    """Devuelve (texto_limpio, lista_de_bloques_de_promo)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="es-AR",
            timezone_id="America/Argentina/Buenos_Aires",
        )
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    full_text = soup.get_text(separator="\n", strip=True)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)

    # Intentar extraer bloques individuales de promo
    blocks = extract_promo_blocks(soup)
    return full_text, blocks


def extract_promo_blocks(soup: BeautifulSoup) -> list[str]:
    """
    Heurística: busca contenedores repetitivos que parezcan cards de promo.
    Funciona con la mayoría de los sitios de retail argentinos.
    """
    candidates = []

    # Buscar por clases comunes de tarjetas/items
    for selector in ["article", "[class*='card']", "[class*='promo']",
                     "[class*='discount']", "[class*='bank']", "[class*='benefit']",
                     "li", "[class*='item']"]:
        elements = soup.select(selector)
        if 3 <= len(elements) <= 60:
            texts = [e.get_text(separator=" ", strip=True) for e in elements]
            texts = [t for t in texts if len(t) > 30]
            if texts:
                candidates.append(texts)

    # Devolver el conjunto más probable (mayor cantidad de items con contenido similar en largo)
    if not candidates:
        return []
    best = max(candidates, key=lambda lst: len(lst))
    return best


# ──────────────────────────────────────────────
#  SNAPSHOT / DIFF
# ──────────────────────────────────────────────

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_previous() -> dict | None:
    if SNAPSHOT_FILE.exists():
        return json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    return None


def save_snapshot(text: str, blocks: list[str]):
    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "date": datetime.date.today().isoformat(),
        "hash": hash_text(text),
        "text": text,
        "blocks": blocks,
    }
    SNAPSHOT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_diff(old_text: str, new_text: str) -> str:
    """Diff legible línea a línea."""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile="anterior", tofile="actual",
        lineterm="", n=2
    )
    return "\n".join(list(diff)[:200])   # máx 200 líneas de diff


def find_new_removed_blocks(old_blocks: list[str], new_blocks: list[str]) -> tuple[list, list]:
    """Detecta bloques (cards de promo) que aparecieron o desaparecieron."""
    old_set = set(old_blocks)
    new_set = set(new_blocks)
    added   = [b for b in new_blocks if b not in old_set]
    removed = [b for b in old_blocks if b not in new_set]
    return added, removed


# ──────────────────────────────────────────────
#  REPORTE DE TEXTO
# ──────────────────────────────────────────────

def build_report(
    changed: bool,
    added: list[str],
    removed: list[str],
    diff_text: str,
    current_blocks: list[str],
    is_first_run: bool,
    date_str: str,
) -> tuple[str, str]:
    """Devuelve (subject, body_text)."""

    lines = []
    lines.append(f"MONITOR CARREFOUR — Descuentos Bancarios")
    lines.append(f"Relevamiento: {date_str}")
    lines.append(f"Fuente: {URL}")
    lines.append("=" * 55)

    if is_first_run:
        lines.append("\n✅ PRIMER RELEVAMIENTO — baseline guardado.\n")
        lines.append(f"Se encontraron {len(current_blocks)} bloques de promociones.\n")
        if current_blocks:
            lines.append("── PROMOCIONES DETECTADAS ──")
            for i, b in enumerate(current_blocks, 1):
                lines.append(f"\n[{i}] {b[:300]}")
        subject = f"[Carrefour Monitor] Primer relevamiento — {datetime.date.today().isoformat()}"

    elif not changed:
        lines.append("\n✅ SIN CAMBIOS respecto al relevamiento anterior.\n")
        lines.append(f"Promociones activas: {len(current_blocks)}")
        subject = f"[Carrefour Monitor] ✅ Sin cambios — {datetime.date.today().isoformat()}"

    else:
        lines.append("\n⚠️  SE DETECTARON CAMBIOS\n")
        subject = f"[Carrefour Monitor] ⚠️ CAMBIOS detectados — {datetime.date.today().isoformat()}"

        if added:
            lines.append(f"── NUEVAS PROMOCIONES ({len(added)}) ──")
            for b in added:
                lines.append(f"\n➕ {b[:400]}")
            lines.append("")

        if removed:
            lines.append(f"── PROMOCIONES ELIMINADAS ({len(removed)}) ──")
            for b in removed:
                lines.append(f"\n➖ {b[:400]}")
            lines.append("")

        if not added and not removed:
            lines.append("(No se detectaron cards nuevas/eliminadas — el cambio puede ser en el texto de una promo existente)\n")

        if diff_text:
            lines.append("── DETALLE DEL DIFF (primeras líneas) ──")
            lines.append(diff_text[:2000])

    lines.append("\n" + "=" * 55)
    lines.append("Reporte generado automáticamente por carrefour_monitor")

    return subject, "\n".join(lines)


def build_html(body_text: str, changed: bool, is_first_run: bool) -> str:
    banner_style = (
        "background:#fff3cd;border:1px solid #ffc107;" if changed and not is_first_run
        else "background:#d4edda;border:1px solid #28a745;"
    )
    banner_icon = "⚠️" if changed and not is_first_run else "✅"
    banner_msg  = "Se detectaron cambios" if changed and not is_first_run else (
        "Primer relevamiento guardado" if is_first_run else "Sin cambios"
    )

    escaped = body_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Colorear líneas del diff
    colored = []
    for line in escaped.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            colored.append(f'<span style="color:#155724;background:#d4edda;display:block">{line}</span>')
        elif line.startswith("-") and not line.startswith("---"):
            colored.append(f'<span style="color:#721c24;background:#f8d7da;display:block">{line}</span>')
        else:
            colored.append(f'<span style="display:block">{line}</span>')
    pre_content = "\n".join(colored)

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  body{{font-family:Arial,sans-serif;color:#333;max-width:720px;margin:auto;padding:24px}}
  h1{{color:#003087;border-bottom:2px solid #003087;padding-bottom:8px;font-size:20px}}
  .banner{{padding:12px 16px;border-radius:6px;margin-bottom:20px;{banner_style}}}
  pre{{background:#f8f9fa;border:1px solid #dee2e6;border-radius:6px;padding:16px;
       font-size:13px;overflow-x:auto;white-space:pre-wrap;word-break:break-word}}
  .footer{{margin-top:24px;font-size:11px;color:#888;border-top:1px solid #eee;padding-top:10px}}
</style></head><body>
<h1>🏪 Monitor Carrefour — Descuentos Bancarios</h1>
<div class="banner">{banner_icon} <strong>{banner_msg}</strong></div>
<pre>{pre_content}</pre>
<div class="footer">Fuente: <a href="{URL}">{URL}</a> · Generado automáticamente</div>
</body></html>"""


# ──────────────────────────────────────────────
#  EMAIL
# ──────────────────────────────────────────────

def send_email(subject: str, body_text: str, body_html: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = GMAIL_RECIPIENT
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html",  "utf-8"))
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(GMAIL_SENDER, GMAIL_PASSWORD)
        s.sendmail(GMAIL_SENDER, GMAIL_RECIPIENT, msg.as_string())
    print(f"✅ Email enviado a {GMAIL_RECIPIENT}")


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────

def main():
    date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"\n{'='*50}\n  Carrefour Monitor — {date_str}\n{'='*50}\n")

    print("🌐 Scrapeando...")
    current_text, current_blocks = scrape()
    current_hash = hash_text(current_text)
    print(f"   Texto extraído: {len(current_text)} chars, {len(current_blocks)} bloques")

    previous = load_previous()
    is_first_run = previous is None

    changed = False
    added, removed, diff_text = [], [], ""

    if not is_first_run:
        prev_hash   = previous.get("hash", "")
        prev_text   = previous.get("text", "")
        prev_blocks = previous.get("blocks", [])
        changed = current_hash != prev_hash
        print(f"🔄 Cambios: {'SÍ' if changed else 'NO'}")
        if changed:
            added, removed = find_new_removed_blocks(prev_blocks, current_blocks)
            diff_text = compute_diff(prev_text, current_text)
            print(f"   Nuevas: {len(added)} | Eliminadas: {len(removed)}")
    else:
        print("📋 Primera ejecución — guardando baseline")

    save_snapshot(current_text, current_blocks)
    print("💾 Snapshot guardado")

    subject, body_text = build_report(
        changed, added, removed, diff_text,
        current_blocks, is_first_run, date_str
    )
    body_html = build_html(body_text, changed, is_first_run)

    print(f"\n{body_text}\n")
    send_email(subject, body_text, body_html)
    print("✅ Listo\n")


if __name__ == "__main__":
    main()
