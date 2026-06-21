import pandas as pd
import streamlit as st

st.set_page_config(page_title="ShockWatch", layout="centered")
st.title("🚛 ShockWatch")
st.markdown("Calcula el impacto de un shock en el precio del combustible sobre tu negocio de transporte.")

# --- Data real cargada (no requiere internet ni API) ---
df_precios = pd.read_csv("data/precios_combustible.csv")
st.subheader("Evolución del precio promedio del diésel (S/ por galón)")
st.line_chart(df_precios.set_index("mes"))
st.caption("Datos ilustrativos de tendencia de precios de combustible en Perú. Para producción, se conectaría a OSINERGMIN Facilito.")

st.divider()
st.subheader("Simula tu exposición")

galones_mes = st.number_input("Consumo de combustible mensual (galones)", min_value=1, value=200)
costo_actual_galon = st.number_input("Precio actual del galón de diésel (S/)", min_value=1.0, value=19.30, step=0.1)
pct_costos_combustible = st.slider("¿Qué % de tus costos totales es combustible?", 0, 100, 35)
shock_pct = st.slider("Simula un shock internacional (% de aumento)", 0, 50, 15)

coef_traspaso = 0.6
aumento_precio_local = shock_pct * coef_traspaso
nuevo_precio_galon = costo_actual_galon * (1 + aumento_precio_local / 100)
costo_mensual_actual = galones_mes * costo_actual_galon
costo_mensual_nuevo = galones_mes * nuevo_precio_galon
diferencia = costo_mensual_nuevo - costo_mensual_actual

st.metric("Precio nuevo por galón (S/)", f"{nuevo_precio_galon:.2f}", f"+{aumento_precio_local:.1f}%")
st.metric("Costo mensual adicional (S/)", f"{diferencia:.2f}")

def generar_recomendacion(diferencia, pct_costos_combustible):
    if diferencia <= 0:
        return "Tu situación actual es estable. No se proyecta impacto con este escenario."
    elif diferencia < 200:
        return "Impacto moderado. Revisa tus tarifas en las próximas semanas, no es urgente."
    elif diferencia < 500:
        return "Impacto significativo. Te recomendamos ajustar tarifas o negociar cláusulas de variación de combustible con tus clientes en los próximos días."
    else:
        return "Impacto alto. Considera renegociar contratos de inmediato y evaluar qué rutas/clientes dejan de ser rentables bajo este escenario."

if st.button("Generar recomendación"):
    st.success(generar_recomendacion(diferencia, pct_costos_combustible))