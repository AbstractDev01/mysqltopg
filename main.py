import psycopg2
import mysql.connector
import csv
import os
import argparse
from datetime import datetime

def connect_to_mysql(host, database, username, password, port=3306):
    """Conectar a la base de datos MySQL"""
    try:
        conn = mysql.connector.connect(
            host=host,
            database=database,
            user=username,
            password=password,
            port=port
        )
        print(f"Conexión exitosa a la base de datos MySQL: {database}")
        return conn
    except Exception as e:
        print(f"Error al conectar a MySQL: {e}")
        return None

def connect_to_postgresql(host, database, username, password, port=5432):
    """Conectar a la base de datos PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=username,
            password=password,
            port=port
        )
        print(f"Conexión exitosa a la base de datos PostgreSQL: {database}")
        return conn
    except Exception as e:
        print(f"Error al conectar a PostgreSQL: {e}")
        return None

def get_tables(mysql_conn):
    """Obtener todas las tablas de la base de datos MySQL"""
    cursor = mysql_conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables

def get_table_schema(mysql_conn, table_name):
    """Obtener el esquema de una tabla en MySQL"""
    cursor = mysql_conn.cursor()
    cursor.execute(f"""
    SELECT 
        COLUMN_NAME,
        DATA_TYPE,
        CHARACTER_MAXIMUM_LENGTH,
        IS_NULLABLE,
        COLUMN_DEFAULT
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = '{table_name}' AND TABLE_SCHEMA = DATABASE()
    ORDER BY ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    cursor.close()
    return columns

def mysql_to_postgresql_type(mysql_type, max_length=None):
    """Convertir tipo de dato de MySQL a PostgreSQL"""
    type_mapping = {
        'int': 'INTEGER',
        'tinyint': 'SMALLINT',
        'smallint': 'SMALLINT',
        'mediumint': 'INTEGER',
        'bigint': 'BIGINT',
        'float': 'REAL',
        'double': 'DOUBLE PRECISION',
        'decimal': 'DECIMAL',
        'numeric': 'NUMERIC',
        'date': 'DATE',
        'datetime': 'TIMESTAMP',
        'timestamp': 'TIMESTAMP',
        'time': 'TIME',
        'year': 'INTEGER',
        'char': f'CHAR({max_length})' if max_length else 'CHAR',
        'varchar': f'VARCHAR({max_length})' if max_length else 'VARCHAR',
        'binary': 'BYTEA',
        'varbinary': 'BYTEA',
        'tinyblob': 'BYTEA',
        'tinytext': 'TEXT',
        'blob': 'BYTEA',
        'text': 'TEXT',
        'mediumblob': 'BYTEA',
        'mediumtext': 'TEXT',
        'longblob': 'BYTEA',
        'longtext': 'TEXT',
        'enum': 'TEXT',
        'set': 'TEXT',
        'boolean': 'BOOLEAN',
        'bool': 'BOOLEAN',
        'json': 'JSONB',
    }
    
    
    if mysql_type.lower() == 'tinyint' and max_length == 1:
        return 'BOOLEAN'
    
    return type_mapping.get(mysql_type.lower(), 'TEXT')  

def create_postgresql_table(pg_conn, table_name, columns):
    """Crear tabla en PostgreSQL basada en el esquema de MySQL"""
    cursor = pg_conn.cursor()
    
    create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
    column_definitions = []
    
    for col in columns:
        column_name = col[0]
        data_type = mysql_to_postgresql_type(col[1], col[2])
        is_nullable = "NULL" if col[3] == 'YES' else "NOT NULL"
        default_value = f"DEFAULT {col[4]}" if col[4] else ""
        
        
        if default_value:
            default_value = default_value.replace("CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP")
            default_value = default_value.replace("NOW()", "CURRENT_TIMESTAMP")
        
        column_def = f"    {column_name} {data_type} {is_nullable} {default_value}".strip()
        column_definitions.append(column_def)
    
    create_table_sql += ",\n".join(column_definitions)
    create_table_sql += "\n);"
    
    try:
        cursor.execute(create_table_sql)
        pg_conn.commit()
        print(f"Tabla {table_name} creada exitosamente en PostgreSQL")
        return True
    except Exception as e:
        pg_conn.rollback()
        print(f"Error al crear la tabla {table_name}: {e}")
        print(f"SQL: {create_table_sql}")
        return False
    finally:
        cursor.close()

