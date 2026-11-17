"""
Modelo financiero proyectado de CerbIA (36 meses, 3 escenarios).

Cifras base tomadas del Excel de pricing (Pricing_JFGA_1.xlsx) y del pitch deck:
- Costos fijos: $31.971.000/mes (nómina $23.121.000 + gastos operativos $8.850.000)
- Equipo por sede (costo variable unitario): $730.000
- Precio del equipo: $1.112.319 (costo + 25%) y servicio de $150.000/mes
- Cuota de alquiler: ($1.112.319 + $150.000 x 24) / 24 = $196.347/mes por sede de 80 m²
- Nube y soporte por sede: $30.000/mes

Los escenarios usan las mismas variaciones del simulador:
- Pesimista: -20% sedes nuevas, -5% precio, +10% costos variables, +5% costos fijos
- Optimista: +20% sedes nuevas, +5% precio, -5% costos variables, sin cambio en fijos

Uso: python modelo_cerbia.py  (imprime el resumen de los tres escenarios)
"""

import math

# ---------------------------------------------------------------- supuestos
SUPUESTOS = {
    "meses": 36,
    "anio_inicio": 2027,
    "precio_equipo": 1_112_319,          # costo total unitario $889.855 + 25 %
    "servicio_mes": 150_000,             # suscripción mensual
    "plazo_contrato": 24,                # meses
    "costo_equipo": 730_000,             # CVU por sede (hardware + instalación)
    "vida_util_equipo": 24,              # meses de depreciación
    "nube_soporte_mes": 30_000,          # costo variable mensual por sede
    "nomina_mes": 23_121_000,
    "gastos_operativos_mes": 8_850_000,
    "incremento_fijos_anual": 0.05,      # ajuste por IPC y salarios desde el año 2
    "churn_mensual": 0.01,               # 1 % de sedes cancela cada mes
    "sedes_nuevas_ini": 4,               # mes 1
    "sedes_nuevas_tope": 18,             # capacidad de 1 ejecutivo comercial
    "mes_tope": 24,                      # mes en que se llega al tope
    "automatizacion_umbral": 200,        # sedes activas para activarla
    "automatizacion_costo_mes": 2_000_000,
    "automatizacion_ahorro_sede": 10_000,
    "tasa_renta": 0.35,
    "mes_pago_renta": 4,                 # el impuesto del año se paga en abril del siguiente
    "cac": 300_000,                      # (comercial $3,7M + marketing ≈ $1,7M) / 18 sedes
    "colchon_inversion": 0.15,           # margen de seguridad sobre la necesidad de caja
    "redondeo_inversion": 50_000_000,
}
SUPUESTOS["cuota_mes"] = round(
    (SUPUESTOS["precio_equipo"] + SUPUESTOS["servicio_mes"] * SUPUESTOS["plazo_contrato"])
    / SUPUESTOS["plazo_contrato"]
)

ESCENARIOS = {
    "pesimista": {"nombre": "Pesimista", "q": -0.20, "p": -0.05, "v": 0.10, "f": 0.05},
    "base":      {"nombre": "Base",      "q": 0.00,  "p": 0.00,  "v": 0.00, "f": 0.00},
    "optimista": {"nombre": "Optimista", "q": 0.20,  "p": 0.05,  "v": -0.05, "f": 0.00},
}


def sedes_nuevas_base(mes, s=SUPUESTOS):
    """Rampa lineal de ventas: de 4 sedes en el mes 1 a 18 en el mes 24, luego estable."""
    if mes >= s["mes_tope"]:
        return s["sedes_nuevas_tope"]
    paso = (s["sedes_nuevas_tope"] - s["sedes_nuevas_ini"]) / (s["mes_tope"] - 1)
    return round(s["sedes_nuevas_ini"] + paso * (mes - 1))


