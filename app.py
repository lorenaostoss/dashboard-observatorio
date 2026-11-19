"""
Observatorio de Salud Mental · ¿Dónde intervenir primero para prevenir el burnout?
Tablero para equipos de Talento Humano y SST.
Ejecutar:  streamlit run app.py
"""
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================================
# 1. CONFIGURACIÓN Y PALETA
# ============================================================================
st.set_page_config(page_title="Observatorio · Burnout", page_icon="🌿", layout="wide")

VERDE_OSCURO = "#0E2E17"   # títulos, "mi organización", menú activo
SALVIA = "#6B906E"         # condición favorable, cambios buenos
OLIVA = "#887F22"          # acentos y líneas de referencia
MALVA = "#8B6074"          # intención de retiro
OXIDO = "#78442F"          # condición desfavorable, riesgo, prioridad
GRIS = "#B9C1BA"           # contexto (las demás organizaciones)
GRIS_TEXTO = "#5E6B61"
BORDE = "#E4E9E3"
FUENTE = "Source Sans Pro, sans-serif"

TODAS = "Todas las organizaciones"
N_MIN = 10
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ============================================================================
# 2. ESTILO (CSS): fondo blanco, tarjetas redondeadas, menú lateral
# ============================================================================
st.markdown(f"""
<style>
  .stApp {{ background: #FFFFFF; }}
  .block-container {{ padding-top: 3.2rem; padding-bottom: 2rem; max-width: 1400px; }}
  h1, h2, h3, h4 {{ color: {VERDE_OSCURO}; }}

  /* Menú lateral */
  section[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid {BORDE}; }}
  .marca {{ display:flex; align-items:center; gap:12px; margin: 4px 0 22px 0; }}
  .marca .logo {{ width:42px; height:42px; border-radius:11px; background:{VERDE_OSCURO};
                  color:#fff; font-weight:700; display:flex; align-items:center; justify-content:center; }}
  .marca .t1 {{ color:{VERDE_OSCURO}; font-weight:700; line-height:1.1; }}
  .marca .t2 {{ color:{GRIS_TEXTO}; font-size:.85rem; }}
  .seccion {{ color:{VERDE_OSCURO}; font-weight:700; font-size:1.05rem; margin:18px 0 6px 0; }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > div {{ width: 100%; }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label {{
      padding: 9px 12px; border-radius: 10px; margin-bottom: 4px; width: 100%; cursor: pointer; }}
  /* ocultar el círculo del radio (dos variantes según la versión de Streamlit) */
  section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child:not(:has([data-testid="stMarkdownContainer"])),
  section[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child:not([data-testid="stMarkdownContainer"]) {{
      display: none; }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{ background:#F1F4F0; }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{ background:{VERDE_OSCURO}; }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {{ color:#FFFFFF; font-weight:600; }}
  .pie {{ background:{SALVIA}; color:#fff; border-radius:12px; padding:14px; font-size:.82rem; margin-top:26px; }}

  /* Encabezado */
  .encabezado {{ display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:14px; }}
  .encabezado .titulo {{ font-size:1.9rem; font-weight:700; color:{VERDE_OSCURO}; line-height:1.15; }}
  .encabezado .sub {{ color:{GRIS_TEXTO}; }}
  .chip {{ display:inline-block; border:1px solid {BORDE}; border-radius:9px; padding:6px 12px;
           color:{GRIS_TEXTO}; font-size:.85rem; margin-left:8px; background:#fff; }}

  /* Tarjetas */
  .kpi {{ background:#fff; border:1px solid {BORDE}; border-radius:14px; padding:16px 18px;
          box-shadow:0 2px 10px rgba(14,46,23,.05); height:100%; }}
  .kpi .lbl {{ color:{GRIS_TEXTO}; font-size:.9rem; }}
  .kpi .val {{ color:{VERDE_OSCURO}; font-size:1.9rem; font-weight:700; margin-top:4px; }}
  .kpi .nota {{ color:{GRIS_TEXTO}; font-size:.78rem; margin-top:2px; }}
  .pill {{ display:inline-block; font-size:.78rem; font-weight:600; padding:2px 8px; border-radius:7px;
           margin-left:8px; vertical-align:middle; }}
  .pill.mal {{ color:{OXIDO}; background:#F3E9E4; border:1px solid #E2CBBF; }}
  .pill.bien {{ color:#3F5E42; background:#E9F0E9; border:1px solid #CADBCB; }}
  .pill.neutro {{ color:{GRIS_TEXTO}; background:#F1F3F0; border:1px solid {BORDE}; }}
  div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:14px !important; border-color:{BORDE} !important;
          box-shadow:0 2px 10px rgba(14,46,23,.05); background:#fff; }}
  .titulo-tarjeta {{ color:{VERDE_OSCURO}; font-weight:700; font-size:1.08rem; margin-bottom:0; }}
  .sub-tarjeta {{ color:{GRIS_TEXTO}; font-size:.85rem; margin-bottom:6px; }}
  .etq {{ color:{GRIS_TEXTO}; font-size:.78rem; }}
  .aviso {{ background:#FAF7EC; border-left:4px solid {OLIVA}; border-radius:8px; padding:10px 14px;
            color:#4A4520; font-size:.9rem; margin-top:6px; }}
  .ilustrativo {{ background:#F7F1F4; border:1px dashed {MALVA}; border-radius:12px; padding:12px 16px; color:#4E3542; }}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# 3. DATOS (solo tablas agregadas, generadas por preparar_datos.py)
# ============================================================================
@st.cache_data
def cargar():
    archivos = ["agregados_org", "agregados_grupo", "factores_org", "asociacion", "items_org",
                "sensibilidad", "registro_limpieza", "verificaciones", "retiro_riesgo"]
    return {k: pd.read_csv(os.path.join(DATA, f"{k}.csv")) for k in archivos}


D = cargar()
ORG_TAB = D["agregados_org"].set_index("org")


# ============================================================================
# 4. FUNCIONES DE AYUDA
# ============================================================================
def fmt(x, dec=0, suf="%"):
    """Número en formato colombiano: 1.234,5"""
    if pd.isna(x):
        return "—"
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".") + suf


def kpi(col, etiqueta, valor, pill=None, tipo="neutro", nota="", texto=False):
    """Tarjeta de indicador como la del diseño de referencia (texto=True para valores que son palabras)."""
    p = f'<span class="pill {tipo}">{pill}</span>' if pill else ""
    estilo_val = ' style="font-size:1.3rem"' if texto else ""
    col.markdown(f'<div class="kpi"><div class="lbl">{etiqueta}</div>'
                 f'<div class="val"{estilo_val}>{valor}{p}</div><div class="nota">{nota}</div></div>',
                 unsafe_allow_html=True)


def titulo_tarjeta(titulo, sub=""):
    st.markdown(f'<p class="titulo-tarjeta">{titulo}</p><p class="sub-tarjeta">{sub}</p>', unsafe_allow_html=True)


def calculado():
    st.markdown('<span class="etq">🔢 Resultado calculado con las respuestas de la encuesta.</span>',
                unsafe_allow_html=True)


def precaucion(texto):
    st.markdown(f'<div class="aviso">⚠️ <b>Precaución al leer.</b> {texto}</div>', unsafe_allow_html=True)


def estilo(fig, alto=380, leyenda=False):
    fig.update_layout(height=alto, margin=dict(l=8, r=24, t=8, b=36), plot_bgcolor="white",
                      paper_bgcolor="white", font=dict(family=FUENTE, size=13, color=VERDE_OSCURO),
                      hoverlabel=dict(bgcolor="white", font_family=FUENTE), showlegend=leyenda,
                      legend=dict(orientation="h", y=1.1, x=0))
    fig.update_xaxes(showgrid=True, gridcolor="#EEF1ED", zeroline=False, linecolor=BORDE,
                     tickfont=dict(color=GRIS_TEXTO))
    fig.update_yaxes(showgrid=False, linecolor=BORDE, tickfont=dict(color=GRIS_TEXTO))
    return fig


def mostrar(fig):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ============================================================================
# 5. MENÚ LATERAL (un solo filtro gobierna todo el tablero)
# ============================================================================
PAGINAS = ["🏠  Inicio", "📊  Riesgo de burnout", "🔗  Factores asociados",
           "🎯  Dónde intervenir", "👥  Grupos", "📋  Datos y límites"]

with st.sidebar:
    st.markdown('<div class="marca"><div class="logo">OSM</div><div><div class="t1">Observatorio</div>'
                '<div class="t2">Salud mental en el trabajo</div></div></div>', unsafe_allow_html=True)
    orgs = sorted(o for o in ORG_TAB.index if o != TODAS)
    opciones = [TODAS] + orgs
    pedida = st.query_params.get("org", TODAS)
    org = st.selectbox("Tu organización", opciones,
                       index=opciones.index(pedida) if pedida in opciones else 0)
    st.markdown('<div class="seccion">Menú</div>', unsafe_allow_html=True)
    pagina = st.radio("Menú", PAGINAS, label_visibility="collapsed")
    st.markdown('<div class="pie">🔒 Las organizaciones aparecen con un código y los grupos de menos de '
                '10 respuestas no se muestran.</div>', unsafe_allow_html=True)

fila, tot = ORG_TAB.loc[org], ORG_TAB.loc[TODAS]
nombre = "el conjunto" if org == TODAS else org

# Encabezado común a todas las páginas
st.markdown(f"""
<div class="encabezado">
  <div><div class="titulo">{pagina[3:]}</div>
       <div class="sub">¿Dónde intervenir primero para prevenir el burnout? · {org}</div></div>
  <div><span class="chip">📅 {fila.periodo}</span><span class="chip">👤 {fmt(fila.n_bat, 0, '')} respuestas</span></div>
</div>""", unsafe_allow_html=True)


# ============================================================================
# 6. PÁGINAS
# ============================================================================
def pagina_inicio():
    c = st.columns(3)
    bloques = [("¿Quién lo usa?", "El líder de <b>Talento Humano o SST</b> de cada organización que participó "
                "en el levantamiento del Observatorio, al planear su programa de riesgo psicosocial."),
               ("¿Qué pregunta responde?", "<b>¿Qué tan extendido está el riesgo de burnout en mi organización y "
                "qué condiciones del trabajo debo atender primero?</b>"),
               ("¿Qué decisión permite?", "Elegir <b>uno o dos factores</b> para priorizar y <b>en qué grupos</b> "
                "enfocar la acción, en vez de repartir el presupuesto en todo.")]
    for col, (t, d) in zip(c, bloques):
        col.markdown(f'<div class="kpi"><div class="titulo-tarjeta">{t}</div>'
                     f'<div style="margin-top:6px">{d}</div></div>', unsafe_allow_html=True)
    st.write("")
    with st.container(border=True):
        titulo_tarjeta("Cómo usarlo en 4 pasos")
        p = st.columns(4)
        pasos = [("1 · Elige tu organización", "En el menú lateral. Todo el tablero se ajusta."),
                 ("2 · Mira el riesgo", "¿Qué % de personas supera el punto de corte de burnout?"),
                 ("3 · Revisa los factores", "¿Qué condiciones del trabajo van de la mano con más burnout?"),
                 ("4 · Prioriza", "¿Qué factor es frecuente en tu organización y está muy asociado al burnout?")]
        for col, (t, d) in zip(p, pasos):
            col.markdown(f"**{t}**  \n{d}")
    with st.container(border=True):
        titulo_tarjeta("Alcance elegido y por qué")
        st.markdown(
            f"- **15 organizaciones** y **{fmt(tot.n_bat, 0, '')} respuestas** con el BAT-12 completo. "
            "Se muestran con un **código** (A, B, C…), como hace el Observatorio, para no exponer a ninguna empresa.\n"
            "- **Burnout: BAT-12.** Es el indicador central porque tiene **puntos de corte publicados**: permite decir "
            "*cuántas personas* están en riesgo, no solo dar un promedio.\n"
            "- **Factores psicosociales (HSE):** demandas, control, apoyo del líder y de compañeros, claridad y conflicto "
            "de rol, gestión del cambio, más responsabilidad organizacional e interferencia trabajo→familia. Son las "
            "condiciones sobre las que la organización **puede actuar**.\n"
            "- **Intención de retiro**, para mostrar por qué el burnout también le importa al negocio.\n"
            "- Quedan fuera las escalas sin punto de corte ni relación directa con la pregunta "
            "(expectativas laborales, pares de adjetivos, preguntas Sí/No).")


def pagina_riesgo():
    dif = fila.pct_riesgo - tot.pct_riesgo
    rr = D["retiro_riesgo"].set_index("org").loc[org]
    c = st.columns(4)
    if org == TODAS:
        kpi(c[0], "En riesgo de burnout", fmt(fila.pct_riesgo, 1), nota="BAT-12 ≥ 2,54")
    else:
        kpi(c[0], "En riesgo de burnout", fmt(fila.pct_riesgo, 1),
            f"{'↑' if dif > 0 else '↓'} {fmt(abs(dif), 1, ' pp')}", "mal" if dif > 0 else "bien",
            f"BAT-12 ≥ 2,54 · conjunto: {fmt(tot.pct_riesgo, 1)}")
    kpi(c[1], "Burnout severo", fmt(fila.pct_severo, 1), nota="BAT-12 ≥ 2,96")
    kpi(c[2], "Intervalo de confianza 95 %", f"{fmt(fila.ic_bajo)} – {fmt(fila.ic_alto)}",
        nota="Rango probable del % en riesgo")
    if pd.notna(rr.retiro_en_riesgo) and pd.notna(rr.retiro_sin_riesgo):
        kpi(c[3], "Quieren irse (en riesgo)", fmt(rr.retiro_en_riesgo),
            f"×{fmt(rr.retiro_en_riesgo / rr.retiro_sin_riesgo, 1, '')}", "mal",
            f"vs. {fmt(rr.retiro_sin_riesgo)} de quienes no están en riesgo")
    else:
        kpi(c[3], "Quieren irse (en riesgo)", "—", nota=f"Menos de {N_MIN} personas en un grupo")
    st.write("")

    izq, der = st.columns([1.7, 1])
    with izq, st.container(border=True):
        titulo_tarjeta("¿Cómo está tu organización frente a las demás?",
                       "% en riesgo de burnout (punto) e intervalo de confianza 95 % (línea)")
        t = D["agregados_org"][D["agregados_org"].org != TODAS].sort_values("pct_riesgo")
        fig = go.Figure()
        for _, r in t.iterrows():
            sel = r.org == org
            fig.add_trace(go.Scatter(x=[r.ic_bajo, r.ic_alto], y=[r.org] * 2, mode="lines", showlegend=False,
                                     line=dict(color=VERDE_OSCURO if sel else "#DDE3DD", width=3 if sel else 2),
                                     hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=t.pct_riesgo, y=t.org, mode="markers", showlegend=False,
            marker=dict(size=[14 if o == org else 9 for o in t.org],
                        color=[VERDE_OSCURO if o == org else GRIS for o in t.org], line=dict(color="white", width=2)),
            customdata=t[["n_bat", "ic_bajo", "ic_alto", "periodo"]].values,
            hovertemplate="<b>%{y}</b><br>En riesgo: %{x:.1f} %<br>IC 95 %: %{customdata[1]:.1f}–%{customdata[2]:.1f} %"
                          "<br>n = %{customdata[0]}<br>%{customdata[3]}<extra></extra>"))
        fig.add_vline(x=tot.pct_riesgo, line=dict(color=OLIVA, width=1.5))
        fig.add_annotation(x=tot.pct_riesgo, y=1.03, yref="paper", text=f"Conjunto {fmt(tot.pct_riesgo, 1)}",
                           showarrow=False, font=dict(color=OLIVA, size=12), xanchor="left")
        estilo(fig, 470)
        fig.update_xaxes(ticksuffix=" %", rangemode="tozero")
        fig.update_yaxes(tickvals=t.org, ticktext=[f"<b>{o}</b>" if o == org else o for o in t.org])
        mostrar(fig)
        calculado()
        precaucion("Si las líneas de dos organizaciones se cruzan, <b>no se puede decir que una esté peor</b>. "
                   "Además se midieron en <b>momentos distintos (2024–2026)</b> y respondió quien quiso.")

    with der:
        with st.container(border=True):
            titulo_tarjeta("¿Por qué importa?", "% con intención de retiro")
            if pd.notna(rr.retiro_en_riesgo) and pd.notna(rr.retiro_sin_riesgo):
                fig = go.Figure(go.Bar(
                    x=[rr.retiro_sin_riesgo, rr.retiro_en_riesgo], y=["Sin riesgo", "En riesgo"], orientation="h",
                    marker=dict(color=[GRIS, MALVA], cornerradius=6),
                    text=[fmt(rr.retiro_sin_riesgo), fmt(rr.retiro_en_riesgo)], textposition="outside",
                    customdata=[int(rr.n_sin_riesgo), int(rr.n_en_riesgo)],
                    hovertemplate="%{y}: %{x:.1f} %<br>n = %{customdata}<extra></extra>"))
                estilo(fig, 170)
                fig.update_xaxes(visible=False, range=[0, rr.retiro_en_riesgo * 1.35])
                mostrar(fig)
            else:
                st.info(f"Menos de {N_MIN} personas en un grupo: no se muestra.")
        with st.container(border=True):
            titulo_tarjeta("¿Qué síntoma pesa más?", "Promedio de 1 (nunca) a 5 (siempre)")
            subs = ["Agotamiento", "Distanciamiento mental", "Deterioro cognitivo", "Deterioro emocional"]
            fig = go.Figure()
            fig.add_trace(go.Bar(y=subs, x=[tot["media_" + s] for s in subs], orientation="h", name="Conjunto",
                                 marker=dict(color=GRIS, cornerradius=5)))
            if org != TODAS:
                fig.add_trace(go.Bar(y=subs, x=[fila["media_" + s] for s in subs], orientation="h", name=org,
                                     marker=dict(color=VERDE_OSCURO, cornerradius=5)))
            estilo(fig, 250, leyenda=org != TODAS)
            fig.update_layout(barmode="group", bargap=0.3, legend=dict(y=-0.25))
            fig.update_xaxes(range=[1, 5])
            fig.update_yaxes(autorange="reversed")
            mostrar(fig)
            st.markdown('<span class="etq">El <b>agotamiento</b> es el síntoma más alto en todas las organizaciones.</span>',
                        unsafe_allow_html=True)


def pagina_factores():
    aso = D["asociacion"].sort_values("diferencia_pp")
    clar = aso.set_index("factor").loc["Claridad del rol"]
    with st.container(border=True):
        titulo_tarjeta("Con demandas altas, interferencia trabajo→familia o conflicto de rol, "
                       "el riesgo de burnout es unas tres veces mayor",
                       "% en riesgo de burnout según el factor esté en condición favorable o desfavorable · 15 organizaciones")
        fig = go.Figure()
        for _, r in aso.iterrows():
            fig.add_trace(go.Scatter(x=[r.riesgo_favorable, r.riesgo_desfavorable], y=[r.factor] * 2, mode="lines",
                                     showlegend=False, line=dict(color="#DDE3DD", width=4), hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=aso.riesgo_favorable, y=aso.factor, mode="markers", name="Condición favorable",
                                 marker=dict(size=13, color=SALVIA, line=dict(color="white", width=2)),
                                 customdata=aso[["n_favorable"]].values,
                                 hovertemplate="<b>%{y}</b> · favorable<br>%{x:.1f} % en riesgo<br>n = %{customdata[0]}<extra></extra>"))
        fig.add_trace(go.Scatter(x=aso.riesgo_desfavorable, y=aso.factor, mode="markers+text",
                                 name="Condición desfavorable",
                                 marker=dict(size=13, color=OXIDO, line=dict(color="white", width=2)),
                                 text=[f"  ×{fmt(v, 1, '')}" for v in aso.razon], textposition="middle right",
                                 textfont=dict(color=VERDE_OSCURO, size=12), customdata=aso[["n_desfavorable"]].values,
                                 hovertemplate="<b>%{y}</b> · desfavorable<br>%{x:.1f} % en riesgo<br>n = %{customdata[0]}<extra></extra>"))
        estilo(fig, 470, leyenda=True)
        fig.update_layout(margin=dict(t=40))
        fig.update_xaxes(ticksuffix=" %", range=[0, 58], title="% de personas en riesgo de burnout")
        mostrar(fig)
        st.markdown('<span class="etq">“×3,7” = riesgo en condición desfavorable ÷ riesgo en condición favorable.</span>',
                    unsafe_allow_html=True)
        calculado()
        precaucion("Es una <b>asociación, no una causa</b>: la encuesta se aplicó una sola vez. "
                   f"En <b>claridad del rol</b> solo {int(clar.n_desfavorable)} personas están en condición desfavorable, "
                   "así que ese resultado es menos estable.")
    with st.expander("¿Qué es “condición desfavorable”?"):
        st.markdown("Cada factor se convierte en un índice de **0 a 100** (100 = lo más favorable; en demandas, conflicto "
                    "de rol e interferencia trabajo→familia la escala se invierte). La persona está en **condición "
                    "desfavorable** si su índice queda **por debajo de 50**, del lado negativo del punto medio.")
    with st.expander("Ver tabla"):
        st.dataframe(aso.sort_values("diferencia_pp", ascending=False).round(1), hide_index=True)


def pagina_prioridades():
    fac = D["factores_org"]
    f_org = fac[fac.org == org].set_index("factor")
    f_tot = fac[fac.org == TODAS].set_index("factor")
    m = D["asociacion"].set_index("factor")[["diferencia_pp"]].join(f_org[["pct_desfavorable", "n"]])
    m["impacto"] = m.pct_desfavorable / 100 * m.diferencia_pp       # frecuencia × asociación
    m = m.sort_values("impacto", ascending=False)
    top = m.index[:2].tolist()
    m["prioridad"] = m.index.isin(top)

    c = st.columns(3)
    kpi(c[0], "Prioridad 1", top[0], nota=f"{fmt(m.loc[top[0], 'pct_desfavorable'])} en condición desfavorable", texto=True)
    kpi(c[1], "Prioridad 2", top[1], nota=f"{fmt(m.loc[top[1], 'pct_desfavorable'])} en condición desfavorable", texto=True)
    mejor = f_org.pct_desfavorable.idxmin()
    kpi(c[2], "Fortaleza", mejor, nota=f"solo {fmt(f_org.loc[mejor, 'pct_desfavorable'])} en condición desfavorable", texto=True)
    st.write("")

    izq, der = st.columns([1, 1.15])
    with izq, st.container(border=True):
        titulo_tarjeta("Impacto potencial de cada factor", "Personas en riesgo que acompañan al factor, por cada 100")
        mi = m.sort_values("impacto")
        fig = go.Figure(go.Bar(
            y=mi.index, x=mi.impacto, orientation="h",
            marker=dict(color=[OXIDO if p else SALVIA for p in mi.prioridad], cornerradius=6),
            text=[fmt(v, 1, "") for v in mi.impacto], textposition="outside",
            customdata=mi[["pct_desfavorable", "diferencia_pp"]].values,
            hovertemplate="<b>%{y}</b><br>%{customdata[0]:.1f} % desfavorable × %{customdata[1]:.1f} puntos"
                          "<extra></extra>"))
        estilo(fig, 420)
        fig.update_xaxes(range=[0, mi.impacto.max() * 1.25])
        mostrar(fig)
    with der, st.container(border=True):
        titulo_tarjeta("¿De dónde sale?", "Frecuencia en tu organización × asociación con el burnout")
        fig = go.Figure(go.Scatter(
            x=m.pct_desfavorable, y=m.diferencia_pp, mode="markers+text", text=m.index,
            textposition=["top right" if x < 12 else "top left" if x > 40 else "top center" for x in m.pct_desfavorable],
            textfont=dict(size=11, color=VERDE_OSCURO),
            marker=dict(size=14, color=[OXIDO if p else SALVIA for p in m.prioridad], line=dict(color="white", width=2)),
            hovertemplate="<b>%{text}</b><br>%{x:.1f} % desfavorable<br>%{y:.1f} puntos más de riesgo<extra></extra>"))
        estilo(fig, 420)
        fig.update_xaxes(title=f"% de {nombre} en condición desfavorable", ticksuffix=" %",
                         range=[-3, max(60, m.pct_desfavorable.max() * 1.15)])
        fig.update_yaxes(title="Diferencia de riesgo (puntos)", range=[0, m.diferencia_pp.max() * 1.2],
                         showgrid=True, gridcolor="#EEF1ED")
        mostrar(fig)
    calculado()
    precaucion("El impacto potencial sirve para <b>ordenar</b> prioridades, no promete cuánto bajará el burnout. "
               "La diferencia de riesgo se toma del <b>conjunto</b> porque en una sola organización los grupos son pequeños.")
    st.write("")

    with st.container(border=True):
        titulo_tarjeta("Perfil de los factores", f"% en condición desfavorable · {nombre} frente al conjunto")
        p = f_tot[["pct_desfavorable"]].rename(columns={"pct_desfavorable": "tot"}).join(
            f_org[["pct_desfavorable"]].rename(columns={"pct_desfavorable": "org"})).sort_values("tot")
        fig = go.Figure()
        for fct, r in p.iterrows():
            fig.add_trace(go.Scatter(x=[r.tot, r.org], y=[fct] * 2, mode="lines", showlegend=False,
                                     line=dict(color="#DDE3DD", width=4), hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=p.tot, y=p.index, mode="markers", name="Conjunto",
                                 marker=dict(size=11, color=GRIS, line=dict(color="white", width=2))))
        if org != TODAS:
            fig.add_trace(go.Scatter(x=p.org, y=p.index, mode="markers", name=org,
                                     marker=dict(size=13, color=VERDE_OSCURO, line=dict(color="white", width=2))))
        estilo(fig, 390, leyenda=True)
        fig.update_layout(margin=dict(t=40))
        fig.update_xaxes(ticksuffix=" %", rangemode="tozero")
        mostrar(fig)

    with st.container(border=True):
        titulo_tarjeta("¿Qué hay detrás de cada factor?")
        factor = st.selectbox("Factor", list(m.index), index=0, key=f"factor_{org}")
        it = D["items_org"]
        i_org = it[(it.org == org) & (it.factor == factor)].set_index("enunciado")
        i_tot = it[(it.org == TODAS) & (it.factor == factor)].set_index("enunciado")
        regla = ("responde a menudo, frecuentemente o siempre" if factor in ("Demandas", "Conflicto de rol") else
                 "está algo, muy o totalmente de acuerdo" if factor == "Interferencia trabajo→familia" else
                 "responde nunca o rara vez")
        st.markdown(f'<p class="sub-tarjeta">% de personas que {regla} (respuesta desfavorable)</p>',
                    unsafe_allow_html=True)
        orden = i_tot.sort_values("pct_desfavorable").index
        fig = go.Figure()
        fig.add_trace(go.Bar(y=orden, x=i_tot.loc[orden, "pct_desfavorable"], orientation="h", name="Conjunto",
                             marker=dict(color=GRIS, cornerradius=5)))
        if org != TODAS:
            fig.add_trace(go.Bar(y=orden, x=i_org.reindex(orden)["pct_desfavorable"], orientation="h", name=org,
                                 marker=dict(color=VERDE_OSCURO, cornerradius=5),
                                 text=[fmt(v) for v in i_org.reindex(orden)["pct_desfavorable"]], textposition="outside"))
        estilo(fig, 110 + 60 * len(orden), leyenda=True)
        fig.update_layout(barmode="group", bargap=0.3, margin=dict(t=40))
        fig.update_xaxes(ticksuffix=" %", rangemode="tozero")
        mostrar(fig)

    ACCIONES = {
        "Demandas": ["Revisar cargas y plazos con cada líder en las semanas de más presión.",
                     "Acordar reglas de horario: sin correos ni reuniones fuera de jornada."],
        "Interferencia trabajo→familia": ["Piloto de horario flexible o bloques protegidos para responsabilidades familiares.",
                                          "Avisar con anticipación los cambios de turno o de planes."],
        "Conflicto de rol": ["Definir un solo canal de priorización cuando dos jefes piden cosas distintas."],
        "Apoyo del líder": ["Formación de líderes en seguimiento y reconocimiento; espacios 1:1 periódicos."],
        "Gestión del cambio": ["Consultar a los equipos antes de los cambios y explicar cómo funcionarán."],
        "Responsabilidad organizacional": ["Comunicar qué se hizo con los resultados de esta medición.",
                                           "Hacer visibles y fáciles de usar los recursos de salud mental."],
        "Control": ["Dar margen de decisión sobre el orden y el ritmo de las tareas."],
        "Apoyo de compañeros": ["Fortalecer rutinas de trabajo en equipo y apoyo entre pares."],
        "Claridad del rol": ["Actualizar descripciones de cargo y objetivos con cada persona."],
    }
    lista = "".join(f"<li>{a}</li>" for a in ACCIONES[factor])
    st.markdown(f'<div class="ilustrativo">✏️ <b>Ejemplo ilustrativo, no sale de los datos.</b> Acciones que '
                f'Talento Humano podría discutir para <b>{factor.lower()}</b>:<ul style="margin:6px 0 0 0">{lista}</ul></div>',
                unsafe_allow_html=True)


def pagina_grupos():
    nombres = {"cargo": "Tipo de cargo", "modalidad": "Modalidad", "edad": "Edad", "sexo": "Sexo"}
    var = st.radio("Ver por", list(nombres), format_func=nombres.get, horizontal=True)
    g = D["agregados_grupo"]
    g = g[(g.org == org) & (g.variable == var)].copy()
    if var == "edad":
        g["grupo"] = pd.Categorical(g.grupo, ["18-29", "30-39", "40-49", "50 o más"], ordered=True)
        g = g.sort_values("grupo")
    else:
        g = g.sort_values("pct_riesgo", na_position="first")
    vis = g[~g.suprimido]
    with st.container(border=True):
        if len(vis):
            mx = vis.loc[vis.pct_riesgo.idxmax()]
            titulo_tarjeta(f"En {nombre}, el grupo con más riesgo por {nombres[var].lower()} es {mx.grupo} "
                           f"({fmt(mx.pct_riesgo)})", "% en riesgo de burnout e intervalo de confianza 95 %")
        fig = go.Figure()
        for _, r in vis.iterrows():
            fig.add_trace(go.Scatter(x=[r.ic_bajo, r.ic_alto], y=[str(r.grupo)] * 2, mode="lines", showlegend=False,
                                     line=dict(color="#DDE3DD", width=4), hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=vis.pct_riesgo, y=vis.grupo.astype(str), mode="markers+text", showlegend=False,
                                 text=[fmt(v) for v in vis.pct_riesgo], textposition="top center",
                                 marker=dict(size=14, color=VERDE_OSCURO, line=dict(color="white", width=2)),
                                 customdata=vis[["n_bat"]].values,
                                 hovertemplate="<b>%{y}</b><br>%{x:.1f} % en riesgo<br>n = %{customdata[0]}<extra></extra>"))
        fig.add_vline(x=fila.pct_riesgo, line=dict(color=OLIVA, width=1.5))
        fig.add_annotation(x=fila.pct_riesgo, y=1.06, yref="paper", text=f"Promedio de {nombre}",
                           showarrow=False, font=dict(color=OLIVA, size=12), xanchor="left")
        estilo(fig, 130 + 70 * max(len(vis), 1))
        fig.update_layout(margin=dict(t=30))
        fig.update_xaxes(ticksuffix=" %", rangemode="tozero")
        mostrar(fig)
        calculado()
        ocultos = g[g.suprimido].grupo.astype(str).tolist()
        if ocultos:
            st.markdown(f'<div class="pie" style="margin-top:8px">🔒 <b>No se muestran:</b> {", ".join(ocultos)}. '
                        f'Tienen menos de {N_MIN} respuestas, o su dato podría deducirse por resta.</div>',
                        unsafe_allow_html=True)
        precaucion("Los grupos pequeños tienen intervalos amplios: úsalo para <b>decidir dónde preguntar más</b> "
                   "(grupos focales, conversación con líderes), no para sacar conclusiones sobre personas.")


def pagina_datos():
    log = D["registro_limpieza"]
    paso = log.groupby("paso")["n"].sum()
    v = D["verificaciones"].set_index("verificacion")["resultado"]
    c = st.columns(4)
    kpi(c[0], "Registros en los 16 archivos", fmt(paso.get("0. Registros en el archivo"), 0, ""))
    kpi(c[1], "No autorizaron el uso", fmt(-paso.get("1. Excluidos: no autorizaron el uso", 0), 0, ""), nota="Excluidos")
    kpi(c[2], "Duplicados", fmt(-paso.get("2. Excluidos: registro duplicado", 0), 0, ""), nota="Excluidos")
    kpi(c[3], "Con BAT-12 completo", fmt(paso.get("5. Con BAT-12 completo (≥10 de 12 ítems)"), 0, ""),
        nota="Base de los indicadores")
    st.write("")
    izq, der = st.columns(2)
    with izq, st.container(border=True):
        titulo_tarjeta("Revisiones realizadas")
        st.markdown(f"""
- **Consentimiento:** se excluyó a quien marcó *“No, autorizo”*.
- **Duplicados:** mismo perfil y **todas** las respuestas idénticas dentro de una organización.
- **{v.get('Dos archivos: organización')} llegó en 2 archivos** ({v.get('Dos archivos: registros por archivo (antes de limpiar)')}): coincidencias por hora de inicio: **{v.get('Dos archivos: registros con la misma hora de inicio en ambos archivos')}**; por perfil y respuestas: **{v.get('Dos archivos: registros con perfil y respuestas idénticos en ambos archivos')}**. Se unieron.
- **Escalas equivalentes:** las 16 bases usan las mismas opciones. {v.get('Organizaciones con ítems faltantes')} no tiene 2 ítems y redacta un ítem del BAT-12 distinto.
- **Orden de la escala HSE (7 opciones):** se probó el orden alterno y **el orden de los factores no cambia**.
- **Faltantes:** BAT-12 con ≥ 10 de 12 ítems; cada factor con ≥ 50 % de sus ítems.
- **Anonimato:** organizaciones con código; sin nombres, correos, documentos, ciudad, dependencia ni textos abiertos. Grupos de menos de {N_MIN} ocultos.
""")
    with der, st.container(border=True):
        titulo_tarjeta("Cómo se calcula cada indicador")
        st.markdown("""
| Indicador | Cálculo |
|---|---|
| **% en riesgo** | Promedio de los 12 ítems del BAT-12 (1–5). Riesgo ≥ 2,54; severo ≥ 2,96 (Schaufeli et al., 2023) |
| **IC 95 %** | Método de Wilson |
| **Índice del factor** | Promedio de sus ítems (1–7) llevado a 0–100; 100 = más favorable |
| **% desfavorable** | % de personas con índice < 50 |
| **Diferencia de riesgo** | % en riesgo (desfavorable) − % en riesgo (favorable), en el conjunto |
| **Impacto potencial** | % desfavorable × diferencia de riesgo ÷ 100 |
| **Intención de retiro** | Promedio de 4 ítems (1–6); ≥ 4 = de acuerdo con irse |
""")
    with st.expander("Ver prueba de sensibilidad del orden de la escala"):
        st.dataframe(D["sensibilidad"].round(1), hide_index=True)
    with st.container(border=True):
        titulo_tarjeta("Qué permiten concluir los datos y qué no")
        a, b = st.columns(2)
        a.markdown(f'<div class="kpi" style="border-left:4px solid {SALVIA}"><b>Sí permiten</b><ul>'
                   '<li>Estimar qué parte de quienes respondieron supera el punto de corte de riesgo.</li>'
                   '<li>Ver qué condiciones del trabajo <b>van de la mano</b> con más burnout.</li>'
                   '<li>Ordenar prioridades de intervención en cada organización.</li></ul></div>',
                   unsafe_allow_html=True)
        b.markdown(f'<div class="kpi" style="border-left:4px solid {OXIDO}"><b>No permiten</b><ul>'
                   '<li>Afirmar que un factor <b>causa</b> el burnout (medición única).</li>'
                   '<li>Generalizar a toda la planta: la participación fue voluntaria.</li>'
                   '<li>Hacer un ranking estricto: años y tamaños distintos (de 78 a 2.100).</li>'
                   '<li>Diagnosticar: el BAT-12 es un tamizaje y su corte se validó en Europa.</li></ul></div>',
                   unsafe_allow_html=True)
    st.caption("Referencias: Schaufeli, De Witte, Hakanen, Kaltiainen y Kok (2023), *Scand J Work Environ Health*, "
               "49(4), 293–302, https://doi.org/10.5271/sjweh.4093 · Hadžibajramović, Schaufeli y De Witte (2022), "
               "*BMC Public Health*, 22, https://doi.org/10.1186/s12889-022-12946-y · HSE Management Standards "
               "Indicator Tool. Datos: Observatorio de Salud Mental, Universidad de La Sabana.")


# ============================================================================
# 7. MOSTRAR LA PÁGINA ELEGIDA EN EL MENÚ
# ============================================================================
{PAGINAS[0]: pagina_inicio, PAGINAS[1]: pagina_riesgo, PAGINAS[2]: pagina_factores,
 PAGINAS[3]: pagina_prioridades, PAGINAS[4]: pagina_grupos, PAGINAS[5]: pagina_datos}[pagina]()
