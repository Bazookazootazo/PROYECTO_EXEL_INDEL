import sqlite3
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, db_path="gestion_personal.db"):
        self.db_path = db_path

    @contextmanager
    def conectar(self):
        """Gestor de contexto para asegurar el cierre seguro de la conexión y cursor."""
        conexion = sqlite3.connect(self.db_path)
        conexion.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
        try:
            yield conexion
            conexion.commit()
        except Exception as e:
            conexion.rollback()
            raise e
        finally:
            conexion.close()

    def ejecutar_consulta(self, query, params=()):
        """Ejecuta consultas SELECT de forma segura."""
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def ejecutar_dml(self, query, params=()):
        """Ejecuta consultas INSERT, UPDATE o DELETE de forma segura."""
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.lastrowid