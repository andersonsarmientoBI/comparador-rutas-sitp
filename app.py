import glob
import geopandas as gpd
import pandas as pd
import streamlit as st
import folium
from shapely.ops import unary_union
from streamlit_folium import st_folium

BUFFER_METROS = 30
MAX_RUTAS_EN_MAPA = 5

# Configuración de la página
st.set_page_config(page_title="Comparador de Rutas SITP", layout="wide")

st.title("🚍 Comparador Interactivo de Solapamiento de Rutas")
st.markdown("Selecciona una ruta principal y las rutas con las que deseas comparar su coincidencia espacial.")

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

# Reproyección y disolución se cachean para no repetirlas al mover el mapa.
@st.cache_data
def preparar_geometrias(_gdf):
    gdf_metrico = _gdf.to_crs(epsg=3116)
    gdf_wgs84 = _gdf.to_crs(epsg=4326)
    rutas = sorted(gdf_metrico["cod_linea"].unique())
    geometrias_m = {
        ruta: gdf_metrico[gdf_metrico["cod_linea"] == ruta].dissolve()["geometry"].values[0]
        for ruta in rutas
    }
    geometrias_wgs84 = {
        ruta: gdf_wgs84[gdf_wgs84["cod_linea"] == ruta].dissolve()["geometry"].values[0]
        for ruta in rutas
    }
    return rutas, geometrias_m, geometrias_wgs84


@st.cache_data
def cargar_proyectos():
    proyectos_m = {}
    proyectos_wgs84 = {}
    nombres = {}

    for archivo in sorted(glob.glob("proyectos_bogota/*.geojson")):
        proyecto = gpd.read_file(archivo)
        nombre_archivo = archivo.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        nombre = nombre_archivo.removesuffix(".geojson").replace("_", " ")

        # Metro_Linea_1 tiene coordenadas métricas con un CRS declarado incorrecto.
        if proyecto.total_bounds.max() > 1000:
            proyecto = proyecto.set_crs(epsg=3116, allow_override=True)
        elif proyecto.crs is None:
            proyecto = proyecto.set_crs(epsg=4326)

        geometria = unary_union(proyecto.to_crs(epsg=3116).geometry)
        geometria_wgs84 = unary_union(proyecto.to_crs(epsg=4326).geometry)
        clave = f"proyecto:{nombre}"
        proyectos_m[clave] = geometria
        proyectos_wgs84[clave] = geometria_wgs84
        nombres[clave] = nombre

    return proyectos_m, proyectos_wgs84, nombres


rutas_disponibles, geometrias_rutas, geometrias_rutas_wgs84 = preparar_geometrias(gdf_raw)
consorcios = gdf_raw.groupby("cod_linea")["oper_ruta"].first().to_dict()
geometrias_proyectos, geometrias_proyectos_wgs84, nombres_proyectos = cargar_proyectos()


@st.cache_data
def calcular_solapamientos(_geometrias, _consorcios, ruta_estudio):
    geom_estudio_m = _geometrias[ruta_estudio]
    long_estudio_km = geom_estudio_m.length / 1000.0
    buffer_estudio = geom_estudio_m.buffer(BUFFER_METROS)
    solapamientos = []

    for ruta, geometria in _geometrias.items():
        if ruta == ruta_estudio or not geometria.intersects(buffer_estudio):
            continue

        km_compartidos = geometria.intersection(buffer_estudio).length / 1000.0
        porcentaje = min(round((km_compartidos / long_estudio_km) * 100, 1), 100.0)
        if porcentaje > 5:
            solapamientos.append({
                "ruta": ruta,
                "porcentaje": porcentaje,
                "consorcio": _consorcios[ruta],
                "km_compartidos": km_compartidos,
            })

    return sorted(solapamientos, key=lambda item: item["porcentaje"], reverse=True)

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("⚙️ Configuración de Comparación")
ruta_estudio = st.sidebar.selectbox("Ruta Principal (Estudio):", rutas_disponibles, index=0)

# --- CÁLCULOS GEOGRÁFICOS ---
geom_estudio_m = geometrias_rutas[ruta_estudio]
long_estudio_km = geom_estudio_m.length / 1000.0
buffer_estudio = geom_estudio_m.buffer(BUFFER_METROS)
solapamientos = calcular_solapamientos(geometrias_rutas, consorcios, ruta_estudio)
opciones_comparacion = {
    item["ruta"]: f"{item['ruta']} | {item['porcentaje']}% | {item['consorcio']}"
    for item in solapamientos
}

for clave, nombre in nombres_proyectos.items():
    geometria = geometrias_proyectos[clave]
    km_compartidos = geometria.intersection(buffer_estudio).length / 1000.0
    porcentaje = min(round((km_compartidos / long_estudio_km) * 100, 1), 100.0)
    opciones_comparacion[clave] = f"{nombre} | {porcentaje}% | Proyecto Bogotá"