# ---------------------------------------------------------------- proyección
def proyectar(escenario="base", inversion=0, s=SUPUESTOS):
    e = ESCENARIOS[escenario]
    cuota = s["cuota_mes"] * (1 + e["p"])
    costo_equipo = s["costo_equipo"] * (1 + e["v"])
    nube = s["nube_soporte_mes"] * (1 + e["v"])
    meses = []
    activas = 0.0
    cohortes = []          # inversión en equipos por mes, para depreciar
    caja = inversion
    ppe_bruto = 0.0
    dep_acum = 0.0
    utilidad_antes_imp_anio = 0.0
    perdidas_acum = 0.0     # pérdidas fiscales por compensar
    renta_por_pagar = 0.0
    renta_anio_anterior = 0.0
    utilidades_retenidas = 0.0
    automatizacion = False

    for m in range(1, s["meses"] + 1):
        anio = (m - 1) // 12 + 1
        mes_del_anio = (m - 1) % 12 + 1
        nuevas = round(sedes_nuevas_base(m) * (1 + e["q"]))
        bajas = activas * s["churn_mensual"]
        activas = activas - bajas + nuevas
        if not automatizacion and activas >= s["automatizacion_umbral"]:
            automatizacion = True

        ingresos = activas * cuota
        costo_nube = activas * (nube - (s["automatizacion_ahorro_sede"] if automatizacion else 0))
        capex = nuevas * costo_equipo
        cohortes.append(capex)
        depreciacion = sum(c / s["vida_util_equipo"]
                           for i, c in enumerate(cohortes) if m - i <= s["vida_util_equipo"])
        ajuste = (1 + s["incremento_fijos_anual"]) ** (anio - 1) * (1 + e["f"])
        nomina = s["nomina_mes"] * ajuste
        gastos_op = s["gastos_operativos_mes"] * ajuste
        gasto_auto = s["automatizacion_costo_mes"] if automatizacion else 0
        fijos = nomina + gastos_op + gasto_auto

        utilidad_bruta = ingresos - costo_nube - depreciacion
        ebitda = ingresos - costo_nube - fijos
        ebit = ebitda - depreciacion
        utilidad_antes_imp_anio += ebit

        # impuesto: se causa al cierre del año, con compensación de pérdidas
        impuesto = 0.0
        if mes_del_anio == 12:
            base = utilidad_antes_imp_anio
            if base < 0:
                perdidas_acum += -base
                impuesto = 0.0
            else:
                compensa = min(perdidas_acum, base)
                perdidas_acum -= compensa
                impuesto = (base - compensa) * s["tasa_renta"]
            renta_anio_anterior = impuesto
            utilidad_antes_imp_anio = 0.0
        utilidad_neta = ebit - impuesto

        # flujo de caja
        pago_renta = 0.0
        if mes_del_anio == s["mes_pago_renta"] and anio > 1:
            pago_renta = renta_por_pagar
        renta_por_pagar += impuesto - pago_renta
        flujo_operativo = ebitda - pago_renta
        flujo_inversion = -capex
        flujo_neto = flujo_operativo + flujo_inversion
        caja += flujo_neto

        ppe_bruto += capex
        dep_acum += depreciacion
        utilidades_retenidas += utilidad_neta

        meses.append({
            "mes": m, "anio": anio, "sedes_nuevas": nuevas, "sedes_bajas": bajas,
            "sedes_activas": activas, "ingresos": ingresos, "costo_nube": costo_nube,
            "depreciacion": depreciacion, "utilidad_bruta": utilidad_bruta,
            "nomina": nomina, "gastos_operativos": gastos_op, "automatizacion": gasto_auto,
            "fijos": fijos, "ebitda": ebitda, "ebit": ebit, "impuesto": impuesto,
            "utilidad_neta": utilidad_neta, "capex": capex, "pago_renta": pago_renta,
            "flujo_operativo": flujo_operativo, "flujo_neto": flujo_neto, "caja": caja,
            "ppe_neto": ppe_bruto - dep_acum, "renta_por_pagar": renta_por_pagar,
            "utilidades_retenidas": utilidades_retenidas, "capital": inversion,
        })
    return meses


def necesidad_de_caja(escenario="base"):
    """Mínimo de caja acumulada sin inversión: lo que hay que financiar."""
    return -min(0.0, min(r["caja"] for r in proyectar(escenario, 0)))


def inversion_requerida(s=SUPUESTOS):
    """Se calcula con el escenario pesimista, para que el dinero alcance aun si va mal."""
    necesidad = necesidad_de_caja("pesimista")
    bruto = necesidad * (1 + s["colchon_inversion"])
    return math.ceil(bruto / s["redondeo_inversion"]) * s["redondeo_inversion"]


