# Contexto Técnico y Funcional: Herramienta de Análisis y Solapamiento de Rutas (SITP)

## 1. Visión General
Esta aplicación está construida en **Streamlit, GeoPandas, Folium y Pandas** para analizar, comparar y visualizar espacial e interactivamente las rutas de transporte público del SITP (Unidades Funcionales UF 6 y UF 17 / Green Móvil)[cite: 2].

El objetivo técnico principal es auditar el nivel de competencia geoespacial (solapamiento de trazados) y caracterizar la demanda a lo largo del recorrido mediante matrices Origen-Destino (O-D)[cite: 2].

---

## 2. Componentes y Lógica Geoespacial

### Procesamiento de Geometrías
* **Sistemas de Referencia Espacial (CRS):**
  * **Procesamiento y Cálculos:** MAGNA-SIRGAS / Origen Bogotá (`EPSG:3116`) para mediciones en metros/kilómetros[cite: 2].
  * **Visualización en Mapas:** WGS84 (`EPSG:4326`) para renderizado dinámico en Folium[cite: 2].
* **Banda de Análisis (Buffer):** Se genera un área de influencia de **20 metros a cada lado de la vía (40 metros en total)** para capturar paraderos, infraestructura multicarril y vías paralelas inmediatas[cite: 2].

### Cálculo de Solapamiento
Se determina la intersección espacial entre el buffer de la **Ruta de Estudio** y los trazados de la **Competencia** (otras rutas del SITP o Proyectos Futuros como Metro L1, Av. 68, Regiotram y Nueva Calle 13)[cite: 2]:

$$\%_{\text{solapamiento}} = \left( \frac{\text{Longitud de buffer compartido (km)}}{\text{Longitud total de la ruta (km)}} \right) \times 100$$

---

## 3. Segmentación y Matriz Origen-Destino (O-D)

### División Tramos de Recorrido
Para modelar la dinámica de demanda (subidas y bajadas de pasajeros)[cite: 2], los trazados geométricos se segmentan longitudinalmente en tres zonas por sentido (Ida / Vuelta)[cite: 2]:

* **Origen / Cabecera (0% - 30%):** Evaluado como tramo de alta captación / alimentador[cite: 2].
* **Tramo Intermedio (30% - 70%):** Evaluado como zona integradora, conector o de alta rotación de pasaje[cite: 2].
* **Destino / Cierre (70% - 100%):** Evaluado como zona de descarga o desembarque masivo[cite: 2].

### Estructura de Datos O-D
* Inferencia de patrones de viaje combinando secuencias de paraderos GTFS, registros de validaciones e inferencia de desembarque[cite: 2].
* Análisis de flujos de viaje por localidades (autocontención interna vs. viajes interlocalidades)[cite: 2].

---

## 4. Requerimientos de Interfaz de Usuario (Streamlit UI)

* **Panel Lateral (Sidebar):**
  * Selector de **Ruta de Estudio** (Green Móvil / UF 6 y UF 17)[cite: 2].
  * Selectores multivariable para **Rutas de Competencia / Capas de Contraste** (SITP actual, Troncales o Proyectos Futuros)[cite: 2].

* **Visualizador Espacial (Folium / streamlit-folium):**
  * Capa vectorial de la Ruta de Estudio[cite: 2].
  * Capa con la **Zona de Coincidencia** (intersección de buffers a 40m) resaltada[cite: 2].
  * Control de capas (Toggle): Trazados GeoJSON, Paraderos GTFS, Puntos de Abordaje/Desembarque y Heatmaps[cite: 2].

* **Módulo Analytics y Gráficos:**
  * Métricas principales (Distancia total de ruta y % de Solapamiento geoespacial)[cite: 2].
  * Gráficos interactivos (Plotly/Altair) de distribución de subidas/bajadas por los 6 tramos operativos (3 Ida + 3 Vuelta)[cite: 2].
  * Matriz / Flujos de movilidad Origen-Destino entre localidades[cite: 2].