def export_table_data(mysql_conn, table_name, output_dir):
    """Exportar datos de la tabla de MySQL a un archivo CSV"""
    cursor = mysql_conn.cursor()
    
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = os.path.join(output_dir, f"{table_name}.csv")
    
    try:
        
        cursor.execute(f"SELECT * FROM {table_name}")
        
        
        columns = [column[0] for column in cursor.description]
        
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csv_file:
            csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(columns)  
            
            
            batch_size = 1000
            rows = cursor.fetchmany(batch_size)
            
            while rows:
                
                clean_rows = []
                for row in rows:
                    clean_row = []
                    for value in row:
                        if value is None:
                            clean_row.append(None)
                        elif isinstance(value, bytes):
                            clean_row.append(value.hex())  
                        else:
                            clean_row.append(value)
                    clean_rows.append(clean_row)
                
                csv_writer.writerows(clean_rows)
                rows = cursor.fetchmany(batch_size)
        
        print(f"Datos de la tabla {table_name} exportados exitosamente a {file_path}")
        return file_path
    except Exception as e:
        print(f"Error al exportar datos de la tabla {table_name}: {e}")
        return None
    finally:
        cursor.close()

def import_table_data(pg_conn, table_name, csv_file):
    """Importar datos del archivo CSV a la tabla de PostgreSQL"""
    cursor = pg_conn.cursor()
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            
            header = next(csv.reader([f.readline()]))
            columns = ', '.join(f'"{col}"' for col in header)  
            
            
            copy_sql = f'COPY "{table_name}" ({columns}) FROM STDIN WITH CSV HEADER DELIMITER \',\''
            
            
            f.seek(0)
            
            
            cursor.copy_expert(copy_sql, f)
            pg_conn.commit()
            
            
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            row_count = cursor.fetchone()[0]
            
            print(f"Importados {row_count} registros a la tabla {table_name} en PostgreSQL")
            return True
    except Exception as e:
        pg_conn.rollback()
        print(f"Error al importar datos a la tabla {table_name}: {e}")
        print("Intentando importar fila por fila...")
        
        try:
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)  
                placeholders = ', '.join(['%s'] * len(header))
                columns = ', '.join(f'"{col}"' for col in header)
                
                insert_query = f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders})'
                
                
                batch_size = 100
                batch = []
                count = 0
                
                for row in reader:
                    
                    processed_row = [None if val == '' else val for val in row]
                    batch.append(processed_row)
                    count += 1
                    
                    if len(batch) >= batch_size:
                        cursor.executemany(insert_query, batch)
                        pg_conn.commit()
                        batch = []
                
                
                if batch:
                    cursor.executemany(insert_query, batch)
                    pg_conn.commit()
                
                print(f"Importados {count} registros a la tabla {table_name} en PostgreSQL (método alternativo)")
                return True
        except Exception as inner_e:
            pg_conn.rollback()
            print(f"Error en método alternativo de importación: {inner_e}")
            return False
    finally:
        cursor.close()

def get_primary_keys(mysql_conn, table_name):
    """Obtener las claves primarias de una tabla en MySQL"""
    cursor = mysql_conn.cursor()
    cursor.execute(f"""
    SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = '{table_name}'
      AND CONSTRAINT_NAME = 'PRIMARY'
    ORDER BY ORDINAL_POSITION
    """)
    
    pk_columns = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return pk_columns

def migrate_constraints(mysql_conn, pg_conn, table_name):
    """Migrar las restricciones de clave primaria"""
    try:
        
        pk_columns = get_primary_keys(mysql_conn, table_name)
        
        
        if pk_columns:
            pg_cursor = pg_conn.cursor()
            pk_columns_str = ', '.join(f'"{col}"' for col in pk_columns)
            pk_name = f"pk_{table_name}"
            pk_sql = f'ALTER TABLE "{table_name}" ADD CONSTRAINT {pk_name} PRIMARY KEY ({pk_columns_str})'
            
            try:
                pg_cursor.execute(pk_sql)
                pg_conn.commit()
                print(f"Clave primaria creada para la tabla {table_name}")
            except Exception as e:
                pg_conn.rollback()
                print(f"Error al crear clave primaria para la tabla {table_name}: {e}")
            finally:
                pg_cursor.close()
        
        return True
    except Exception as e:
        print(f"Error al migrar restricciones para la tabla {table_name}: {e}")
        return False

