import os
# Workaround para Windows/Anaconda: numpy (vía MKL) y ctranslate2 (usado por faster-whisper)
# a veces traen cada uno su propia copia de libiomp5md.dll, lo que choca y puede trabar
# el programa (OMP: Error #15). Esto debe ir ANTES de importar streamlit/pandas/faster_whisper.
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import streamlit as st
import pandas as pd
import math
import hashlib
import secrets
import tempfile
import unicodedata
import difflib
from datetime import datetime
import folium
from streamlit_folium import st_folium
import plotly.express as px
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

# Import defensivo: si Whisper no se instaló bien en el entorno de despliegue,
# la app sigue funcionando normal, solo sin la búsqueda por voz.
WHISPER_DISPONIBLE = True
try:
    from faster_whisper import WhisperModel
except Exception:
    WHISPER_DISPONIBLE = False



def generar_pdf_flota(df_recom, detalle_por_distrito, historico, producto_flota, ahorro_mensual, consumo_mensual_galones):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle("titulo", parent=styles["Title"], textColor=colors.HexColor("#1a1a2e"))
    subtitulo_style = ParagraphStyle("subtitulo", parent=styles["Normal"], textColor=colors.grey, fontSize=10)

    story = [
        Paragraph("⛽ ShockWatch — Informe de Flota", titulo_style),
        Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} · Combustible: {producto_flota}", subtitulo_style),
        Spacer(1, 16),
    ]

    if consumo_mensual_galones > 0:
        story.append(Paragraph(
            f"<b>Ahorro mensual estimado:</b> S/ {ahorro_mensual:.0f} (grifo recomendado vs. promedio de zona, "
            f"consumo estimado {consumo_mensual_galones:,} galones/mes)", styles["Normal"]))
        story.append(Spacer(1, 12))

    data_tabla = [["Distrito", "Grifo recomendado", "Dirección", "Precio", "Prom. zona", "Ahorro/galón"]]
    for _, row in df_recom.iterrows():
        data_tabla.append([
            row["Distrito"], row["Grifo recomendado"][:30], row["Dirección"][:30],
            f"S/ {row['Precio']:.2f}", f"S/ {row['Promedio de zona']:.2f}", f"S/ {row['Ahorro por galón']:.2f}",
        ])

    tabla = Table(data_tabla, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D62828")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [tabla, Spacer(1, 20)]

    fig1, ax1 = plt.subplots(figsize=(6, 3))
    x = range(len(df_recom))
    ax1.bar([i - 0.2 for i in x], df_recom["Precio"], width=0.4, label="Precio recomendado", color="#1B8A5A")
    ax1.bar([i + 0.2 for i in x], df_recom["Promedio de zona"], width=0.4, label="Promedio de zona", color="#5B6472")
    y_min = min(df_recom["Precio"].min(), df_recom["Promedio de zona"].min())
    y_max = max(df_recom["Precio"].max(), df_recom["Promedio de zona"].max())
    margen = (y_max - y_min) * 0.25 if y_max > y_min else y_max * 0.1
    ax1.set_ylim(max(0, y_min - margen), y_max + margen)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(df_recom["Distrito"], rotation=20, ha="right", fontsize=8)
    ax1.set_ylabel("S/ por galón")
    ax1.legend(fontsize=8)
    fig1.tight_layout()
    img1 = io.BytesIO()
    fig1.savefig(img1, format="png", dpi=150)
    plt.close(fig1)
    img1.seek(0)
    story += [Paragraph("<b>Precio recomendado vs. promedio de la zona</b>", styles["Normal"]),
              Image(img1, width=16 * cm, height=8 * cm), Spacer(1, 16)]

    if not historico.empty:
        fig2, ax2 = plt.subplots(figsize=(6, 3))
        tiene_datos = False
        for distrito, info in detalle_por_distrito.items():
            hist_est = historico[
                (historico["RUC"] == info["ruc"]) & (historico["DIRECCIÓN"] == info["direccion"]) &
                (historico["categoria"] == producto_flota)
            ].sort_values("FECHA DE REGISTRO")
            if len(hist_est) >= 2:
                fecha_max = historico["FECHA DE REGISTRO"].max()
                hist_4m = hist_est[hist_est["FECHA DE REGISTRO"] >= fecha_max - pd.Timedelta(days=120)]
                ax2.plot(hist_4m["FECHA DE REGISTRO"], hist_4m["PRECIO DE VENTA (SOLES)"], marker="o", markersize=3, label=distrito)
                tiene_datos = True
        if tiene_datos:
            ax2.set_ylabel("S/ por galón")
            ax2.legend(fontsize=8)
            fig2.autofmt_xdate()
            fig2.tight_layout()
            img2 = io.BytesIO()
            fig2.savefig(img2, format="png", dpi=150)
            img2.seek(0)
            story += [Paragraph("<b>Histórico de precio (últimos 4 meses)</b>", styles["Normal"]),
                      Image(img2, width=16 * cm, height=8 * cm)]
        plt.close(fig2)

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Fuente: OSINERGMIN — Registro de precios de combustibles. Ubicación aproximada al centroide del distrito.",
        ParagraphStyle("footer", parent=styles["Normal"], fontSize=7, textColor=colors.grey)))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


MAPA_PRODUCTO_HIST = {
    "Diesel B5 S-50 UV": "Diesel B5", "Diesel B5 S-50": "Diesel B5",
    "DIESEL B5": "Diesel B5", "DIESEL B5 UV": "Diesel B5",
    "Diesel 2 S-50 UV": "Diesel 2", "Diesel 2 S-50": "Diesel 2",
    "GASOHOL REGULAR": "Gasohol Regular (84)", "GASOHOL PREMIUM": "Gasohol Premium (90+)",
    "GASOLINA REGULAR": "Gasolina Regular", "GASOLINA PREMIUM": "Gasolina Premium",
    "GAS NATURAL VEHICULAR COMPRIMIDO": "GNV",
    "GAS NATURAL VEHICULAR LICUEFACTADO": "GLP Vehicular",
}

DIAS_ES = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo",
}
DIAS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@st.cache_data
def load_historico():
    if os.path.exists("data/lima_historico_completo.csv"):
        h = pd.read_csv("data/lima_historico_completo.csv")
        h["FECHA DE REGISTRO"] = pd.to_datetime(h["FECHA DE REGISTRO"], errors="coerce")
        h["PRECIO DE VENTA (SOLES)"] = h["PRECIO DE VENTA (SOLES)"].astype(str).str.replace(",", ".").astype(float)
        h["categoria"] = h["PRODUCTO"].map(MAPA_PRODUCTO_HIST)
        return h
    return pd.DataFrame()


