"""
Genera el tablero para inversionistas de CerbIA como un solo archivo HTML.

Los gráficos se dibujan en SVG desde Python, sin librerías externas, así que el
archivo abre sin internet. El selector de escenario cambia todas las cifras.

Uso:  python generar_dashboard.py
Salida: dashboard_cerbia.html (archivo completo para abrir en el navegador)
        dashboard_cerbia_artifact.html (misma página, sin <html>/<head>, para publicar)
"""

import base64
import html
import math
from pathlib import Path

import modelo_cerbia as M

AQUI = Path(__file__).parent
RES = M.correr_todo()
S = M.SUPUESTOS
INV = RES["inversion"]
ORDEN = ["pesimista", "base", "optimista"]


# ------------------------------------------------------------------ formato
def miles(x, dec=0):
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pesos(x):
    return ("−" if x < 0 else "") + "$" + miles(abs(x))


def millones(x, dec=1):
    return ("−" if x < 0 else "") + "$" + miles(abs(x) / 1e6, dec) + " M"


def esc(t):
    return html.escape(str(t), quote=True)


def fecha(m):
    if m is None:
        return "después del mes 36"
    nombres = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{nombres[(m - 1) % 12]} de {S['anio_inicio'] + (m - 1) // 12}"


def mes_txt(m):
    if m is None:
        return "después del mes 36"
    nombres = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"mes {m} ({nombres[(m - 1) % 12]} {S['anio_inicio'] + (m - 1) // 12})"


# ------------------------------------------------------------------ escalas
def ticks(lo, hi, n=5):
    span = hi - lo if hi > lo else 1
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    paso = min((k * mag for k in (1, 2, 2.5, 5, 10) if k * mag >= raw), default=10 * mag)
    a = math.floor(lo / paso) * paso
    b = math.ceil(hi / paso) * paso
    out, v = [], a
    while v <= b + paso / 2:
        out.append(v)
        v += paso
    return out


# ------------------------------------------------------------------ gráficos SVG
W, H = 640, 300
PAD = {"l": 62, "r": 18, "t": 30, "b": 38}


def svg_lineas(series, ref=None, marca=None, fmt_y=lambda v: miles(v / 1e6), titulo_y="Millones COP",
               area_idx=None):
    """series: lista de (nombre, clase_css, valores[36], punteada)."""
    todos = [v for _, _, vals, _ in series for v in vals]
    if ref:
        todos += [ref[0]]
    lo, hi = min(0, min(todos)), max(todos)
    ty = ticks(lo, hi)
    lo, hi = ty[0], ty[-1]
    n = len(series[0][2])
    iw, ih = W - PAD["l"] - PAD["r"], H - PAD["t"] - PAD["b"]
    X = lambda i: PAD["l"] + iw * i / (n - 1)
    Y = lambda v: PAD["t"] + ih * (1 - (v - lo) / (hi - lo))
    p = [f'<div class="chartwrap"><svg viewBox="0 0 {W} {H}" role="img" class="chart">']
    for t in ty:
        y = Y(t)
        cls = "zero" if abs(t) < 1e-9 else "grid"
        p.append(f'<line class="{cls}" x1="{PAD["l"]}" x2="{W - PAD["r"]}" y1="{y:.1f}" y2="{y:.1f}"/>')
        p.append(f'<text class="tick" x="{PAD["l"] - 8}" y="{y + 4:.1f}" text-anchor="end">{fmt_y(t)}</text>')
    for m in (1, 6, 12, 18, 24, 30, 36):
        p.append(f'<text class="tick" x="{X(m - 1):.1f}" y="{H - PAD["b"] + 18}" text-anchor="middle">{m}</text>')
    p.append(f'<text class="axis" x="{W - PAD["r"]}" y="{H - 4}" text-anchor="end">Mes</text>')
    p.append(f'<text class="axis" x="4" y="12">{esc(titulo_y)}</text>')
    for a in (12, 24):
        x = X(a - 0.5)
        p.append(f'<line class="year" x1="{x:.1f}" x2="{x:.1f}" y1="{PAD["t"]}" y2="{H - PAD["b"]}"/>')
    if ref:
        val, etiqueta = ref
        y = Y(val)
        p.append(f'<line class="ref" x1="{PAD["l"]}" x2="{W - PAD["r"]}" y1="{y:.1f}" y2="{y:.1f}"/>')
        p.append(f'<text class="reflabel" x="{PAD["l"] + 6}" y="{y - 6:.1f}">{esc(etiqueta)}</text>')
    for idx, (nombre, cls, vals, punteada) in enumerate(series):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
        if area_idx == idx:
            base = Y(max(lo, 0))
            p.append(f'<polygon class="area {cls}" points="{X(0):.1f},{base:.1f} {pts} {X(n - 1):.1f},{base:.1f}"/>')
        dash = ' stroke-dasharray="6 5"' if punteada else ""
        p.append(f'<polyline class="line {cls}" points="{pts}"{dash}/>')
        for i, v in enumerate(vals):
            p.append(f'<circle class="hit" cx="{X(i):.1f}" cy="{Y(v):.1f}" r="7">'
                     f'<title>{esc(nombre)} · mes {i + 1}: {esc(fmt_y(v))}</title></circle>')
        p.append(f'<circle class="dot {cls}" cx="{X(n - 1):.1f}" cy="{Y(vals[-1]):.1f}" r="4"/>')
    if marca:
        i, v, etiqueta, cls = marca
        x, y = X(i), Y(v)
        anchor = "start" if i < n * 0.6 else "end"
        dx = 10 if anchor == "start" else -10
        p.append(f'<circle class="mark {cls}" cx="{x:.1f}" cy="{y:.1f}" r="6"/>')
        p.append(f'<text class="marklabel" x="{x + dx:.1f}" y="{y + (18 if v < (hi + lo) / 2 else -10):.1f}" '
                 f'text-anchor="{anchor}">{esc(etiqueta)}</text>')
    p.append("</svg></div>")
    return "".join(p)


def barras_h(items, fmt=lambda v: millones(v, 1), ancho=W, alto_fila=26):
    """items: (etiqueta, valor, clase)."""
    lab_w, val_w = 230, 92
    h = alto_fila * len(items) + 8
    vmax = max(v for _, v, _ in items)
    iw = ancho - lab_w - val_w
    p = [f'<svg viewBox="0 0 {ancho} {h}" role="img" class="chart">']
    for k, (et, v, cls) in enumerate(items):
        y = 4 + k * alto_fila
        w = iw * v / vmax
        p.append(f'<text class="cat" x="{lab_w - 10}" y="{y + alto_fila * 0.62:.1f}" text-anchor="end">{esc(et)}</text>')
        p.append(f'<rect class="bar {cls}" x="{lab_w}" y="{y + 4}" width="{w:.1f}" height="{alto_fila - 9}" rx="3">'
                 f'<title>{esc(et)}: {esc(fmt(v))}</title></rect>')
        p.append(f'<text class="val" x="{lab_w + w + 8:.1f}" y="{y + alto_fila * 0.62:.1f}">{esc(fmt(v))}</text>')
    p.append("</svg>")
    return "".join(p)


def barra_apilada(partes, total_txt, fmt=None):
    fmt = fmt or pesos
    """Una barra 100 % con leyenda debajo. partes: (etiqueta, valor, clase)."""
    total = sum(v for _, v, _ in partes)
    segs, x = [], 0.0
    for et, v, cls in partes:
        w = 100 * v / total
        segs.append(f'<span class="seg {cls}" style="width:{w:.2f}%" title="{esc(et)}: {esc(fmt(v))}"></span>')
        x += w
    leyenda = "".join(
        f'<li><i class="sw {cls}"></i><span>{esc(et)}</span><b>{esc(fmt(v))}</b><em>{100 * v / total:.0f}%</em></li>'
        for et, v, cls in partes)
    return (f'<div class="stack" role="img" aria-label="{esc(total_txt)}">{"".join(segs)}</div>'
            f'<ul class="legend">{leyenda}</ul>')


# ------------------------------------------------------------------ bloques por escenario
def bloque_escenario(k):
    e = RES["escenarios"][k]
    ms, an, mt = e["mensual"], e["anual"], e["metricas"]
    v = e["variaciones"]
    sin_inv = M.proyectar(k, 0)
    a3 = an[2]
    margen_ebitda = a3["ebitda"] / a3["ingresos"]

    kpis = [
        ("Ingresos año 3", millones(a3["ingresos"]), f"{miles(a3['sedes_activas_cierre'])} sedes activas al cierre"),
        ("EBITDA año 3", millones(a3["ebitda"]), f"Margen EBITDA {miles(100 * margen_ebitda, 1)}%"),
        ("EBITDA positivo desde", f"Mes {mt['mes_ebitda_positivo']}", fecha(mt["mes_ebitda_positivo"])),
        ("Caja más baja", millones(mt["caja_minima"]), f"en el mes {mt['mes_caja_minima']}, nunca negativa"),
        ("Caja al mes 36", millones(ms[-1]["caja"]), f"de {millones(INV, 0)} invertidos"),
        ("Ingreso anual recurrente", millones(mt["arr_final"]), "cuotas del mes 36 × 12"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><span class="kl">{esc(a)}</span><strong>{esc(b)}</strong><span class="ks">{esc(c)}</span></div>'
        for a, b, c in kpis)

    caja = svg_lineas(
        [("Caja con la inversión", "s-gold", [r["caja"] for r in ms], False),
         ("Caja sin inversión", "s-muted", [r["caja"] for r in sin_inv], True)],
        marca=(mt["mes_caja_minima"] - 1, mt["caja_minima"],
               f"Mínimo: {millones(mt['caja_minima'], 0)}", "s-gold"),
        area_idx=0)

    ingresos_costos = svg_lineas(
        [("Ingresos", "s-gold", [r["ingresos"] for r in ms], False),
         ("Costos de operación (fijos + nube)", "s-ink", [r["fijos"] + r["costo_nube"] for r in ms], False)],
        marca=(mt["mes_ebitda_positivo"] - 1, ms[mt["mes_ebitda_positivo"] - 1]["ingresos"],
               f"Mes {mt['mes_ebitda_positivo']}: ingresos superan costos", "s-gold") if mt["mes_ebitda_positivo"] else None)

    mes_pe = next((r["mes"] for r in ms if r["sedes_activas"] >= mt["punto_equilibrio_sedes"]), None)
    sedes = svg_lineas(
        [("Sedes activas", "s-gold", [r["sedes_activas"] for r in ms], False)],
        ref=(mt["punto_equilibrio_sedes"], f"Punto de equilibrio: {mt['punto_equilibrio_sedes']} sedes"),
        marca=(mes_pe - 1, ms[mes_pe - 1]["sedes_activas"], f"Lo cruza en el mes {mes_pe}", "s-gold") if mes_pe else None,
        fmt_y=lambda x: miles(x), titulo_y="Sedes", area_idx=0)

    cuota = S["cuota_mes"] * (1 + v["p"])
    equipo = S["costo_equipo"] * (1 + v["v"]) / S["vida_util_equipo"]
    nube = S["nube_soporte_mes"] * (1 + v["v"])
    cuota_html = barra_apilada(
        [("Equipo (depreciación mensual)", equipo, "c-ink"),
         ("Nube y soporte", nube, "c-muted"),
         ("Margen de contribución", cuota - equipo - nube, "c-gold")],
        f"Composición de la cuota de {pesos(cuota)}")

    return {
        "kpis": kpi_html, "caja": caja, "ingresos_costos": ingresos_costos, "sedes": sedes,
        "cuota": cuota_html, "cuota_total": pesos(cuota),
        "margen_pct": miles(100 * (cuota - equipo - nube) / cuota, 1),
        "estados": estados(an), "mes_pe": mes_pe,
    }


def fila(nombre, vals, cls=""):
    celdas = "".join(f'<td class="{"neg" if v < 0 else ""}">{esc(millones(v))}</td>' for v in vals)
    return f'<tr class="{cls}"><th scope="row">{esc(nombre)}</th>{celdas}</tr>'


def estados(an):
    col = lambda k: [a[k] for a in an]
    cab = '<tr><th></th>' + "".join(f'<th scope="col">Año {a["anio"]}<span>{S["anio_inicio"] + a["anio"] - 1}</span></th>' for a in an) + "</tr>"
    resultados = [
        fila("Ingresos por alquiler", col("ingresos"), "strong"),
        fila("Nube y soporte", [-x for x in col("costo_nube")]),
        fila("Depreciación de equipos", [-x for x in col("depreciacion")]),
        fila("Utilidad bruta", col("utilidad_bruta"), "sub"),
        fila("Nómina", [-x for x in col("nomina")]),
        fila("Gastos operativos", [-x for x in col("gastos_operativos")]),
        fila("Automatización", [-x for x in col("automatizacion")]),
        fila("Utilidad operacional (EBIT)", col("ebit"), "sub"),
        fila("Impuesto de renta (35%)", [-x for x in col("impuesto")]),
        fila("Utilidad neta", col("utilidad_neta"), "total"),
        fila("EBITDA", col("ebitda"), "memo"),
    ]
    flujo = [
        fila("Caja inicial", col("caja_inicial")),
        fila("EBITDA", col("ebitda")),
        fila("Pago de impuesto", [-a["flujo_operativo"] + a["ebitda"] for a in an]),
        fila("Flujo de operación", col("flujo_operativo"), "sub"),
        fila("Compra de equipos (inversión)", [-x for x in col("capex")]),
        fila("Flujo neto del año", col("flujo_neto"), "sub"),
        fila("Caja final", col("caja_final"), "total"),
    ]
    balance = [
        fila("Caja", col("caja_final")),
        fila("Equipos instalados (neto)", col("ppe_neto")),
        fila("Total activos", [a["caja_final"] + a["ppe_neto"] for a in an], "sub"),
        fila("Impuesto por pagar", col("renta_por_pagar")),
        fila("Capital aportado", col("capital")),
        fila("Utilidades (pérdidas) acumuladas", col("utilidades_retenidas")),
        fila("Total pasivo y patrimonio",
             [a["renta_por_pagar"] + a["capital"] + a["utilidades_retenidas"] for a in an], "total"),
    ]
    t = lambda filas: f'<div class="tablewrap"><table class="fin"><thead>{cab}</thead><tbody>{"".join(filas)}</tbody></table></div>'
    return {"resultados": t(resultados), "flujo": t(flujo), "balance": t(balance)}


# ------------------------------------------------------------------ bloques fijos
def uso_de_fondos():
    ms = RES["escenarios"]["base"]["mensual"]
    tope = RES["escenarios"]["base"]["metricas"]["mes_caja_minima"]
    rs = [r for r in ms if r["mes"] <= tope]
    equipos = sum(r["capex"] for r in rs)
    operacion = -sum(r["ebitda"] - r["pago_renta"] for r in rs)
    reserva = INV - equipos - operacion
    return barra_apilada(
        [("Operación hasta el punto de equilibrio", operacion, "c-ink"),
         ("Equipos para las sedes nuevas", equipos, "c-gold"),
         ("Reserva para el escenario pesimista", reserva, "c-muted")],
        f"Uso de los {pesos(INV)}", fmt=lambda v: millones(v, 0)), tope, equipos, operacion, reserva


def costos_fijos():
    items = [
        ("Líder técnico (CTO)", 7_975_000, "c-ink"), ("Desarrollador software e IA", 6_090_000, "c-ink"),
        ("Ejecutivo comercial B2B", 3_700_000, "c-ink"), ("Ingeniero de soporte y ensamble", 3_256_000, "c-ink"),
        ("Arriendo oficina y taller", 2_800_000, "c-muted"), ("Gestor administrativo", 2_100_000, "c-ink"),
        ("Marketing y pauta B2B", 1_800_000, "c-muted"), ("Contabilidad y revisoría", 900_000, "c-muted"),
        ("Herramientas cloud y desarrollo", 800_000, "c-muted"), ("Servicios públicos e internet", 650_000, "c-muted"),
        ("Transporte comercial", 600_000, "c-muted"), ("Servicios legales y marcas", 500_000, "c-muted"),
        ("Software administrativo", 450_000, "c-muted"), ("Seguros y pólizas", 350_000, "c-muted"),
    ]
    assert sum(v for _, v, _ in items) == S["nomina_mes"] + S["gastos_operativos_mes"]
    return '<div class="costs">' + barras_h(items, fmt=lambda v: millones(v, 2), ancho=900, alto_fila=26) + '</div>'


def tabla_escenarios():
    filas = [
        ("Sedes nuevas por mes", lambda e: f"{miles(100 * e['variaciones']['q'], 0)}%" if e['variaciones']['q'] else "Plan"),
        ("Precio", lambda e: f"{miles(100 * e['variaciones']['p'], 0)}%" if e['variaciones']['p'] else "Plan"),
        ("Sedes activas mes 36", lambda e: miles(e["metricas"]["sedes_finales"])),
        ("Ingresos año 3", lambda e: millones(e["anual"][2]["ingresos"])),
        ("EBITDA año 3", lambda e: millones(e["anual"][2]["ebitda"])),
        ("Utilidad neta año 3", lambda e: millones(e["anual"][2]["utilidad_neta"])),
        ("EBITDA positivo desde", lambda e: f"Mes {e['metricas']['mes_ebitda_positivo']}"),
        ("Caja más baja", lambda e: millones(e["metricas"]["caja_minima"])),
        ("Caja al mes 36", lambda e: millones(e["mensual"][-1]["caja"])),
    ]
    cab = "<tr><th></th>" + "".join(f'<th scope="col" class="h-{k}">{RES["escenarios"][k]["nombre"]}</th>' for k in ORDEN) + "</tr>"
    cuerpo = "".join(
        f'<tr><th scope="row">{esc(n)}</th>' + "".join(f'<td class="c-{k}">{esc(f(RES["escenarios"][k]))}</td>' for k in ORDEN) + "</tr>"
        for n, f in filas)
    return f'<div class="tablewrap"><table class="fin esc"><thead>{cab}</thead><tbody>{cuerpo}</tbody></table></div>'


# ------------------------------------------------------------------ página
CSS = r"""
:root{
  /* Layout: banda de marca arriba, fila de indicadores, rejilla de dos columnas que baja a una en el celular */
  --bg:#f4f6f9; --surface:#ffffff; --ink:#011a3d; --muted:#5b6b7d; --line:#dde3ea;
  --gold:#a8831a; --gold-fill:#c9a227; --navy:#011a3d; --on-navy:#ffffff; --on-navy-muted:#c8d1d9;
  --area:rgba(201,162,39,.16); --neg:#b3261e; --pos:#1e7a4f; --chip:#eef1f5;
  --display:"Archivo Black","Archivo","Arial Black",Arial,sans-serif;
  --body:"Inter","Segoe UI",Roboto,Arial,sans-serif;
  color-scheme:light;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#05122a; --surface:#0b1f3f; --ink:#e8eef6; --muted:#9db0c8; --line:#1d3558;
  --gold:#e0bc4a; --gold-fill:#c9a227; --navy:#020d22; --on-navy:#ffffff; --on-navy-muted:#aebdd1;
  --area:rgba(224,188,74,.14); --neg:#f08a80; --pos:#6fd3a0; --chip:#132b52; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#05122a; --surface:#0b1f3f; --ink:#e8eef6; --muted:#9db0c8; --line:#1d3558;
  --gold:#e0bc4a; --gold-fill:#c9a227; --navy:#020d22; --on-navy:#ffffff; --on-navy-muted:#aebdd1;
  --area:rgba(224,188,74,.14); --neg:#f08a80; --pos:#6fd3a0; --chip:#132b52; color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 var(--body)}
.wrap{max-width:1180px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
header.band{background:var(--navy);color:var(--on-navy);border-bottom:6px solid var(--gold-fill)}
header.band .wrap{display:flex;gap:24px;align-items:center;padding-block:22px;flex-wrap:wrap}
.logo{background:#fff;border-radius:12px;padding:6px 12px;flex:none}
.logo img{height:64px;display:block}
.hgroup{flex:1;min-width:0}
.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--gold-fill);font-weight:700}
h1{font-family:var(--display);font-size:clamp(26px,4vw,40px);line-height:1.05;margin:4px 0 6px;text-wrap:balance}
.lead{color:var(--on-navy-muted);margin:0;max-width:70ch}
.ask{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.18);border-radius:12px;padding:12px 16px;flex:none}
.ask span{display:block;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--on-navy-muted)}
.ask strong{font-family:var(--display);font-size:28px;color:var(--gold-fill);font-variant-numeric:tabular-nums}
.ask em{display:block;font-style:normal;font-size:12px;color:var(--on-navy-muted)}
main.wrap{padding-block:20px 40px;display:grid;grid-template-columns:minmax(0,1fr);gap:18px}
.bar{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.seg-ctl{display:inline-flex;background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:4px}
.seg-ctl button{font:600 14px var(--body);border:0;background:transparent;color:var(--muted);padding:8px 16px;border-radius:999px;cursor:pointer}
.seg-ctl button[aria-pressed="true"]{background:var(--ink);color:var(--bg)}
.seg-ctl button:focus-visible,.tabs button:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
.note{color:var(--muted);font-size:13px;margin:0}
.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:grid;gap:2px;min-width:0}
.kl{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.kpi strong{font-family:var(--display);font-size:22px;font-weight:400;font-variant-numeric:tabular-nums;white-space:nowrap}
.ks{font-size:12px;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px 18px;min-width:0;display:grid;grid-template-columns:minmax(0,1fr);gap:8px;align-content:start}
.card h2{font-family:var(--display);font-weight:400;font-size:19px;margin:0;text-wrap:balance}
.card p{margin:0;color:var(--muted);font-size:14px}
.card .key{color:var(--ink);font-weight:600}
.wide{grid-column:1/-1}
.chart{width:100%;height:auto;display:block}
.chartwrap{overflow-x:auto}
.costs{max-width:900px}
.chart text{font-family:var(--body)}
.chart .grid{stroke:var(--line);stroke-width:1}
.chart .zero{stroke:var(--muted);stroke-width:1.2}
.chart .year{stroke:var(--line);stroke-dasharray:3 4}
.chart .tick,.chart .axis{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
.chart .ref{stroke:var(--neg);stroke-width:1.5;stroke-dasharray:6 4}
.chart .reflabel{fill:var(--neg);font-size:12px;font-weight:600}
.chart .line{fill:none;stroke-width:2.6;stroke-linejoin:round;stroke-linecap:round}
.chart .line.s-gold{stroke:var(--gold-fill)} .chart .line.s-ink{stroke:var(--ink)} .chart .line.s-muted{stroke:var(--muted)}
.chart .area.s-gold{fill:var(--area);stroke:none}
.chart .dot.s-gold,.chart .mark.s-gold{fill:var(--gold-fill)} .chart .dot.s-ink{fill:var(--ink)} .chart .dot.s-muted{fill:var(--muted)}
.chart .mark{stroke:var(--surface);stroke-width:2.5}
.chart .marklabel{fill:var(--ink);font-size:12.5px;font-weight:700}
.chart .hit{fill:transparent;stroke:none}
.chart .cat{fill:var(--ink);font-size:12.5px}
.chart .val{fill:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
.chart .bar.c-ink{fill:var(--ink)} .chart .bar.c-muted{fill:var(--muted);opacity:.55}
.legend-inline{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--muted);margin:0;padding:0;list-style:none}
.legend-inline i{display:inline-block;width:18px;height:3px;border-radius:2px;vertical-align:middle;margin-right:6px}
.legend-inline i.dash{background:repeating-linear-gradient(90deg,var(--muted) 0 6px,transparent 6px 10px)!important}
.stack{display:flex;height:34px;border-radius:8px;overflow:hidden;border:1px solid var(--line)}
.seg{display:block;height:100%}
.c-ink{background:var(--ink)} .c-gold{background:var(--gold-fill)} .c-muted{background:var(--muted);opacity:.55}
.legend{list-style:none;margin:6px 0 0;padding:0;display:grid;gap:6px}
.legend li{display:grid;grid-template-columns:14px 1fr auto 44px;gap:10px;align-items:center;font-size:14px}
.legend b{font-variant-numeric:tabular-nums;font-weight:600}
.legend em{font-style:normal;color:var(--muted);text-align:right;font-variant-numeric:tabular-nums}
.sw{width:14px;height:14px;border-radius:3px;display:block}
.tabs{display:flex;gap:6px;flex-wrap:wrap}
.tabs button{font:600 13px var(--body);border:1px solid var(--line);background:var(--chip);color:var(--ink);padding:7px 14px;border-radius:8px;cursor:pointer}
.tabs button[aria-selected="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.tablewrap{overflow-x:auto}
table.fin{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:14px;min-width:520px}
table.fin th,table.fin td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
table.fin th[scope="row"]{text-align:left;font-weight:500;white-space:normal}
table.fin thead th{font-size:13px;color:var(--muted);font-weight:700}
table.fin thead th span{display:block;font-weight:400;font-size:11px}
table.fin tr.sub th,table.fin tr.sub td{font-weight:700}
table.fin tr.strong th,table.fin tr.strong td{font-weight:700}
table.fin tr.total th,table.fin tr.total td{font-weight:800;border-top:2px solid var(--ink);border-bottom:2px solid var(--ink)}
table.fin tr.memo th,table.fin tr.memo td{color:var(--muted);font-style:italic}
table.fin td.neg{color:var(--neg)}
table.esc td.c-base,table.esc th.h-base{background:var(--chip)}
.unit{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.unit div{border-left:3px solid var(--gold-fill);padding:2px 0 2px 10px;min-width:0}
.unit strong{display:block;font-family:var(--display);font-weight:400;font-size:20px;font-variant-numeric:tabular-nums}
.unit span{font-size:12.5px;color:var(--muted)}
footer.wrap{color:var(--muted);font-size:12.5px;padding-block:0 32px}
footer ul{margin:6px 0 0;padding-left:18px;display:grid;gap:3px;max-width:100ch}
@media (max-width:1000px){.kpis{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:760px){.grid{grid-template-columns:minmax(0,1fr)}.unit{grid-template-columns:repeat(2,minmax(0,1fr))}.ask{width:100%}}
@media (max-width:480px){.chartwrap .chart{min-width:560px}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.kpi strong{font-size:19px}.legend li{grid-template-columns:14px 1fr auto}.legend em{display:none}}
@media (prefers-reduced-motion:no-preference){.seg-ctl button,.tabs button{transition:background .15s,color .15s}}
"""

JS = r"""
(function(){
  const btns=document.querySelectorAll('[data-esc]');
  const panes=document.querySelectorAll('[data-pane]');
  function show(k){
    btns.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.esc===k)));
    panes.forEach(p=>{p.hidden=p.dataset.pane!==k});
    try{localStorage.setItem('cerbia-esc',k)}catch(e){}
  }
  btns.forEach(b=>b.addEventListener('click',()=>show(b.dataset.esc)));
  let ini='base'; try{ini=localStorage.getItem('cerbia-esc')||'base'}catch(e){}
  show(ini);
  document.querySelectorAll('[data-tabs]').forEach(g=>{
    const tb=g.querySelectorAll('[role="tab"]'), tp=g.querySelectorAll('[role="tabpanel"]');
    tb.forEach(b=>b.addEventListener('click',()=>{
      tb.forEach(x=>x.setAttribute('aria-selected',String(x===b)));
      tp.forEach(p=>{p.hidden=p.id!==b.getAttribute('aria-controls')});
    }));
  });
})();
"""


def pagina(completa=True):
    logo = base64.b64encode((AQUI / "img" / "logo.png").read_bytes()).decode()
    bloques = {k: bloque_escenario(k) for k in ORDEN}
    fondos, mes_tope, equipos, operacion, reserva = uso_de_fondos()
    base = RES["escenarios"]["base"]
    mt = base["metricas"]

    def pane(k, contenido):
        return f'<div data-pane="{k}" hidden>{contenido}</div>'

    def por_esc(fn):
        return "".join(pane(k, fn(k, bloques[k])) for k in ORDEN)

    def estados_html(k, b):
        return f'''<div data-tabs>
          <div class="tabs" role="tablist">
            <button type="button" role="tab" aria-selected="true" aria-controls="er-{k}">Estado de resultados</button>
            <button type="button" role="tab" aria-selected="false" aria-controls="fc-{k}">Flujo de caja</button>
            <button type="button" role="tab" aria-selected="false" aria-controls="bg-{k}">Balance general</button>
          </div>
          <div role="tabpanel" id="er-{k}">{b["estados"]["resultados"]}</div>
          <div role="tabpanel" id="fc-{k}" hidden>{b["estados"]["flujo"]}</div>
          <div role="tabpanel" id="bg-{k}" hidden>{b["estados"]["balance"]}</div>
        </div>'''

    cuerpo = f'''
<header class="band">
  <div class="wrap">
    <div class="logo"><img src="data:image/png;base64,{logo}" alt="CerbIA"></div>
    <div class="hgroup">
      <div class="eyebrow">Tablero para inversionistas · Proyección {S["anio_inicio"]}–{S["anio_inicio"] + 2}</div>
      <h1>CerbIA: control de acceso con IA en alquiler</h1>
      <p class="lead">Las pymes de Bogotá alquilan control de acceso con rostro, tarjeta y análisis de comportamiento por {pesos(S["cuota_mes"])} al mes por sede de 80 m², sin pagar el equipo de entrada. Este tablero muestra cuánto dinero necesita la empresa, en qué se usa y cuándo empieza a ganar.</p>
    </div>
    <div class="ask"><span>Inversión que buscamos</span><strong>{millones(INV, 0)}</strong><em>≈ USD {miles(INV / 4000 / 1000)} mil · alcanza aun en el escenario pesimista</em></div>
  </div>
</header>
<main class="wrap">
  <div class="bar">
    <div class="seg-ctl" role="group" aria-label="Escenario">
      <button type="button" data-esc="pesimista" aria-pressed="false">Pesimista</button>
      <button type="button" data-esc="base" aria-pressed="true">Base</button>
      <button type="button" data-esc="optimista" aria-pressed="false">Optimista</button>
    </div>
    <p class="note">Pesimista: 20% menos sedes, precio −5%, costos variables +10% y fijos +5%. Optimista: 20% más sedes, precio +5%, costos variables −5%.</p>
  </div>

  {por_esc(lambda k, b: f'<section class="kpis" aria-label="Indicadores">{b["kpis"]}</section>')}

  <div class="grid">
    <section class="card">
      <h2>La caja nunca se queda en cero</h2>
      <p>Sin inversión la caja caería hasta {millones(-RES["necesidad_base"], 0)} en el escenario base. Con {millones(INV, 0)} el punto más bajo queda positivo y desde ahí la caja crece.</p>
      <ul class="legend-inline"><li><i style="background:var(--gold-fill)"></i>Con la inversión</li><li><i class="dash"></i>Sin inversión</li></ul>
      {por_esc(lambda k, b: b["caja"])}
    </section>
    <section class="card">
      <h2>Cuándo los ingresos superan los costos</h2>
      <p>Los costos de operación son casi todos fijos ({millones(S["nomina_mes"] + S["gastos_operativos_mes"], 1)} al mes). Cada sede nueva suma ingresos y muy poco costo, por eso las curvas se cruzan.</p>
      <ul class="legend-inline"><li><i style="background:var(--gold-fill)"></i>Ingresos</li><li><i style="background:var(--ink)"></i>Costos de operación (fijos + nube)</li></ul>
      {por_esc(lambda k, b: b["ingresos_costos"])}
    </section>
    <section class="card">
      <h2>Sedes activas frente al punto de equilibrio</h2>
      <p>Con {mt["punto_equilibrio_sedes"]} sedes activas el margen de las sedes paga los costos fijos del año 1. Se vende de 4 sedes en el mes 1 a 18 por mes desde el mes 24, con 1% de cancelaciones mensuales.</p>
      {por_esc(lambda k, b: b["sedes"])}
    </section>
    <section class="card">
      <h2>A dónde va cada cuota mensual</h2>
      {por_esc(lambda k, b: f'<p>De la cuota de <span class="key">{b["cuota_total"]}</span>, el {b["margen_pct"]}% queda como margen para pagar los costos fijos y generar utilidad.</p>' + b["cuota"])}
      <div class="unit">
        <div><strong>{pesos(mt["cac"])}</strong><span>Costo de conseguir una sede (CAC)</span></div>
        <div><strong>{millones(mt["ltv"], 2)}</strong><span>Margen de una sede en 24 meses (LTV)</span></div>
        <div><strong>{miles(mt["ltv_cac"], 1)} : 1</strong><span>LTV frente a CAC; lo sano es 3 : 1</span></div>
        <div><strong>{miles(mt["recuperacion_cac_meses"], 1)} meses</strong><span>Para recuperar el CAC</span></div>
      </div>
    </section>

    <section class="card wide">
      <h2>Estados financieros proyectados</h2>
      <p>Cifras en millones de pesos, sin IVA. La pérdida de los dos primeros años se compensa con la utilidad del tercero, por eso no hay impuesto de renta en el periodo.</p>
      {por_esc(estados_html)}
    </section>

    <section class="card">
      <h2>En qué se usan los {millones(INV, 0)}</h2>
      <p>Se calcula con el escenario base hasta el mes {mes_tope}, cuando la caja toca su punto más bajo. La reserva cubre la necesidad extra del escenario pesimista ({millones(RES["necesidad_pesimista"], 0)} en total).</p>
      {fondos}
    </section>
    <section class="card">
      <h2>Comparación de escenarios</h2>
      <p>En los tres casos la caja se mantiene positiva con la inversión solicitada.</p>
      {tabla_escenarios()}
    </section>

    <section class="card wide">
      <h2>Estructura de costos fijos: {millones(S["nomina_mes"] + S["gastos_operativos_mes"], 2)} al mes</h2>
      <p>La nómina pesa el 72% ({millones(S["nomina_mes"], 2)}); los gastos operativos, el 28%. En azul oscuro, cargos de nómina con prestaciones; en gris, gastos operativos.</p>
      {costos_fijos()}
    </section>
  </div>
</main>
<footer class="wrap">
  <strong>Supuestos del modelo</strong>
  <ul>
    <li>Cuota: equipo de {pesos(S["precio_equipo"])} (costo de {pesos(889_855)} más 25%) y servicio de {pesos(S["servicio_mes"])} al mes, repartidos en {S["plazo_contrato"]} meses.</li>
    <li>Cada sede nueva exige comprar un equipo de {pesos(S["costo_equipo"])}, que se deprecia en {S["vida_util_equipo"]} meses. Nube y soporte cuestan {pesos(S["nube_soporte_mes"])} por sede al mes.</li>
    <li>Costos fijos de {pesos(S["nomina_mes"] + S["gastos_operativos_mes"])} al mes, con ajuste de 5% anual desde el año 2. Con 200 sedes activas se activa la automatización: {pesos(S["automatizacion_costo_mes"])} al mes y {pesos(S["automatizacion_ahorro_sede"])} de ahorro por sede.</li>
    <li>Impuesto de renta del 35% con compensación de pérdidas; se paga en abril del año siguiente. Los clientes pagan mes anticipado, sin cartera.</li>
    <li>CAC: ejecutivo comercial ({pesos(3_700_000)}) más marketing (≈ {pesos(1_700_000)}) entre 18 sedes nuevas al mes. TRM de referencia: {pesos(4000)} por dólar.</li>
    <li>Fuentes: Excel de pricing de CerbIA, pitch deck (BOM cotizado en DigiKey y Mouser, nómina con factor prestacional) y gasto actual de 4 clientes. Proyección generada con Python (modelo_cerbia.py).</li>
  </ul>
</footer>
'''
    titulo = "<title>CerbIA Tablero Inversionistas</title>"
    meta = '<meta name="claude:viewport-fit-sides" content="cover">'
    fuentes = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
               '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;600;700;800&display=swap">')
    if completa:
        return (f'<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
                f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
                f'{titulo}{fuentes}<style>{CSS}</style></head><body>{cuerpo}<script>{JS}</script></body></html>')
    return f'{titulo}{meta}{fuentes}<style>{CSS}</style>{cuerpo}<script>{JS}</script>'


if __name__ == "__main__":
    M.verificar_balance(RES)
    (AQUI / "dashboard_cerbia.html").write_text(pagina(True), encoding="utf-8")
    (AQUI / "dashboard_cerbia_artifact.html").write_text(pagina(False), encoding="utf-8")
    print("Listo:", AQUI / "dashboard_cerbia.html")
