import glob
import geopandas as gpd
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

# Configuración de la página
st.set_page_config(page_title="Comparador de Rutas SITP", layout="wide")

st.title("🚍 Comparador Interactivo de Solapamiento de Rutas")
st.markdown("Selecciona dos rutas para analizar su coincidencia espacial y métricas operativas.")

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_geojson():
    archivos = glob.glob("*.geojson")
    if not archivos:
        return None
    gdf = gpd.read_file(archivos[0])
    gdf["cod_linea"] = gdf["cod_linea"].astype(str).str.strip()
    gdf["oper_ruta"] = gdf["oper_ruta"].fillna("No Aplica").astype(str).str.strip()
    return gdf

gdf_raw = cargar_geojson()

if gdf_raw is None:
    st.error("❌ No se encontró ningún archivo `.geojson` en el directorio de la aplicación.")
    st.stop()

# Reproyección a sistema métrico local (EPSG:3116) y lat/lon para mapa (EPSG:4326)
gdf_metrico = gdf_raw.to_crs(epsg=3116)
rutas_disponibles = sorted(gdf_metrico["cod_linea"].unique())

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("⚙️ Configuración de Comparación")
ruta_estudio = st.sidebar.selectbox("Ruta Principal (Estudio):", rutas_disponibles, index=0)

# Filtrar para evitar seleccionar la misma ruta
rutas_comp_opciones = [r for r in rutas_disponibles if r != ruta_estudio]
ruta_comparar = st.sidebar.selectbox("Ruta a Comparar:", rutas_comp_opciones, index=0)

distancia_buffer = st.sidebar.slider("Margen de tolerancia (metros):", 10, 100, 30)

# --- CÁLCULOS GEOGRÁFICOS ---
geom_estudio_m = gdf_metrico[gdf_metrico["cod_linea"] == ruta_estudio].dissolve()["geometry"].values[0]
geom_comp_m = gdf_metrico[gdf_metrico["cod_linea"] == ruta_comparar].dissolve()["geometry"].values[0]

long_estudio_km = geom_estudio_m.length / 1000.0
long_comp_km = geom_comp_m.length / 1000.0

buffer_estudio = geom_estudio_m.buffer(distancia_buffer)
porcentaje = 0.0
km_compartidos = 0.0

if geom_comp_m.intersects(buffer_estudio):
    interseccion = geom_comp_m.intersection(buffer_estudio)
    km_compartidos = interseccion.length / 1000.0
    porcentaje = min(round((km_compartidos / long_estudio_km) * 100, 1), 100.0)

# --- PANEL DE MÉTRICAS CLAVE ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Solapamiento Trazado", f"{porcentaje}%")
col2.metric("Distancia Compartida", f"{round(km_compartidos, 2)} km")
col3.metric(f"Longitud {ruta_estudio}", f"{round(long_estudio_km, 2)} km")
col4.metric(f"Longitud {ruta_comparar}", f"{round(long_comp_km, 2)} km")

st.divider()

# --- PESTAÑAS: MAPA Y TABLA ---
tab_mapa, tab_tabla = st.tabs(["🗺️ Mapa Interactivo (Zoom)", "📊 Tabla Comparativa"])

with tab_mapa:
    # Preparar Geometrías para Folium (WGS84 / EPSG:4326)
    gdf_wgs84 = gdf_raw.to_crs(epsg=4326)
    geom_estudio_wgs = gdf_wgs84[gdf_wgs84["cod_linea"] == ruta_estudio].dissolve()["geometry"].values[0]
    geom_comp_wgs = gdf_wgs84[gdf_wgs84["cod_linea"] == ruta_comparar].dissolve()["geometry"].values[0]

    # Calcular centroide del mapa
    centro = [geom_estudio_wgs.centroid.y, geom_estudio_wgs.centroid.x]

    # Crear Mapa Folium
    #m = folium.Map(location=centro, zoom_start=12, tiles="CartoDB positron")
    m = folium.Map(location=centro, zoom_start=12, tiles="OpenStreetMap")

    # Dibujar Zona Compartida (Buffer)
    buffer_franja_estudio = geom_estudio_m.buffer(120)
    buffer_franja_comp = geom_comp_m.buffer(100)
    zona_compartida_m = buffer_franja_estudio.intersection(buffer_franja_comp)

    if not zona_compartida_m.is_empty:
        zona_wgs = gpd.GeoSeries([zona_compartida_m], crs=3116).to_crs(epsg=4326).values[0]
        folium.GeoJson(
            zona_wgs,
            name="Franja Compartida",
            style_function=lambda x: {
                "fillColor": "#FF1744",
                "color": "#D50000",
                "weight": 1,
                "fillOpacity": 0.4,
            },
        ).add_to(m)

    # Dibujar Ruta 1 (Estudio)
    folium.GeoJson(
        geom_estudio_wgs,
        name=f"Ruta Estudio: {ruta_estudio}",
        style_function=lambda x: {"color": "#1B5E20", "weight": 5, "opacity": 0.9},
        tooltip=f"Ruta Estudio: {ruta_estudio}",
    ).add_to(m)

    # Dibujar Ruta 2 (Comparar)
    folium.GeoJson(
        geom_comp_wgs,
        name=f"Ruta Comparada: {ruta_comparar}",
        style_function=lambda x: {"color": "#FF6D00", "weight": 4, "dashArray": "5, 5", "opacity": 0.9},
        tooltip=f"Ruta Comparada: {ruta_comparar}",
    ).add_to(m)

    folium.LayerControl().add_to(m)

    # Renderizar el mapa dentro de Streamlit
    st_folium(m, width="100%", height=600)

with tab_tabla:
    st.subheader("Datos de las rutas seleccionadas")
    datos_rutas = gdf_raw[gdf_raw["cod_linea"].isin([ruta_estudio, ruta_comparar])][
        ["cod_linea", "oper_ruta"]
    ].drop_duplicates()
    
    st.dataframe(datos_rutas, use_container_width=True)