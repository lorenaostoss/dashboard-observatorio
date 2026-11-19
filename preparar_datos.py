"""
preparar_datos.py
=================
Convierte las bases originales del Observatorio de Salud Mental (Excel, una por
organización) en TABLAS AGREGADAS y anónimas que usa el dashboard.

Las bases originales NO se suben al repositorio (ver .gitignore): contienen
correos, nombres, números de identificación y campos de texto libre.

Uso:
    python preparar_datos.py --entrada ruta/a/carpeta_con_excels

Salida (carpeta data/):
    agregados_org.csv        indicadores por organización
    agregados_grupo.csv      indicadores por organización x grupo (solo n >= N_MIN)
    factores_org.csv         índice de cada factor psicosocial por organización
    asociacion.csv           % riesgo de burnout según condición del factor (conjunto)
    asociacion_org.csv       lo mismo dentro de cada organización (solo celdas n >= N_MIN)
    items_org.csv            % por ítem (para el detalle de cada factor)
    sensibilidad.csv         prueba de robustez del orden de la escala
    registro_limpieza.csv    cuántos registros entran y salen en cada paso
    revision_escalas.csv     etiquetas de respuesta encontradas por escala y archivo
"""
import argparse
import glob
import os
import re
import sys
import unicodedata

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from items import ITEMS  # noqa: E402

N_MIN = 10          # tamaño mínimo de grupo para publicar un resultado
CORTE_RIESGO = 2.54  # BAT-12: riesgo de burnout (Schaufeli et al., 2023)
CORTE_SEVERO = 2.96  # BAT-12: burnout severo

# --------------------------------------------------------------------------
# Escalas de respuesta (etiqueta normalizada -> puntaje)
# --------------------------------------------------------------------------
# HSE: 7 opciones de frecuencia. El orden entre "alguna vez"/"algunas veces" y
# "a menudo"/"frecuentemente" no es evidente; se asume el de abajo y se prueba
# el orden alterno en sensibilidad.csv.
ESC_HSE = {'nunca': 1, 'rara vez': 2, 'alguna vez': 3, 'algunas veces': 4,
           'a menudo': 5, 'frecuentemente': 6, 'siempre': 7}
ESC_HSE_ALT = {'nunca': 1, 'rara vez': 2, 'algunas veces': 3, 'alguna vez': 4,
               'frecuentemente': 5, 'a menudo': 6, 'siempre': 7}
ESC_BAT = {'nunca': 1, 'raramente': 2, 'alguna veces': 3, 'algunas veces': 3,
           'a menudo': 4, 'siempre': 5}
ESC_ACUERDO6 = {'muy en desacuerdo': 1, 'moderadamente en desacuerdo': 2,
                'ligeramente en desacuerdo': 3, 'ligeramente de acuerdo': 4,
                'moderadamente de acuerdo': 5, 'muy de acuerdo': 6}
# Conflicto trabajo-familia: 7 opciones; la posición 2 aparece como
# "muy" o "moderadamente en desacuerdo" según el bloque (nunca ambas a la vez).
ESC_ACUERDO7 = {'totalmente en desacuerdo': 1, 'muy en desacuerdo': 2,
                'moderadamente en desacuerdo': 2, 'algo en desacuerdo': 3,
                'ni de acuerdo ni en desacuerdo': 4, 'algo de acuerdo': 5,
                'muy de acuerdo': 6, 'totalmente de acuerdo': 7}


def familia(item_id):
    if item_id.startswith('bat'):
        return 'bat'
    if item_id[:3] in ('eng', 'sat', 'ret'):
        return 'acuerdo6'
    if item_id.startswith('tf'):
        return 'acuerdo7'
    return 'hse'


ESCALA = {'hse': ESC_HSE, 'bat': ESC_BAT, 'acuerdo6': ESC_ACUERDO6, 'acuerdo7': ESC_ACUERDO7}

