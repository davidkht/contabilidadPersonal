import sqlite3
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def get_resource_path():
    """ Retorna la ruta absoluta al recurso, para uso en desarrollo o en el ejecutable empaquetado. """
    if getattr(sys, 'frozen', False):
        # Si el programa ha sido empaquetado, el directorio base es el que PyInstaller proporciona
        base_path = sys._MEIPASS
    else:
        # Si estamos en desarrollo, utiliza la ubicación del script
        base_path = os.path.dirname(os.path.realpath(__file__))

    return base_path

# Guarda la ruta del script para su uso posterior en la aplicación
script_directory = get_resource_path()

# Conexión a la base de datos SQLite
database = os.path.join(script_directory,'..','databases','deudas.db')



# database = r"C:\Users\K\Documents\Proyectos\contabilidad\databases\deudas.db"
with sqlite3.connect(database) as conn:
    c = conn.cursor()
    # Crear tabla
    c.execute('''
    CREATE TABLE IF NOT EXISTS Deudas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL COLLATE NOCASE,
        apellido TEXT NOT NULL COLLATE NOCASE,
        telefono TEXT,
        email TEXT,
        monto REAL NOT NULL,
        interes REAL DEFAULT 0,
        fecha DATE NOT NULL,
        descripcion TEXT,
        UNIQUE(nombre, apellido)
    )
    ''')
    conn.commit()

# Funciones para manejar las deudas
def registrar_persona(nombre, apellido, telefono, email, monto, interes=0, descripcion=''):
    fecha = datetime.now().strftime('%Y-%m-%d')
    try:
        with sqlite3.connect(database) as conn:
            c = conn.cursor()
            c.execute('''
            INSERT INTO Deudas (nombre, apellido, telefono, email, monto, interes, fecha, descripcion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, apellido, telefono, email, monto, interes, fecha, descripcion))
            conn.commit()

        # Crear tabla individual para la persona
        crear_tabla_persona(nombre, apellido)
        
        # Insertar la deuda en la tabla individual
        table_name = f"{nombre}_{apellido}".replace(' ', '_')
        with sqlite3.connect(database) as conn:
            c = conn.cursor()
            c.execute(f'''
            INSERT INTO {table_name} (deuda_total, transaccion, fecha, descripcion)
            VALUES (?, ?, ?, ?)
            ''', (monto, monto, fecha, descripcion))
            conn.commit()
    except sqlite3.IntegrityError:
        print("Error")
        raise PermissionError      

def crear_tabla_persona(nombre, apellido):
    table_name = f"{nombre}_{apellido}".replace(' ', '_')
    with sqlite3.connect(database) as conn:
        c = conn.cursor()
        c.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deuda_total REAL NOT NULL,
            transaccion REAL NOT NULL,
            fecha DATE NOT NULL,
            descripcion TEXT
        )
        ''')
        conn.commit()

def actualizar_deuda(nombre, apellido, deuda_total, transaccion, descripcion=''):
    fecha = datetime.now().strftime('%Y-%m-%d')
    with sqlite3.connect(database) as conn:
        c = conn.cursor()
        c.execute('''
        UPDATE Deudas
        SET monto = monto + ?
        WHERE nombre = ? AND apellido = ?
        ''', (transaccion, nombre, apellido))
        conn.commit()
    
    table_name = f"{nombre}_{apellido}".replace(' ', '_')
    with sqlite3.connect(database) as conn:
        c = conn.cursor()
        c.execute(f'''
        INSERT INTO {table_name} (deuda_total, transaccion, fecha, descripcion)
        VALUES (?, ?, ?, ?)
        ''', (deuda_total, transaccion, fecha, descripcion))
        conn.commit()

def editar_registro(nombre, apellido,telefono,email):
    with sqlite3.connect(database) as conn:
        c = conn.cursor()
        c.execute("""
                  UPDATE deudas 
                  SET telefono=?, email=? 
                  WHERE nombre=? AND apellido=?""", (telefono,email,nombre, apellido))
        conn.commit()

