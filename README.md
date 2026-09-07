# comparador-rutas-sitp

## Datos locales pesados

El archivo de entrada `validaciones_rutas_consolidado.parquet` es un dataset local grande y no debe subirse al repositorio.

Estrategia recomendada:
- guardar el archivo en una carpeta local fuera del repo, por ejemplo `data/` o una ruta compartida
- dejar el nombre exacto `validaciones_rutas_consolidado.parquet`
- apuntar la app con una variable de entorno:
  - `VALIDACIONES_PATH=C:/ruta/validaciones_rutas_consolidado.parquet`
  - o `VALIDACIONES_DIR=C:/ruta/datos`
- si se renueva el archivo con datos nuevos, solo se reemplaza el archivo local y se vuelve a ejecutar la app/calculo

La app intentará buscar el archivo en estos sitios, en orden:
1. `VALIDACIONES_PATH`
2. raíz del proyecto
3. `VALIDACIONES_DIR`
4. `data/` dentro del proyecto

Esto permite mantener el código estable y reciclar la misma estructura cuando el dataset cambie en el futuro.