# --------------------------------------------------------------------------
# Factores psicosociales (dirección: +1 = más es mejor, -1 = más es peor)
# --------------------------------------------------------------------------
FACTORES = {
    'Demandas':                       (['dem1', 'dem2', 'dem3', 'dem4'], -1, 7),
    'Control':                        (['ctrl1', 'ctrl2', 'ctrl3'], +1, 7),
    'Apoyo del líder':                ([f'lid{i}' for i in range(1, 8)], +1, 7),
    'Apoyo de compañeros':            (['gru1', 'gru2', 'gru3'], +1, 7),
    'Claridad del rol':               (['rol1', 'rol2', 'rol3', 'rol4'], +1, 7),
    'Conflicto de rol':               (['con1', 'con2', 'con3'], -1, 7),
    'Gestión del cambio':             (['cam1', 'cam2', 'cam3', 'cam4'], +1, 7),
    'Responsabilidad organizacional': ([f'res{i}' for i in range(1, 6)], +1, 7),
    'Interferencia trabajo→familia':  ([f'tf{i}' for i in range(1, 6)], -1, 7),
}
BAT_SUB = {
    'Agotamiento': ['bat_ag1', 'bat_ag2', 'bat_ag3'],
    'Distanciamiento mental': ['bat_dm1', 'bat_dm2', 'bat_dm3'],
    'Deterioro cognitivo': ['bat_dc1', 'bat_dc2', 'bat_dc3'],
    'Deterioro emocional': ['bat_de1', 'bat_de2', 'bat_de3'],
}

def norm(s):
    s = unicodedata.normalize('NFKD', str(s))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', s.replace('\xa0', ' ')).lower().strip()


def nombre_org(ruta):
    """Identificador de la organización tomado del nombre del archivo: se quita el
    título común de la encuesta, los números de versión y la puntuación. Así los dos
    archivos de una misma organización (p. ej. "...Trabajo1-56 (2)" y "...Trabajo (1)")
    quedan con el mismo identificador y se unen."""
    base = os.path.splitext(os.path.basename(ruta))[0]
    s = unicodedata.normalize('NFKD', base)
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    s = s.replace('indicadores de bienestar y salud mental en el mundo del trabajo', ' ')
    tokens = s.split()
    while tokens and tokens[-1].isdigit():
        tokens.pop()
    if tokens:
        tokens[-1] = re.sub(r'\d+$', '', tokens[-1])
    return ' '.join(t for t in tokens if t).upper() or base


def buscar_col(encabezados, patron):
    hits = [i for i, h in enumerate(encabezados) if re.search(patron, h)]
    return hits[0] if hits else None


def grupo_cargo(v):
    v = norm(v)
    if v in ('nan', ''):
        return np.nan
    if v.startswith(('directiv', 'estrateg')):
        return 'Directivo / estratégico'
    if v.startswith(('administrativ', 'profesional', 'tactic')):
        return 'Administrativo / profesional'
    if v.startswith(('docente', 'instructor')):
        return 'Docente / instructor'
    if v.startswith(('operativ', 'operarativ', 'asistencial', 'tecnico')):
        return 'Operativo / asistencial'
    return np.nan


def grupo_modalidad(v):
    v = norm(v)
    if v == 'presencial':
        return 'Presencial'
    if v == 'hibrido':
        return 'Híbrido'
    if v in ('remoto', 'teletrabajo', 'virtual', 'trabajo en casa'):
        return 'Remoto'
    return np.nan


def grupo_edad(v):
    try:
        e = float(str(v).strip())
    except ValueError:
        return np.nan
    if e < 18 or e > 80:
        return np.nan
    if e < 30:
        return '18-29'
    if e < 40:
        return '30-39'
    if e < 50:
        return '40-49'
    return '50 o más'


def grupo_sexo(v):
    v = norm(v)
    return {'mujer': 'Mujer', 'hombre': 'Hombre'}.get(v, np.nan)