rutas_seleccionadas = st.sidebar.multiselect(
    "Rutas y proyectos para comparar:",
    options=list(opciones_comparacion),
    format_func=lambda opcion: opciones_comparacion[opcion],
    max_selections=MAX_RUTAS_EN_MAPA,
    help=f"Puedes seleccionar hasta {MAX_RUTAS_EN_MAPA} rutas para mantener el mapa ágil.",
)

datos_solapados = [
    item for item in solapamientos if item["ruta"] in rutas_seleccionadas
]
datos_proyectos = []
for clave, nombre in nombres_proyectos.items():
    if clave not in rutas_seleccionadas:
        continue
    geometria = geometrias_proyectos[clave]
    km_compartidos = geometria.intersection(buffer_estudio).length / 1000.0
    datos_proyectos.append({
        "clave": clave,
        "ruta": nombre,
        "porcentaje": min(round((km_compartidos / long_estudio_km) * 100, 1), 100.0),
        "consorcio": "Proyecto Bogotá",
        "km_compartidos": km_compartidos,
    })
datos_comparados = datos_solapados + datos_proyectos
max_porcentaje = max((item["porcentaje"] for item in datos_comparados), default=0)
km_compartidos = sum(item["km_compartidos"] for item in datos_comparados)

# --- PANEL DE MÉTRICAS CLAVE ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Elementos seleccionados", len(rutas_seleccionadas))
col2.metric("Mayor solapamiento", f"{max_porcentaje}%")
col3.metric("Distancia compartida", f"{round(km_compartidos, 2)} km")
col4.metric(f"Longitud {ruta_estudio}", f"{round(long_estudio_km, 2)} km")

st.divider()

# --- PESTAÑAS: MAPA Y TABLA ---
tab_mapa, tab_tabla = st.tabs(["🗺️ Mapa Interactivo (Zoom)", "📊 Tabla Comparativa"])

with tab_mapa:
    # Preparar Geometrías para Folium (WGS84 / EPSG:4326)
    geom_estudio_wgs = geometrias_rutas_wgs84[ruta_estudio]

    # Calcular centroide del mapa
    centro = [geom_estudio_wgs.centroid.y, geom_estudio_wgs.centroid.x]

    # Crear Mapa Folium
    #m = folium.Map(location=centro, zoom_start=12, tiles="CartoDB positron")
    m = folium.Map(location=centro, zoom_start=12, tiles="OpenStreetMap")

    # Dibujar Ruta 1 (Estudio)
    folium.GeoJson(
        geom_estudio_wgs,
        name=f"Ruta Estudio: {ruta_estudio}",
        style_function=lambda x: {"color": "#1B5E20", "weight": 5, "opacity": 0.9},
        tooltip=f"Ruta Estudio: {ruta_estudio}",
    ).add_to(m)

    colores_rutas = ["#FF6D00", "#1565C0", "#6A1B9A", "#00838F", "#AD1457"]
    for indice, item in enumerate(datos_comparados):
        clave = item.get("clave", item["ruta"])
        es_proyecto = clave in geometrias_proyectos
        ruta = item["ruta"]
        geom_comp_wgs = (
            geometrias_proyectos_wgs84[clave]
            if es_proyecto
            else geometrias_rutas_wgs84[ruta]
        )
        geometria_m = geometrias_proyectos[clave] if es_proyecto else geometrias_rutas[ruta]
        zona_compartida_m = buffer_estudio.intersection(geometria_m.buffer(BUFFER_METROS))
        if not zona_compartida_m.is_empty:
            zona_wgs = gpd.GeoSeries([zona_compartida_m], crs=3116).to_crs(epsg=4326).values[0]
            folium.GeoJson(
                zona_wgs,
                name=f"Zona compartida: {ruta}",
                style_function=lambda x: {
                    "fillColor": "#FF1744",
                    "color": "#D50000",
                    "weight": 2,
                    "fillOpacity": 0.5,
                },
            ).add_to(m)

        folium.GeoJson(
            geom_comp_wgs,
            name=f"{ruta} ({item['porcentaje']}% - {item['consorcio']})",
            style_function=lambda x, color=colores_rutas[indice % len(colores_rutas)]: {
                "color": color, "weight": 4, "dashArray": "5, 5", "opacity": 0.9
            },
            tooltip=f"{ruta} | Solapamiento: {item['porcentaje']}% | {item['consorcio']}",
        ).add_to(m)

    folium.LayerControl().add_to(m)

    # Renderizar el mapa dentro de Streamlit
    st_folium(m, width="100%", height=600)

with tab_tabla:
    st.subheader("Datos de las rutas seleccionadas")
    datos_rutas = pd.DataFrame(
        datos_comparados,
        columns=["ruta", "porcentaje", "consorcio", "km_compartidos"],
    )[["ruta", "porcentaje", "consorcio"]]
    if datos_rutas.empty:
        st.info("Selecciona una o varias rutas en el panel lateral para mostrarlas en el mapa.")
    st.dataframe(datos_rutas, use_container_width=True)