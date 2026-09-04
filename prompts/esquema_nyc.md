Base de datos PostgreSQL con PostGIS. Datos de Nueva York.
**SRID 26918 (UTM zona 18N). Las unidades son METROS**, no grados.

## Tablas

### nyc_neighborhoods

Barrios de la ciudad (129 filas).

| columna  | tipo         | descripción                                                     |
| -------- | ------------ | --------------------------------------------------------------- |
| gid      | integer      | clave primaria                                                  |
| boroname | varchar      | distrito: Brooklyn, Manhattan, Queens, The Bronx, Staten Island |
| name     | varchar      | nombre del barrio                                               |
| geom     | MultiPolygon | límite del barrio                                               |

### nyc_census_blocks

Bloques censales con población.

| columna    | tipo         | descripción                |
| ---------- | ------------ | -------------------------- |
| gid        | integer      | clave primaria             |
| blkid      | varchar      | identificador del bloque   |
| popn_total | float8       | población total            |
| popn_white | float8       | población blanca           |
| popn_black | float8       | población negra            |
| popn_nativ | float8       | población nativa americana |
| popn_asian | float8       | población asiática         |
| popn_other | float8       | otra población             |
| boroname   | varchar      | distrito                   |
| geom       | MultiPolygon | límite del bloque          |

**No tiene columna de barrio.** Para población por barrio hay que unir espacialmente
con `nyc_neighborhoods`. Para población por distrito basta con `boroname`, sin join.

### nyc_streets

Red vial.

| columna | tipo            | descripción                                               |
| ------- | --------------- | --------------------------------------------------------- |
| gid     | integer         | clave primaria                                            |
| id      | float8          | identificador original                                    |
| name    | varchar         | nombre de la calle (puede ser NULL)                       |
| oneway  | varchar         | sentido único                                             |
| type    | varchar         | residential, motorway, primary, secondary, tertiary, etc. |
| geom    | MultiLineString | trazado                                                   |

Una calle aparece en varias filas (segmentos). Para longitudes totales usa
`GROUP BY name` con `SUM(ST_Length(geom))`.

### nyc_subway_stations

Estaciones de metro.

| columna   | tipo    | descripción                                        |
| --------- | ------- | -------------------------------------------------- |
| gid       | integer | clave primaria                                     |
| name      | varchar | nombre corto de la estación                        |
| long_name | varchar | nombre completo                                    |
| alt_name  | varchar | nombre alternativo                                 |
| cross_st  | varchar | calle transversal                                  |
| label     | varchar | etiqueta de mapa                                   |
| borough   | varchar | distrito                                           |
| nghbhd    | varchar | barrio                                             |
| routes    | varchar | líneas que paran, separadas por coma (ej: 'A,C,E') |
| transfers | varchar | transbordos disponibles                            |
| color     | varchar | color de la línea                                  |
| express   | varchar | marca de parada expresa                            |
| closed    | varchar | marca de estación cerrada                          |
| geom      | Point   | ubicación                                          |

Tiene `borough` y `nghbhd`, así que para filtrar por distrito o barrio
**no hace falta join espacial**.

### nyc_homicides

Registros de homicidios.

| columna    | tipo    | descripción                              |
| ---------- | ------- | ---------------------------------------- |
| gid        | integer | clave primaria                           |
| incident_d | date    | fecha del incidente                      |
| boroname   | varchar | distrito                                 |
| num_victim | varchar | número de víctimas (es TEXTO, no número) |
| primary_mo | varchar | móvil principal                          |
| id         | float8  | identificador original                   |
| weapon     | varchar | arma usada                               |
| light_dark | varchar | 'D' de día, 'N' de noche                 |
| year       | float8  | año (es DOUBLE PRECISION, no entero)     |
| geom       | Point   | ubicación                                |

Como `year` es `float8`, para mostrarlo como año usa `year::int`.

## Funciones espaciales

- `ST_Intersects(a.geom, b.geom)` — se tocan o solapan
- `ST_Contains(poligono.geom, punto.geom)` — el punto está dentro
- `ST_DWithin(a.geom, b.geom, 500)` — a menos de 500 metros
- `ST_Distance(a.geom, b.geom)` — distancia en metros
- `ST_Area(geom)` — área en m²
- `ST_Length(geom)` — longitud en metros
- `ST_Intersection(a.geom, b.geom)` — geometría común entre dos
- `ST_Centroid(ST_Union(geom))` — centro de varias geometrías
- `ST_Transform(geom, 4326)` — pasar a latitud/longitud

## Reglas de PostgreSQL y PostGIS

- `ROUND()` con decimales exige casteo: `ROUND(valor::numeric, 2)`
- Para asignar un polígono pequeño a uno grande sin doble conteo:
  `ST_Contains(grande.geom, ST_Centroid(pequeño.geom))`
