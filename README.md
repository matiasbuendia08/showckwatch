# ⛽ ShockWatch

Encuentra el grifo más barato cerca de ti en Lima y Callao, en tiempo real — y optimiza el
abastecimiento de tu flota con datos, no con intuición.

**Demo en vivo:** _[pega aquí tu URL de Streamlit Cloud cuando la tengas]_

---

## ⚠️ Por qué tú eres el founder indicado (completar)

> _TODO: una línea de founder–market fit. Ej: "Vi a mi tío, que tiene 3 camiones de reparto,
> perder cientos de soles al mes por no saber dónde cargar combustible — y decidí resolverlo
> con los datos públicos que nadie estaba usando."_

Como solo founder, cubro los roles clásicos de un equipo apoyándome en agentes de IA:
- **Claude (vía esta conversación)** funcionó como mi co-fundador técnico: diseño de producto,
  arquitectura de datos, debugging, y diseño visual.
- _TODO: completa si usaste algo más (Codex, Cursor, etc.)._

## El problema

_TODO: completar con el resumen de tus 5 entrevistas. Quién sufre el problema, qué tan doloroso
es (horas, soles), cómo lo resuelven hoy sin esto._

## Qué hace ShockWatch

**Para consumidores (B2C):**
- Mapa de precios de combustible en tiempo real por distrito, producto y marca.
- Verificación comunitaria de precios (consenso entre reportes de usuarios distintos).
- Índice de Riesgo de Shock (0–100): combina dispersión de precios, riesgo histórico por día
  de la semana y volatilidad reciente — cada componente con peso igual, sin caja negra.
- Transparencia sobre la antigüedad del dato oficial de OSINERGMIN.

**Para flotas (B2B, plan de pago):**
- Recomendación de grifo óptimo por zona, con pricing escalonado según el tamaño de la flota
  (S/15 a S/90/mes, no un precio plano).
- **Backtest histórico:** ahorro comprobado con datos reales de los últimos 4 meses, no
  proyectado.
- Ranking de zonas por oportunidad real de ahorro (coeficiente de variación de precios).
- Informes descargables en PDF y CSV.

## Arquitectura

```
Usuario (navegador)
        │
        ▼
 Streamlit (frontend + backend en un solo proceso)
        │
        ├── Pandas: limpieza y análisis de precios e histórico
        ├── Folium: mapa interactivo
        ├── Plotly / Matplotlib: gráficos y backtest
        ├── ReportLab: generación de informes PDF
        └── Capa de datos: archivos CSV (data/)
              ├── lima_mapa_precios.csv        (snapshot actual, fuente: OSINERGMIN)
              ├── lima_historico_completo.csv  (histórico, fuente: OSINERGMIN)
              ├── usuarios.csv                 (cuentas, password hasheado con sha256+salt)
              ├── reportes_comunidad.csv       (reportes de precio de usuarios)
              └── waitlist.csv
```

> Diagrama visual en `docs/arquitectura.png`.

## Herramientas del curso utilizadas

| Herramienta | Dónde se usa | Por qué |
|---|---|---|
| Streamlit | Todo el frontend/backend | Permite construir e iterar el producto completo como solo founder, sin separar frontend/backend. |
| Folium + GeoPandas-style lat/lon | Mapa de precios | Visualización geoespacial de estaciones de servicio. |
| _TODO_ | _Función de IA agregada (Whisper o Claude API)_ | _Completar tras implementar_ |

## Cómo correrlo localmente

```bash
git clone <tu-repo>
cd shockwatch
pip install -r requirements.txt
streamlit run app.py
```

Coloca tus CSV de datos en `data/` y el tema visual en `.streamlit/config.toml` (ya incluido).

## Modelo de negocio

- **Free:** 1 zona, recomendación básica.
- **Flota Pro:** S/15–90/mes según número de vehículos (1–5 / 6–15 / 16–50).
- **Empresarial:** flotas de 50+ vehículos, plan a coordinar.

Costo variable por usuario: mínimo (sin llamadas a APIs de pago en el flujo principal),
lo que da un contribution margin alto desde el día uno.

## Estructura del repositorio

```
shockwatch/
├── app.py
├── requirements.txt
├── LICENSE
├── .env.example
├── .streamlit/config.toml
├── data/            # muestras de datos (CSV)
├── docs/            # pitch deck, capturas, diagrama de arquitectura, video demo
└── .github/workflows/ci.yml
```

## Autor

_TODO: tu nombre, una línea bio, contacto._
