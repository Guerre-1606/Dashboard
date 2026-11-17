"""Tablero financiero de CerbIA servido con Flask.

La página se genera una sola vez al arrancar, a partir de modelo_cerbia.py.
Para cambiar un supuesto: edita modelo_cerbia.py, sube el cambio y Render
vuelve a desplegar con los números nuevos.
"""
from pathlib import Path

from flask import Flask, Response, send_from_directory

import generar_dashboard

AQUI = Path(__file__).parent
app = Flask(__name__)

HTML = generar_dashboard.pagina(completa=True)


@app.get("/")
def tablero():
    return Response(HTML, mimetype="text/html")


@app.get("/excel")
def excel():
    return send_from_directory(AQUI / "static", "Modelo_Financiero_CerbIA.xlsx", as_attachment=True)


@app.get("/salud")
def salud():
    return {"estado": "ok"}


if __name__ == "__main__":
    app.run(debug=True, port=5000)
