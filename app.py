import streamlit as st

st.set_page_config(page_title="ShockWatch", layout="centered")
st.title("🚛 ShockWatch")
st.markdown("Calcula el impacto de un shock en el precio del combustible sobre tu negocio de transporte.")

galones_mes = st.number_input("Consumo de combustible mensual (galones)", min_value=1, value=200)
costo_actual_galon = st.number_input("Precio actual del galón de diésel (S/)", min_value=1.0, value=17.5, step=0.1)
pct_costos_combustible = st.slider("¿Qué % de tus costos totales es combustible?", 0, 100, 35)

shock_pct = st.slider("Simula un shock internacional (% de aumento)", 0, 50, 15)
coef_traspaso = 0.6  # basado en análisis IPE: shocks internacionales se trasladan parcialmente al precio local

aumento_precio_local = shock_pct * coef_traspaso
nuevo_precio_galon = costo_actual_galon * (1 + aumento_precio_local / 100)
costo_mensual_actual = galones_mes * costo_actual_galon
costo_mensual_nuevo = galones_mes * nuevo_precio_galon
diferencia = costo_mensual_nuevo - costo_mensual_actual

st.metric("Precio nuevo por galón (S/)", f"{nuevo_precio_galon:.2f}", f"+{aumento_precio_local:.1f}%")
st.metric("Costo mensual adicional (S/)", f"{diferencia:.2f}")

if diferencia > 0:
    st.warning(f"Con un shock de {shock_pct}%, tu costo mensual sube en S/ {diferencia:.2f}. "
               f"Si el combustible es el {pct_costos_combustible}% de tus costos, considera ajustar tarifas pronto.")