def consultar_deudas():
    with sqlite3.connect(database) as conn:
        query = '''
        SELECT id, nombre, apellido, telefono, email, monto, interes, fecha 
        FROM Deudas
        '''
        df = pd.read_sql(query, conn)
    return df

def consultar_tabla_persona(nombre, apellido):
    table_name = f"{nombre}_{apellido}".replace(' ', '_')
    with sqlite3.connect(database) as conn:
        df = pd.read_sql(f'SELECT * FROM {table_name}', conn)
    return df

def borrar_usuario(nombre, apellido, permiso=True):
    if permiso:
        with sqlite3.connect(database) as conn:
            c = conn.cursor()
            c.execute('''
            DELETE FROM Deudas
            WHERE nombre = ? AND apellido = ?
            ''', (nombre, apellido))
            conn.commit()
        
        # Borrar la tabla individual de la persona
        table_name = f"{nombre}_{apellido}".replace(' ', '_')
        with sqlite3.connect(database) as conn:
            c = conn.cursor()
            c.execute(f'DROP TABLE IF EXISTS {table_name}')
            conn.commit()

def exportar_datos_a_csv(tabla,nombre=None,apellido=None,filename='deudas_exportadas.csv'):
    if tabla== 'Deudas':
        df = consultar_deudas()
    elif tabla== 'Usuario':
        df = consultar_tabla_persona(nombre, apellido)
    else:
        raise TypeError
    df.to_csv(filename, index=False)
    return filename

def generar_grafica(nombre, apellido, output_path='historial_movimientos.png'):
    df_movimientos=consultar_tabla_persona(nombre,apellido)

    # Crear un gráfico de barras con matplotlib
    fig, ax = plt.subplots(figsize=(6,4))
    

    # Crear las barras para cada movimiento individualmente
    ax.bar(df_movimientos['id'], df_movimientos['transaccion'], color='blue')
    # Etiquetas y título del gráfico
    ax.set_xlabel('N°')
    ax.set_ylabel('Monto')
    ax.set_title('Historial de Movimientos')

    # Añadir una cuadrícula al gráfico
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Configurar los ticks del eje y para mostrar más valores
    ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=10, prune='lower'))
    ax.yaxis.set_minor_locator(plt.MaxNLocator(nbins=20))

    # Guardar la gráfica como una imagen
    plt.savefig(output_path)
    plt.close(fig)

def verificar_y_calcular_intereses():
    with sqlite3.connect(database) as conn:
        c = conn.cursor()
        c.execute('SELECT nombre, apellido, monto, interes FROM Deudas WHERE interes > 0')
        deudas = c.fetchall()

        for deuda in deudas:
            nombre, apellido, monto, interes = deuda
            table_name = f"{nombre}_{apellido}".replace(' ', '_')

            # Obtener el último movimiento de la persona
            c.execute(f'SELECT fecha, deuda_total FROM {table_name} ORDER BY fecha DESC LIMIT 1')
            ultimo_movimiento = c.fetchone()
            if ultimo_movimiento:
                fecha_ultimo_movimiento, deuda_total = ultimo_movimiento
                fecha_ultimo_movimiento = datetime.strptime(fecha_ultimo_movimiento, '%Y-%m-%d')
                fecha_actual = datetime.now()

                # Verificar si ha pasado más de un mes desde el último movimiento
                if (fecha_actual - fecha_ultimo_movimiento).days >= 30:
                    meses = (fecha_actual.year - fecha_ultimo_movimiento.year) * 12 + fecha_actual.month - fecha_ultimo_movimiento.month
                    if meses > 0:
                        interes_calculado = deuda_total * interes * meses
                        actualizar_deuda(nombre, apellido, deuda_total + interes_calculado, interes_calculado, descripcion=f'Interés acumulado')


