Base de datos PostgreSQL con PostGIS. Datos de Nueva York.
**SRID 26918 (UTM zona 18N). Las unidades son METROS**, no grados.

## Tablas

### nyc_neighborhoods

Barrios de la ciudad.
| columna | tipo | descripción |
|---|---|---|
| gid | integer | clave primaria |
| boroname | varchar | distrito: Brooklyn, Manhattan, Queens, The Bronx, Staten Island |
| name | varchar | nombre del barrio |
| geom | MultiPolygon | límite del barrio |

### nyc_streets

Red vial.
| columna | tipo | descripción |
|---|---|---|
| gid | integer | clave primaria |
| name | varchar | nombre de la calle |
| oneway | varchar | 'yes' si es de un solo sentido |
| type | varchar | residential, motorway, primary, secondary, tertiary |
| geom | MultiLineString | trazado |

### nyc_subway_stations

Estaciones de metro.
| columna | tipo | descripción |
|---|---|---|
| gid | integer | clave primaria |
| name | varchar | nombre de la estación |
| borough | varchar | distrito |
| routes | varchar | líneas que paran, separadas por coma (ej: 'A,C,E') |
| express | varchar | 'express' si es parada expresa |
| geom | Point | ubicación |

### nyc_census_blocks

Bloques censales con población.
| columna | tipo | descripción |
|---|---|---|
| gid | integer | clave primaria |
| blkid | varchar | identificador del bloque |
| popn_total | float8 | población total |
| popn_white | float8 | población blanca |
| popn_black | float8 | población negra |
| hood | varchar | barrio al que pertenece |
| geom | MultiPolygon | límite del bloque |

### nyc_homicides

Registros de homicidios.
| columna | tipo | descripción |
|---|---|---|
| gid | integer | clave primaria |
| boroname | varchar | distrito |
| weapon | varchar | arma usada |
| year | integer | año |
| num_victim | varchar | número de víctimas |
| geom | Point | ubicación |

## Funciones espaciales frecuentes

- `ST_Intersects(a.geom, b.geom)` — comprueba si dos geometrías se tocan o solapan.
- `ST_Contains(poligono.geom, punto.geom)` — el punto está dentro del polígono.
- `ST_DWithin(a.geom, b.geom, 500)` — a menos de 500 **metros** de distancia.
- `ST_Distance(a.geom, b.geom)` — distancia en metros.
- `ST_Area(geom)` — área en metros cuadrados.
- `ST_Length(geom)` — longitud en metros.

## Ejemplos

**Pregunta:** ¿Cuántos barrios hay por distrito?

```sql
SELECT boroname, COUNT(*) AS total
FROM nyc_neighborhoods
GROUP BY boroname
ORDER BY total DESC
LIMIT 100;
```

**Pregunta:** ¿Qué estaciones de metro están en Brooklyn?

```sql
SELECT name, routes
FROM nyc_subway_stations
WHERE borough = 'Brooklyn'
LIMIT 100;
```

**Pregunta:** ¿Cuál es la población total del barrio West Village?

```sql
SELECT SUM(b.popn_total) AS poblacion
FROM nyc_census_blocks b
JOIN nyc_neighborhoods n ON ST_Intersects(b.geom, n.geom)
WHERE n.name = 'West Village'
LIMIT 100;
```

**Pregunta:** ¿Qué calles pasan a menos de 200 metros de la estación Broad St?

```sql
SELECT DISTINCT s.name
FROM nyc_streets s
JOIN nyc_subway_stations e ON ST_DWithin(s.geom, e.geom, 200)
WHERE e.name = 'Broad St'
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

**Pregunta:** ¿Qué armas se usaron con más frecuencia?

```sql
SELECT weapon, COUNT(*) AS casos
FROM nyc_homicides
WHERE weapon IS NOT NULL
GROUP BY weapon
ORDER BY casos DESC
LIMIT 100;
```

**Pregunta:** ¿Cómo evolucionaron los homicidios por año?

```sql
SELECT year, COUNT(*) AS casos
FROM nyc_homicides
GROUP BY year
ORDER BY year
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

