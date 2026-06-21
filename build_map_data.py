"""
ShockWatch - Paso 3: Construir el dataset final para el mapa
Cruza estaciones únicas + precios actuales + centroides de distrito (INEI),
aplica un jitter determinístico (mismo grifo siempre cae en el mismo punto visual),
detecta marca, y estandariza los nombres de producto para el filtro de la app.

Requiere que ya existan:
  - data/lima_estaciones_unicas.csv
  - data/lima_precios_actuales.csv
  - lima_distritos_centroides.csv  (en la raíz del proyecto)
"""

import hashlib
import math
import pandas as pd

est = pd.read_csv("data/lima_estaciones_unicas.csv")
precios = pd.read_csv("data/lima_precios_actuales.csv")
cent = pd.read_csv("lima_distritos_centroides.csv")

for df in [est, precios, cent]:
    df["DISTRITO"] = df["DISTRITO"].str.strip().str.upper()

cent_simple = cent[["DISTRITO", "lat", "lon"]].drop_duplicates(subset="DISTRITO")

# 1. Unir estaciones con el centroide de su distrito
est_geo = est.merge(cent_simple, on="DISTRITO", how="left")
sin_centroide = est_geo["lat"].isna().sum()
if sin_centroide:
    print(f"⚠️ {sin_centroide} estaciones sin centroide (revisar nombres de distrito)")


def jitter(ruc, direccion, lat, lon, radio_grados=0.01):
    """Dispersión visual determinística: el mismo grifo siempre cae en el mismo punto."""
    h = hashlib.md5(f"{ruc}{direccion}".encode()).hexdigest()
    seed = int(h[:8], 16)
    angulo = (seed % 360) * (math.pi / 180)
    distancia = ((seed // 360) % 100) / 100 * radio_grados
    return lat + distancia * math.cos(angulo), lon + distancia * math.sin(angulo)


est_geo[["lat_j", "lon_j"]] = est_geo.apply(
    lambda r: pd.Series(jitter(r["RUC"], r["DIRECCIÓN"], r["lat"], r["lon"])), axis=1
)

# 2. Detectar marca / cadena a partir de la razón social
#    Nota: OSINERGMIN no tiene un campo de "marca/bandera" en el registro público.
#    Esto es una aproximación buscando nombres de cadenas conocidas en la razón social legal;
#    la mayoría de grifos son operadores independientes cuya razón social no menciona la marca
#    visible en el cartel, así que la mayoría caerá en "Independiente / no identificada".
MARCAS_CONOCIDAS = ["PRIMAX", "REPSOL", "PETROPERU", "PETROPERÚ", "PECSA", "TERPEL", "MOBIL", "ENERGYGAS"]


def detectar_marca(razon_social):
    rs = str(razon_social).upper()
    for marca in MARCAS_CONOCIDAS:
        if marca in rs:
            return "PETROPERU" if marca == "PETROPERÚ" else marca
    return "Independiente / no identificada"


est_geo["marca"] = est_geo["RAZÓN SOCIAL"].apply(detectar_marca)

# 3. Estandarizar nombres de producto (consolidar variantes de escritura)
MAPA_PRODUCTO = {
    "Diesel B5 S-50 UV": "Diesel B5", "Diesel B5 S-50": "Diesel B5",
    "DIESEL B5": "Diesel B5", "DIESEL B5 UV": "Diesel B5",
    "Diesel 2 S-50 UV": "Diesel 2", "Diesel 2 S-50": "Diesel 2",
    "GASOHOL REGULAR": "Gasohol Regular (84)", "GASOHOL PREMIUM": "Gasohol Premium (90+)",
    "GASOLINA REGULAR": "Gasolina Regular", "GASOLINA PREMIUM": "Gasolina Premium",
    "GAS NATURAL VEHICULAR COMPRIMIDO": "GNV",
    "GAS NATURAL VEHICULAR LICUEFACTADO": "GLP Vehicular",
}

precios["categoria"] = precios["PRODUCTO"].map(MAPA_PRODUCTO)
precios_consumidor = precios[precios["categoria"].notna()].copy()

# 4. Unir precios con la geolocalización y marca de cada estación
final = precios_consumidor.merge(
    est_geo[["RUC", "DIRECCIÓN", "RAZÓN SOCIAL", "DISTRITO", "marca", "lat_j", "lon_j"]],
    on=["RUC", "DIRECCIÓN"], how="left", suffixes=("", "_est"),
)

# --- Calcular tendencia: precio actual vs. promedio de las 4 semanas previas ---
historico = pd.read_csv("data/lima_historico_completo.csv")
historico["FECHA DE REGISTRO"] = pd.to_datetime(historico["FECHA DE REGISTRO"], errors="coerce")
historico["PRECIO DE VENTA (SOLES)"] = historico["PRECIO DE VENTA (SOLES)"].astype(str).str.replace(",", ".").astype(float)

tendencias = []
for (ruc, direccion, producto), grupo in historico.groupby(["RUC", "DIRECCIÓN", "PRODUCTO"]):
    grupo = grupo.sort_values("FECHA DE REGISTRO")
    fecha_actual = grupo["FECHA DE REGISTRO"].max()
    precio_actual = grupo.loc[grupo["FECHA DE REGISTRO"] == fecha_actual, "PRECIO DE VENTA (SOLES)"].iloc[-1]

    ventana_previa = grupo[
        (grupo["FECHA DE REGISTRO"] < fecha_actual) &
        (grupo["FECHA DE REGISTRO"] >= fecha_actual - pd.Timedelta(days=28))
    ]

    if len(ventana_previa) >= 1:
        promedio_previo = ventana_previa["PRECIO DE VENTA (SOLES)"].mean()
        if precio_actual < promedio_previo * 0.98:
            senal = "🔻 Bajo el promedio de 4 semanas"
        elif precio_actual > promedio_previo * 1.02:
            senal = "🔺 Sobre el promedio de 4 semanas"
        else:
            senal = "➖ Estable"
    else:
        senal = "Sin historial suficiente"

    tendencias.append({"RUC": ruc, "DIRECCIÓN": direccion, "PRODUCTO": producto, "tendencia": senal})

df_tendencias = pd.DataFrame(tendencias)
final = final.merge(df_tendencias, on=["RUC", "DIRECCIÓN", "PRODUCTO"], how="left")
final["tendencia"] = final["tendencia"].fillna("Sin historial suficiente")

final_clean = final[
    ["RUC", "RAZÓN SOCIAL", "DISTRITO", "DIRECCIÓN", "marca", "categoria",
     "PRECIO DE VENTA (SOLES)", "FECHA DE REGISTRO", "lat_j", "lon_j", "tendencia"]
]
final_clean.columns = ["ruc", "nombre", "distrito", "direccion", "marca", "producto", "precio", "fecha", "lat", "lon", "tendencia"]

final_clean.to_csv("data/lima_mapa_precios.csv", index=False, encoding="utf-8")

print(f"Listo: data/lima_mapa_precios.csv ({len(final_clean):,} filas)")
print(f"Productos disponibles: {sorted(final_clean['producto'].unique())}")
print(f"Estaciones sin coordenadas: {final_clean['lat'].isna().sum()}")
print(f"Tendencias calculadas: {final_clean['tendencia'].value_counts().to_dict()}")