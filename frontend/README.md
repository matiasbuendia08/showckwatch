# ⛽ ShockWatch

Encuentra el grifo más barato cerca de ti en Lima y Callao, en tiempo real — y optimiza el
abastecimiento de tu flota con datos comprobados, no con intuición.

**Demo en vivo:** _[pega aquí tu URL de Streamlit Cloud cuando la tengas]_

---

## Por qué este founder (completar)

> _TODO: una línea de founder–market fit, basada en tus 5 entrevistas reales._

Como solo founder, cubro los roles clásicos de un equipo apoyándome en agentes de IA:
- **Claude** funcionó como co-fundador técnico durante todo el desarrollo: diseño de producto,
  arquitectura de datos, debugging y diseño visual.
- _TODO: completa si usaste algo más (Claude Code, Codex, etc.) y para qué exactamente._

## El problema

_TODO: completar con el resumen de tus 5 entrevistas — quién sufre el problema, qué tan
doloroso es (horas, soles), cómo lo resuelven hoy sin esto._

## Qué hace ShockWatch

**Para consumidores (B2C):**
- Mapa de precios de combustible en tiempo real por distrito, producto y marca (fuente:
  OSINERGMIN).
- Verificación comunitaria de precios: si 2+ usuarios distintos reportan un precio parecido,
  se marca como verificado.
- Índice de Riesgo de Shock (0–100), mostrado como gauge: combina dispersión de precios entre
  estaciones, riesgo histórico por día de la semana, y volatilidad reciente — cada componente
  con peso igual, sin caja negra.
- Transparencia sobre la antigüedad del dato oficial de OSINERGMIN para cada estación.
- Cuentas persistentes (login) y gamificación: puntos y ranking por reportar precios.

**Para flotas (B2B, plan de pago):**
- Recomendación de grifo óptimo por zona, con pricing escalonado según tamaño de flota
  (S/15–90/mes según número de vehículos, no un precio plano).
- **Backtest histórico:** ahorro comprobado con datos reales de los últimos 4 meses (no
  proyectado) — la flota ve cuánto habría ahorrado de verdad siguiendo la recomendación.
- Ranking de zonas por oportunidad real de ahorro (coeficiente de variación de precios).
- ROI del plan calculado en vivo: cuánto cuesta vs. cuánto ahorra.
- Informes descargables en PDF y CSV.

## Insight

El dato de precios ya es público (OSINERGMIN lo publica gratis). El valor no está en mostrar
precios — está en decirle a una flota exactamente qué grifo visitar y cuándo, con el ahorro
**comprobado con datos históricos reales**, no con una proyección hipotética. Esa es la
diferencia entre "esto debería ahorrarte plata" y "esto te ahorró S/X el mes pasado, y aquí
está la prueba".

## Arquitectura

```
Usuario (navegador)
        │
        ▼
 Streamlit (frontend + backend en un solo proceso)
        │
        ├── Pandas: limpieza y análisis de precios e histórico
        ├── Folium: mapa interactivo
        ├── Plotly / Matplotlib: gráficos, gauge SVG, backtest
        ├── ReportLab: generación de informes PDF
        └── Capa de datos: archivos CSV (data/)
              ├── lima_mapa_precios.csv        (snapshot actual — fuente: OSINERGMIN)
              ├── lima_historico_completo.csv  (histórico — fuente: OSINERGMIN)
              ├── usuarios.csv                 (cuentas; password hasheado con sha256+salt)
              ├── reportes_comunidad.csv       (reportes de precio de usuarios)
              └── waitlist.csv
```

> Diagrama visual en `docs/arquitectura.png` (pendiente de agregar).

## Herramientas del curso utilizadas

| Herramienta | Dónde se usa | Por qué |
|---|---|---|
| Streamlit | Todo el frontend/backend | Permite construir e iterar el producto completo como solo founder, sin separar frontend/backend. |
| Folium | Mapa de precios geolocalizado | Visualización geoespacial de estaciones de servicio. |
| Pandas | Backtest histórico, índice de riesgo, predicción por día de semana | Análisis estadístico simple y transparente sobre datos reales de OSINERGMIN. |
| Whisper (vía `faster-whisper`, local, sin API) | Búsqueda de distrito por voz en la pantalla de inicio | Pensado para choferes y flotas que no deberían tocar la pantalla mientras manejan. Se eligió `faster-whisper` sobre `openai-whisper` porque no depende de `torch`: instala ~60 MB en vez de ~1.2 GB, crítico para no romper el build en el free tier de Streamlit Cloud. Si el import falla por cualquier razón, la app sigue funcionando normal sin esta función (`WHISPER_DISPONIBLE = False`). |

## Cómo correrlo localmente

```bash
git clone https://github.com/matiasbuendia08/showckwatch.git
cd showckwatch
pip install -r requirements.txt
streamlit run app.py
```

Tus CSV de datos van en `data/`. El tema visual ya está en `.streamlit/config.toml`.

## Modelo de negocio

- **Free:** 1 zona, recomendación básica.
- **Flota Pro:** S/15–90/mes según número de vehículos (1–5 / 6–15 / 16–50).
- **Empresarial:** flotas de 50+ vehículos, plan a coordinar.

Costo variable por usuario: mínimo (sin llamadas a APIs de pago en el flujo principal hoy),
lo que da un contribution margin alto desde el día uno.

## Riesgos conocidos

- **Fuente única de datos:** todo depende del registro de OSINERGMIN. Se mitiga mostrando la
  antigüedad del dato y cruzándolo (parcialmente) con reportes comunitarios.
- **Persistencia en la nube:** Streamlit Community Cloud no garantiza almacenamiento
  permanente entre reinicios — los CSV de usuarios/reportes pueden resetearse. Para producción
  real se necesitaría una base de datos.
- _TODO: tercer riesgo (regulatorio, de mercado, o de ejecución como solo founder)._

## Estructura del repositorio

```
showckwatch/
├── app.py
├── requirements.txt
├── LICENSE
├── .env.example
├── .gitignore
├── .streamlit/config.toml
├── data/                  # CSV fuente (OSINERGMIN) + datos generados en runtime
├── build_map_data.py      # pipeline de preparación de datos geoespaciales
├── preprocess_lima.py     # limpieza de precios crudos de OSINERGMIN
├── docs/research/         # evidencia de las 5 entrevistas de validación
└── .github/workflows/ci.yml
```

## Autor

_TODO: tu nombre, una línea bio, contacto._