def get_foreign_keys(mysql_conn, database):
    """Obtener todas las claves foráneas de la base de datos MySQL"""
    cursor = mysql_conn.cursor()
    cursor.execute(f"""
    SELECT
        TABLE_NAME,
        COLUMN_NAME,
        CONSTRAINT_NAME,
        REFERENCED_TABLE_NAME,
        REFERENCED_COLUMN_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE REFERENCED_TABLE_SCHEMA = '{database}'
      AND REFERENCED_TABLE_NAME IS NOT NULL
    ORDER BY TABLE_NAME, CONSTRAINT_NAME
    """)
    
    result = cursor.fetchall()
    cursor.close()
    
    
    foreign_keys = {}
    for row in result:
        table_name, column_name, constraint_name, ref_table_name, ref_column_name = row
        
        if constraint_name not in foreign_keys:
            foreign_keys[constraint_name] = {
                'table_name': table_name,
                'columns': [],
                'ref_table_name': ref_table_name,
                'ref_columns': []
            }
        
        foreign_keys[constraint_name]['columns'].append(column_name)
        foreign_keys[constraint_name]['ref_columns'].append(ref_column_name)
    
    return foreign_keys

def migrate_foreign_keys(mysql_conn, pg_conn, database_name):
    """Migrar todas las claves foráneas después de que todas las tablas estén creadas"""
    try:
        
        foreign_keys = get_foreign_keys(mysql_conn, database_name)
        
        
        pg_cursor = pg_conn.cursor()
        
        for fk_name, fk_info in foreign_keys.items():
            table_name = fk_info['table_name']
            columns = ', '.join(f'"{col}"' for col in fk_info['columns'])
            ref_table_name = fk_info['ref_table_name']
            ref_columns = ', '.join(f'"{col}"' for col in fk_info['ref_columns'])
            
            
            pg_fk_name = f"fk_{table_name}_{ref_table_name}_{fk_name[-10:]}"
            
            fk_sql = f"""
            ALTER TABLE "{table_name}"
            ADD CONSTRAINT {pg_fk_name} FOREIGN KEY ({columns})
            REFERENCES "{ref_table_name}" ({ref_columns})
            """
            
            try:
                pg_cursor.execute(fk_sql)
                pg_conn.commit()
                print(f"Clave foránea {pg_fk_name} creada exitosamente")
            except Exception as e:
                pg_conn.rollback()
                print(f"Error al crear clave foránea {pg_fk_name}: {e}")
        
        pg_cursor.close()
        return True
    except Exception as e:
        print(f"Error al migrar claves foráneas: {e}")
        return False

def get_indexes(mysql_conn, table_name):
    """Obtener los índices de una tabla en MySQL que no son claves primarias"""
    cursor = mysql_conn.cursor()
    cursor.execute(f"""
    SELECT
        INDEX_NAME,
        COLUMN_NAME,
        NON_UNIQUE
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = '{table_name}'
      AND INDEX_NAME != 'PRIMARY'
    ORDER BY INDEX_NAME, SEQ_IN_INDEX
    """)
    
    result = cursor.fetchall()
    cursor.close()
    
    
    indexes = {}
    for row in result:
        index_name, column_name, non_unique = row
        
        if index_name not in indexes:
            indexes[index_name] = {
                'columns': [],
                'is_unique': not bool(non_unique)
            }
        
        indexes[index_name]['columns'].append(column_name)
    
    return indexes

def migrate_indexes(mysql_conn, pg_conn, table_name):
    """Migrar índices no relacionados con claves primarias"""
    try:
        
        indexes = get_indexes(mysql_conn, table_name)
        
        
        pg_cursor = pg_conn.cursor()
        
        for index_name, index_info in indexes.items():
            columns = ', '.join(f'"{col}"' for col in index_info['columns'])
            unique = "UNIQUE" if index_info['is_unique'] else ""
            
            
            pg_index_name = f"idx_{table_name}_{index_name}"
            
            idx_sql = f"""
            CREATE {unique} INDEX {pg_index_name} ON "{table_name}" ({columns})
            """
            
            try:
                pg_cursor.execute(idx_sql)
                pg_conn.commit()
                print(f"Índice {pg_index_name} creado exitosamente")
            except Exception as e:
                pg_conn.rollback()
                print(f"Error al crear índice {pg_index_name}: {e}")
        
        pg_cursor.close()
        return True
    except Exception as e:
        print(f"Error al migrar índices para la tabla {table_name}: {e}")
        return False

def reset_sequences(pg_conn, table_name):
    """Resetear las secuencias de PostgreSQL para columnas auto-incrementales"""
    try:
        cursor = pg_conn.cursor()
        
        
        cursor.execute(f"""
        SELECT column_name, column_default 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}' 
        AND column_default LIKE 'nextval%'
        """)
        
        for row in cursor.fetchall():
            column_name = row[0]
            sequence_info = row[1]
            
            
            
            sequence_parts = sequence_info.split("'")
            if len(sequence_parts) >= 2:
                sequence_name = sequence_parts[1]
                
                
                update_seq_sql = f"""
                SELECT setval('{sequence_name}', 
                  (SELECT COALESCE(MAX("{column_name}"), 1) FROM "{table_name}"), 
                  (SELECT MAX("{column_name}") IS NOT NULL FROM "{table_name}"))
                """
                
                cursor.execute(update_seq_sql)
                pg_conn.commit()
                print(f"Secuencia actualizada para la columna {column_name} en la tabla {table_name}")
        
        cursor.close()
        return True
    except Exception as e:
        print(f"Error al resetear secuencias para la tabla {table_name}: {e}")
        return False

