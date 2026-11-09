import sqlite3
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import os
import sys



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

with sqlite3.connect(database) as conn:
    c = conn.cursor()
    # Crear tabla - Create the main Deudas table with person information
    c.execute('''
    CREATE TABLE IF NOT EXISTS Deudas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL COLLATE NOCASE,
        apellido TEXT NOT NULL COLLATE NOCASE,
        documento TEXT,
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

# Funciones para manejar las deudas - Functions to handle debt operations
def registrar_persona(nombre, apellido, telefono, email, monto, interes=0, descripcion='', documento=''):
    """
    Registers a new person in the database with their debt information.
    
    Args:
        nombre (str): First name of the person
        apellido (str): Last name of the person
        telefono (str): Phone number
        email (str): Email address
        monto (float): Initial debt amount
        interes (float): Interest rate (default 0)
        descripcion (str): Description of the debt
        documento (str): ID document number (DNI, passport, etc.)
    
    Raises:
        PermissionError: If a person with the same nombre and apellido already exists
    """
    fecha = datetime.now().strftime('%Y-%m-%d')
    try:
        with sqlite3.connect(database) as conn:
            c = conn.cursor()
            c.execute('''
            INSERT INTO Deudas (nombre, apellido, documento, telefono, email, monto, interes, fecha, descripcion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, apellido, documento, telefono, email, monto, interes, fecha, descripcion))
            conn.commit()

        # Crear tabla individual para la persona - Create individual table for the person
        crear_tabla_persona(nombre, apellido)
        
        # Insertar la deuda en la tabla individual - Insert the debt in the individual table
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

def editar_registro(nombre, apellido, telefono, email, documento=''):
    """
    Updates an existing person's information in the database (UPSERT operation).
    
    Args:
        nombre (str): First name of the person
        apellido (str): Last name of the person
        telefono (str): Phone number
        email (str): Email address
        documento (str): ID document number (DNI, passport, etc.)
    
    This function updates the telefono, email, and documento fields for an existing person.
    """
    with sqlite3.connect(database) as conn:
        c = conn.cursor()
        c.execute("""
                  UPDATE Deudas 
                  SET telefono=?, email=?, documento=? 
                  WHERE nombre=? AND apellido=?""", (telefono, email, documento, nombre, apellido))
        conn.commit()

def consultar_deudas():
    """
    Retrieves all debts from the database.
    
    Returns:
        pandas.DataFrame: A DataFrame containing all person records with their debt information
    """
    with sqlite3.connect(database) as conn:
        query = '''
        SELECT id, nombre, apellido, documento, telefono, email, monto, interes, fecha 
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
    """
    Generates a line plot showing the total debt over the number of entries for a specific person.

    This function fetches the transaction history for a person, then plots their
    total debt against the transaction number (ID). The resulting plot is saved
    to an image file.

    Args:
        nombre (str): The first name of the person.
        apellido (str): The last name of the person.
        output_path (str, optional): The path to save the output image file. 
                                     Defaults to 'historial_movimientos.png'.
    """
    df_movimientos = consultar_tabla_persona(nombre, apellido)

    # Sort the DataFrame by 'id' to ensure the line plot connects points in order of entry.
    df_movimientos = df_movimientos.sort_values(by='id')

    # Create a figure and an axes for the plot with a specific size.
    fig, ax = plt.subplots(figsize=(6, 4))
    
    # Plot the total debt ('deuda_total') against the transaction ID ('id').
    # A marker is used for each data point and a solid line connects them.
    ax.plot(
        df_movimientos['id'], 
        df_movimientos['deuda_total'], 
        marker='s', 
        linestyle='-', 
        color='red',
        linewidth=1,
        markerfacecolor='red',
        markersize=1.5,
        markeredgecolor='black',
        markeredgewidth=0.2
    )
    
    #Set the background color to grey
    ax.set_facecolor('lightgrey')
  
    # Set the labels for the x and y axes.
    ax.set_xlabel('Transaction Number')
    ax.set_ylabel('Total Debt')
    # Set the title of the plot.
    ax.set_title('Debt History')
  
    # Add horizontal and vertical lines at the origin (0,0) to serve as a reference grid.
    ax.axhline(0, color='black', linestyle='-', linewidth=0.5)
    ax.axvline(0, color='black', linestyle='-', linewidth=0.5)

    # Format the y-axis labels to appear as currency, preventing scientific notation.
    # This uses a FuncFormatter to apply a lambda function that formats the tick values.
    # The format string '${x:,.0f}' means:
    # - Start with a '$' sign.
    # - Use a comma as a thousands separator.
    # - Display the number with 0 decimal places (as an integer).
    formatter = mticker.FuncFormatter(lambda x, p: f'${x:,.0f}')
    ax.yaxis.set_major_formatter(formatter)

    # Configure the y-axis to have a reasonable number of ticks.
    # 'prune='lower'' can remove the lowest tick if it's too close to the edge.
    ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=10, prune='lower'))
    ax.yaxis.set_minor_locator(plt.MaxNLocator(nbins=20))

    # Ensure the x-axis ticks are integers.
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))

    # Adjust layout to make sure everything fits, preventing labels from being cut off.
    plt.tight_layout()

    # Save the generated plot to the specified image file.
    plt.savefig(output_path)
    # Close the figure to free up memory.
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


