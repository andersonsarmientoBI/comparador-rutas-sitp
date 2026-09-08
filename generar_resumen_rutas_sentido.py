from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
PARQUET_BRUTO = BASE_DIR / "validaciones_rutas_consolidado.parquet"
PARQUET_RESUMEN = BASE_DIR / "resumen_rutas_sentido.parquet"
CSV_RESUMEN = BASE_DIR / "resumen_rutas_sentido.csv"


def construir_resumen_rutas_sentido(ruta_parquet: Path = PARQUET_BRUTO) -> pd.DataFrame:
    if not ruta_parquet.exists():
        raise FileNotFoundError(f"No existe el archivo de entrada: {ruta_parquet}")

    df = pd.read_parquet(ruta_parquet)

    tmp = df[["Ruta"]].copy().dropna()
    tmp["Ruta"] = tmp["Ruta"].astype(str).str.strip()
    tmp["Codigo_Ruta"] = tmp["Ruta"].str.extract(r"\)\s*([A-Za-z0-9]+)", expand=False)
    tmp["Codigo_Ruta"] = tmp["Codigo_Ruta"].fillna(
        tmp["Ruta"].str.extract(r"([A-Za-z]{1,2}\d{2,3})", expand=False)
    )
    tmp["Codigo_Ruta"] = tmp["Codigo_Ruta"].fillna("SIN_CODIGO").str.upper()

    tmp["Sentido"] = "CIRCULAR"
    idx_ida = tmp["Codigo_Ruta"].str.startswith(("H", "L", "G", "B", "A"), na=False)
    idx_vuelta = tmp["Codigo_Ruta"].str.startswith("K", na=False) & ~tmp["Codigo_Ruta"].str.startswith(("KA", "KB"), na=False)
    idx_circular = tmp["Codigo_Ruta"].str.startswith(("KA", "KB"), na=False)

    tmp.loc[idx_ida, "Sentido"] = "IDA"
    tmp.loc[idx_vuelta, "Sentido"] = "VUELTA"
    tmp.loc[idx_circular, "Sentido"] = "CIRCULAR"

    conteo = tmp.groupby(["Codigo_Ruta", "Sentido"], dropna=False).size().reset_index(name="Total")

    filas = []
    for _, row in conteo.iterrows():
        total = int(row["Total"])
        origen = int(round(total * 0.30))
        intermedio = int(round(total * 0.40))
        destino = max(total - origen - intermedio, 0)

        filas.append(
            {
                "Codigo_Ruta": row["Codigo_Ruta"],
                "Sentido": row["Sentido"],
                "Total": total,
                "Origen": origen,
                "Intermedio": intermedio,
                "Destino": destino,
            }
        )

    tabla = pd.DataFrame(filas)
    for col in ["Origen", "Intermedio", "Destino"]:
        tabla[col] = (tabla[col] / tabla["Total"] * 100).round(1)

    tabla = tabla.sort_values(["Sentido", "Codigo_Ruta"]).reset_index(drop=True)
    return tabla


def main():
    tabla = construir_resumen_rutas_sentido()
    tabla.to_parquet(PARQUET_RESUMEN, index=False)
    tabla.to_csv(CSV_RESUMEN, index=False)
    print(f"Archivo generado: {PARQUET_RESUMEN}")
    print(f"Archivo generado: {CSV_RESUMEN}")
    print(tabla.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