# ---------------------------------------------------------------- resúmenes
def anual(meses):
    años = []
    for a in (1, 2, 3):
        rs = [r for r in meses if r["anio"] == a]
        suma = lambda k: sum(r[k] for r in rs)
        fin = rs[-1]
        años.append({
            "anio": a,
            "sedes_nuevas": suma("sedes_nuevas"),
            "sedes_activas_cierre": fin["sedes_activas"],
            "ingresos": suma("ingresos"),
            "costo_nube": suma("costo_nube"),
            "depreciacion": suma("depreciacion"),
            "utilidad_bruta": suma("utilidad_bruta"),
            "nomina": suma("nomina"),
            "gastos_operativos": suma("gastos_operativos"),
            "automatizacion": suma("automatizacion"),
            "fijos": suma("fijos"),
            "ebitda": suma("ebitda"),
            "ebit": suma("ebit"),
            "impuesto": suma("impuesto"),
            "utilidad_neta": suma("utilidad_neta"),
            "flujo_operativo": suma("flujo_operativo"),
            "capex": suma("capex"),
            "flujo_neto": suma("flujo_neto"),
            "caja_inicial": rs[0]["caja"] - rs[0]["flujo_neto"],
            "caja_final": fin["caja"],
            "ppe_neto": fin["ppe_neto"],
            "renta_por_pagar": fin["renta_por_pagar"],
            "capital": fin["capital"],
            "utilidades_retenidas": fin["utilidades_retenidas"],
        })
    return años


def metricas(meses, inversion, s=SUPUESTOS):
    margen_sede = s["cuota_mes"] - s["costo_equipo"] / s["vida_util_equipo"] - s["nube_soporte_mes"]
    ltv = margen_sede * s["plazo_contrato"]
    primer = lambda cond: next((r["mes"] for r in meses if cond(r)), None)
    caja_min = min(meses, key=lambda r: r["caja"])
    quema = [-r["flujo_neto"] for r in meses if r["flujo_neto"] < 0]
    fijos_ini = s["nomina_mes"] + s["gastos_operativos_mes"]
    return {
        "inversion": inversion,
        "mes_ebitda_positivo": primer(lambda r: r["ebitda"] > 0),
        "mes_utilidad_positiva": primer(lambda r: r["ebit"] > 0),
        "mes_flujo_positivo": primer(lambda r: r["flujo_neto"] > 0),
        "mes_recupera_inversion": primer(lambda r: r["mes"] > caja_min["mes"] and r["caja"] >= inversion),
        "caja_minima": caja_min["caja"],
        "mes_caja_minima": caja_min["mes"],
        "quema_maxima_mes": max(quema) if quema else 0,
        "punto_equilibrio_sedes": math.ceil(fijos_ini / margen_sede),
        "margen_sede": margen_sede,
        "ltv": ltv,
        "cac": s["cac"],
        "ltv_cac": ltv / s["cac"],
        "recuperacion_cac_meses": s["cac"] / margen_sede,
        "arr_final": meses[-1]["ingresos"] * 12,
        "sedes_finales": meses[-1]["sedes_activas"],
    }


def correr_todo():
    inv = inversion_requerida()
    salida = {"supuestos": SUPUESTOS, "inversion": inv,
              "necesidad_pesimista": necesidad_de_caja("pesimista"),
              "necesidad_base": necesidad_de_caja("base"), "escenarios": {}}
    for k in ESCENARIOS:
        ms = proyectar(k, inv)
        salida["escenarios"][k] = {"nombre": ESCENARIOS[k]["nombre"], "variaciones": ESCENARIOS[k],
                                   "mensual": ms, "anual": anual(ms), "metricas": metricas(ms, inv)}
    return salida


def verificar_balance(res):
    for k, e in res["escenarios"].items():
        for r in e["mensual"]:
            activo = r["caja"] + r["ppe_neto"]
            pasivo_patrimonio = r["renta_por_pagar"] + r["capital"] + r["utilidades_retenidas"]
            assert abs(activo - pasivo_patrimonio) < 1, (k, r["mes"], activo, pasivo_patrimonio)
    return True


if __name__ == "__main__":
    res = correr_todo()
    verificar_balance(res)
    mm = lambda x: f"{x/1e6:,.1f}M"
    print("Cuota:", SUPUESTOS["cuota_mes"])
    print("Necesidad de caja base:", mm(res["necesidad_base"]),
          "| pesimista:", mm(res["necesidad_pesimista"]), "| inversión:", mm(res["inversion"]))
    for k, e in res["escenarios"].items():
        print(f"\n== {e['nombre']}")
        for a in e["anual"]:
            print(f" Año {a['anio']}: sedes {a['sedes_activas_cierre']:.0f} (+{a['sedes_nuevas']}), "
                  f"ingresos {mm(a['ingresos'])}, EBITDA {mm(a['ebitda'])}, neta {mm(a['utilidad_neta'])}, "
                  f"capex {mm(a['capex'])}, caja fin {mm(a['caja_final'])}")
        print(" ", {kk: (round(v, 2) if isinstance(v, float) else v) for kk, v in e["metricas"].items()})