# --------------------------------------------------------------------------
# 1. Lectura y estandarización
# --------------------------------------------------------------------------
def leer_archivo(ruta, log, revision):
    crudo = pd.read_excel(ruta, header=None, sheet_name=0)
    enc = [norm(x) for x in crudo.iloc[1]]   # fila 2 = enunciado real
    datos = crudo.iloc[2:].reset_index(drop=True)
    org = nombre_org(ruta)
    archivo = os.path.basename(ruta)
    out = pd.DataFrame({'org': org, 'archivo': archivo}, index=datos.index)

    # Perfil (solo variables agregables; nada de nombre, correo, ID, texto libre)
    def col(p):
        i = buscar_col(enc, p)
        return datos.iloc[:, i] if i is not None else pd.Series(np.nan, index=datos.index)

    out['consentimiento'] = col(r'^column$').map(norm)
    out['inicio'] = pd.to_datetime(col(r'^hora de inicio$'), errors='coerce')
    out['fin'] = pd.to_datetime(col(r'^hora de finalizacion$'), errors='coerce')
    out['sexo'] = col(r'^sexo$').map(grupo_sexo)
    out['edad'] = col(r'^edad$').map(grupo_edad)
    out['modalidad'] = col(r'modalidad de trabajo').map(grupo_modalidad)
    out['cargo'] = col(r'^(tipo de cargo|cargo)$').map(grupo_cargo)
    # Variables de perfil adicionales que solo sirven para detectar duplicados
    perfil_extra = [col(p).astype(str).map(norm) for p in
                    (r'^estado civil$', r'^numero de hijos$', r'^nivel educativo$',
                     r'estrato', r'ingreso salarial', r'^edad$')]
    out['_perfil'] = pd.concat(perfil_extra, axis=1).apply(lambda r: '|'.join(map(str, r.tolist())), axis=1)

    for k, (_, kw) in ITEMS.items():
        i = buscar_col(enc, norm(kw))
        fam = familia(k)
        if i is None:
            out[k] = np.nan
            revision.append({'archivo': archivo, 'org': org, 'item': k, 'estado': 'no está en la base'})
            continue
        etiquetas = datos.iloc[:, i].map(lambda v: norm(v) if pd.notna(v) else np.nan)
        out[k + '_txt'] = etiquetas
        out[k] = etiquetas.map(ESCALA[fam])
        raras = set(etiquetas.dropna()) - set(ESCALA[fam])
        if raras:
            revision.append({'archivo': archivo, 'org': org, 'item': k,
                             'estado': 'etiquetas no reconocidas: ' + ', '.join(sorted(raras))})
    log.append({'archivo': archivo, 'org': org, 'paso': '0. Registros en el archivo', 'n': len(out)})
    return out


def puntaje(df, items, min_frac=0.5):
    """Media de los ítems respondidos si se respondió al menos min_frac de ellos."""
    disp = [i for i in items if i in df and df[i].notna().any()]
    if not disp:
        return pd.Series(np.nan, index=df.index)
    m = df[disp]
    ok = m.notna().sum(axis=1) >= max(1, int(np.ceil(min_frac * len(disp))))
    return m.mean(axis=1).where(ok)


def a_indice(media, direccion, puntos):
    """Escala 1..puntos -> 0..100 donde 100 = condición más favorable."""
    x = (media - 1) / (puntos - 1) * 100
    return x if direccion > 0 else 100 - x


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z ** 2 / n
    centro = (p + z ** 2 / (2 * n)) / den
    margen = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return (max(0, centro - margen) * 100, min(1, centro + margen) * 100)


def calcular_personas(df, escala_hse=None):
    """Índices por persona. escala_hse permite recalcular con el orden alterno."""
    d = df.copy()
    if escala_hse is not None:
        for k in ITEMS:
            if familia(k) == 'hse' and k + '_txt' in d:
                d[k] = d[k + '_txt'].map(escala_hse)
    bat_items = [i for sub in BAT_SUB.values() for i in sub]
    d['bat'] = puntaje(d, bat_items, min_frac=10 / 12)
    for sub, its in BAT_SUB.items():
        d['bat_' + sub] = puntaje(d, its, min_frac=2 / 3)
    d['riesgo'] = np.where(d['bat'].notna(), d['bat'] >= CORTE_RIESGO, np.nan)
    d['severo'] = np.where(d['bat'].notna(), d['bat'] >= CORTE_SEVERO, np.nan)
    for f, (its, direc, pts) in FACTORES.items():
        media = puntaje(d, its)
        d['idx_' + f] = a_indice(media, direc, pts)
        d['desf_' + f] = np.where(media.notna(), d['idx_' + f] < 50, np.nan)
    # Intención de retiro (ret1 en sentido inverso)
    ret = d[['ret2', 'ret3', 'ret4']].copy()
    ret['ret1_inv'] = 7 - d['ret1']
    media_ret = ret.mean(axis=1).where(ret.notna().sum(axis=1) >= 2)
    d['retiro'] = np.where(media_ret.notna(), media_ret >= 4, np.nan)
    return d


