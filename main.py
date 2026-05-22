import yfinance as yf
import google.generativeai as genai
import os
import glob
from datetime import datetime
import requests

# 1. CONEXIÓN A GEMINI (Arreglado el nombre del modelo)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-pro-latest') # <-- Ahora sí lo encontrará

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
fecha_legible = datetime.now().strftime("%d/%m/%Y")

# 2. DESCARGA DE DATOS (Con trampa anti-bloqueo de Yahoo)
activos = {
    "S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "DAX": "^GDAXI",
    "EUR/USD": "EURUSD=X", "DXY": "DX-Y.NYB", "Oro (Futuro)": "GC=F",
    "Petroleo WTI": "CL=F", "Bitcoin": "BTC-USD"
}

# Creamos una sesión que simula ser Chrome de Windows
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})

datos_texto = f"DATOS DE MERCADO ACTUALES AL {fecha_legible}:\n"
for nombre, ticker in activos.items():
    try:
        # Usamos la sesión trucada
        data = yf.Ticker(ticker, session=session)
        hist = data.history(period="2d")
        
        if len(hist) >= 2:
            c_hoy = hist['Close'].iloc[-1]
            c_ayer = hist['Close'].iloc[-2]
            var_pct = ((c_hoy - c_ayer) / c_ayer) * 100
            datos_texto += f"- {nombre}: {c_hoy:.2f} (Variación 24h: {var_pct:.2f}%)\n"
        else:
            datos_texto += f"- {nombre}: Mercado cerrado / Sin datos\n"
    except Exception as e:
        datos_texto += f"- {nombre}: Datos no disponibles temporalmente\n"

# 3. EL PROMPT E INSTRUCCIONES
instrucciones_diseno = """
Eres un analista senior de mercados. Tu único output será código HTML autocontenible desde <!DOCTYPE html> hasta </html>.
ESTRUCTURA DEL HTML:
1. Header con título "Briefing Institucional" y fecha.
2. Resumen ejecutivo (4 bullets).
3. Tabla de cotizaciones con los activos dados.
4. Análisis macro de los activos.

USA EXACTAMENTE ESTE CSS EN EL HEAD (NO LO CAMBIES):
<style>
body { background: #0d1117; color: #c9d1d9; font-family: -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 30px; }
h1, h2 { color: #f0f6fc; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
h3 { color: #58a6ff; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; background: #161b22; }
th, td { padding: 10px; border-bottom: 1px solid #30363d; text-align: left; }
th { background: #21262d; color: #f0f6fc; }
.up { color: #00d4aa; font-weight: bold; }
.down { color: #ff4757; font-weight: bold; }
</style>
"""

prompt_completo = datos_texto + "\n" + instrucciones_diseno

# LLAMADA A LA IA
response = model.generate_content(prompt_completo)
html_informe = response.text

if html_informe.startswith("```html"):
    html_informe = html_informe[7:-3]
elif html_informe.startswith("```"):
    html_informe = html_informe[3:-3]

# 4. GUARDAR ARCHIVOS
os.makedirs("historico", exist_ok=True) 

with open("latest.html", "w", encoding="utf-8") as f:
    f.write(html_informe.strip())

with open(f"historico/{fecha_hoy}.html", "w", encoding="utf-8") as f:
    f.write(html_informe.strip())

# 5. CREAR PORTADA
archivos_hist = sorted(glob.glob("historico/*.html"), reverse=True)
lista_enlaces = ""
for ruta in archivos_hist:
    nombre_archivo = os.path.basename(ruta)
    fecha_archivo = nombre_archivo.replace(".html", "")
    lista_enlaces += f'<li><a href="{ruta}">Briefing del {fecha_archivo}</a></li>\n'

landing_page = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Portal Macro</title>
<style>body {{ background: #0d1117; color: #c9d1d9; font-family: sans-serif; text-align: center; padding: 50px 20px; }}
.btn {{ background: #1f6feb; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px; display:inline-block; margin-bottom: 40px; }}
.caja {{ background: #161b22; border: 1px solid #30363d; padding: 20px; max-width: 400px; margin: 0 auto; text-align: left; border-radius: 8px; }}
a {{ color: #58a6ff; text-decoration: none; display: block; padding: 10px 0; border-bottom: 1px solid #30363d;}}</style>
</head><body><h1>Mesa de Análisis Cuantitativo</h1>
<a href="latest.html" class="btn">Leer Informe de Hoy ({fecha_legible})</a>
<div class="caja"><h2>Hemeroteca</h2><ul>{lista_enlaces}</ul></div></body></html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(landing_page.strip())

print("Informe generado con éxito.")
