# ¿Dónde intervenir primero para prevenir el burnout?

Propuesta de visualización para el **Observatorio de Salud Mental — Universidad de La Sabana**
(Proyecto final, Visualización y Análisis de Datos 2026-II).

**Público:** líderes de Talento Humano y Seguridad y Salud en el Trabajo (SST) de las organizaciones participantes.
**Pregunta:** ¿Qué tan extendido está el riesgo de burnout en mi organización y qué condiciones del trabajo debería atender primero?
**Decisión que habilita:** elegir uno o dos factores psicosociales para priorizar y en qué grupos enfocar la acción.

## Qué muestra el tablero

| Página del menú | Pregunta | Visualización |
|---|---|---|
| Inicio | ¿Quién lo usa y para qué? | Tarjetas guía |
| Riesgo de burnout | % de personas en riesgo (BAT-12) | Indicadores + puntos con intervalo de confianza por organización |
| Factores asociados | ¿Qué factores van de la mano con más burnout? | Mancuernas favorable vs. desfavorable |
| Dónde intervenir | ¿Qué factor priorizar en mi organización? | Impacto potencial + frecuencia × asociación + detalle por ítem |
| Grupos | ¿Dónde se concentra el riesgo? | Riesgo por cargo, modalidad, edad y sexo (grupos < 10 ocultos) |
| Datos y límites | ¿Cómo se prepararon los datos y qué no permiten concluir? | Registro de limpieza, revisiones, fórmulas, límites |

## Datos

- 16 archivos Excel (15 organizaciones; una organización tenía dos archivos y se unieron tras verificar 0 registros coincidentes).
- 4.391 registros → 4.327 analizados (61 sin autorización, 3 duplicados) → 4.324 con BAT-12 completo.
- Paleta: #0E2E17, #6B906E, #887F22, #8B6074, #78442F sobre fondo blanco.
- Instrumentos usados: BAT-12 (burnout), HSE Management Standards (factores psicosociales), responsabilidad organizacional,
  conflicto trabajo→familia e intención de retiro.

**Privacidad:** las bases originales **no están en este repositorio** (`.gitignore`). La carpeta `data/` solo contiene
**tablas agregadas**; cualquier grupo con menos de 10 respuestas se oculta (y, si hace falta, un segundo grupo para que no pueda deducirse por resta).

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para regenerar las tablas agregadas a partir de las bases originales (solo en tu computador):

```bash
python preparar_datos.py --entrada datos_originales
```

Las organizaciones aparecen con un código (Organización A, B, C…). La clave código → nombre la genera
`preparar_datos.py` en `datos_originales/clave_organizaciones.csv`, que **no** se sube a GitHub.

Enlace directo a una organización: `...?org=Organización%20B`

## Archivos

- `app.py` — tablero Streamlit.
- `preparar_datos.py` — limpieza, verificaciones, anonimización y cálculo de indicadores.
- `items.py` — mapa de cada ítem del cuestionario a su factor.
- `data/` — tablas agregadas que lee el tablero.

## Referencias

- Schaufeli, W. B., De Witte, H., Hakanen, J. J., Kaltiainen, J., & Kok, R. (2023). How to assess severe burnout? Cutoff points for the Burnout Assessment Tool (BAT) based on three European samples. *Scandinavian Journal of Work, Environment & Health, 49*(4), 293–302. https://doi.org/10.5271/sjweh.4093
- Hadžibajramović, E., Schaufeli, W., & De Witte, H. (2022). Shortening of the Burnout Assessment Tool (BAT)—from 23 to 12 items using content and Rasch analysis. *BMC Public Health, 22*. https://doi.org/10.1186/s12889-022-12946-y
