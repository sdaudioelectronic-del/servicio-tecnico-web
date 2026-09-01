import sqlite3

conexion = sqlite3.connect("servicio.db")

conexion.execute("""
    ALTER TABLE ordenes
    ADD COLUMN codigo TEXT
""")

conexion.commit()
conexion.close()

print("Base de datos actualizada correctamente.")