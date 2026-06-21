"""
ShockWatch - Paso 1 (v2): Preprocesamiento desde Excel multi-hoja
Lee 'precios 2026.xlsx' (puede tener varias hojas si supera el límite de Excel por hoja),
filtra a Lima Metropolitana + Callao (incluyendo la variante "PROV. CONST. DEL CALLAO"),
y genera:
  1. data/lima_precios_actuales.csv  -> último precio registrado por estación y producto
  2. data/lima_estaciones_unicas.csv -> lista de estaciones únicas (para geocodificar/asignar centroide)

Requiere: pip install openpyxl
"""

import pandas as pd

RUTA_ARCHIVO = "precios 2026.xlsx"  # está en la misma carpeta que este script

COLUMNAS = [
    "RUC", "RAZÓN SOCIAL", "DEPARTAMENTO", "PROVINCIA", "DISTRITO",
    "DIRECCIÓN", "FECHA DE REGISTRO", "PRODUCTO", "PRECIO DE VENTA (SOLES)", "UNIDAD",
]

print("Detectando hojas del archivo...")
xls = pd.ExcelFile(RUTA_ARCHIVO, engine="openpyxl")
print(f"Hojas encontradas: {xls.sheet_names}")

chunks_filtrados = []
total_leidas = 0

for hoja in xls.sheet_names:
    print(f"\nLeyendo hoja '{hoja}' (esto puede tardar varios minutos por hoja)...")
    df_hoja = pd.read_excel(xls, sheet_name=hoja, usecols=lambda c: c in COLUMNAS)
    total_leidas += len(df_hoja)

    dep = df_hoja["DEPARTAMENTO"].str.strip().str.upper()
    prov = df_hoja["PROVINCIA"].str.strip().str.upper()

    es_lima = (dep == "LIMA") & (prov == "LIMA")
    es_callao = dep.str.contains("CALLAO", na=False)

    filtro = df_hoja[es_lima | es_callao]
    if len(filtro):
        chunks_filtrados.append(filtro)

    print(f"  hoja '{hoja}': {len(df_hoja):,} filas leídas, {len(filtro):,} de Lima/Callao")
    print(f"  total acumulado leído: {total_leidas:,} filas")

df_lima = pd.concat(chunks_filtrados, ignore_index=True)
print(f"\nTotal filas de Lima Metropolitana + Callao: {len(df_lima):,}")

# Normalizar nombre de Callao para que coincida con el shapefile de INEI
df_lima["DEPARTAMENTO"] = df_lima["DEPARTAMENTO"].str.strip().str.upper().replace(
    {"PROV. CONST. DEL CALLAO": "CALLAO"}
)
df_lima["PROVINCIA"] = df_lima["PROVINCIA"].str.strip().str.upper().replace(
    {"PROV. CONST. DEL CALLAO": "CALLAO"}
)
df_lima["DISTRITO"] = df_lima["DISTRITO"].str.strip().str.upper()

# Limpieza de precio y fecha
df_lima["PRECIO DE VENTA (SOLES)"] = (
    df_lima["PRECIO DE VENTA (SOLES)"].astype(str).str.replace(",", ".").astype(float)
)
df_lima["FECHA DE REGISTRO"] = pd.to_datetime(df_lima["FECHA DE REGISTRO"], errors="coerce")

# --- Histórico completo (para calcular tendencias de precio) ---
df_lima[["RUC", "DIRECCIÓN", "PRODUCTO", "PRECIO DE VENTA (SOLES)", "FECHA DE REGISTRO"]].to_csv(
    "data/lima_historico_completo.csv", index=False, encoding="utf-8"
)
print(f"Guardado data/lima_historico_completo.csv ({len(df_lima):,} filas)")

# --- Último precio por estación + producto ---
ultimo_precio = (
    df_lima.sort_values("FECHA DE REGISTRO")
    .groupby(["RUC", "DIRECCIÓN", "PRODUCTO"], as_index=False)
    .last()
)
ultimo_precio.to_csv("data/lima_precios_actuales.csv", index=False, encoding="utf-8")
print(f"\nGuardado data/lima_precios_actuales.csv ({len(ultimo_precio):,} filas)")

# --- Estaciones únicas ---
estaciones_unicas = df_lima.drop_duplicates(subset=["RUC", "DIRECCIÓN"])[
    ["RUC", "RAZÓN SOCIAL", "DEPARTAMENTO", "PROVINCIA", "DISTRITO", "DIRECCIÓN"]
]
estaciones_unicas.to_csv("data/lima_estaciones_unicas.csv", index=False, encoding="utf-8")
print(f"Guardado data/lima_estaciones_unicas.csv ({len(estaciones_unicas):,} estaciones únicas)")
print("\nListo.")