st.set_page_config(page_title="ShockWatch - Precios de Combustible Lima", layout="wide", page_icon="⛽")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@500;700&family=Inter:wght@400;500;600;700&family=Roboto+Mono:wght@500;700&display=swap');

    :root {
        --ink: #14171F;
        --canvas: #FAF8F4;
        --pump-green: #1B8A5A;
        --signal-amber: #F4A623;
        --alert-red: #D62828;
        --steel: #5B6472;
    }

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Forzar nuestro fondo y look sin importar si el visitante tiene activado el modo
       oscuro de Streamlit (Settings -> Theme) — el diseño no debe depender de eso. */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: var(--canvas) !important;
    }

    .main > div { padding-top: 1rem; }

    h1, h2, h3 { font-family: 'Inter', sans-serif; font-weight: 700; color: var(--ink) !important; }

    /* Acotado a los contenedores reales de texto de Streamlit (markdown/caption/label),
       NUNCA a la etiqueta <p> genérica — esa se cuela dentro de botones y otros widgets
       que tienen su propio fondo, y ahí es donde se generó el bug de "negro sobre negro". */
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"], [data-testid="stWidgetLabel"] {
        color: var(--ink) !important;
    }

    /* Cuadros de selectbox / multiselect / inputs: forzar SIEMPRE fondo claro + texto
       oscuro JUNTOS. El bug de "letra negra sobre fondo negro" pasa cuando se fuerza
       solo el texto sin tocar el fondo (o viceversa) — hay que mover ambos a la vez. */
    [data-baseweb="select"] > div,
    [data-baseweb="base-input"],
    .stTextInput input, .stNumberInput input, .stTextArea textarea,
    [data-testid="stDateInput"] input {
        background-color: #FFFFFF !important;
        color: var(--ink) !important;
        border-color: #E8E4DC !important;
    }
    [data-baseweb="select"] span, [data-baseweb="select"] div {
        color: var(--ink) !important;
    }
    /* Lista desplegable del selectbox al abrirla (incluye listas largas con
       virtualización, donde Streamlit no usa <li> sino <div> por dentro —
       por eso se fuerza TODO lo de adentro, sin depender de la etiqueta exacta). */
    [data-baseweb="popover"] {
        background-color: #FFFFFF !important;
    }
    [data-baseweb="popover"] * {
        background-color: #FFFFFF !important;
        color: var(--ink) !important;
    }

    /* Métricas como placas de tablero */
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E8E4DC;
        border-radius: 10px;
        padding: 12px 16px;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Roboto Mono', monospace;
        font-weight: 700;
        font-size: 1.4rem;
        color: var(--ink) !important;
    }
    [data-testid="stMetricLabel"] { font-weight: 600; color: var(--steel) !important; }

    /* Botones: fondo Y texto SIEMPRE juntos, como pareja, para los dos tipos (normal y primario) */
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
        border-radius: 8px;
        font-weight: 600;
        border: 1px solid #E8E4DC;
        background-color: #FFFFFF !important;
        color: var(--ink) !important;
    }
    .stButton > button p, .stDownloadButton > button p, .stFormSubmitButton > button p,
    .stButton > button span, .stDownloadButton > button span, .stFormSubmitButton > button span {
        color: var(--ink) !important;
    }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
        background-color: var(--signal-amber) !important;
        border: none;
    }
    .stButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primary"] p,
    .stButton > button[kind="primary"] span, .stFormSubmitButton > button[kind="primary"] span {
        color: var(--ink) !important;
    }

    /* Sidebar: forzar texto e inputs legibles sin importar el tema del visitante */
    [data-testid="stSidebar"] {
        background-color: #F1ECE2 !important;
    }
    [data-testid="stSidebar"] * {
        color: var(--ink) !important;
    }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea {
        background-color: #FFFFFF !important;
        color: var(--ink) !important;
    }

    /* Expanders y alertas con esquinas consistentes */
    [data-testid="stExpander"], [data-testid="stAlert"] {
        border-radius: 10px;
        border: 1px solid #E8E4DC;
    }
    [data-testid="stExpander"] summary, [data-testid="stExpander"] p {
        color: var(--ink) !important;
    }

    .precio-mono { font-family: 'Roboto Mono', monospace; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

REPORTES_PATH = "data/reportes_comunidad.csv"
WAITLIST_PATH = "data/waitlist.csv"
USUARIOS_PATH = "data/usuarios.csv"


@st.cache_data
def load_data():
    return pd.read_csv("data/lima_mapa_precios.csv")


def load_reportes():
    if os.path.exists(REPORTES_PATH):
        return pd.read_csv(REPORTES_PATH)
    return pd.DataFrame(columns=["fecha", "estacion", "distrito", "precio_reportado", "calificacion", "comentario", "email_reportero"])


def guardar_reporte(estacion, distrito, precio, calificacion, comentario, email_reportero=None):
    df_r = load_reportes()
    nuevo = pd.DataFrame([{
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "estacion": estacion, "distrito": distrito,
        "precio_reportado": precio, "calificacion": calificacion, "comentario": comentario,
        "email_reportero": email_reportero,
    }])
    pd.concat([df_r, nuevo], ignore_index=True).to_csv(REPORTES_PATH, index=False)


def load_waitlist():
    if os.path.exists(WAITLIST_PATH):
        return pd.read_csv(WAITLIST_PATH)
    return pd.DataFrame(columns=["fecha", "correo", "distrito", "producto"])


def guardar_waitlist(correo, distrito, producto):
    df_w = load_waitlist()
    nuevo = pd.DataFrame([{
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "correo": correo, "distrito": distrito, "producto": producto,
    }])
    pd.concat([df_w, nuevo], ignore_index=True).to_csv(WAITLIST_PATH, index=False)

def verificar_alertas_precio(email):
    """Compara las suscripciones del usuario en la waitlist contra la tendencia actual
    de precios y devuelve avisos cuando el precio está bajo su promedio de 4 semanas."""
    if not email:
        return []
    wl = load_waitlist()
    if wl.empty:
        return []
    mis_alertas = wl[wl["correo"] == email]
    if mis_alertas.empty:
        return []
    mapa = load_data()
    avisos = []
    vistos = set()
    for _, fila in mis_alertas.iterrows():
        clave = (fila["distrito"], fila["producto"])
        if clave in vistos:
            continue
        vistos.add(clave)
        match = mapa[
            (mapa["distrito"] == fila["distrito"])
            & (mapa["producto"] == fila["producto"])
            & (mapa["tendencia"] == "🔻 Bajo el promedio de 4 semanas")
        ]
        if not match.empty:
            precio_min = match["precio"].min()
            avisos.append(
                f"🔔 **{fila['producto']}** en **{fila['distrito']}** está bajo su promedio de "
                f"las últimas 4 semanas — desde S/ {precio_min:.2f}. Buen momento para cargar."
            )
    return avisos

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ================= SISTEMA DE CUENTAS (sin APIs externas) =================
# Nota de seguridad: hash sha256+salt en CSV es válido para una demo/MVP académico,
# NO para producción real (ahí se necesitaría bcrypt/argon2 + base de datos real).

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return h, salt


def load_usuarios():
    columnas = ["email", "password_hash", "salt", "tipo_cuenta", "plan_pro",
                "num_vehiculos", "ahorro_historico", "puntos_reportero"]
    if os.path.exists(USUARIOS_PATH):
        u = pd.read_csv(USUARIOS_PATH)
        if "plan_pro" in u.columns:
            u["plan_pro"] = u["plan_pro"].astype(str).str.lower().isin(["true", "1"])
        return u
    return pd.DataFrame(columns=columnas)


def registrar_usuario(email, password, tipo_cuenta):
    if not email or not password:
        return False, "Completa correo y contraseña."
    usuarios = load_usuarios()
    if email in usuarios["email"].values:
        return False, "Ese correo ya está registrado."
    h, salt = hash_password(password)
    nuevo = pd.DataFrame([{
        "email": email, "password_hash": h, "salt": salt, "tipo_cuenta": tipo_cuenta,
        "plan_pro": False, "num_vehiculos": 1, "ahorro_historico": 0.0, "puntos_reportero": 0,
    }])
    pd.concat([usuarios, nuevo], ignore_index=True).to_csv(USUARIOS_PATH, index=False)
    return True, "Cuenta creada con éxito."


def verificar_login(email, password):
    usuarios = load_usuarios()
    fila = usuarios[usuarios["email"] == email]
    if fila.empty:
        return False, None
    fila = fila.iloc[0]
    h, _ = hash_password(password, fila["salt"])
    if h == fila["password_hash"]:
        return True, fila
    return False, None


def obtener_usuario(email):
    if not email:
        return None
    usuarios = load_usuarios()
    fila = usuarios[usuarios["email"] == email]
    if fila.empty:
        return None
    return fila.iloc[0]


def actualizar_usuario(email, **kwargs):
    usuarios = load_usuarios()
    idx = usuarios[usuarios["email"] == email].index
    if len(idx):
        for k, v in kwargs.items():
            usuarios.loc[idx, k] = v
        usuarios.to_csv(USUARIOS_PATH, index=False)


def sumar_puntos(email, puntos):
    usuarios = load_usuarios()
    idx = usuarios[usuarios["email"] == email].index
    if len(idx):
        usuarios.loc[idx, "puntos_reportero"] = usuarios.loc[idx, "puntos_reportero"].fillna(0) + puntos
        usuarios.to_csv(USUARIOS_PATH, index=False)


def top_reporteros(n=5):
    usuarios = load_usuarios()
    if usuarios.empty or "puntos_reportero" not in usuarios.columns:
        return pd.DataFrame()
    top = usuarios[usuarios["puntos_reportero"] > 0].sort_values("puntos_reportero", ascending=False).head(n)
    if top.empty:
        return top
    top = top.copy()
    top["correo_oculto"] = top["email"].apply(
        lambda e: (str(e)[:2] + "***@" + str(e).split("@")[-1]) if "@" in str(e) else "***"
    )
    return top[["correo_oculto", "puntos_reportero"]]


# ================= PRECIO DEL PLAN POR TAMAÑO DE FLOTA =================
def calcular_precio_plan(num_vehiculos):
    """Pricing escalonado por tamaño de flota en vez de un precio plano de S/10."""
    if num_vehiculos <= 5:
        return 15
    elif num_vehiculos <= 15:
        return 35
    elif num_vehiculos <= 50:
        return 90
    return None  # plan empresarial a medida


# ================= VERIFICACIÓN COMUNITARIA DE PRECIOS =================
def calcular_verificacion_precio(reportes_df, estacion, dias=7, tolerancia=0.15):
    """Si 2+ usuarios DISTINTOS reportan un precio similar en los últimos `dias` días,
    el precio se marca como verificado por la comunidad."""
    if reportes_df.empty:
        return False, 0
    df_r = reportes_df.copy()
    df_r["fecha"] = pd.to_datetime(df_r["fecha"], errors="coerce")
    recientes = df_r[(df_r["estacion"] == estacion) & (df_r["fecha"] >= datetime.now() - pd.Timedelta(days=dias))]
    if recientes.empty:
        return False, 0
    precio_mediana = recientes["precio_reportado"].median()
    coincidentes = recientes[(recientes["precio_reportado"] - precio_mediana).abs() <= tolerancia]
    if "email_reportero" in coincidentes.columns:
        n_distintos = coincidentes["email_reportero"].dropna().nunique()
    else:
        n_distintos = len(coincidentes)
    return n_distintos >= 2, n_distintos


# ================= PREDICCIÓN DE RIESGO POR DÍA DE LA SEMANA =================
@st.cache_data
def predecir_riesgo_semana(historico, categoria):
    """Estima qué día de la semana ha tenido históricamente más subidas de precio
    para una categoría de combustible, usando solo el histórico propio (sin APIs)."""
    if historico.empty or not categoria:
        return {}
    h = historico[historico["categoria"] == categoria].copy()
    if h.empty:
        return {}
    h = h.sort_values(["RUC", "DIRECCIÓN", "FECHA DE REGISTRO"])
    h["cambio"] = h.groupby(["RUC", "DIRECCIÓN"])["PRECIO DE VENTA (SOLES)"].diff()
    h = h.dropna(subset=["cambio", "FECHA DE REGISTRO"])
    if h.empty:
        return {}
    h["dia_semana"] = h["FECHA DE REGISTRO"].dt.day_name()
    total_por_dia = h.groupby("dia_semana")["cambio"].count()
    subidas_por_dia = h[h["cambio"] > 0].groupby("dia_semana")["cambio"].count()
    riesgo = (subidas_por_dia / total_por_dia).fillna(0).sort_values(ascending=False)
    return riesgo.to_dict()


# ================= NUEVO 1: BACKTEST HISTÓRICO (ahorro comprobado, no proyectado) =================
def calcular_backtest_historico(historico, df_actual, distritos, categoria, consumo_mensual_galones, meses=4):
    """Backtest: ¿cuánto habría ahorrado la flota en los últimos `meses` meses
    si hubiera seguido la recomendación de la estación más barata cada mes,
    comparado con pagar el promedio de la zona? Basado 100% en datos históricos reales,
    no en una proyección hipotética."""
    if historico.empty or not distritos:
        return pd.DataFrame()

    mapa_distrito = df_actual[["ruc", "direccion", "distrito"]].drop_duplicates(subset=["ruc", "direccion"])
    h = historico.merge(mapa_distrito, left_on=["RUC", "DIRECCIÓN"], right_on=["ruc", "direccion"], how="inner")
    h = h[(h["categoria"] == categoria) & (h["distrito"].isin(distritos))].copy()
    if h.empty:
        return pd.DataFrame()

    fecha_max = h["FECHA DE REGISTRO"].max()
    fecha_min = fecha_max - pd.Timedelta(days=30 * meses)
    h = h[h["FECHA DE REGISTRO"] >= fecha_min]
    if h.empty:
        return pd.DataFrame()
    h["mes"] = h["FECHA DE REGISTRO"].dt.to_period("M").astype(str)

    filas = []
    for (mes, distrito), grupo in h.groupby(["mes", "distrito"]):
        promedio_estacion = grupo.groupby(["RUC", "DIRECCIÓN"])["PRECIO DE VENTA (SOLES)"].mean()
        if promedio_estacion.empty:
            continue
        precio_recomendado = promedio_estacion.min()
        precio_promedio_zona = promedio_estacion.mean()
        ahorro_galon = precio_promedio_zona - precio_recomendado
        filas.append({
            "Mes": mes, "Distrito": distrito,
            "Precio recomendado": round(precio_recomendado, 2),
            "Promedio de zona": round(precio_promedio_zona, 2),
            "Ahorro por galón": round(ahorro_galon, 2),
        })
    if not filas:
        return pd.DataFrame()
    df_bt = pd.DataFrame(filas).sort_values(["Mes", "Distrito"])
    df_bt["Ahorro estimado (S/)"] = df_bt["Ahorro por galón"] * consumo_mensual_galones
    return df_bt


# ================= NUEVO 2: ÍNDICE DE RIESGO DE SHOCK (transparente, 3 componentes iguales) =================
def calcular_indice_shock(historico, df_actual, distrito, producto):
    """Índice de Riesgo de Shock (0-100) = promedio simple de 3 métricas, cada una con peso 1/3
    (peso igual a propósito: no hay evidencia para justificar pesos distintos, así evitamos
    sobreajustar el modelo sin datos que lo respalden):
    1) Dispersión de precios entre estaciones de la zona (coeficiente de variación)
    2) Riesgo histórico de subida para el día de la semana actual
    3) Frecuencia histórica de subidas en los últimos 60 días
    """
    # 1) Dispersión actual entre estaciones
    zona_actual = df_actual[(df_actual["distrito"] == distrito) & (df_actual["producto"] == producto)]
    if len(zona_actual) >= 2 and zona_actual["precio"].mean() > 0:
        cv = zona_actual["precio"].std() / zona_actual["precio"].mean()
        score_dispersion = min(100, cv * 1000)
    else:
        score_dispersion = 0

    h_zona = pd.DataFrame()
    if not historico.empty:
        mapa_distrito = df_actual[["ruc", "direccion", "distrito"]].drop_duplicates(subset=["ruc", "direccion"])
        h = historico.merge(mapa_distrito, left_on=["RUC", "DIRECCIÓN"], right_on=["ruc", "direccion"], how="inner")
        h_zona = h[(h["categoria"] == producto) & (h["distrito"] == distrito)].copy()

    # 2) Riesgo histórico del día de semana actual
    score_dia = 0
    if not h_zona.empty:
        riesgo_semana_zona = predecir_riesgo_semana(h_zona, producto)
        dia_hoy_en = DIAS_EN[datetime.now().weekday()]
        score_dia = riesgo_semana_zona.get(dia_hoy_en, 0) * 100

    # 3) Frecuencia histórica reciente de subidas (últimos 60 días)
    score_volatilidad = 0
    if not h_zona.empty:
        h_zona = h_zona.sort_values(["RUC", "DIRECCIÓN", "FECHA DE REGISTRO"])
        h_zona["cambio"] = h_zona.groupby(["RUC", "DIRECCIÓN"])["PRECIO DE VENTA (SOLES)"].diff()
        fecha_max_z = h_zona["FECHA DE REGISTRO"].max()
        if pd.notna(fecha_max_z):
            recientes = h_zona[h_zona["FECHA DE REGISTRO"] >= fecha_max_z - pd.Timedelta(days=60)]
            cambios_recientes = recientes["cambio"].dropna()
            if len(cambios_recientes) > 0:
                score_volatilidad = (cambios_recientes > 0).mean() * 100

    indice = round((score_dispersion + score_dia + score_volatilidad) / 3, 1)
    detalle = {
        "Dispersión entre estaciones": round(score_dispersion, 1),
        "Riesgo del día de hoy": round(score_dia, 1),
        "Volatilidad reciente (60 días)": round(score_volatilidad, 1),
    }
    return indice, detalle


def etiqueta_riesgo(indice):
    if indice < 33:
        return "🟢 Bajo", "#1B8A5A"
    elif indice < 66:
        return "🟡 Medio", "#F4A623"
    return "🔴 Alto", "#D62828"


def gauge_svg(valor, etiqueta_texto):
    """Dibuja el Índice de Riesgo de Shock como un gauge tipo tablero de auto
    (igual al medidor de gasolina/temperatura), en vez de solo texto de color."""
    cx, cy, r = 90, 92, 68

    def punto(phi_deg, radio):
        phi = math.radians(phi_deg)
        return cx + radio * math.cos(phi), cy + radio * math.sin(phi)

    def banda(v_ini, v_fin, color):
        x1, y1 = punto(180 + (v_ini / 100) * 180, r)
        x2, y2 = punto(180 + (v_fin / 100) * 180, r)
        return f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 0 1 {x2:.1f} {y2:.1f}" stroke="{color}" stroke-width="14" fill="none" stroke-linecap="round" />'

    x_aguja, y_aguja = punto(180 + (valor / 100) * 180, r - 16)

    return f"""
    <svg viewBox="0 0 180 150" width="170">
        {banda(0, 33, "#1B8A5A")}
        {banda(33, 66, "#F4A623")}
        {banda(66, 100, "#D62828")}
        <line x1="{cx}" y1="{cy}" x2="{x_aguja:.1f}" y2="{y_aguja:.1f}" stroke="#14171F" stroke-width="4" stroke-linecap="round" />
        <circle cx="{cx}" cy="{cy}" r="6" fill="#14171F" />
        <text x="{cx}" y="{cy + 26}" text-anchor="middle" font-family="'Roboto Mono', monospace" font-size="22" font-weight="700" fill="#14171F">{valor:.0f}</text>
        <text x="{cx}" y="{cy + 42}" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="#5B6472">{etiqueta_texto}</text>
    </svg>
    """


# ================= NUEVO 3: RANKING DE OPORTUNIDAD DE AHORRO POR ZONA =================
def ranking_oportunidad_zonas(df_actual, producto, top_n=10):
    """Ranking de distritos según el coeficiente de variación de precios para un producto:
    a mayor dispersión, mayor diferencia real entre el grifo más caro y el más barato,
    y por lo tanto mayor oportunidad genuina de ahorro al optimizar."""
    filas = []
    for distrito, grupo in df_actual[df_actual["producto"] == producto].groupby("distrito"):
        if len(grupo) < 2 or grupo["precio"].mean() == 0:
            continue
        cv = grupo["precio"].std() / grupo["precio"].mean()
        filas.append({
            "Distrito": distrito,
            "Estaciones": len(grupo),
            "Precio mínimo": round(grupo["precio"].min(), 2),
            "Precio máximo": round(grupo["precio"].max(), 2),
            "Dispersión (CV)": round(cv, 3),
            "Oportunidad de ahorro (S//galón)": round(grupo["precio"].max() - grupo["precio"].min(), 2),
        })
    if not filas:
        return pd.DataFrame()
    return pd.DataFrame(filas).sort_values("Dispersión (CV)", ascending=False).head(top_n).reset_index(drop=True)


# ================= NUEVO 4: ANTIGÜEDAD DEL DATO OFICIAL (transparencia de fuente única) =================
def antiguedad_dato_oficial(historico, ruc, direccion, categoria):
    """Días transcurridos desde el último registro oficial de OSINERGMIN para esta
    estación y categoría. No agrega una segunda fuente, pero deja explícito qué tan
    desactualizado puede estar el único dato del que depende todo el sistema."""
    if historico.empty:
        return None
    h = historico[
        (historico["RUC"] == ruc) & (historico["DIRECCIÓN"] == direccion) & (historico["categoria"] == categoria)
    ]
    if h.empty:
        return None
    ultima_fecha = h["FECHA DE REGISTRO"].max()
    if pd.isna(ultima_fecha):
        return None
    return (datetime.now() - ultima_fecha).days


def etiqueta_antiguedad(dias):
    if dias is None:
        return "Sin histórico para esta estación", "#5B6472"
    if dias <= 15:
        return f"🟢 Actualizado hace {dias} días", "#1B8A5A"
    elif dias <= 30:
        return f"🟡 Hace {dias} días — revisar antes de confiar del todo", "#F4A623"
    return f"🔴 Hace {dias} días — dato oficial posiblemente desactualizado", "#D62828"


# ================= NUEVO 5: BÚSQUEDA POR VOZ CON WHISPER (local, sin API) =================
@st.cache_resource
def cargar_modelo_whisper():
    """Carga el modelo 'tiny' una sola vez (cacheado). Usamos faster-whisper en vez de
    openai-whisper porque NO depende de torch — instala ~60 MB en vez de ~1.2 GB,
    crítico para no tumbar el build en un free tier de despliegue."""
    return WhisperModel("tiny", device="cpu", compute_type="int8")


def transcribir_audio(audio_value):
    """Transcribe un audio grabado con st.audio_input. Si algo falla (modelo, formato,
    memoria), devuelve None en vez de tumbar la app — el resto de ShockWatch sigue
    funcionando igual aunque esta función específica no responda."""
    if not WHISPER_DISPONIBLE or audio_value is None:
        return None
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_value.getvalue())
            tmp_path = tmp.name
        modelo = cargar_modelo_whisper()
        segments, _ = modelo.transcribe(tmp_path, language="es")
        return " ".join(s.text for s in segments).strip()
    except Exception:
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def normalizar_texto(s):
    """Quita tildes y pasa a minúsculas, para que 'Surco' coincida con lo que diga
    Whisper aunque la transcripción venga con o sin acentos."""
    s = s.lower()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def buscar_distrito_en_texto(texto, distritos_disponibles, umbral=0.78):
    """Compara el texto transcrito contra la lista real de distritos (vocabulario cerrado,
    no intenta entender lenguaje libre). Whisper comete dos tipos de error típicos con
    nombres propios: separa palabras compuestas ("mira flores") o las deletrea mal
    fométicamente ("patcha comac" por "Pachacamac") — por eso el matching tiene 3 niveles,
    de más a menos confiable, y se detiene en el primero que encuentre algo:

    1) Coincidencia EXACTA completa (sin tildes/espacios) — resuelve el caso "mira flores"
       sin confundir "Miraflores" con "San Juan de Miraflores".
    2) Contención parcial, priorizando el nombre más largo/específico — resuelve que la
       gente diga el nombre corto y coloquial ("Surco" en vez de "Santiago de Surco").
    3) Similitud aproximada (difflib, de la librería estándar, sin dependencias nuevas)
       — resuelve errores fonéticos como "patcha comac".
    """
    if not texto:
        return None
    texto_norm = normalizar_texto(texto)
    texto_sin_espacios = texto_norm.replace(" ", "")
    if len(texto_sin_espacios) < 3:
        return None

    # Nivel 1: coincidencia exacta completa
    for distrito in distritos_disponibles:
        if normalizar_texto(distrito).replace(" ", "") == texto_sin_espacios:
            return distrito

    # Nivel 2: contención parcial (nombre corto/coloquial, o frases de relleno alrededor)
    candidatos = []
    for distrito in distritos_disponibles:
        distrito_sin_esp = normalizar_texto(distrito).replace(" ", "")
        if distrito_sin_esp in texto_sin_espacios or (
            len(texto_sin_espacios) >= 4 and texto_sin_espacios in distrito_sin_esp
        ):
            candidatos.append(distrito)
    if candidatos:
        return max(candidatos, key=len)

    # Nivel 3: similitud aproximada, tolera errores fonéticos
    palabras = texto_norm.split()
    candidatos_texto = list(palabras)
    candidatos_texto += [" ".join(palabras[i:i + 2]) for i in range(len(palabras) - 1)]
    candidatos_texto += [" ".join(palabras[i:i + 3]) for i in range(len(palabras) - 2)]
    candidatos_texto += [texto_sin_espacios, texto_norm]

    mejor_distrito, mejor_similitud = None, 0
    for distrito in distritos_disponibles:
        distrito_norm = normalizar_texto(distrito)
        distrito_sin_esp = distrito_norm.replace(" ", "")
        for candidato in candidatos_texto:
            similitud = max(
                difflib.SequenceMatcher(None, distrito_norm, candidato).ratio(),
                difflib.SequenceMatcher(None, distrito_sin_esp, candidato.replace(" ", "")).ratio(),
            )
            if similitud > mejor_similitud:
                mejor_similitud = similitud
                mejor_distrito = distrito
    return mejor_distrito if mejor_similitud >= umbral else None