- El operador `<->` ordena por distancia y usa el índice; prefiérelo a `ORDER BY ST_Distance(...)`
- `ST_DWithin(a, b, d)` es mejor que `ST_Distance(a, b) < d` porque aprovecha el índice
- El área sale en m²; divide entre 1000000 para km²
- Brooklyn, Manhattan, Queens, The Bronx y Staten Island son **distritos**
  (`boroname` / `borough`), no barrios (`name` / `nghbhd`)

## Ejemplos

### Consultas no espaciales

**Pregunta:** ¿Cuántos barrios hay por distrito?

```sql
SELECT boroname, COUNT(*) AS total
FROM nyc_neighborhoods
GROUP BY boroname
ORDER BY total DESC
LIMIT 100;
```

**Pregunta:** ¿Cuál es la población de cada distrito?

```sql
SELECT boroname, SUM(popn_total) AS poblacion
FROM nyc_census_blocks
GROUP BY boroname
ORDER BY poblacion DESC
LIMIT 100;
```

**Pregunta:** ¿Qué estaciones de metro hay en el barrio Chelsea?

```sql
SELECT name, routes
FROM nyc_subway_stations
WHERE nghbhd = 'Chelsea'
LIMIT 100;
```

**Pregunta:** ¿Cuántas estaciones hay por barrio?

```sql
SELECT nghbhd, COUNT(*) AS estaciones
FROM nyc_subway_stations
GROUP BY nghbhd
ORDER BY estaciones DESC
LIMIT 100;
```

**Pregunta:** ¿Cuántos homicidios hubo por distrito?

```sql
SELECT boroname, COUNT(*) AS total
FROM nyc_homicides
GROUP BY boroname
ORDER BY total DESC
LIMIT 100;
```

**Pregunta:** ¿Cómo evolucionaron los homicidios por año?

```sql
SELECT year::int AS anio, COUNT(*) AS casos
FROM nyc_homicides
GROUP BY year
ORDER BY year
LIMIT 100;
```

**Pregunta:** ¿Qué armas se usaron con más frecuencia?

```sql
SELECT weapon, COUNT(*) AS casos
FROM nyc_homicides
WHERE weapon IS NOT NULL
GROUP BY weapon
ORDER BY casos DESC
LIMIT 100;
```

### Medición: área, longitud, distancia

**Pregunta:** ¿Cuáles son los 5 barrios más grandes por área?

```sql
SELECT name, boroname, ROUND((ST_Area(geom) / 1000000)::numeric, 2) AS km2
FROM nyc_neighborhoods
ORDER BY ST_Area(geom) DESC
LIMIT 5;
```

**Pregunta:** ¿Cuántos kilómetros de vía hay por tipo de calle?

```sql
SELECT type, ROUND((SUM(ST_Length(geom)) / 1000)::numeric, 1) AS km
FROM nyc_streets
GROUP BY type
ORDER BY km DESC
LIMIT 100;
```

**Pregunta:** ¿Cuál es la calle más larga de Manhattan?

```sql
SELECT s.name, ROUND(SUM(ST_Length(s.geom))::numeric, 0) AS metros
FROM nyc_streets s
JOIN nyc_neighborhoods n ON ST_Intersects(s.geom, n.geom)
WHERE n.boroname = 'Manhattan' AND s.name IS NOT NULL
GROUP BY s.name
ORDER BY metros DESC
LIMIT 1;
```

**Pregunta:** ¿Cuántos metros de Broadway pasan por cada distrito?

```sql
SELECT n.boroname,
       ROUND(SUM(ST_Length(ST_Intersection(s.geom, n.geom)))::numeric, 0) AS metros
FROM nyc_streets s
JOIN nyc_neighborhoods n ON ST_Intersects(s.geom, n.geom)
WHERE s.name = 'Broadway'
GROUP BY n.boroname
ORDER BY metros DESC
LIMIT 100;
```

### Contención y pertenencia

**Pregunta:** ¿Cuál es la población del barrio West Village?

```sql
SELECT SUM(b.popn_total) AS poblacion
FROM nyc_census_blocks b
JOIN nyc_neighborhoods n ON ST_Intersects(b.geom, n.geom)
WHERE n.name = 'West Village'
LIMIT 100;
```

**Pregunta:** ¿En qué barrios ocurrieron más homicidios?

```sql
SELECT n.name, n.boroname, COUNT(h.gid) AS casos
FROM nyc_neighborhoods n
JOIN nyc_homicides h ON ST_Contains(n.geom, h.geom)
GROUP BY n.name, n.boroname
ORDER BY casos DESC
LIMIT 100;
```

**Pregunta:** ¿Qué calles cruzan por el barrio SoHo?

```sql
SELECT DISTINCT s.name, s.type
FROM nyc_streets s
JOIN nyc_neighborhoods n ON ST_Intersects(s.geom, n.geom)
WHERE n.name = 'SoHo' AND s.name IS NOT NULL
ORDER BY s.name
LIMIT 100;
```