**Pregunta:** ¿Cuántos homicidios ocurrieron a menos de 300 metros de una estación de metro?

```sql
SELECT COUNT(DISTINCT h.gid) AS casos
FROM nyc_homicides h
JOIN nyc_subway_stations e ON ST_DWithin(h.geom, e.geom, 300)
LIMIT 100;
```

**Pregunta:** ¿Cuál es la tasa de homicidios por cada 100.000 habitantes en cada barrio?

```sql
SELECT n.name,
       COUNT(h.gid) AS homicidios,
       SUM(b.popn_total) AS poblacion,
       ROUND((COUNT(h.gid) * 100000.0 / NULLIF(SUM(b.popn_total), 0))::numeric, 2) AS tasa
FROM nyc_neighborhoods n
JOIN nyc_census_blocks b ON ST_Intersects(n.geom, b.geom)
LEFT JOIN nyc_homicides h ON ST_Contains(n.geom, h.geom)
GROUP BY n.name
HAVING SUM(b.popn_total) > 0
ORDER BY tasa DESC
LIMIT 100;
```

**Pregunta:** ¿Los homicidios con arma de fuego ocurren más de noche?

```sql
SELECT light_dark, COUNT(*) AS casos
FROM nyc_homicides
WHERE weapon = 'gun'
GROUP BY light_dark
ORDER BY casos DESC
LIMIT 100;
```

**Pregunta:** ¿Cuál es la estación de metro más cercana al homicidio con id 5?

```sql
SELECT e.name, ROUND(ST_Distance(h.geom, e.geom)::numeric, 1) AS metros
FROM nyc_homicides h, nyc_subway_stations e
WHERE h.gid = 5
ORDER BY h.geom <-> e.geom
LIMIT 1;
```

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

**Pregunta:** ¿Cuántas estaciones de metro hay en cada barrio?

```sql
SELECT n.name, n.boroname, COUNT(e.gid) AS estaciones
FROM nyc_neighborhoods n
LEFT JOIN nyc_subway_stations e ON ST_Contains(n.geom, e.geom)
GROUP BY n.name, n.boroname
ORDER BY estaciones DESC
LIMIT 100;
```

**Pregunta:** ¿En qué barrio está la estación Union Sq?

```sql
SELECT n.name, n.boroname
FROM nyc_neighborhoods n
JOIN nyc_subway_stations e ON ST_Contains(n.geom, e.geom)
WHERE e.name = 'Union Sq'
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
SELECT e.name, e.routes,
       ROUND(ST_Distance(n.geom, e.geom)::numeric, 0) AS metros
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

**Pregunta:** ¿Qué calles cruzan por el barrio SoHo?

```sql
SELECT DISTINCT s.name, s.type
FROM nyc_streets s
JOIN nyc_neighborhoods n ON ST_Intersects(s.geom, n.geom)
WHERE n.name = 'SoHo'
  AND s.name IS NOT NULL
ORDER BY s.name
LIMIT 100;
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

**Pregunta:** ¿Qué barrios están a menos de 200 metros de la línea A del metro?

```sql
SELECT DISTINCT n.name, n.boroname
FROM nyc_neighborhoods n
JOIN nyc_subway_stations e ON ST_DWithin(n.geom, e.geom, 200)
WHERE e.routes LIKE '%A%'
ORDER BY n.boroname, n.name
LIMIT 100;
```

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

**Pregunta:** ¿Qué distrito tiene mayor proporción de población negra?

```sql
SELECT n.boroname,
       ROUND((SUM(b.popn_black) * 100.0 / NULLIF(SUM(b.popn_total), 0))::numeric, 1) AS porcentaje
FROM nyc_neighborhoods n
JOIN nyc_census_blocks b ON ST_Contains(n.geom, ST_Centroid(b.geom))
GROUP BY n.boroname
ORDER BY porcentaje DESC
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

**Pregunta:** ¿Dónde está el centro geográfico del barrio Harlem?

```sql
SELECT name, ST_AsText(ST_Centroid(geom)) AS centro
FROM nyc_neighborhoods
WHERE name = 'Harlem'
LIMIT 100;
```
