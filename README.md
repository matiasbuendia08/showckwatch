# ⛽ ShockWatch

Ayudamos a flotas y conductores profesionales a **anticipar** las subidas de precio de
combustible y **controlar** su gasto — no solo a encontrar el grifo más barato.

**Demo en vivo:** [matiasbuendia08.github.io/showckwatch/pwa](https://matiasbuendia08.github.io/showckwatch/pwa/)
(instalable como app · si no carga, usa la URL directa: https://showckwatch-m57ifcrvlry3vybnvqh3ie.streamlit.app/)

**Repo:** https://github.com/matiasbuendia08/showckwatch

---

## Founder

**Matias Alonso Buendia Ugarriza** — estudiante de Economía en la Universidad del Pacífico (top 8%
de su clase, 2025) y practicante de estudios económicos en el Instituto Peruano de Economía (IPE) enfocado en temas de política pública, 
donde trabaja en análisis de competitividad regional, nowcasting del PBI y
reportes de coyuntura publicados en El Comercio, Gestión y RPP para diversos temas.

**Founder–market fit:** en el IPE participó directamente en el análisis del shock energético de
Camisea y su impacto en los precios de combustibles a nivel nacional — el mismo fenómeno que le da
nombre a "ShockWatch". Ese análisis encontró que el precio promedio de
los combustibles llegó a subir hasta 27% frente al promedio de enero-febrero, pero con una gran dispersión entre regiones, en parte por la
interrupción del gasoducto de Camisea. No se
"interesó" en el problema desde afuera: lo analizó profesionalmente antes de decidir construirle
una solución al usuario final.

También ha construido y publicado productos de datos públicos antes de este proyecto: una página
interactiva sobre los resultados electorales de Perú 2026 a nivel de los 1,874 distritos del país,
y varias infografías de difusión para el IPE. Maneja Python, R y Stata.

Como solo founder, cubre los roles clásicos de un equipo apoyándose en agentes de IA:
- **Claude** funcionó como co-fundador técnico durante todo el desarrollo: diseño de producto,
  arquitectura de datos, y debugging real de despliegue — detectó y corrigió que `openai-whisper`
  traía ~1.2 GB de `torch` con CUDA antes de que rompiera el build, y resolvió un conflicto de
  OpenMP específico de Windows que trababa la app.

## El problema

**Hipótesis inicial (descartada por las entrevistas):** pensábamos que el problema era ayudar a
encontrar el grifo más barato. Las 5 entrevistas debilitaron esta hipótesis: Carlos no busca el
precio más bajo sino confiabilidad y no perder tiempo; Rosa prácticamente no compara precios;
Jorge gestiona presupuestos completos, no estaciones individuales.

**Quién lo sufre (segmento validado):** conductores profesionales que dependen del margen (Carlos,
Milagros) y empresas/flotas que gestionan presupuesto de combustible (Jorge) — **no** conductores
casuales ocasionales (Rosa), que priorizan comodidad y cercanía y no pagarían por esto.

**Cómo lo resuelven hoy sin esto:** Excel manual, WhatsApp entre colegas, o Facilito. Milagros
probó Facilito y no dijo "no tiene información" — dijo "no me acostumbré" y "no era práctico para
la ruta que estaba haciendo." El problema no es construir otro mapa que el usuario tenga que abrir
cada día: es llevar la información cuando se necesita (WhatsApp, Telegram, alertas).

## Qué hace ShockWatch

**Para consumidores (B2C — capa de adquisición):**
- Mapa de precios de combustible en tiempo real por distrito, producto y marca (fuente:
  OSINERGMIN).
- Verificación comunitaria de precios: si 2+ usuarios distintos reportan un precio parecido,
  se marca como verificado.
- Índice de Riesgo de Shock (0–100), mostrado como gauge: combina dispersión de precios entre
  estaciones, riesgo histórico por día de la semana, y volatilidad reciente — cada componente
  con peso igual, sin caja negra.
- Transparencia sobre la antigüedad del dato oficial de OSINERGMIN para cada estación.
- Cuentas persistentes (login) y gamificación: puntos y ranking por reportar precios.
- Búsqueda de distrito por voz (Whisper local) para conductores que no deberían tocar la pantalla
  mientras manejan.

**Para flotas y empresas (B2B, plan de pago — el segmento validado por las entrevistas):**
- Recomendación de grifo óptimo por zona, con pricing escalonado según tamaño de flota
  (S/15–90/mes según número de vehículos, no un precio plano).
- **Backtest histórico:** ahorro comprobado con datos reales de los últimos 4 meses (no
  proyectado) — responde directamente al umbral de compra que reveló una de las entrevistas
  ("si me demuestra un ahorro de 2-3%").
- Ranking de zonas por oportunidad real de ahorro (coeficiente de variación de precios).
- ROI del plan calculado en vivo: cuánto cuesta vs. cuánto ahorra.
- Informes descargables en PDF y CSV.
- Lista de espera de alertas predictivas — primer paso hacia notificaciones proactivas
  (WhatsApp/Telegram), la forma de entrega que las entrevistas señalan como la correcta.

## Insight

El dato de precios ya es público (OSINERGMIN lo publica gratis) — eso no es el insight. El insight,
validado con 5 entrevistas, es que el valor real no está en comparar precios sino en **anticipar**
el cambio de precio y **cuantificar** su impacto en el gasto, entregado de forma proactiva en vez
de exigir que el usuario abra una app todos los días. El propio nombre del producto — ShockWatch —
ya apuntaba a esto antes de validarlo: vigilar el shock, no solo el precio.

## Arquitectura

![Arquitectura de ShockWatch](docs/arquitectura.png)

```
Usuario (navegador / celular)
        ▲
        │
   ┌────┴─────────────────────────┐
   │                               │
GitHub Pages              URL directa
(PWA instalable)          Streamlit Cloud
   │                               │
   └──────────────┬────────────────┘
                   ▼
        Streamlit (frontend + backend en un solo proceso)
                │
                ├── Pandas: limpieza y análisis de precios e histórico
                ├── Folium: mapa interactivo
                ├── Plotly / Matplotlib: gráficos, gauge de riesgo, backtest
                ├── ReportLab: generación de informes PDF
                └── faster-whisper: búsqueda de distrito por voz (local, sin API)
                          │
                          ▼
                Capa de datos: archivos CSV (data/)
                  ├── lima_mapa_precios.csv        (snapshot actual — fuente: OSINERGMIN)
                  ├── lima_historico_completo.csv  (histórico — fuente: OSINERGMIN)
                  ├── usuarios.csv                 (cuentas; password hasheado con sha256+salt)
                  ├── reportes_comunidad.csv       (reportes de precio de usuarios)
                  └── waitlist.csv
```

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

El tema visual está en `.streamlit/config.toml`. No se necesitan API keys ni variables de entorno
para correr la app (todo el procesamiento de voz es local); `.env.example` queda como referencia
para quien quiera extender el proyecto con APIs externas en el futuro.

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
- **Ejecución como solo founder con tiempo limitado:** se mitiga con uso intensivo de agentes de
  IA (Claude) como co-founder técnico, ya demostrado construyendo este mismo prototipo en días.

## Estructura del repositorio

```
showckwatch/
├── app.py                       # app principal (Streamlit) — esto es lo que se despliega
├── requirements.txt
├── packages.txt                 # dependencias de sistema para Streamlit Cloud (ffmpeg, etc.)
├── preprocess_lima.py           # limpieza de precios crudos de OSINERGMIN
├── build_map_data.py            # pipeline de preparación de datos geoespaciales
├── lima_distritos_centroides.csv
├── LICENSE
├── .env.example
├── .gitignore
├── .streamlit/
│   └── config.toml              # tema visual de la app
├── .github/
│   └── workflows/
│       └── ci.yml               # CI básico (lint)
├── data/                        # CSV fuente (OSINERGMIN) + datos generados en runtime
├── pwa/                         # wrapper PWA instalable, servido por GitHub Pages
└── docs/
    ├── ShockWatch_Dossier.pdf   # pitch deck (formato YC)
    ├── arquitectura.png         # diagrama de arquitectura
    └── research/                # evidencia de validación (entrevistas, mercado y competencia)
```

## Autor

Matias Alonso Buendia Ugarriza — Economía, Universidad del Pacífico. Solo founder.
Este proyecto fue construido con asistencia de IA (Claude) para estructuración del código,
debugging y diseño de producto.

## Licencia

MIT