def generate_migration_report(tables, success_tables, failed_tables, start_time):
    """Generar un informe de migración"""
    end_time = datetime.now()
    duration = end_time - start_time
    
    report = f"""
    Fecha y hora de inicio: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
    Fecha y hora de finalización: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
    Duración total: {duration}
    
    Tablas procesadas: {len(tables)}
    Tablas migradas exitosamente: {len(success_tables)}
    Tablas con errores: {len(failed_tables)}
    
    Tablas migradas:
    """
    
    for table in success_tables:
        report += f"    - {table}\n"
    
    if failed_tables:
        report += "\n    Tablas con errores:\n"
        for table in failed_tables:
            report += f"    - {table}\n"
    
    print(report)
    
    
    with open('migration_report.txt', 'w') as f:
        f.write(report)
    
    print("Informe de migración guardado en 'migration_report.txt'")

def main():
    parser = argparse.ArgumentParser(description="Migrar base de datos de MySQL a PostgreSQL")
    
    
    parser.add_argument("--mysql-host", required=True, help="Host MySQL")
    parser.add_argument("--mysql-db", required=True, help="Nombre de la base de datos MySQL")
    parser.add_argument("--mysql-user", required=True, help="Usuario MySQL")
    parser.add_argument("--mysql-password", required=True, help="Contraseña MySQL")
    parser.add_argument("--mysql-port", default=3306, type=int, help="Puerto MySQL (default: 3306)")
    
    
    parser.add_argument("--pg-host", required=True, help="Host PostgreSQL")
    parser.add_argument("--pg-db", required=True, help="Nombre de la base de datos PostgreSQL")
    parser.add_argument("--pg-user", required=True, help="Usuario PostgreSQL")
    parser.add_argument("--pg-password", required=True, help="Contraseña PostgreSQL")
    parser.add_argument("--pg-port", default=5432, type=int, help="Puerto PostgreSQL (default: 5432)")
    
    
    parser.add_argument("--output-dir", default="./exported_data", help="Directorio para archivos CSV exportados")
    parser.add_argument("--tables", nargs="+", help="Lista específica de tablas a migrar (opcional)")
    
    args = parser.parse_args()
    
    start_time = datetime.now()
    print(f"Iniciando migración: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    
    mysql_conn = connect_to_mysql(args.mysql_host, args.mysql_db, args.mysql_user, args.mysql_password, args.mysql_port)
    pg_conn = connect_to_postgresql(args.pg_host, args.pg_db, args.pg_user, args.pg_password, args.pg_port)
    
    if not mysql_conn or not pg_conn:
        print("No se pudo establecer conexión con una o ambas bases de datos. Abortando.")
        return
    
    
    tables = args.tables if args.tables else get_tables(mysql_conn)
    print(f"Se encontraron {len(tables)} tablas para migrar")
    
    success_tables = []
    failed_tables = []
    
    
    for table_name in tables:
        print(f"\nProcesando tabla: {table_name}")
        
        
        columns = get_table_schema(mysql_conn, table_name)
        
        
        if not create_postgresql_table(pg_conn, table_name, columns):
            failed_tables.append(table_name)
            continue
        
        
        csv_file = export_table_data(mysql_conn, table_name, args.output_dir)
        if not csv_file:
            failed_tables.append(table_name)
            continue
        
        
        if not import_table_data(pg_conn, table_name, csv_file):
            failed_tables.append(table_name)
            continue
        
        
        if not migrate_constraints(mysql_conn, pg_conn, table_name):
            print(f"Advertencia: No se pudieron migrar todas las restricciones para la tabla {table_name}")
        
        
        if not migrate_indexes(mysql_conn, pg_conn, table_name):
            print(f"Advertencia: No se pudieron migrar todos los índices para la tabla {table_name}")
        
        
        reset_sequences(pg_conn, table_name)
        
        success_tables.append(table_name)
    
    
    print("\nMigrando claves foráneas...")
    migrate_foreign_keys(mysql_conn, pg_conn, args.mysql_db)
    
    
    generate_migration_report(tables, success_tables, failed_tables, start_time)
    
    
    mysql_conn.close()
    pg_conn.close()
    
    print("\nMigración completada.")

if __name__ == "__main__":
    main()