**Pregunta:** ¿Qué barrios no tienen ninguna estación de metro?

```sql
SELECT n.name, n.boroname
FROM nyc_neighborhoods n
WHERE NOT EXISTS (
    SELECT 1 FROM nyc_subway_stations e
    WHERE ST_Contains(n.geom, e.geom)
)
ORDER BY n.boroname, n.name
LIMIT 100;
```

### Proximidad y distancia

**Pregunta:** ¿Cuántos homicidios ocurrieron a menos de 300 metros de una estación?

```sql
SELECT COUNT(DISTINCT h.gid) AS casos
FROM nyc_homicides h
JOIN nyc_subway_stations e ON ST_DWithin(h.geom, e.geom, 300)
LIMIT 100;
```

**Pregunta:** ¿Qué estaciones están a menos de 1 km de la estación Broad St?

```sql
SELECT b.name, b.routes, ROUND(ST_Distance(a.geom, b.geom)::numeric, 0) AS metros
FROM nyc_subway_stations a, nyc_subway_stations b
WHERE a.name = 'Broad St'
  AND a.gid <> b.gid
  AND ST_DWithin(a.geom, b.geom, 1000)
ORDER BY metros
LIMIT 100;
```

**Pregunta:** ¿Cuál es la estación de metro más cercana al barrio Little Italy?

```sql
SELECT e.name, e.routes, ROUND(ST_Distance(n.geom, e.geom)::numeric, 0) AS metros
FROM nyc_neighborhoods n, nyc_subway_stations e
WHERE n.name = 'Little Italy'
ORDER BY n.geom <-> e.geom
LIMIT 1;
```

**Pregunta:** ¿Qué población vive a menos de 500 metros de una estación de metro?

```sql
SELECT ROUND(SUM(b.popn_total)::numeric, 0) AS poblacion
FROM nyc_census_blocks b
WHERE EXISTS (
    SELECT 1 FROM nyc_subway_stations e
    WHERE ST_DWithin(b.geom, e.geom, 500)
)
LIMIT 100;
```

**Pregunta:** ¿Qué barrios están a menos de 200 metros de la línea A del metro?

```sql
SELECT DISTINCT n.name, n.boroname
FROM nyc_neighborhoods n
JOIN nyc_subway_stations e ON ST_DWithin(n.geom, e.geom, 200)
WHERE e.routes LIKE '%A%'
ORDER BY n.boroname, n.name
LIMIT 100;
```

### Agregación demográfica

**Pregunta:** ¿Cuál es la densidad de población de cada barrio?

```sql
SELECT n.name, n.boroname,
       ROUND(SUM(b.popn_total)::numeric, 0) AS poblacion,
       ROUND((SUM(b.popn_total) / (ST_Area(n.geom) / 1000000))::numeric, 0) AS hab_km2
FROM nyc_neighborhoods n
JOIN nyc_census_blocks b ON ST_Contains(n.geom, ST_Centroid(b.geom))
GROUP BY n.name, n.boroname, n.geom
ORDER BY hab_km2 DESC
LIMIT 100;
```

**Pregunta:** ¿Cuál es la tasa de homicidios por cada 100.000 habitantes en cada barrio?

```sql
SELECT n.name,
       COUNT(h.gid) AS homicidios,
       SUM(b.popn_total) AS poblacion,
       ROUND((COUNT(h.gid) * 100000.0 / NULLIF(SUM(b.popn_total), 0))::numeric, 2) AS tasa
FROM nyc_neighborhoods n
JOIN nyc_census_blocks b ON ST_Contains(n.geom, ST_Centroid(b.geom))
LEFT JOIN nyc_homicides h ON ST_Contains(n.geom, h.geom)
GROUP BY n.name
HAVING SUM(b.popn_total) > 0
ORDER BY tasa DESC
LIMIT 100;
```

### Coordenadas y centroides

**Pregunta:** ¿Dónde está el centro de Brooklyn?

```sql
SELECT ST_AsText(ST_Centroid(ST_Union(geom))) AS centro
FROM nyc_neighborhoods
WHERE boroname = 'Brooklyn'
LIMIT 100;
```

**Pregunta:** ¿Dónde está el centro geográfico del barrio Harlem?

```sql
SELECT name, ST_AsText(ST_Centroid(geom)) AS centro
FROM nyc_neighborhoods
WHERE name = 'Harlem'
LIMIT 100;
```

**Pregunta:** ¿Cuáles son las coordenadas geográficas de la estación Times Sq?

```sql
SELECT name,
       ROUND(ST_Y(ST_Transform(geom, 4326))::numeric, 6) AS latitud,
       ROUND(ST_X(ST_Transform(geom, 4326))::numeric, 6) AS longitud
FROM nyc_subway_stations
WHERE name LIKE '%Times Sq%'
LIMIT 100;
```
