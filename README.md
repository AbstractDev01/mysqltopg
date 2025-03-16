# Documentación: Herramienta de Migración MySQL a PostgreSQL

## Índice
1. [Introducción](#introducción)
2. [Requisitos](#requisitos)
3. [Arquitectura y Funcionamiento Interno](#arquitectura-y-funcionamiento-interno)
   - [Proceso de Migración](#proceso-de-migración)
   - [Manejo de Tipos de Datos](#manejo-de-tipos-de-datos)
   - [Estrategias de Importación de Datos](#estrategias-de-importación-de-datos)
   - [Migración de Estructura](#migración-de-estructura)
4. [Guía de Uso](#guía-de-uso)
   - [Instalación de Dependencias](#instalación-de-dependencias)
   - [Sintaxis de Comandos](#sintaxis-de-comandos)
   - [Ejemplos de Uso](#ejemplos-de-uso)
   - [Migración Selectiva de Tablas](#migración-selectiva-de-tablas)
5. [Estructura del Código](#estructura-del-código)
   - [Funciones Principales](#funciones-principales)
   - [Manejo de Errores](#manejo-de-errores)
6. [Reporte de Migración](#reporte-de-migración)
7. [Limitaciones y Consideraciones](#limitaciones-y-consideraciones)
8. [Solución de Problemas](#solución-de-problemas)

## Introducción

Esta herramienta es un script de Python diseñado para facilitar la migración completa de bases de datos desde MySQL a PostgreSQL. Realiza la migración de:

- Estructura de las tablas (esquema)
- Datos
- Claves primarias
- Claves foráneas
- Índices
- Secuencias para campos auto-incrementales

El script gestiona automáticamente la conversión de tipos de datos entre ambos sistemas, maneja excepciones y proporciona un informe detallado del proceso de migración.

## Requisitos

- Python 3.6 o superior
- Bibliotecas de Python:
  - `psycopg2` (para la conexión a PostgreSQL)
  - `mysql.connector` (para la conexión a MySQL)
  - Bibliotecas estándar: `csv`, `os`, `argparse`, `datetime`
- Acceso a las bases de datos:
  - Base de datos MySQL de origen
  - Base de datos PostgreSQL de destino (debe estar creada previamente)
- Permisos adecuados en ambos sistemas

## Arquitectura y Funcionamiento Interno

### Proceso de Migración

La herramienta sigue un proceso estructurado para asegurar una migración completa:

1. **Conexión a las bases de datos**: Establece conexiones a MySQL y PostgreSQL.
2. **Identificación de tablas**: Obtiene la lista de tablas a migrar.
3. **Para cada tabla**:
   - Obtiene el esquema desde MySQL
   - Crea la estructura equivalente en PostgreSQL
   - Exporta los datos a archivos CSV intermedios
   - Importa los datos desde CSV a PostgreSQL
   - Establece las claves primarias
   - Crea los índices necesarios
   - Ajusta las secuencias para campos auto-incrementales
4. **Migración de relaciones**: Crea las claves foráneas después de que todas las tablas estén migradas.
5. **Generación de informe**: Produce un reporte detallado del proceso.

### Manejo de Tipos de Datos

El script incluye un mapeo completo para convertir los tipos de datos de MySQL a sus equivalentes en PostgreSQL:

| MySQL | PostgreSQL |
|-------|------------|
| int | INTEGER |
| tinyint | SMALLINT (o BOOLEAN para tinyint(1)) |
| smallint | SMALLINT |
| mediumint | INTEGER |
| bigint | BIGINT |
| float | REAL |
| double | DOUBLE PRECISION |
| decimal | DECIMAL |
| varchar | VARCHAR (con longitud) |
| text | TEXT |
| datetime | TIMESTAMP |
| timestamp | TIMESTAMP |
| enum, set | TEXT |
| json | JSONB |
| blob, binary | BYTEA |

La función `mysql_to_postgresql_type()` gestiona estas conversiones, considerando las particularidades de cada sistema.

### Estrategias de Importación de Datos

El script implementa dos estrategias para la importación de datos:

1. **Método rápido (COPY)**: Utiliza el comando `COPY` de PostgreSQL para una importación eficiente de datos desde CSV.
2. **Método alternativo (INSERT)**: Si el método COPY falla, utiliza sentencias INSERT en lotes para importar los datos fila por fila.

Este enfoque de respaldo garantiza que la migración pueda completarse incluso cuando surgen problemas con formatos de datos específicos o caracteres especiales.

### Migración de Estructura

La migración de la estructura gestiona:

- **Definiciones de columnas**: Tipo, nulidad, valores por defecto
- **Claves primarias**: Detectadas y recreadas en PostgreSQL
- **Índices**: Identificados por nombre, unicidad y columnas
- **Claves foráneas**: Migradas después de crear todas las tablas
- **Secuencias**: Actualizadas para que continúen desde el último valor utilizado

## Guía de Uso

### Instalación de Dependencias

```bash
pip install psycopg2-binary mysql-connector-python
```

### Sintaxis de Comandos

```bash
python migrate_mysql_to_postgresql.py \
  --mysql-host <host> \
  --mysql-db <database> \
  --mysql-user <username> \
  --mysql-password <password> \
  --mysql-port <port> \
  --pg-host <host> \
  --pg-db <database> \
  --pg-user <username> \
  --pg-password <password> \
  --pg-port <port> \
  [--output-dir <directory>] \
  [--tables <table1> <table2> ...]
```

Parámetros:
- `--mysql-host`: Servidor MySQL
- `--mysql-db`: Nombre de la base de datos MySQL
- `--mysql-user`: Usuario MySQL
- `--mysql-password`: Contraseña MySQL
- `--mysql-port`: Puerto MySQL (predeterminado: 3306)
- `--pg-host`: Servidor PostgreSQL
- `--pg-db`: Nombre de la base de datos PostgreSQL
- `--pg-user`: Usuario PostgreSQL
- `--pg-password`: Contraseña PostgreSQL
- `--pg-port`: Puerto PostgreSQL (predeterminado: 5432)
- `--output-dir`: Directorio para archivos CSV intermedios (predeterminado: "./exported_data")
- `--tables`: Lista opcional de tablas específicas a migrar

### Ejemplos de Uso

**Migración completa de una base de datos:**

```bash
python migrate_mysql_to_postgresql.py \
  --mysql-host localhost \
  --mysql-db tienda_online \
  --mysql-user root \
  --mysql-password secreto123 \
  --pg-host localhost \
  --pg-db tienda_online \
  --pg-user postgres \
  --pg-password admin123
```

**Especificando puertos no predeterminados:**

```bash
python migrate_mysql_to_postgresql.py \
  --mysql-host localhost \
  --mysql-db tienda_online \
  --mysql-user root \
  --mysql-password secreto123 \
  --mysql-port 3307 \
  --pg-host localhost \
  --pg-db tienda_online \
  --pg-user postgres \
  --pg-password admin123 \
  --pg-port 5433
```

### Migración Selectiva de Tablas

Para migrar solo tablas específicas:

```bash
python migrate_mysql_to_postgresql.py \
  --mysql-host localhost \
  --mysql-db tienda_online \
  --mysql-user root \
  --mysql-password secreto123 \
  --pg-host localhost \
  --pg-db tienda_online \
  --pg-user postgres \
  --pg-password admin123 \
  --tables productos categorias usuarios pedidos
```

## Estructura del Código

### Funciones Principales

| Función | Descripción |
|---------|-------------|
| `connect_to_mysql` | Establece la conexión con la base de datos MySQL |
| `connect_to_postgresql` | Establece la conexión con la base de datos PostgreSQL |
| `get_tables` | Obtiene la lista de tablas de la base de datos MySQL |
| `get_table_schema` | Extrae el esquema de una tabla MySQL |
| `mysql_to_postgresql_type` | Convierte tipos de datos de MySQL a PostgreSQL |
| `create_postgresql_table` | Crea la estructura de tabla en PostgreSQL |
| `export_table_data` | Exporta datos de MySQL a CSV |
| `import_table_data` | Importa datos desde CSV a PostgreSQL |
| `get_primary_keys` | Obtiene información de claves primarias |
| `migrate_constraints` | Migra las restricciones de clave primaria |
| `get_foreign_keys` | Obtiene información de claves foráneas |
| `migrate_foreign_keys` | Migra las claves foráneas |
| `get_indexes` | Obtiene información de índices |
| `migrate_indexes` | Migra los índices |
| `reset_sequences` | Actualiza las secuencias para campos auto-incrementales |
| `generate_migration_report` | Genera el informe de migración |
| `main` | Función principal que coordina el proceso |

### Manejo de Errores

El script implementa manejo de errores en múltiples niveles:

- **Conexión a bases de datos**: Verifica y reporta errores de conexión
- **Creación de tablas**: Rollback en caso de error al crear tablas
- **Importación de datos**: Estrategia alternativa si el método principal falla
- **Migración de restricciones**: Continúa con advertencias si no puede migrar alguna restricción
- **Seguimiento de éxitos y fallos**: Registra tablas migradas exitosamente y las que fallaron

## Reporte de Migración

Al finalizar, el script genera un informe detallado que incluye:

- Fecha y hora de inicio y finalización
- Duración total de la migración
- Número de tablas procesadas
- Número de tablas migradas exitosamente
- Número y lista de tablas con errores
- Lista completa de tablas migradas

Este informe se muestra en la consola y también se guarda en un archivo llamado `migration_report.txt`.

## Limitaciones y Consideraciones

- **Tamaño de la base de datos**: Para bases de datos muy grandes, considere aumentar la memoria disponible para Python.
- **Tipo de datos específicos**: Algunos tipos de datos específicos de MySQL pueden no tener una conversión exacta.
- **Funciones y procedimientos almacenados**: El script no migra funciones, procedimientos almacenados, disparadores o vistas.
- **Codificación de caracteres**: Asegúrese de que ambas bases de datos utilizan codificaciones compatibles.
- **Permisos**: El usuario debe tener permisos de lectura en MySQL y permisos de escritura en PostgreSQL.
- **Espacio en disco**: Se requiere espacio adicional para los archivos CSV intermedios.

## Solución de Problemas

- **Error de conexión a MySQL**: Verifique credenciales, host y puerto. Asegúrese de que el usuario tenga permisos de lectura.
- **Error de conexión a PostgreSQL**: Verifique credenciales, host y puerto. Confirme que la base de datos existe.
- **Errores en la importación de datos**: Revise los archivos CSV generados para detectar caracteres problemáticos.
- **Problemas con claves foráneas**: Asegúrese de que todas las tablas relacionadas se están migrando en la sesión actual.
- **Secuencias no actualizadas**: Ejecute manualmente la función `reset_sequences()` para las tablas afectadas.
- **Tablas con errores**: Consulte los mensajes específicos en la consola para cada error y aborde cada uno individualmente.
