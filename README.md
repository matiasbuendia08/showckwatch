# 🚛 ShockWatch

**Calculadora de exposición a shocks de combustible para pequeños transportistas de carga en Perú.**

## El problema
Transportistas de carga independientes (flotas de 1-10 camiones) ven hasta 30-40% de sus costos operativos en diésel. Cuando hay un shock de precios, se enteran por las noticias después de que ya les afectó, y no saben cuánto deberían ajustar sus tarifas. Hoy lo resuelven "a ojo", sin un número real.

## La solución
Una calculadora donde el transportista ingresa su consumo y costos actuales, simula un shock de precio, y obtiene al instante: (1) cuánto sube su costo mensual en soles, y (2) una recomendación concreta de acción según la severidad del impacto.

## Demo
🔗 **URL pública:** [PEGA TU URL DE STREAMLIT AQUÍ]

## Cómo correrlo localmente
```bash
git clone https://github.com/matiasbuendia08/showckwatch.git
cd showckwatch
pip install -r requirements.txt
streamlit run app.py
```

## Arquitectura
- **Frontend/app:** Streamlit (interfaz interactiva, gráficos, simulador)
- **Datos:** CSV con tendencia de precios de combustible (`data/precios_combustible.csv`)
- **Lógica:** modelo simple de traspaso de shock internacional a costo local + motor de recomendación basado en reglas

## Herramientas del curso utilizadas
- **Streamlit** — interfaz del producto (Lecturas 3-7 del curso)
- **Procesamiento y limpieza de datos con Python/Pandas** — ingesta y visualización de datos públicos de precios de combustible

## Autor
Matias Alonso Buendia Ugarriza — Economía, Universidad del Pacífico — Solo founder.
Este proyecto fue construido con asistencia de IA (Claude) para estructuración del código y debugging.

## Licencia
MIT
