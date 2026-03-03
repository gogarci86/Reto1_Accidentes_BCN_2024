import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import os

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE LA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Accidentes Barcelona 2024", layout="wide")
st.title("🚗 Análisis de Accidentes de Tráfico en Barcelona")
st.markdown("Dashboard interactivo con información sobre accidentes de tráfico en Barcelona.")

# -----------------------------------------------------------------------------
# 2. CARGA Y LIMPIEZA DE DATOS
# -----------------------------------------------------------------------------
# Usamos cache para no recargar y limpiar los datos cada vez que se interactúa con la web
@st.cache_data
def load_and_clean_data(filepath):
    # Cargar datos
    df = pd.read_csv(filepath)
    
    # LIMPIEZA DE DATOS:
    
    # a) Eliminar duplicados: Comprobamos si hay registros idénticos (ej. mismo expediente)
    df = df.drop_duplicates(subset=['Numero_expedient'])
    
    # b) Tratamiento de nulos: 
    # En estos datasets, si la celda de "muertos" o "lesionados" está vacía, suele significar 0.
    cols_to_fill_zero = [
        "Numero_morts", 
        "Numero_lesionats_lleus", 
        "Numero_lesionats_greus", 
        "Numero_victimes"
    ]
    df[cols_to_fill_zero] = df[cols_to_fill_zero].fillna(0)
    
    # La descripción de la causa del peatón suele ser nula si no implica peatones. 
    df['Descripcio_causa_vianant'] = df['Descripcio_causa_vianant'].fillna("No aplica / No peatón")
    
    # c) Datos anómalos:
    # Filtramos coordenadas erróneas que caigan fuera del área metropolitana de BCN.
    # Latitud de Barcelona ronda 41.3 - 41.5 y Longitud 2.05 - 2.25
    df = df[
        (df['Latitud_WGS84'] > 41.3) & (df['Latitud_WGS84'] < 41.5) &
        (df['Longitud_WGS84'] > 2.05) & (df['Longitud_WGS84'] < 2.25)
    ]
    
    # Renombrar columnas de coordenadas para que pydeck y st.map las lean fácilmente
    df = df.rename(columns={"Latitud_WGS84": "lat", "Longitud_WGS84": "lon"})
    
    return df

# Cargar el dataframe de forma segura buscando en la misma carpeta que este script
directorio_actual = os.path.dirname(os.path.abspath(__file__))
ruta_csv = os.path.join(directorio_actual, "2024_accidents_gu_bcn.csv")

df = load_and_clean_data(ruta_csv)

# -----------------------------------------------------------------------------
# 3. MÉTRICAS PRINCIPALES
# -----------------------------------------------------------------------------
st.header("Resumen General")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Accidentes", len(df))
col2.metric("Total Víctimas", int(df["Numero_victimes"].sum()))
col3.metric("Heridos Graves", int(df["Numero_lesionats_greus"].sum()))
col4.metric("Fallecidos", int(df["Numero_morts"].sum()))

st.divider()

# -----------------------------------------------------------------------------
# 4. MAPA DE ZONAS CON MÁS ACCIDENTES (MAPA DE CALOR)
# -----------------------------------------------------------------------------
st.header("📍 Zonas con mayor concentración de accidentes")
st.markdown("Mapa de calor (Heatmap) que muestra la densidad general de siniestros.")

# Configuramos una vista inicial centrada en Barcelona
view_state = pdk.ViewState(latitude=41.3851, longitude=2.1734, zoom=11, pitch=40)

# Capa de Heatmap
heatmap_layer = pdk.Layer(
    "HeatmapLayer",
    data=df,
    opacity=0.8,
    get_position=["lon", "lat"],
    aggregation="SUM",
    get_weight=1, # Cada accidente vale 1
    radiusPixels=30,
)

st.pydeck_chart(pdk.Deck(layers=[heatmap_layer], initial_view_state=view_state))

# -----------------------------------------------------------------------------
# 5. MAPA DE ACCIDENTES MÁS GRAVES
# -----------------------------------------------------------------------------
st.header("🚨 Zonas con accidentes más graves")
st.markdown("Visualización de accidentes que han provocado heridos graves o fallecidos. El tamaño y color del punto varían según la gravedad.")

# Filtramos solo los accidentes graves o con muertos
df_graves = df[(df["Numero_morts"] > 0) | (df["Numero_lesionats_greus"] > 0)].copy()

# Creamos una métrica de "gravedad" para el tamaño del círculo
df_graves["gravedad"] = (df_graves["Numero_lesionats_greus"] * 2) + (df_graves["Numero_morts"] * 5)

scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_graves,
    get_position=["lon", "lat"],
    get_color="[200, 30, 0, 160]", # Rojo para alta gravedad
    get_radius="gravedad * 30",     # A mayor gravedad, radio más grande
    pickable=True
)

st.pydeck_chart(pdk.Deck(
    layers=[scatter_layer], 
    initial_view_state=view_state,
    tooltip={"text": "Barrio: {Nom_barri}\nCalle: {Nom_carrer}\nGraves: {Numero_lesionats_greus}\nMuertos: {Numero_morts}"}
))

# -----------------------------------------------------------------------------
# 6. GRÁFICOS E INSIGHTS RELEVANTES ADICIONALES
# -----------------------------------------------------------------------------
st.header("📊 Insights Adicionales")

col_a, col_b = st.columns(2)

with col_a:
    # Accidentes por día de la semana
    st.subheader("Accidentes por Día de la Semana")
    # Para ordenar los días correctamente
    orden_dias = ['Dilluns', 'Dimarts', 'Dimecres', 'Dijous', 'Divendres', 'Dissabte', 'Diumenge']
    accidentes_dia = df['Descripcio_dia_setmana'].value_counts().reindex(orden_dias).reset_index()
    accidentes_dia.columns = ['Día', 'Cantidad']
    
    fig_dia = px.bar(accidentes_dia, x='Día', y='Cantidad', color='Cantidad', color_continuous_scale='Blues')
    st.plotly_chart(fig_dia, use_container_width=True)

with col_b:
    # Distritos con más accidentes
    st.subheader("Top Distritos con más accidentes")
    distritos = df['Nom_districte'].value_counts().reset_index()
    distritos.columns = ['Distrito', 'Accidentes']
    
    fig_dist = px.bar(distritos, x='Accidentes', y='Distrito', orientation='h', color='Accidentes', color_continuous_scale='Reds')
    fig_dist.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_dist, use_container_width=True)

# Turnos (Mañana, Tarde, Noche)
st.subheader("Accidentes según el Turno")
turnos = df['Descripcio_torn'].value_counts().reset_index()
turnos.columns = ['Turno', 'Cantidad']
fig_turno = px.pie(turnos, values='Cantidad', names='Turno', hole=0.4, color_discrete_sequence=px.colors.sequential.Sunset)
st.plotly_chart(fig_turno, use_container_width=True)