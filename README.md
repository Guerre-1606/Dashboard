# Tablero financiero CerbIA

Aplicación Flask que muestra el tablero para inversionistas: escenarios,
estados financieros proyectados a 3 años, caja, unit economics y uso de fondos.

## Probar en tu computador

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre http://localhost:5000

## Subir a Render

1. Crea un repositorio en GitHub y sube todo el contenido de esta carpeta
   (app.py debe quedar en la raíz del repositorio, no dentro de otra carpeta).
2. En render.com: **New → Web Service** y conecta el repositorio.
3. Render detecta `render.yaml`. Si te pide los datos a mano:
   - Runtime: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Plan: **Free**
4. Dale **Create Web Service**. En 2 o 3 minutos queda en
   `https://cerbia-dashboard.onrender.com` (o el nombre que elijas).

En el plan gratuito el servicio se duerme tras 15 minutos sin visitas y la
primera carga después tarda unos 50 segundos. Ábrelo un rato antes de la
presentación para que esté despierto.

## Rutas

| Ruta | Qué muestra |
|---|---|
| `/` | El tablero |
| `/excel` | Descarga el modelo financiero en Excel |
| `/salud` | Chequeo que usa Render |

## Cambiar supuestos

Todos los números salen de `SUPUESTOS` y `ESCENARIOS` en `modelo_cerbia.py`.
Cambia el valor, haz commit y push; Render redespliega solo.
El Excel de `static/` no se regenera solo: córrelo con `exportar_excel.py`
del paquete original y reemplaza el archivo.