DISTRITOS_CALLAO = {"CALLAO", "BELLAVISTA", "CARMEN DE LA LEGUA REYNOSO", "LA PERLA", "LA PUNTA", "VENTANILLA", "MI PERU"}

df = load_data()

if "departamento" not in st.session_state:
    st.session_state.departamento = None
if "distrito" not in st.session_state:
    st.session_state.distrito = None
if "vista_flota" not in st.session_state:
    st.session_state.vista_flota = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None

st.markdown(
    """
    <div style="background:#14171F; border-radius:12px; padding:22px 28px; margin-bottom:20px;
                border-left: 6px solid #F4A623;">
        <span style="font-family:'Oswald',sans-serif; font-weight:700; font-size:2rem;
                     letter-spacing:1px; color:#FAF8F4; text-transform:uppercase;">
            ⛽ ShockWatch
        </span>
        <div style="color:#B8B2A4; font-size:0.95rem; margin-top:4px;">
            Precios de combustible en tiempo real — Lima y Callao
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ================= AVISOS: ¿bajó el precio en mi distrito de interés? =================
if st.session_state.user_email:
    for aviso_precio in verificar_alertas_precio(st.session_state.user_email):
        st.success(aviso_precio)

# ================= BARRA LATERAL — CUENTA + RANKING DE REPORTEROS =================
with st.sidebar:
    st.markdown("### 👤 Mi cuenta")

    if st.session_state.user_email:
        usuario_sidebar = obtener_usuario(st.session_state.user_email)
        st.success(f"Sesión iniciada:\n{st.session_state.user_email}")
        if usuario_sidebar is not None:
            st.caption(f"🏆 {int(usuario_sidebar.get('puntos_reportero', 0) or 0)} puntos como reportero")
            if bool(usuario_sidebar.get("plan_pro", False)):
                st.caption(f"💰 Ahorro histórico (flota): S/ {float(usuario_sidebar.get('ahorro_historico', 0) or 0):.0f}")
        if st.button("Cerrar sesión"):
            st.session_state.user_email = None
            st.rerun()
    else:
        tab_login, tab_registro = st.tabs(["Iniciar sesión", "Crear cuenta"])
        with tab_login:
            email_l = st.text_input("Correo", key="login_email")
            pass_l = st.text_input("Contraseña", type="password", key="login_pass")
            if st.button("Entrar", key="btn_login"):
                ok, _ = verificar_login(email_l, pass_l)
                if ok:
                    st.session_state.user_email = email_l
                    st.rerun()
                else:
                    st.error("Correo o contraseña incorrectos.")
        with tab_registro:
            email_r = st.text_input("Correo", key="reg_email")
            pass_r = st.text_input("Contraseña", type="password", key="reg_pass")
            tipo_r = st.radio("Tipo de cuenta", ["consumidor", "flota"], key="reg_tipo")
            if st.button("Crear cuenta", key="btn_registro"):
                ok, msg = registrar_usuario(email_r, pass_r, tipo_r)
                if ok:
                    st.session_state.user_email = email_r
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        st.caption("Inicia sesión para guardar tu historial de ahorro y ganar puntos por tus reportes.")

    st.divider()
    st.markdown("### 🏆 Top reporteros")
    ranking_rep = top_reporteros()
    if ranking_rep.empty:
        st.caption("Aún no hay reportes con puntos. ¡Sé el primero!")
    else:
        for i, fila_rank in enumerate(ranking_rep.itertuples(), start=1):
            st.caption(f"{i}. {fila_rank.correo_oculto} — {int(fila_rank.puntos_reportero)} pts")

# ================= VISTA: PANEL DE FLOTA (B2B) =================
if st.session_state.vista_flota:
    if st.button("← Volver al modo consumidor"):
        st.session_state.vista_flota = False
        st.rerun()

    usuario_actual = obtener_usuario(st.session_state.user_email)

    if usuario_actual is not None:
        plan_pro_activo = bool(usuario_actual.get("plan_pro", False))
        ahorro_historico_actual = float(usuario_actual.get("ahorro_historico", 0) or 0)
        num_vehiculos_guardado = int(usuario_actual.get("num_vehiculos", 1) or 1)
    else:
        if "plan_pro" not in st.session_state:
            st.session_state.plan_pro = False
        if "ahorro_historico" not in st.session_state:
            st.session_state.ahorro_historico = 0
        plan_pro_activo = st.session_state.plan_pro
        ahorro_historico_actual = st.session_state.ahorro_historico
        num_vehiculos_guardado = 1

    st.subheader("🚚 Panel de Flota")
    st.caption("Dinos dónde opera tu flota y te decimos el grifo ideal en cada zona.")

    # --- Pricing por tamaño de flota, no precio plano ---
    num_vehiculos = st.number_input(
        "¿Cuántos vehículos tiene tu flota?", min_value=1, step=1, value=num_vehiculos_guardado
    )
    precio_plan = calcular_precio_plan(num_vehiculos)

    col_plan1, col_plan2 = st.columns(2)
    with col_plan1:
        st.markdown("**Plan Gratis**")
        st.caption("1 zona · recomendación básica")
    with col_plan2:
        if precio_plan:
            st.markdown(f"**⭐ Plan Flota Pro — S/ {precio_plan}/mes** ({num_vehiculos} vehículo{'s' if num_vehiculos != 1 else ''})")
        else:
            st.markdown("**⭐ Plan Flota Empresas — Personalizado**")
        st.caption("Múltiples zonas · análisis detallado · backtest histórico · informe descargable · historial de ahorro persistente")

        if not plan_pro_activo:
            if not precio_plan:
                st.info("Flota grande detectada (50+ vehículos). Contáctanos para un plan empresarial a medida.")
            else:
                if st.button(f"🔓 Activar Plan Flota Pro — S/ {precio_plan}/mes"):
                    if usuario_actual is not None:
                        actualizar_usuario(st.session_state.user_email, plan_pro=True, num_vehiculos=num_vehiculos)
                    else:
                        st.session_state.plan_pro = True
                    st.rerun()
                st.caption("*(pago simulado para esta demo)*")
            if not st.session_state.user_email:
                st.caption("⚠️ Sin iniciar sesión, tu plan y tu ahorro se perderán al cerrar el navegador.")
        else:
            st.success(f"✅ Plan Pro activo — S/ {precio_plan if precio_plan else 'plan empresarial'}/mes")

    with st.expander("📊 Ver tabla de precios completa"):
        st.table(pd.DataFrame({
            "Vehículos en la flota": ["1 – 5", "6 – 15", "16 – 50", "50+"],
            "Precio mensual": ["S/ 15", "S/ 35", "S/ 90", "Plan empresarial (a coordinar)"],
        }))

    st.divider()

    producto_flota = st.selectbox("Combustible principal de tu flota", sorted(df["producto"].unique()), key="producto_flota")

    # --- NUEVO 3: ranking de oportunidad por zona, ANTES de elegir distritos ---
    with st.expander("📊 ¿Dónde realmente conviene optimizar? (ranking de zonas por oportunidad de ahorro)"):
        ranking_zonas = ranking_oportunidad_zonas(df, producto_flota)
        if ranking_zonas.empty:
            st.caption("No hay suficientes datos para este combustible.")
        else:
            st.dataframe(ranking_zonas, hide_index=True, use_container_width=True)
            st.caption(
                "Dispersión (CV) = desviación estándar de precios ÷ precio promedio en la zona. "
                "A mayor dispersión, mayor diferencia real entre el grifo más caro y el más barato — "
                "y por lo tanto, mayor oportunidad de ahorro al elegir bien. En zonas con CV bajo, "
                "el servicio aporta poco valor porque todos cobran casi lo mismo."
            )

    historico = load_historico()

    max_zonas = None if plan_pro_activo else 1
    distritos_flota = st.multiselect(
        "¿En qué distritos opera tu flota?", sorted(df["distrito"].unique()), max_selections=max_zonas,
    )
    if not plan_pro_activo:
        st.caption("Plan Gratis: 1 zona a la vez. Activa el Plan Pro para comparar varias zonas juntas.")

    # --- Predicción de día de mayor riesgo de subida ---
    riesgo_semana_flota = predecir_riesgo_semana(historico, producto_flota)
    if riesgo_semana_flota:
        with st.expander("📅 ¿Qué día conviene abastecer la flota? (predicción basada en histórico)"):
            df_riesgo_flota = pd.DataFrame([
                {"Día": DIAS_ES.get(d, d), "Riesgo histórico de subida": f"{v * 100:.0f}%"}
                for d, v in riesgo_semana_flota.items()
            ])
            st.dataframe(df_riesgo_flota, hide_index=True, use_container_width=True)
            st.caption("Estimado a partir del histórico de precios de esta categoría. No garantiza el comportamiento futuro.")

    consumo_mensual_galones = st.number_input(
        "Consumo mensual estimado de tu flota (galones)",
        min_value=0, step=100, value=500
    )

    # --- Resumen rápido apenas elige zonas, ahora con Índice de Riesgo de Shock ---
    if distritos_flota:
        st.markdown("**📋 Resumen rápido de tus zonas**")
        cols_resumen = st.columns(len(distritos_flota))
        for i, distrito in enumerate(distritos_flota):
            zona_preview = df[(df["distrito"] == distrito) & (df["producto"] == producto_flota)]
            with cols_resumen[i]:
                st.metric(distrito, f"{len(zona_preview)} grifos")
                if len(zona_preview):
                    st.caption(f"S/ {zona_preview['precio'].min():.2f} – S/ {zona_preview['precio'].max():.2f}")
                    st.caption(f"Dispersión: S/ {zona_preview['precio'].max() - zona_preview['precio'].min():.2f}")
                indice_zona, _ = calcular_indice_shock(historico, df, distrito, producto_flota)
                etiqueta_zona, color_zona = etiqueta_riesgo(indice_zona)
                st.markdown(
                    f"<span style='color:{color_zona}; font-weight:700;'>{etiqueta_zona} ({indice_zona:.0f}/100)</span>",
                    unsafe_allow_html=True,
                )
        with st.expander("¿Cómo se calcula el Índice de Riesgo de Shock?"):
            st.markdown(
                "Promedio simple (peso igual, 1/3 cada uno) de:\n"
                "1. **Dispersión** entre estaciones de la zona (coeficiente de variación)\n"
                "2. **Riesgo del día de hoy** (% histórico de subidas ese día de la semana)\n"
                "3. **Volatilidad reciente** (% de subidas en los últimos 60 días)\n\n"
                "Se usa peso igual a propósito: no hay evidencia para justificar que un componente "
                "pese más que otro, así que no se sobreajusta el modelo sin datos que lo respalden."
            )

    st.divider()

    if st.button("Calcular plan de abastecimiento óptimo", type="primary") and distritos_flota:
        reportes_flota = load_reportes()
        rating_prom = reportes_flota.groupby("estacion")["calificacion"].mean() if len(reportes_flota) else pd.Series(dtype=float)

        recomendaciones = []
        detalle_por_distrito = {}

        for distrito in distritos_flota:
            zona = df[(df["distrito"] == distrito) & (df["producto"] == producto_flota)].copy()
            if len(zona) == 0:
                continue
            zona["clave"] = zona["nombre"] + " — " + zona["direccion"]
            zona["rating"] = zona["clave"].map(rating_prom).fillna(0)
            zona = zona.sort_values(["precio", "rating"], ascending=[True, False])
            mejor = zona.iloc[0]
            promedio_zona = zona["precio"].mean()
            indice_shock_d, detalle_indice_d = calcular_indice_shock(historico, df, distrito, producto_flota)
            etiqueta_d, _ = etiqueta_riesgo(indice_shock_d)
            dias_antig_d = antiguedad_dato_oficial(historico, mejor["ruc"], mejor["direccion"], producto_flota)
            etiqueta_antig_d, _ = etiqueta_antiguedad(dias_antig_d)

            recomendaciones.append({
                "Distrito": distrito, "Grifo recomendado": mejor["nombre"], "Dirección": mejor["direccion"],
                "Precio": round(mejor["precio"], 2), "Promedio de zona": round(promedio_zona, 2),
                "Calificación": round(mejor["rating"], 1) if mejor["rating"] > 0 else None,
                "Ahorro por galón": round(promedio_zona - mejor["precio"], 2),
                "Índice de riesgo": f"{indice_shock_d:.0f} ({etiqueta_d})",
                "Antigüedad del dato": etiqueta_antig_d,
            })
            detalle_por_distrito[distrito] = {
                "estaciones_en_zona": len(zona), "tendencia_grifo": mejor.get("tendencia", "Sin datos"),
                "ruc": mejor["ruc"], "direccion": mejor["direccion"],
                "indice_shock": indice_shock_d, "detalle_indice": detalle_indice_d,
            }

        if recomendaciones:
            df_recom = pd.DataFrame(recomendaciones)
            ahorro_mensual = df_recom["Ahorro por galón"].mean() * consumo_mensual_galones

            st.success(f"Grifo ideal encontrado en {len(df_recom)} de tus zonas:")
            st.dataframe(df_recom, hide_index=True, use_container_width=True)

            if plan_pro_activo:
                # --- Ahorro persistido por cuenta ---
                if ahorro_mensual > 0:
                    nuevo_ahorro_historico = ahorro_historico_actual + ahorro_mensual
                    if usuario_actual is not None:
                        actualizar_usuario(st.session_state.user_email, ahorro_historico=nuevo_ahorro_historico)
                    else:
                        st.session_state.ahorro_historico = nuevo_ahorro_historico
                    ahorro_historico_actual = nuevo_ahorro_historico

                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.metric("📈 Ahorro histórico acumulado (proyectado)", f"S/ {ahorro_historico_actual:.0f}")
                with col_m2:
                    if precio_plan and ahorro_mensual > 0:
                        roi = ahorro_mensual / precio_plan
                        st.metric("💡 Retorno sobre el plan (este mes)", f"{roi:.1f}x")

                if precio_plan and ahorro_mensual > 0:
                    st.info(
                        f"Tu plan cuesta S/ {precio_plan}/mes y este cálculo proyecta un ahorro de "
                        f"S/ {ahorro_mensual:.0f}/mes → el plan se paga solo y deja ganancia neta."
                    )

                # --- NUEVO 1: BACKTEST HISTÓRICO — ahorro comprobado, no proyectado ---
                st.subheader("🔬 Backtest histórico: ahorro comprobado con datos reales")
                st.caption(
                    "Esto NO es una proyección: es lo que la flota habría ahorrado realmente cada mes "
                    "si hubiera elegido la estación más barata de la zona, según los precios "
                    "históricos registrados por OSINERGMIN."
                )
                df_backtest = calcular_backtest_historico(historico, df, distritos_flota, producto_flota, consumo_mensual_galones, meses=4)
                if not df_backtest.empty:
                    resumen_mes = df_backtest.groupby("Mes")["Ahorro estimado (S/)"].sum().reset_index().sort_values("Mes")
                    resumen_mes["Ahorro acumulado"] = resumen_mes["Ahorro estimado (S/)"].cumsum()
                    total_comprobado = resumen_mes["Ahorro estimado (S/)"].sum()

                    st.metric("💰 Ahorro total comprobado (meses con histórico disponible)", f"S/ {total_comprobado:.0f}")

                    fig_bt = px.bar(
                        resumen_mes, x="Mes", y="Ahorro estimado (S/)",
                        color_discrete_sequence=["#1B8A5A"], labels={"Ahorro estimado (S/)": "S/ ahorrados ese mes"},
                    )
                    fig_bt.add_scatter(
                        x=resumen_mes["Mes"], y=resumen_mes["Ahorro acumulado"],
                        mode="lines+markers", name="Ahorro acumulado", line=dict(color="#D62828"),
                    )
                    st.plotly_chart(fig_bt, use_container_width=True)

                    with st.expander("Ver detalle del backtest por zona y mes"):
                        st.dataframe(df_backtest, hide_index=True, use_container_width=True)
                else:
                    st.caption("No hay suficiente histórico todavía para hacer un backtest de estas zonas/combustible.")

                st.subheader("📊 Precio recomendado vs. promedio de la zona")
                fig = px.bar(
                    df_recom, x="Distrito", y=["Precio", "Promedio de zona"], barmode="group",
                    color_discrete_sequence=["#1B8A5A", "#5B6472"],
                    labels={"value": "S/ por galón", "variable": ""},
                )
                y_min = min(df_recom["Precio"].min(), df_recom["Promedio de zona"].min())
                y_max = max(df_recom["Precio"].max(), df_recom["Promedio de zona"].max())
                margen = (y_max - y_min) * 0.25 if y_max > y_min else y_max * 0.1
                fig.update_yaxes(range=[max(0, y_min - margen), y_max + margen])
                fig.update_layout(legend_title_text="")
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("📈 Histórico de precio (últimos 4 meses) por grifo recomendado")
                if not historico.empty:
                    for distrito, info in detalle_por_distrito.items():
                        hist_estacion = historico[
                            (historico["RUC"] == info["ruc"]) &
                            (historico["DIRECCIÓN"] == info["direccion"]) &
                            (historico["categoria"] == producto_flota)
                        ].sort_values("FECHA DE REGISTRO")

                        if len(hist_estacion) >= 2:
                            fecha_max = historico["FECHA DE REGISTRO"].max()
                            hist_4m = hist_estacion[hist_estacion["FECHA DE REGISTRO"] >= fecha_max - pd.Timedelta(days=120)]
                            st.caption(f"**{distrito}** — {info['tendencia_grifo']}")
                            st.line_chart(hist_4m.set_index("FECHA DE REGISTRO")["PRECIO DE VENTA (SOLES)"])
                        else:
                            st.caption(f"**{distrito}**: histórico insuficiente para graficar tendencia.")
                else:
                    st.caption("No se encontró el archivo de histórico completo.")

                csv = df_recom.to_csv(index=False).encode("utf-8")
                pdf_bytes = generar_pdf_flota(df_recom, detalle_por_distrito, historico, producto_flota, ahorro_mensual, consumo_mensual_galones)

                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    st.download_button("📥 Descargar CSV", csv, file_name="shockwatch_plan_flota.csv", mime="text/csv")
                with col_dl2:
                    st.download_button("📄 Descargar informe PDF", pdf_bytes, file_name="shockwatch_informe_flota.pdf", mime="application/pdf")

            else:
                st.info("🔒 Activa el Plan Pro para ver el backtest histórico comprobado, gráficos, informe descargable y ahorro acumulado persistente.")
        else:
            st.warning("No encontramos estaciones para esa combinación de distritos y combustible.")

# ================= VISTA: CONSUMIDOR (B2C) =================
elif st.session_state.departamento is None:
    st.subheader("¿Dónde quieres buscar?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📍 LIMA", use_container_width=True, key="dep_lima"):
            st.session_state.departamento = "LIMA"
            st.rerun()
    with col2:
        if st.button("📍 CALLAO", use_container_width=True, key="dep_callao"):
            st.session_state.departamento = "CALLAO"
            st.rerun()

    st.write("")
    st.caption("🔎 O busca tu distrito directamente")
    distritos_todos = sorted(df["distrito"].unique())
    busqueda = st.selectbox("Buscar distrito", ["— Escribe para buscar —"] + distritos_todos, label_visibility="collapsed")
    if busqueda != "— Escribe para buscar —":
        st.session_state.departamento = "CALLAO" if busqueda in DISTRITOS_CALLAO else "LIMA"
        st.session_state.distrito = busqueda
        st.rerun()

    if WHISPER_DISPONIBLE:
        st.caption("🎤 O dilo en voz alta — pensado para cuando estás manejando")
        audio_busqueda = st.audio_input("Di el nombre de tu distrito", label_visibility="collapsed")
        if audio_busqueda is not None:
            with st.spinner("Transcribiendo con Whisper (corre local, sin API)..."):
                texto_voz = transcribir_audio(audio_busqueda)
            if texto_voz:
                distrito_encontrado = buscar_distrito_en_texto(texto_voz, distritos_todos)
                if distrito_encontrado:
                    st.success(f'Escuché: "{texto_voz}" → {distrito_encontrado}')
                    st.session_state.departamento = "CALLAO" if distrito_encontrado in DISTRITOS_CALLAO else "LIMA"
                    st.session_state.distrito = distrito_encontrado
                    st.rerun()
                else:
                    st.warning(f'Escuché: "{texto_voz}" — no reconocí ningún distrito ahí. Intenta de nuevo o usa el buscador de arriba.')
            else:
                st.warning("No pudimos procesar el audio. Intenta de nuevo o usa el buscador de arriba.")

    st.write("")
    st.divider()
    if st.button("🚚 Tengo una flota — ver panel de optimización"):
        st.session_state.vista_flota = True
        st.rerun()

elif st.session_state.distrito is None:
    if st.button("← Cambiar departamento"):
        st.session_state.departamento = None
        st.rerun()

    st.subheader(f"Distrito en {st.session_state.departamento}")
    distritos_disponibles = sorted(df["distrito"].unique())
    distrito_elegido = st.selectbox("Selecciona tu distrito", ["Todos los distritos"] + distritos_disponibles)

    if st.button("Ver precios →", type="primary"):
        st.session_state.distrito = distrito_elegido
        st.rerun()

else:
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("← Cambiar distrito"):
            st.session_state.distrito = None
            st.rerun()

    st.caption(f"Mostrando: {st.session_state.departamento} — {st.session_state.distrito}")

    df_dep = df.copy()
    if st.session_state.distrito != "Todos los distritos":
        df_dep = df_dep[df_dep["distrito"] == st.session_state.distrito]

    col_f1, col_f2 = st.columns(2)
    productos = sorted(df_dep["producto"].unique())
    default_idx = productos.index("Gasohol Regular (84)") if "Gasohol Regular (84)" in productos else 0
    with col_f1:
        producto = st.selectbox("Tipo de combustible", productos, index=default_idx)
    with col_f2:
        marcas = ["Todas las marcas"] + sorted(df_dep["marca"].unique())
        marca_sel = st.selectbox("Marca / cadena", marcas)

    df_f = df_dep[df_dep["producto"] == producto].copy()
    if marca_sel != "Todas las marcas":
        df_f = df_f[df_f["marca"] == marca_sel]

    if len(df_f) == 0:
        st.warning("No hay estaciones para esta combinación de filtros.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Precio promedio", f"S/ {df_f['precio'].mean():.2f}")
        c2.metric("Más barato", f"S/ {df_f['precio'].min():.2f}")
        c3.metric("Más caro", f"S/ {df_f['precio'].max():.2f}")
        c4.metric("Estaciones", f"{len(df_f)}")

        historico_b2c = load_historico()

        # --- NUEVO 2: Índice de Riesgo de Shock para la zona/producto actual (gauge) ---
        if st.session_state.distrito != "Todos los distritos":
            indice_b2c, detalle_b2c = calcular_indice_shock(historico_b2c, df, st.session_state.distrito, producto)
            etiqueta_b2c, color_b2c = etiqueta_riesgo(indice_b2c)
            col_idx1, col_idx2 = st.columns([1, 2])
            with col_idx1:
                st.markdown(gauge_svg(indice_b2c, "Riesgo de shock"), unsafe_allow_html=True)
            with col_idx2:
                st.markdown(f"<div style='padding-top:2.2em; color:{color_b2c}; font-weight:700; font-size:1.1rem;'>{etiqueta_b2c}</div>", unsafe_allow_html=True)
                with st.expander("¿Cómo se calcula este índice?"):
                    for k, v in detalle_b2c.items():
                        st.caption(f"• {k}: {v}/100")
                    st.caption("Promedio simple de los tres componentes (peso igual, sin sobreajuste).")

        # --- Predicción de día de la semana ---
        riesgo_semana_b2c = predecir_riesgo_semana(historico_b2c, producto)
        if riesgo_semana_b2c:
            with st.expander("📅 ¿Qué día conviene llenar el tanque? (predicción basada en histórico)"):
                df_riesgo_b2c = pd.DataFrame([
                    {"Día": DIAS_ES.get(d, d), "Riesgo histórico de subida": f"{v * 100:.0f}%"}
                    for d, v in riesgo_semana_b2c.items()
                ])
                st.dataframe(df_riesgo_b2c, hide_index=True, use_container_width=True)
                st.caption("Estimado a partir del histórico de precios de esta categoría. No garantiza el comportamiento futuro.")

        st.divider()
        col_map, col_list = st.columns([2, 1])

        p_min, p_max = df_f["precio"].min(), df_f["precio"].max()

        def color_precio(p):
            if p_max == p_min:
                return "#1B8A5A"
            ratio = (p - p_min) / (p_max - p_min)
            if ratio < 0.33:
                return "#1B8A5A"
            elif ratio < 0.66:
                return "#F4A623"
            return "#D62828"

        centro_lat, centro_lon = df_f["lat"].mean(), df_f["lon"].mean()

        with col_map:
            m = folium.Map(location=[centro_lat, centro_lon], zoom_start=13, tiles="cartodbpositron")
            for _, row in df_f.iterrows():
                color = color_precio(row["precio"])
                popup_html = (
                    f"<b>{row['nombre']}</b><br>{row['direccion']}<br>"
                    f"<i>{row['distrito']} · {row['marca']}</i><br>"
                    f"<b style='font-size:1.1em'>S/ {row['precio']:.2f}</b><br>"
                    f"<span style='font-size:0.85em'>{row['tendencia']}</span>"
                )
                etiqueta_html = f"""
                <div style="background-color:#14171F; color:{color}; border-radius:4px;
                            padding:3px 7px; font-size:11px; font-weight:700;
                            font-family:'Roboto Mono','Courier New',monospace;
                            white-space:nowrap; box-shadow:0 1px 3px rgba(0,0,0,0.4);
                            text-align:center; border:1px solid {color}55;">
                    {row['precio']:.2f}
                </div>"""
                folium.Marker(
                    location=[row["lat"], row["lon"]],
                    icon=folium.DivIcon(html=etiqueta_html, icon_size=(55, 22), icon_anchor=(27, 11), class_name="empty"),
                    popup=folium.Popup(popup_html, max_width=260),
                ).add_to(m)
            st_folium(m, width=None, height=520, returned_objects=[])

        with col_list:
            st.subheader("🎯 Elige tu grifo — cerca y barato primero")
            st.caption("Ranking combinado: 50% precio, 50% cercanía a tu zona (simulada al centro de tu búsqueda; en producción usaría tu GPS real).")

            df_ranking = df_f.copy()
            df_ranking["distancia_km"] = df_ranking.apply(
                lambda r: haversine_km(centro_lat, centro_lon, r["lat"], r["lon"]), axis=1
            )
            p_min_r, p_max_r = df_ranking["precio"].min(), df_ranking["precio"].max()
            d_min_r, d_max_r = df_ranking["distancia_km"].min(), df_ranking["distancia_km"].max()

            def _score_combinado(row):
                precio_norm = (row["precio"] - p_min_r) / (p_max_r - p_min_r) if p_max_r > p_min_r else 0
                dist_norm = (row["distancia_km"] - d_min_r) / (d_max_r - d_min_r) if d_max_r > d_min_r else 0
                return 0.5 * precio_norm + 0.5 * dist_norm

            df_ranking["score"] = df_ranking.apply(_score_combinado, axis=1)
            df_ranking = df_ranking.sort_values("score").head(10)

            if "grifo_seleccionado" not in st.session_state:
                st.session_state.grifo_seleccionado = None

            for idx, (_, row) in enumerate(df_ranking.iterrows()):
                medalla = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"{idx + 1}."
                clave = row["nombre"] + " — " + row["direccion"]
                st.markdown(
                    f"""<div style="background:#fff; border:1px solid #E8E4DC; border-radius:10px;
                                padding:10px 14px; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-size:0.8em; color:#5B6472;">{medalla}</span><br>
                            <span style="font-weight:600; color:#14171F;">{row['nombre']}</span><br>
                            <span style="font-size:0.75em; color:#5B6472;">{row['distrito']} · {row['marca']} · {row['distancia_km']*1000:.0f} m</span><br>
                            <span style="font-size:0.72em; color:#9B9486;">{row['tendencia']}</span>
                        </div>
                        <div style="background:#14171F; border-radius:6px; padding:6px 10px;">
                            <span class="precio-mono" style="font-size:1.1em; color:{color_precio(row['precio'])};">S/{row['precio']:.2f}</span>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                if st.button("Ver detalle →", key=f"ver_detalle_card_{idx}", use_container_width=True):
                    st.session_state.grifo_seleccionado = clave
                    st.rerun()
                st.write("")

        st.divider()
        st.subheader("🔍 O busca un grifo específico")
        opciones = ["— Elige un grifo —"] + (df_f["nombre"] + " — " + df_f["direccion"]).tolist()
        indice_default = 0
        if st.session_state.get("grifo_seleccionado") in opciones:
            indice_default = opciones.index(st.session_state.grifo_seleccionado)
        grifo_sel = st.selectbox("Grifo", opciones, index=indice_default, label_visibility="collapsed")

        if grifo_sel != "— Elige un grifo —":
            st.session_state.grifo_seleccionado = grifo_sel
            fila = df_f[(df_f["nombre"] + " — " + df_f["direccion"]) == grifo_sel].iloc[0]
            st.markdown(f"### {fila['nombre']}")
            st.markdown(f"{fila['direccion']} · {fila['distrito']} · {fila['marca']}")
            st.markdown(f"**Precio actual: S/ {fila['precio']:.2f}**")
            st.markdown(f"*{fila['tendencia']}*")

            reportes_calif = load_reportes()
            reportes_de_este_grifo = reportes_calif[reportes_calif["estacion"] == grifo_sel]
            if len(reportes_de_este_grifo):
                calif_prom = reportes_de_este_grifo["calificacion"].mean()
                n_rep = len(reportes_de_este_grifo)
                st.markdown(f"⭐ **{calif_prom:.1f}/5** ({n_rep} reporte{'s' if n_rep != 1 else ''} de la comunidad)")
            else:
                st.caption("⭐ Aún sin calificaciones de la comunidad.")

            dias_antig_b2c = antiguedad_dato_oficial(historico_b2c, fila["ruc"], fila["direccion"], producto)
            etiqueta_antig_b2c, color_antig_b2c = etiqueta_antiguedad(dias_antig_b2c)
            st.markdown(f"<span style='color:{color_antig_b2c};'>{etiqueta_antig_b2c}</span>", unsafe_allow_html=True)
            st.caption("Esto es el rezago del registro oficial de OSINERGMIN, la única fuente de este dato — se muestra para que sepas qué tan al día está.")

            reportes_para_verificacion = load_reportes()
            verificado, n_coinciden = calcular_verificacion_precio(reportes_para_verificacion, grifo_sel)
            if verificado:
                st.success(f"✅ Precio verificado por la comunidad ({n_coinciden} reportes recientes de usuarios distintos coinciden)")

            maps_url = f"https://www.google.com/maps/dir/?api=1&destination={fila['lat']},{fila['lon']}"
            st.markdown(f'<a href="{maps_url}" target="_blank" style="color:#1B8A5A; font-weight:600;">📍 Cómo llegar</a>', unsafe_allow_html=True)

            st.write("")
            col_rep, col_wait = st.columns(2)

            with col_rep:
                st.markdown("**📢 Reporta tu experiencia**")
                if not st.session_state.user_email:
                    st.info("Inicia sesión en la barra lateral para reportar (evita spam y te da puntos 🏆).")
                with st.form("form_reporte", clear_on_submit=True):
                    precio_reportado = st.number_input("Precio que viste (S/)", min_value=0.0, step=0.1)
                    st.write("Calificación del servicio")
                    estrellas = st.feedback("stars")
                    comentario = st.text_area("Comentario (opcional)")
                    enviado = st.form_submit_button("Enviar reporte")
                    if enviado:
                        if not st.session_state.user_email:
                            st.error("Debes iniciar sesión para poder reportar.")
                        else:
                            calificacion = (estrellas + 1) if estrellas is not None else None
                            if calificacion is None:
                                st.error("Selecciona una calificación en estrellas.")
                            else:
                                guardar_reporte(grifo_sel, fila["distrito"], precio_reportado, calificacion, comentario, st.session_state.user_email)
                                sumar_puntos(st.session_state.user_email, 10)
                                st.success("¡Gracias! Tu reporte fue guardado. +10 puntos 🏆")

                reportes = load_reportes()
                reportes_de_este = reportes[reportes["estacion"] == grifo_sel]
                if len(reportes_de_este):
                    st.caption("Reportes de la comunidad para este grifo:")
                    st.dataframe(reportes_de_este[["fecha", "precio_reportado", "calificacion", "comentario"]],
                                 hide_index=True, use_container_width=True)

            with col_wait:
                st.markdown("**🔔 Avísame si hay riesgo de shock antes de salir**")
                st.caption("Lista de espera para alertas predictivas (v2). Por ahora registramos tu interés.")
                with st.form("form_waitlist", clear_on_submit=True):
                    correo = st.text_input("Tu correo")
                    enviado_w = st.form_submit_button("Suscribirme")
                    if enviado_w and correo:
                        guardar_waitlist(correo, fila["distrito"], producto)
                        st.success("¡Listo!")
                waitlist = load_waitlist()
                st.metric("Personas en la lista de espera", len(waitlist))