def resumen(g):
    """Indicadores de un grupo de personas."""
    b = g.dropna(subset=['bat'])
    n = len(b)
    k = int(b['riesgo'].sum())
    ks = int(b['severo'].sum())
    lo, hi = wilson(k, n)
    r = g.dropna(subset=['retiro'])
    return pd.Series({
        'n_bat': n,
        'pct_riesgo': k / n * 100 if n else np.nan,
        'ic_bajo': lo, 'ic_alto': hi,
        'pct_severo': ks / n * 100 if n else np.nan,
        'bat_media': b['bat'].mean() if n else np.nan,
        'n_retiro': len(r),
        'pct_retiro': r['retiro'].mean() * 100 if len(r) else np.nan,
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--entrada', default='datos_originales',
                    help='carpeta con los Excel originales (no se sube a GitHub)')
    ap.add_argument('--salida', default='data')
    a = ap.parse_args()
    os.makedirs(a.salida, exist_ok=True)

    archivos = sorted(glob.glob(os.path.join(a.entrada, '*.xlsx')))
    if not archivos:
        sys.exit(f'No encontré archivos .xlsx en {a.entrada}')
    log, revision = [], []
    partes = [leer_archivo(f, log, revision) for f in archivos]
    df = pd.concat(partes, ignore_index=True)
    item_cols = list(ITEMS)

    # 1b. Anonimizar organizaciones: cada una recibe un código ("Organización A", "B"...).
    #     El orden se baraja con una semilla fija para que el código no siga el orden alfabético.
    #     La clave código -> nombre se guarda SOLO en la carpeta de entrada (no se sube a GitHub).
    nombres = sorted(df['org'].unique())
    orden = np.random.default_rng(2026).permutation(len(nombres))
    clave = {nombres[i]: f'Organización {chr(65 + k)}' for k, i in enumerate(orden)}
    pd.Series(clave, name='codigo').rename_axis('organizacion').to_csv(
        os.path.join(a.entrada, 'clave_organizaciones.csv'))
    df['org'] = df['org'].map(clave)
    for r in log + revision:
        r['org'] = clave.get(r['org'], r['org'])
    for p in partes:
        p['org'] = p['org'].map(clave)

    # 2. Consentimiento
    no_aut = df['consentimiento'].str.startswith('no', na=False)
    for (arch, org), g in df[no_aut].groupby(['archivo', 'org']):
        log.append({'archivo': arch, 'org': org, 'paso': '1. Excluidos: no autorizaron el uso', 'n': -len(g)})
    df = df[~no_aut]

    # 3. Duplicados exactos (mismo perfil + mismas respuestas en todos los ítems)
    clave = df[['org', '_perfil'] + [c + '_txt' for c in item_cols if c + '_txt' in df]].apply(lambda r: '|'.join(map(str, r.tolist())), axis=1)
    dup = clave.duplicated(keep='first')
    for (arch, org), g in df[dup].groupby(['archivo', 'org']):
        log.append({'archivo': arch, 'org': org, 'paso': '2. Excluidos: registro duplicado', 'n': -len(g)})
    df = df[~dup]

    # 4. Sin respuestas útiles (BAT-12 y factores vacíos)
    vacios = df[item_cols].notna().sum(axis=1) < 10
    for (arch, org), g in df[vacios].groupby(['archivo', 'org']):
        log.append({'archivo': arch, 'org': org, 'paso': '3. Excluidos: encuesta casi vacía (<10 ítems)', 'n': -len(g)})
    df = df[~vacios].reset_index(drop=True)

    per = calcular_personas(df)
    for (arch, org), g in per.groupby(['archivo', 'org']):
        log.append({'archivo': arch, 'org': org, 'paso': '4. Registros analizados', 'n': len(g)})
        log.append({'archivo': arch, 'org': org, 'paso': '5. Con BAT-12 completo (≥10 de 12 ítems)', 'n': int(g['bat'].notna().sum())})

    # Periodo de recolección (solo mes/año, agregado por organización)
    periodo = per.groupby('org').agg(desde=('inicio', 'min'), hasta=('inicio', 'max'))
    periodo['periodo'] = periodo['desde'].dt.strftime('%m/%Y') + ' – ' + periodo['hasta'].dt.strftime('%m/%Y')

    # --- Agregados por organización ---
    org_tab = per.groupby('org').apply(resumen, include_groups=False).reset_index()
    total = resumen(per).to_dict()
    total['org'] = 'Todas las organizaciones'
    org_tab = pd.concat([org_tab, pd.DataFrame([total])], ignore_index=True)
    org_tab = org_tab.merge(periodo[['periodo']], left_on='org', right_index=True, how='left')
    org_tab.loc[org_tab['org'] == 'Todas las organizaciones', 'periodo'] = (
        per['inicio'].min().strftime('%m/%Y') + ' – ' + per['inicio'].max().strftime('%m/%Y'))
    # Subescalas BAT (medias)
    for sub in BAT_SUB:
        m = per.groupby('org')['bat_' + sub].mean()
        org_tab['media_' + sub] = org_tab['org'].map(m)
        org_tab.loc[org_tab['org'] == 'Todas las organizaciones', 'media_' + sub] = per['bat_' + sub].mean()
    org_tab.to_csv(os.path.join(a.salida, 'agregados_org.csv'), index=False)

    # --- Por grupo dentro de cada organización (supresión n < N_MIN) ---
    filas = []
    for var in ['sexo', 'edad', 'modalidad', 'cargo']:
        for (org, val), g in per.dropna(subset=[var]).groupby(['org', var]):
            s = resumen(g).to_dict()
            s.update(org=org, variable=var, grupo=val)
            filas.append(s)
        for val, g in per.dropna(subset=[var]).groupby(var):
            s = resumen(g).to_dict()
            s.update(org='Todas las organizaciones', variable=var, grupo=val)
            filas.append(s)
    grp = pd.DataFrame(filas)
    grp['suprimido'] = grp['n_bat'] < N_MIN
    # Supresión secundaria: si lo oculto suma < N_MIN personas, se podría deducir restando
    # del total de la organización; entonces se oculta también el grupo visible más pequeño.
    for (org_, var_), idx in grp.groupby(['org', 'variable']).groups.items():
        sub = grp.loc[idx]
        oculto = sub.loc[sub['suprimido'], 'n_bat'].sum()
        if sub['suprimido'].any() and oculto < N_MIN:
            visibles = sub[~sub['suprimido']]
            if len(visibles):
                grp.loc[visibles['n_bat'].idxmin(), 'suprimido'] = True
    cols_val = ['pct_riesgo', 'ic_bajo', 'ic_alto', 'pct_severo', 'bat_media', 'pct_retiro']
    grp.loc[grp['suprimido'], cols_val] = np.nan
    grp.loc[grp['suprimido'], 'n_bat'] = np.nan      # tampoco se publica el n exacto
    grp.loc[grp['n_retiro'] < N_MIN, 'pct_retiro'] = np.nan
    grp = grp.drop(columns=['n_retiro'])
    grp.to_csv(os.path.join(a.salida, 'agregados_grupo.csv'), index=False)

    # --- Factores por organización ---
    filas = []
    for org, g in list(per.groupby('org')) + [('Todas las organizaciones', per)]:
        for f in FACTORES:
            v = g['idx_' + f].dropna()
            d = g['desf_' + f].dropna()
            filas.append({'org': org, 'factor': f, 'n': len(v),
                          'indice': v.mean() if len(v) else np.nan,
                          'pct_desfavorable': d.mean() * 100 if len(d) else np.nan,
                          'items_disponibles': int(sum(g[i].notna().any() for i in FACTORES[f][0]))})
    fac = pd.DataFrame(filas)
    fac.loc[fac['n'] < N_MIN, ['indice', 'pct_desfavorable']] = np.nan
    fac.to_csv(os.path.join(a.salida, 'factores_org.csv'), index=False)

    # --- Asociación factor -> riesgo de burnout ---
    def asociacion(g, f):
        b = g.dropna(subset=['bat', 'desf_' + f])
        des, fav = b[b['desf_' + f] == 1], b[b['desf_' + f] == 0]
        return {'factor': f,
                'n_desfavorable': len(des), 'n_favorable': len(fav),
                'riesgo_desfavorable': des['riesgo'].mean() * 100 if len(des) else np.nan,
                'riesgo_favorable': fav['riesgo'].mean() * 100 if len(fav) else np.nan}

    aso = pd.DataFrame([asociacion(per, f) for f in FACTORES])
    aso['diferencia_pp'] = aso['riesgo_desfavorable'] - aso['riesgo_favorable']
    aso['razon'] = aso['riesgo_desfavorable'] / aso['riesgo_favorable']
    aso.to_csv(os.path.join(a.salida, 'asociacion.csv'), index=False)

    filas = []
    for org, g in per.groupby('org'):
        for f in FACTORES:
            r = asociacion(g, f)
            r['org'] = org
            for lado in ('desfavorable', 'favorable'):
                if r['n_' + lado] < N_MIN:
                    r['riesgo_' + lado] = np.nan
            filas.append(r)
    aso_org = pd.DataFrame(filas)
    aso_org['diferencia_pp'] = aso_org['riesgo_desfavorable'] - aso_org['riesgo_favorable']
    aso_org.to_csv(os.path.join(a.salida, 'asociacion_org.csv'), index=False)

    # --- Detalle por ítem: % que responde en el extremo desfavorable ---
    ENUNCIADOS = {
        'ctrl1': 'Puedo decidir qué hago en mi trabajo', 'ctrl2': 'Puedo opinar sobre la forma de hacer mi trabajo',
        'ctrl3': 'Tengo voz y voto sobre mi ritmo de trabajo',
        'dem1': 'Me presionan para trabajar muchas horas', 'dem2': 'Tengo plazos de entrega inalcanzables',
        'dem3': 'Tengo presiones de tiempo poco realistas', 'dem4': 'Descuido tareas porque tengo mucho que hacer',
        'lid1': 'Puedo confiar en mi líder ante un problema', 'lid2': 'Si el trabajo se pone difícil, mi líder me ayuda',
        'lid3': 'Recibo de mi líder el apoyo que necesito', 'lid4': 'Mi líder escucha mis problemas laborales',
        'lid5': 'Mi líder valora mis contribuciones', 'lid6': 'Mi líder reconoce mi trabajo duro',
        'lid7': 'Mi líder me anima con elogios',
        'gru1': 'Si el trabajo se pone difícil, mis compañeros me ayudan', 'gru2': 'Recibo de mis compañeros el apoyo que necesito',
        'gru3': 'Mis compañeros escuchan mis problemas laborales',
        'rol1': 'Tengo claro lo que se espera de mí', 'rol2': 'Sé cómo hacer mi trabajo',
        'rol3': 'Tengo claros mis deberes y responsabilidades', 'rol4': 'Entiendo cómo mi trabajo aporta al objetivo general',
        'con1': 'Distintos grupos me exigen cosas difíciles de hacer a la vez', 'con2': 'Distintas personas esperan de mí cosas contradictorias',
        'con3': 'Recibo solicitudes incompatibles',
        'cam1': 'Me consultan sobre los cambios', 'cam2': 'Tengo claro cómo funcionarán los cambios',
        'cam3': 'Estoy informado sobre los cambios', 'cam4': 'Puedo expresar inquietudes sobre los cambios',
        'res1': 'La salud física y mental es prioridad de los líderes', 'res2': 'Se mide periódicamente la salud mental',
        'res3': 'Hay recursos accesibles para la salud mental', 'res4': 'Recibo entrenamiento en cuidado de la salud mental',
        'res5': 'Se comunican los resultados de las acciones en salud mental',
        'tf1': 'Las exigencias del trabajo interfieren con mi vida familiar', 'tf2': 'El tiempo de trabajo dificulta mis responsabilidades familiares',
        'tf3': 'Lo que quiero hacer en casa no se hace por el trabajo', 'tf4': 'El trabajo produce tensión que afecta mis deberes familiares',
        'tf5': 'Por el trabajo cambio mis planes familiares',
    }
    filas = []
    for org, g in list(per.groupby('org')) + [('Todas las organizaciones', per)]:
        for f, (its, direc, pts) in FACTORES.items():
            for it in its:
                v = g[it].dropna()
                if len(v) < N_MIN:
                    continue
                if pts == 7 and f != 'Interferencia trabajo→familia':
                    # desfavorable: nunca/rara vez en ítems positivos; a menudo/frecuentemente/siempre en negativos
                    desf = (v <= 2) if direc > 0 else (v >= 5)
                else:
                    desf = (v >= 5)  # de acuerdo (algo, muy, totalmente)
                filas.append({'org': org, 'factor': f, 'item': it, 'enunciado': ENUNCIADOS[it],
                              'n': len(v), 'pct_desfavorable': desf.mean() * 100})
    pd.DataFrame(filas).to_csv(os.path.join(a.salida, 'items_org.csv'), index=False)

    # --- Sensibilidad: orden alterno de la escala HSE ---
    alt = calcular_personas(df, escala_hse=ESC_HSE_ALT)
    aso_alt = pd.DataFrame([asociacion(alt, f) for f in FACTORES])
    aso_alt['diferencia_pp'] = aso_alt['riesgo_desfavorable'] - aso_alt['riesgo_favorable']
    fac_base = per[['idx_' + f for f in FACTORES]].mean()
    fac_alt = alt[['idx_' + f for f in FACTORES]].mean()
    sens = pd.DataFrame({
        'factor': list(FACTORES),
        'indice_orden_supuesto': fac_base.values,
        'indice_orden_alterno': fac_alt.values,
        'dif_pp_orden_supuesto': aso['diferencia_pp'].values,
        'dif_pp_orden_alterno': aso_alt['diferencia_pp'].values,
    })
    sens['rank_supuesto'] = sens['dif_pp_orden_supuesto'].rank(ascending=False).astype(int)
    sens['rank_alterno'] = sens['dif_pp_orden_alterno'].rank(ascending=False).astype(int)
    sens.to_csv(os.path.join(a.salida, 'sensibilidad.csv'), index=False)

    # --- Intención de retiro según riesgo de burnout ---
    filas = []
    for org, g in list(per.groupby('org')) + [('Todas las organizaciones', per)]:
        b = g.dropna(subset=['bat', 'retiro'])
        con, sin = b[b['riesgo'] == 1], b[b['riesgo'] == 0]
        filas.append({'org': org, 'n_en_riesgo': len(con), 'n_sin_riesgo': len(sin),
                      'retiro_en_riesgo': con['retiro'].mean() * 100 if len(con) >= N_MIN else np.nan,
                      'retiro_sin_riesgo': sin['retiro'].mean() * 100 if len(sin) >= N_MIN else np.nan})
    pd.DataFrame(filas).to_csv(os.path.join(a.salida, 'retiro_riesgo.csv'), index=False)

    # --- Verificaciones documentadas ---
    ver = []
    # Organizaciones con dos archivos (en estos datos, una alcaldía): ¿hay registros repetidos entre archivos?
    por_org = {}
    for p in partes:
        por_org.setdefault(p['org'].iloc[0], []).append(p)
    dobles = {o: ps for o, ps in por_org.items() if len(ps) == 2}
    for cod, tun in dobles.items():
        a1, a2 = tun
        cols_txt = [c for c in a1.columns if c.endswith('_txt')]
        def claves(p):
            p = p[~p['consentimiento'].str.startswith('no', na=False)]
            p = p[p[list(ITEMS)].notna().sum(axis=1) >= 10]
            return set(p[['_perfil'] + cols_txt].apply(lambda r: '|'.join(map(str, r.tolist())), axis=1))
        ver.append({'verificacion': 'Dos archivos: organización', 'resultado': cod})
        ver.append({'verificacion': 'Dos archivos: registros con la misma hora de inicio en ambos archivos',
                    'resultado': len(set(a1['inicio'].dropna()) & set(a2['inicio'].dropna()))})
        ver.append({'verificacion': 'Dos archivos: registros con perfil y respuestas idénticos en ambos archivos',
                    'resultado': len(claves(a1) & claves(a2))})
        ver.append({'verificacion': 'Dos archivos: registros por archivo (antes de limpiar)',
                    'resultado': f"{len(a1)} y {len(a2)}"})
    faltan = sorted({r['org'] for r in revision if r['estado'] == 'no está en la base'})
    ver.append({'verificacion': 'Organizaciones con ítems faltantes', 'resultado': ', '.join(faltan) or 'ninguna'})
    ver.append({'verificacion': 'Ítems que no aparecen en alguna base',
                'resultado': '; '.join(f"{r['org']}: {r['item']}" for r in revision if r['estado'] == 'no está en la base') or 'ninguno'})
    ver.append({'verificacion': 'Etiquetas de respuesta no reconocidas',
                'resultado': sum(1 for r in revision if r['estado'].startswith('etiquetas')) })
    pd.DataFrame(ver).to_csv(os.path.join(a.salida, 'verificaciones.csv'), index=False)

    # --- Registro de limpieza y revisión de escalas ---
    pd.DataFrame(log).drop(columns='archivo').to_csv(os.path.join(a.salida, 'registro_limpieza.csv'), index=False)
    pd.DataFrame(revision, columns=['archivo', 'org', 'item', 'estado']).drop(columns='archivo').to_csv(os.path.join(a.salida, 'revision_escalas.csv'), index=False)

    print('Listo.')
    print(org_tab[['org', 'n_bat', 'pct_riesgo', 'pct_severo', 'periodo']].to_string(index=False))


if __name__ == '__main__':
    main()
