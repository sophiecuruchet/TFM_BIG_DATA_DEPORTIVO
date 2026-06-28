# TFM_BIG_DATA_DEPORTIVO
**Proyecto:** Plataforma web de análisis de juego ATP Top 100 (2022-2025), con énfasis en Carlos Alcaraz.

## Contenido principal

- `app/app.py`: aplicación final en Streamlit.
- `etl/build_processed_data.py`: proceso ETL para generar los CSV procesados.
- `data/raw/`: archivos originales del Tennis Charting Project.
- `data/processed/`: datasets limpios usados por la app.
- `app/assets/players/`: imágenes locales/cacheadas de jugadores.
- `requirements.txt`: librerías necesarias.

## Cómo ejecutar

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

## Secciones de la herramienta

1. Inicio: objetivos, KPIs globales y jugadores destacados.
2. Dashboard ATP: box plots, correlaciones y distribución del Top 100.
3. Carlos Alcaraz: análisis específico por temporada, superficie, tipo de golpe y rally length.
4. Comparador ATP: comparación entre cualquier jugador disponible del Top 100, con radar normalizado por percentiles.
5. Ranking ATP cierre de año: Top 100 de cierre 2022, 2023, 2024 y 2025, con fichas e imágenes locales/cacheadas.
6. Metodología y fuentes: explicación del ETL, métricas y limitaciones.

## Métricas clave

- Winner/UE Ratio = winners / errores no forzados.
- Winners por 100 golpes = winners / golpes ejecutados * 100.
- Radar normalizado = percentil 0-100 frente al conjunto de jugadores filtrados.
- Rallies: segmentos 1-3, 4-6, 7-9 y >9 golpes.

## Fuentes

- Jeff Sackmann Tennis Charting Project.
- ATP Tour Rankings Archive.
- Tennis Abstract como referencia contextual.

## Limitación metodológica

La muestra de análisis de juego se basa en partidos charted públicamente disponibles. Por tanto, el proyecto debe interpretarse como una herramienta de análisis reproducible sobre una muestra observada, no como una base oficial completa de todos los partidos ATP.



- Dashboard ATP corregido: solo mantiene un box plot principal y añade líderes Top 100 2025 por métricas de juego.
- Pestaña Carlos Alcaraz ampliada con records, Grand Slams, torneos ganados 2022-2025 y análisis del Australian Open como Grand Slam pendiente.
- Comparador ATP simplificado: radar normalizado, efectividad por golpe, un único box plot Winner/UE y línea de rallies.
- Ranking ATP de cierre anual mantiene Top 100 con imágenes locales/cacheadas.
