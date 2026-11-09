import os
import main
from main import script_directory
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

class App(tk.Tk):

    def __init__(self, title):
        """
        Initializes the main application window.
        
        Args:
            title (str): The window title
        """
        super().__init__()
        self.title(title)
        
        # Window geometry configurations - optimized to fit content without wasted space
        self.home_geometry=[1120, 550]  # Compact but wide enough for the table + right panel
        self.mov_geometry=[1150, 550]   # Slightly wider for the movement view
        self.default_width = self.home_geometry[0]
        self.extended_width = self.home_geometry[0] + 450 # Add just enough space for the side form
        self.height = self.home_geometry[1]

        # Configure global grid weights for responsiveness
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.icono_e_imagen()  # Method to set the application icon

        self.current_frame = None  # Initially no frame is visible
        
        self.place_widgets()

        # Check and calculate interest for debts with interest rates
        main.verificar_y_calcular_intereses()

        self.show_home()  # Show the first frame

        # Handle the window close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        #Run the app
        self.mainloop()  # Start the main event loop of the application

    def place_widgets(self):
        """
        Places the main navigation widgets (like the home button) in the window.
        """
        self.home_button=ttk.Button(self, text=" 🏠 Inicio", image=self.mi_imagen, command=self.show_home, width=15)
        self.home_button.grid(row=0, column=0, sticky='w', padx=(15,15), pady=(15,10))

    def place_tree(self):
        """
        Creates and configures the main TreeView widget that displays all debt records.
        The tree shows a table with person information and their current debt status.
        """
        self.tree=ttk.Treeview(self.tree_frame,height=18)
        self.tree.grid(row=0,column=0,sticky='nsew',padx=(10,10),pady=(10,10))
        # Clear any previous entries in the TreeView to avoid duplications or stale data.
        for i in self.tree.get_children():
            self.tree.delete(i) 

        df=main.consultar_deudas()
        # Add and configure columns in the TreeView based on the DataFrame columns.
        columns = list(df.columns)
        self.tree["show"] = "headings"
        self.tree['columns'] = columns
        for col in columns:
            self.tree.heading(col, text=col.upper())  # Display column headers in uppercase for better aesthetics
            self.tree.column(col, width=100, anchor='center')

        # Specific adjustments for certain columns, setting custom widths for better visibility.
        self.tree.column('id', width=30)
        self.tree.column('nombre', width=85)
        self.tree.column('apellido', width=85)
        self.tree.column('documento', width=95)
        self.tree.column('telefono', width=85)
        self.tree.column('email', width=140)
        self.tree.column('monto', width=100)
        self.tree.column('interes', width=60)
        self.tree.column('fecha', width=90)

        # Insert DataFrame data into the TreeView row by row.
        for index, row in df.iterrows():
            # Format the 'monto' value as currency
            row['monto'] = f"${float(row['monto']):,.2f}"
            self.tree.insert("", tk.END, values=list(row))

        # Add a scrollbar for the TreeView
        scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0,column=1,sticky='ns')

    def icono_e_imagen(self):
        # Obtén el directorio del script
        icon_path = os.path.join(script_directory, '..', 'docs', 'icono.svg')
        
        # Verifica si el archivo existe
        if not os.path.exists(icon_path):
            print(f"El archivo {icon_path} no existe.")
            return
        try:
            # Establece el ícono de la ventana
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error al establecer el ícono: {e}")


    def on_button_click(self):
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item)
            values = item['values']
            self.create_mov_frame(values)

        else:
            messagebox.showerror("Error", "No se ha seleccionado ningún elemento.")

    def mostrar_detalles(self):
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item)
            values = item['values']
            self.create_detalles_frame(values)
        else:
            messagebox.showerror("Error", "No se ha seleccionado ningún elemento.")

    def show_home(self):
        """
        Displays the home screen with the main debt table and action buttons.
        """
        #Logic to clear previous frame
        if self.current_frame:
            self.current_frame.grid_forget()
            self.current_frame.destroy()
            self.current_frame = None

        self.current_frame = HomeFrame(self)
        self.current_frame.grid(row=1, column=0, sticky='nsew')

        #Widgets
        ##Frame for tree - Main debt list display
        self.tree_frame=ttk.LabelFrame(self.current_frame, text="📊 Lista de Deudas", padding=(5, 5))
        self.tree_frame.grid(row=0, column=0, padx=(15,10), pady=(15,15), sticky='nsew')
        self.place_tree()

        # Right panel with action buttons
        self.right_frame=RightFrame(self.current_frame)
        self.right_frame.grid(row=0, column=1, padx=(10,15), pady=(15,15), sticky='nsew')
      
        self.geometry(f"{self.home_geometry[0]}x{self.home_geometry[1]}")

    def create_extra_frame(self,parametro,values=None):
        if parametro=="Nuevo":
            self.extra_frame = RegistroFrame(self.current_frame)
            self.extra_frame.grid(row=0,column=3,padx=10,pady=10, sticky='nsew')
            self.geometry(f"{self.extended_width}x{self.height}")
        elif parametro == "Editar":
            self.extra_frame = EditarFrame(self.current_frame,values)
            self.extra_frame.grid(row=0,column=3,padx=10,pady=10, sticky='nsew')
            self.geometry(f"{self.extended_width}x{self.height}")

    def create_mov_frame(self,values):
        """
        Cambia el frame visible en la ventana principal a uno especificado.

        """
        if self.current_frame:
            self.current_frame.grid_forget()
            self.current_frame.destroy()
            self.current_frame = None

        self.current_frame = MovimientoFrame(self,values)
        self.current_frame.grid(row=1, column=0, sticky='nsew')
        self.geometry(f"{self.mov_geometry[0]}x{self.mov_geometry[1]}")

    def create_detalles_frame(self, values):
        """
        Creates and displays the detailed view frame for a selected person.
        Shows transaction history, graph visualization, and action buttons.
        """
        if self.current_frame:
            self.current_frame.grid_forget()
            self.current_frame.destroy()
            self.current_frame = None

        self.current_frame = DetallesFrame(self, values)
        self.current_frame.grid(row=1, column=0, sticky='nsew')
        # Ensure the window is large enough for the detailed view
        self.geometry(f"{self.home_geometry[0]}x{self.home_geometry[1]}")

    def borrar_registro(self):
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item)
            values = item['values']
            verificacion=messagebox.askyesno("Borrar Registro?","Está seguro de borrar el registro?")
            if verificacion:
                main.borrar_usuario(values[1],values[2])
                self.place_tree()
        else:
            messagebox.showerror("Error", "No se ha seleccionado ningún elemento.")    
           
    def on_closing(self):
        """ Manejar el evento de cierre de la ventana """
        if messagebox.askokcancel("Salir", "¿Seguro que quieres salir?"):
            self.destroy()
            self.quit()

    def editar(self):
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item)
            values = item['values']
            self.create_extra_frame("Editar",values)
            self.right_frame.registrar_boton['state'] = 'disabled'
            self.right_frame.delete_boton['state'] = 'disabled'
            self.right_frame.movimiento_boton['state'] = 'disabled'
            self.right_frame.consultar_boton['state'] = 'disabled'
            self.right_frame.editar_boton['state'] = 'disabled'
            self.right_frame.exportar_boton['state'] = 'disabled'

        else:
            messagebox.showerror("Error", "No se ha seleccionado ningún elemento.")

class RightFrame(ttk.Frame):
    """
    Right panel containing action buttons for managing debt records.
    Separated into management actions (create/delete) and operational actions (edit/view/export).
    """
    def __init__(self,parent):
        super().__init__(parent) 

        # Top frame for record management actions
        self.top_frame=ttk.LabelFrame(self, text='📋 Gestión de Registro', padding=(10, 10))
        self.top_frame.grid(row=0, column=0, padx=(10,10), pady=(10,5), sticky='ew')

        # Bottom frame for available actions on records
        self.bottom_frame=ttk.LabelFrame(self, text='⚡ Acciones Disponibles', padding=(10, 10))
        self.bottom_frame.grid(row=1, column=0, padx=(10,10), pady=(5,10), sticky='ew')

        self.buttons(parent)

    def buttons(self,parent):
        """
        Creates all action buttons with improved styling and consistent sizing.
        """
        button_width = 22  # Consistent button width for better aesthetics

        #Top Frame - Record Management
        self.registrar_boton=ttk.Button(self.top_frame, text='➕ Nuevo Registro', width=button_width, 
                                   command=lambda p="Nuevo": self.master.extra_frame(p)) 
        self.registrar_boton.grid(row=0, column=0, padx=(12,12), pady=(10,8), sticky='ew')

        self.delete_boton=ttk.Button(self.top_frame, text='🗑️ Borrar Registro', width=button_width, 
                                command=self.master.borrar_registro)
        self.delete_boton.grid(row=1, column=0, padx=(12,12), pady=(8,10), sticky='ew')

        #Bottom Frame - Operational Actions
        self.editar_boton=ttk.Button(self.bottom_frame, text='✏️ Editar Persona', width=button_width, command=parent.editar)
        self.editar_boton.grid(row=0, column=0, padx=(12,12), pady=(10,8), sticky='ew')

        self.movimiento_boton=ttk.Button(self.bottom_frame, text='💰 Registrar Movimiento', width=button_width,
                                    command=parent.on_button_click)
        self.movimiento_boton.grid(row=1, column=0, padx=(12,12), pady=(8,8), sticky='ew')

        self.consultar_boton=ttk.Button(self.bottom_frame, text='📊 Consultar Detalles', width=button_width, command=parent.mostrar_detalles)
        self.consultar_boton.grid(row=2, column=0, padx=(12,12), pady=(8,8), sticky='ew')

        self.exportar_boton = ttk.Button(self.bottom_frame, text='📁 Exportar Datos', width=button_width, command=self.exportar_datos)
        self.exportar_boton.grid(row=3, column=0, padx=(12,12), pady=(8,10), sticky='ew')

    def exportar_datos(self):
        # Abrir el diálogo para guardar archivo
        filename='deudas_exportadas.csv'
        ruta=os.path.join(script_directory,'..','..','exports',filename)

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=filename,
            initialdir=ruta,
            title="Guardar archivo como"
        )
        
        # Si el usuario proporciona un archivo, exportar los datos
        if file_path:
            main.exportar_datos_a_csv("Deudas",filename=file_path)
            messagebox.showinfo("Exportación Exitosa", f"Datos exportados a {file_path}")

class RegistroFrame(ttk.Frame):

    def __init__(self,parent):
        super().__init__(parent)
        self.widgets()

    def widgets(self):
        """
        Creates all input widgets for the new person registration form.
        Includes fields for personal information, debt amount, and interest rate.
        """
        #LabelFrame container for the registration form
        registro_frame=ttk.LabelFrame(self, text="Nuevo registro", padding=(15, 15))
        registro_frame.grid(row=0, column=0, padx=(10,10), pady=(10,10))

        #Text variables to store input values
        self.nombre_var=tk.StringVar()
        self.apellido_var=tk.StringVar()
        self.documento_var=tk.StringVar()
        self.tel_var=tk.StringVar()
        self.email_var=tk.StringVar()
        self.monto_var=tk.StringVar()
        self.interes_var=tk.StringVar()

        # Input fields with improved layout and spacing
        # Row 0: Nombre and Apellido
        ttk.Label(registro_frame, text="Nombre:").grid(row=0, column=0, padx=(10,5), pady=(15,10), sticky='e')
        entry_nombre = ttk.Entry(registro_frame, width=25, textvariable=self.nombre_var)
        entry_nombre.grid(row=0, column=1, padx=(5,15), pady=(15,10), sticky='w')

        ttk.Label(registro_frame, text="Apellido:").grid(row=0, column=2, padx=(10,5), pady=(15,10), sticky='e')
        entry_apellido = ttk.Entry(registro_frame, width=25, textvariable=self.apellido_var)
        entry_apellido.grid(row=0, column=3, padx=(5,15), pady=(15,10), sticky='w')

        # Row 1: Documento ID
        ttk.Label(registro_frame, text="Documento ID:").grid(row=1, column=0, padx=(10,5), pady=(10,10), sticky='e')
        entry_documento = ttk.Entry(registro_frame, width=25, textvariable=self.documento_var)
        entry_documento.grid(row=1, column=1, padx=(5,15), pady=(10,10), sticky='w')

        # Row 1 continued: Teléfono
        ttk.Label(registro_frame, text="Teléfono:").grid(row=1, column=2, padx=(10,5), pady=(10,10), sticky='e')
        entry_telefono = ttk.Entry(registro_frame, width=25, textvariable=self.tel_var)
        entry_telefono.grid(row=1, column=3, padx=(5,15), pady=(10,10), sticky='w')

        # Row 2: Email
        ttk.Label(registro_frame, text="Email:").grid(row=2, column=0, padx=(10,5), pady=(10,10), sticky='e')
        entry_email = ttk.Entry(registro_frame, width=25, textvariable=self.email_var)
        entry_email.grid(row=2, column=1, padx=(5,15), pady=(10,10), sticky='w')

        # Row 2 continued: Monto adeudado
        ttk.Label(registro_frame, text="Monto adeudado:").grid(row=2, column=2, padx=(10,5), pady=(10,10), sticky='e')
        entry_monto = NumericEntry(registro_frame, width=25, textvariable=self.monto_var)
        entry_monto.grid(row=2, column=3, padx=(5,15), pady=(10,10), sticky='w')

        # Row 3: Tasa de interés
        ttk.Label(registro_frame, text="Tasa de interés:").grid(row=3, column=0, padx=(10,5), pady=(10,10), sticky='e')
        entry_interes = NumericEntry(registro_frame, width=25, textvariable=self.interes_var)
        entry_interes.grid(row=3, column=1, padx=(5,15), pady=(10,10), sticky='w')

        # Row 3-5: Descripción (spans multiple rows)
        ttk.Label(registro_frame, text="Descripción:").grid(row=3, column=2, padx=(10,5), pady=(10,10), sticky='ne')
        self.entry_descripcion = tk.Text(registro_frame, height=6, width=25, wrap=tk.WORD)
        self.entry_descripcion.grid(row=3, column=3, rowspan=3, padx=(5,15), pady=(10,10), sticky='nw')

        #Buttons with improved styling
        guardar=ttk.Button(registro_frame, text="✓ Registrar Deuda", command=self.guardar_registro, width=22)
        cancelar=ttk.Button(registro_frame, text="✗ Cancelar Registro", command=self.cancelar_registro, width=22)

        guardar.grid(row=4, column=0, columnspan=2, padx=(15,15), pady=(15,20), sticky='ew')
        cancelar.grid(row=5, column=0, columnspan=2, padx=(15,15), pady=(5,20), sticky='ew')

    def guardar_registro(self):
        """
        Saves the user-entered record to the database.
        First verifies that all required fields are filled. If interest or amount are empty,
        it defaults to 0.0 if the user accepts. If not accepted, it does nothing.
        """
        # Validate that required fields are not empty
        if (self.nombre_var.get() == '' or self.apellido_var.get() == '' 
            or self.tel_var.get()=='' or self.email_var.get()==''):

            messagebox.showerror("Error","Por favor llene todos los campos de información requeridos (Nombre, Apellido, Teléfono, Email)")
        else:
            try:
                # Attempt to register the person with all provided data including documento
                main.registrar_persona(self.nombre_var.get(), self.apellido_var.get(),
                               self.tel_var.get(), self.email_var.get(),
                               float(self.monto_var.get()), float(self.interes_var.get()),
                               self.entry_descripcion.get("1.0", tk.END), self.documento_var.get())
                messagebox.showinfo("Éxito", "Registro guardado exitosamente")
                self.master.home()
            except ValueError:
                # Handle case where monto or interes are empty or invalid
                sin_valor=messagebox.askyesno("Sin Valor","""
                                               No ingresó valores en monto y/o
                                               interés. Se utilizará 0.0 por 
                                               defecto,
                                               ¿Está de acuerdo?""")
                if sin_valor:
                    main.registrar_persona(self.nombre_var.get(), self.apellido_var.get(),
                               self.tel_var.get(), self.email_var.get(),
                               0.0, 0.0, self.entry_descripcion.get("1.0", tk.END), self.documento_var.get())
                    messagebox.showinfo("Éxito", "Registro guardado exitosamente")
                    self.master.home()
            except PermissionError:
                messagebox.showerror("Error fatal","No pueden haber registros con el mismo nombre y apellido")

    def cancelar_registro(self):
        self.master.home()

class EditarFrame(ttk.Frame):
    """
    Frame for editing existing person information (UPSERT operation).
    Allows modification of documento, telefono, and email fields.
    """
    def __init__(self, parent, values):
        super().__init__(parent)
        # Initialize text variables with current values from the database
        # values array: [id, nombre, apellido, documento, telefono, email, monto, interes, fecha]
        self.documento_var = tk.StringVar(value=str(values[3]) if values[3] else '')
        self.tel_var = tk.StringVar(value=str(values[4]) if values[4] else '')
        self.email_var = tk.StringVar(value=str(values[5]) if values[5] else '')
        self.widgets(values)

    def widgets(self, values):
        """
        Creates the form widgets for editing person information.
        """
        frame_test = ttk.LabelFrame(self, text="Editar información de:", padding=(20, 15))
        frame_test.grid(row=0, column=0, padx=(15,15), pady=(15,15))

        # Create a bold font for the person's name
        bold_font = ("TkDefaultFont", 14, "bold")

        # Display the person's name at the top
        name_label = ttk.Label(frame_test, text=f"{values[1]} {values[2]}", font=bold_font)
        name_label.grid(row=0, column=0, columnspan=2, sticky='nsew', padx=15, pady=(15,20))

        # Input fields for editable information
        ttk.Label(frame_test, text="Documento ID:").grid(row=1, column=0, pady=8, padx=(15,10), sticky='e')
        entry_documento = ttk.Entry(frame_test, textvariable=self.documento_var, width=30)
        entry_documento.grid(row=1, column=1, pady=8, padx=(0,15), sticky='w')

        ttk.Label(frame_test, text="Teléfono:").grid(row=2, column=0, pady=8, padx=(15,10), sticky='e')
        entry_tel = ttk.Entry(frame_test, textvariable=self.tel_var, width=30)
        entry_tel.grid(row=2, column=1, pady=8, padx=(0,15), sticky='w')

        ttk.Label(frame_test, text="Email:").grid(row=3, column=0, pady=8, padx=(15,10), sticky='e')
        entry_email = ttk.Entry(frame_test, textvariable=self.email_var, width=30)
        entry_email.grid(row=3, column=1, pady=8, padx=(0,15), sticky='w')

        # Action buttons with improved styling
        boton_ok = ttk.Button(frame_test, text='✓ Guardar Cambios', width=22,
                              command=lambda: self.aceptar_cambios_editar_registro(
                                  values[1], values[2], self.tel_var.get(), self.email_var.get(), self.documento_var.get()))

        boton_ok.grid(row=4, column=1, pady=(20,15), padx=(5,20), sticky='e')

        boton_cancelar = ttk.Button(frame_test, text='✗ Cancelar', width=22,
                                    command=self.master.home)
        boton_cancelar.grid(row=4, column=0, pady=(20,15), padx=(20,5), sticky='w')

    def aceptar_cambios_editar_registro(self, nombre, apellido, telefono, email, documento):
        """
        Accepts the changes and updates the database record with the new information.
        """
        main.editar_registro(nombre, apellido, telefono, email, documento)
        messagebox.showinfo("Éxito", "Cambios guardados exitosamente")
        self.master.home()

class HomeFrame(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent)
        # Configure weights so the tree takes up available space
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0) # Right frame fixed width
        self.columnconfigure(3, weight=0) # Extra frame fixed width
        self.rowconfigure(0, weight=1)

    def extra_frame(self,parametro="Nuevo"):
        self.master.create_extra_frame(parametro)
        self.master.right_frame.registrar_boton['state'] = 'disabled'
        self.master.right_frame.delete_boton['state'] = 'disabled'
        self.master.right_frame.movimiento_boton['state'] = 'disabled'
        self.master.right_frame.consultar_boton['state'] = 'disabled'
        self.master.right_frame.editar_boton['state'] = 'disabled'
        self.master.right_frame.exportar_boton['state'] = 'disabled'

    def on_button_click(self):
        self.master.on_button_click()

    def borrar_registro(self):
        self.master.borrar_registro()

    def home(self):
        self.master.show_home()

    def mostrar_detalles(self):
        self.master.mostrar_detalles()

    def editar(self):
        self.master.editar()
        
class MovimientoFrame(ttk.Frame):
    """
    Frame for registering new debt transactions for a selected person.
    Displays the person's transaction history and allows adding new movements.
    """
    def __init__(self,parent,values):
        super().__init__(parent)
        # Extract values from the array: [id, nombre, apellido, documento, telefono, email, monto, interes, fecha]
        self.nombre   = values[1]
        self.apellido = values[2]
        self.monto    = values[6]  # Updated index after adding documento column

        # Configure grid for resizing
        self.columnconfigure(0, weight=1) # Tree frame
        self.columnconfigure(1, weight=0) # Movement input frame
        self.rowconfigure(0, weight=1)

        self.widgets()

    def widgets(self):
        """
        Creates the form widgets for registering new debt movements.
        Includes current debt display, movement input, and quick adjustment buttons.
        """
        #LabelFrame container with improved padding
        self.mov_frame=ttk.LabelFrame(self, text='💰 Nuevo Movimiento', padding=(15, 15))
        self.mov_frame.grid(row=0, column=1, padx=15, pady=20)

        # Style configuration for labels - make them more prominent
        label_font = ("TkDefaultFont", 10, "bold")

        #Labels with improved styling
        ttk.Label(self.mov_frame, text="Deuda actual:", font=label_font).grid(row=1, column=0, padx=12, pady=12, sticky='e')
        ttk.Label(self.mov_frame, text="Movimiento:", font=label_font).grid(row=2, column=0, padx=12, pady=12, sticky='e')
        ttk.Label(self.mov_frame, text="Deuda actualizada:", font=label_font).grid(row=4, column=0, padx=12, pady=12, sticky='e')
        ttk.Label(self.mov_frame, text="Descripción:", font=label_font).grid(row=5, column=0, padx=12, pady=12, sticky='ne')

        #Entry widgets with improved sizing
        self.deuda_var = tk.DoubleVar(value=float(self.monto.replace("$", "").replace(",", "")))
        deuda_entry=ttk.Entry(self.mov_frame, textvariable=self.deuda_var, state='readonly', width=25)
        deuda_entry.grid(row=1, column=1, padx=(5,12), pady=12, sticky='ew')
        
        # Movimiento entry with quick adjustment buttons
        self.movimiento_entry_value=tk.DoubleVar(value=0.0)
        movimiento_entry=NumericEntry(self.mov_frame, textvariable=self.movimiento_entry_value, width=25)
        movimiento_entry.grid(row=2, column=1, padx=(5,12), pady=12, sticky='ew')
        self.movimiento_entry_value.trace_add("write", self.update_value)

        # Nueva deuda (calculated automatically)
        self.nuevadeuda_entry_var = tk.DoubleVar()
        nuevadeuda_entry=ttk.Entry(self.mov_frame, textvariable=self.nuevadeuda_entry_var, state='readonly', width=25)
        nuevadeuda_entry.grid(row=4, column=1, padx=(5,12), pady=12, sticky='ew')

        # Description text area
        self.descr_entry=tk.Text(self.mov_frame, height=4, width=25, wrap=tk.WORD)
        self.descr_entry.grid(row=5, column=1, padx=(5,12), pady=12, sticky='ew')

        #Quick adjustment buttons for movement (positioned over the movement entry)
        menos=ttk.Button(self.mov_frame, text='- 10k', width=5, command=lambda x=False:self.suma(x))
        menos.grid(row=3, column=1, sticky='w', padx=(5,0), pady=0)
        mas=ttk.Button(self.mov_frame, text='+ 10k', width=5, command=lambda x=True:self.suma(x))
        mas.grid(row=3, column=1, sticky='e', padx=(0,12), pady=0)

        #Action buttons with improved styling
        guardar=ttk.Button(self.mov_frame, text="✓ Guardar Movimiento", command=self.save_and_close, width=22)
        guardar.grid(row=6, column=1, padx=12, pady=(15,10), sticky='ew')

        borrar=ttk.Button(self.mov_frame, text="🗑️ Limpiar Campos", command=self.limpiar_datos, width=22)
        borrar.grid(row=6, column=0, padx=12, pady=(15,10), sticky='ew')

        #Tree display for transaction history
        self.place_tree(self.nombre, self.apellido)

    def suma(self, mas_o_menos):
        try:
            valor_actual=self.movimiento_entry_value.get()
            if mas_o_menos:            
                self.movimiento_entry_value.set(valor_actual+10000.0)
            else:self.movimiento_entry_value.set(valor_actual-10000.0)

        #Maneja el caso en el que el entry self.movimiento_entry_value tiene una entrada
        #que no es un float. Especialmente el caso en el que es una cadena vacia ''
        except tk.TclError:
            if mas_o_menos:            
                self.movimiento_entry_value.set(10000.0)
            else:self.movimiento_entry_value.set(-10000.0)

    def update_value(self,*args):
        try:
            deuda = self.deuda_var.get()
            movimiento_var= self.movimiento_entry_value.get()
            movimiento= float(movimiento_var) if movimiento_var != '' else 0.0
            nueva_deuda = deuda + movimiento
            self.nuevadeuda_entry_var.set(nueva_deuda)
        except ValueError:
            # Si hay un valor no válido en alguna de las entradas, no hagas nada
            pass
        #Maneja el caso en el que el entry self.movimiento_entry_value tiene una entrada
        #que no es un float. Especialmente el caso en el que es una cadena vacia ''
        except tk.TclError:
            deuda = self.deuda_var.get()
            self.nuevadeuda_entry_var.set(deuda)

    def limpiar_datos(self):
        # Limpiar todos los campos
        self.movimiento_entry_value.set('')
        self.nuevadeuda_entry_var.set(float(self.deuda_var.get()))
        self.descr_entry.delete("1.0", tk.END)

    def place_tree(self,nombre, apellido):
        """
        Creates a TreeView to display the transaction history for the selected person.
        Height is set to 18 to match the main screen tree for consistency.
        """
        tree_frame=ttk.LabelFrame(self, text=f"{self.nombre.upper()} {self.apellido.upper()}", padding=(5, 5))
        tree_frame.grid(row=0, column=0, sticky='nsew', padx=(10,10), pady=(10,10))
        # Set height=18 to match the main screen tree height for consistency
        self.tree=ttk.Treeview(tree_frame, height=18)
        self.tree.grid(row=0, column=0, sticky='nsew', padx=(10,10), pady=(10,10))
        # Limpia cualquier entrada anterior en el TreeView para evitar duplicaciones o datos obsoletos.
        for i in self.tree.get_children():
            self.tree.delete(i) 

        df=main.consultar_tabla_persona(nombre, apellido)
        # Agrega y configura las columnas del TreeView basándose en las columnas del DataFrame.
        columns = list(df.columns)
        self.tree["show"] = "headings"
        self.tree['columns'] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100,anchor='center')

        # Ajustes específicos para algunas columnas, estableciendo un ancho personalizado para mejorar la visibilidad.
        self.tree.column('id', width=15)
        self.tree.column('deuda_total',width=90)
        self.tree.column('transaccion',width=90)
        self.tree.column('fecha',width=90)
        self.tree.column('descripcion',width=250)

        # Inserta los datos del DataFrame en el TreeView fila por fila.
        for index, row in df.iterrows():
            row['deuda_total'] = f"${float(row['deuda_total']):,.2f}"
            row['transaccion'] = f"${float(row['transaccion']):,.2f}"
            self.tree.insert("", tk.END, values=list(row))


        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0,column=1,sticky='ns')

    def save_and_close(self):
       
        try:
            deuda = self.deuda_var.get()            
            movimiento = self.movimiento_entry_value.get()  
            if movimiento == 0.0:
                messagebox.showerror("Error", "No hay movimiento para registrar")
            else:
                nueva_deuda = deuda + movimiento

                main.actualizar_deuda(self.nombre, self.apellido, 
                                    nueva_deuda, movimiento, self.descr_entry.get("1.0", tk.END))

                self.deuda_var.set(nueva_deuda)
                self.limpiar_datos()
                self.place_tree(self.nombre, self.apellido)        
        #Maneja el caso en el que el entry self.movimiento_entry_value tiene una entrada
        #que no es un float. Especialmente el caso en el que es una cadena vacia ''
        except tk.TclError:
            messagebox.showerror("Error", "No hay movimiento para registrar")

class DetallesFrame(ttk.Frame):
    """
    Frame for displaying detailed information about a person's debt history.
    Shows a graph of debt evolution over time and provides export/email options.
    """
    def __init__(self,master,values):
        super().__init__(master)
        # Extract values from the array: [id, nombre, apellido, documento, telefono, email, monto, interes, fecha]
        self.nombre   = values[1]
        self.apellido = values[2]
        self.documento= values[3]
        self.telefono = values[4]  # Updated index after adding documento column
        self.email    = values[5]  # Updated index after adding documento column
        self.monto    = values[6]  # Updated index after adding documento column
        self.interes  = values[7]  # Updated index after adding documento column
        
        # Configure grid for resizing
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        
        self.widgets_detalles()

    def widgets_detalles(self):
        """
        Creates the detailed view widgets including graph visualization and action buttons.
        """
        #Treeview with transaction history
        self.place_tree(self.nombre, self.apellido)

        #LabelFrame for graph visualization
        detalles_frame=ttk.LabelFrame(self, text='📈 Historial de Movimientos', padding=(15, 15))
        detalles_frame.grid(row=0, column=0, padx=15, pady=20, rowspan=2, sticky='nsew')

        # Generate the debt history graph
        output_path = 'historial_movimientos.png'
        main.generar_grafica(self.nombre, self.apellido, output_path)

        # Load the generated image
        img = Image.open(output_path)
        img_tk = ImageTk.PhotoImage(img)

        # Display the image in a Label
        label = tk.Label(detalles_frame, image=img_tk, width=600)
        label.image = img_tk  # Keep a reference to prevent garbage collection
        label.grid(row=0, column=0, columnspan=2, rowspan=2, padx=15, pady=15)

        #LabelFrame for action buttons
        botones_frame=ttk.LabelFrame(self, text='⚡ Acciones Disponibles', padding=(15, 15))
        botones_frame.grid(row=1, column=1, padx=10, pady=(5,30), sticky='nsew')

        # Display contact information
        telefono_formatted = f"{str(self.telefono)[0:3]}-{str(self.telefono)[3:6]}-{str(self.telefono)[6:]}" if self.telefono else "N/A"
        label_info_font = ("TkDefaultFont", 10)
        
        label_telefono=ttk.Label(botones_frame, text=f"📞 Teléfono: {telefono_formatted}", font=label_info_font)
        label_telefono.grid(row=1, column=0, columnspan=4, sticky='w', padx=(15, 15), pady=(10, 5))

        label_email=ttk.Label(botones_frame, text=f"📧 Email: {self.email if self.email else 'N/A'}", font=label_info_font)
        label_email.grid(row=2, column=0, columnspan=4, sticky='w', padx=(15, 15), pady=(5, 10))

        # Action buttons with improved styling
        boton_exportar = ttk.Button(botones_frame, text='📁 Exportar CSV', width=20,
                                  command=lambda n=self.nombre,a=self.apellido : self.exportar(n,a))
        boton_email    = ttk.Button(botones_frame, text='📧 Enviar E-mail', width=20,
                                  command=lambda n=self.nombre,a=self.apellido,e=self.email:self.enviar_email(n,a,e))
        
        boton_exportar.grid(row=0, column=0, columnspan=2, padx=(15, 10), pady=(20, 20), sticky='ew')
        boton_email.grid(row=0, column=2, columnspan=2, padx=(10, 15), pady=(20, 20), sticky='ew')

        # Configure column weights for proper expansion
        botones_frame.columnconfigure(0, weight=1)
        botones_frame.columnconfigure(1, weight=1)
        botones_frame.columnconfigure(2, weight=1)
        botones_frame.columnconfigure(3, weight=1)
        botones_frame.rowconfigure(1, weight=1)

    def exportar(self,nombre,apellido):
        # Abrir el diálogo para guardar archivo
        nombre_archivo=f'{nombre}_{apellido}.csv'
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=nombre_archivo,
            title="Guardar archivo como"
        )
        # Si el usuario proporciona un archivo, exportar los datos
        if file_path:
            main.exportar_datos_a_csv("Usuario",nombre,apellido,file_path)
            messagebox.showinfo("Exportación Exitosa", f"Datos exportados a {file_path}")

    def enviar_email(self,nombre, apellido, email):
        nombre_archivo=f'{nombre}_{apellido}.csv'
        import email_sender
        subject="Resumen de Movimientos a fecha"
        body = f"""
            Buen día estimado {nombre} {apellido},
            Adjunto excel con un resumen de los movimientos y transacciones
            de nuestros asuntos de dinero.

            Saludos.

            """   
  
        try:
            main.exportar_datos_a_csv("Usuario",nombre,apellido,nombre_archivo)
            email_sender.send_email(subject,body,email,nombre_archivo)
            messagebox.showinfo("Éxito",f'Correo enviado exitosamente a {email}')
            os.remove(nombre_archivo)
        except ConnectionAbortedError as e:
            messagebox.showerror("Error fatal",f'Error al enviar el correo: {e}')
        except ConnectionError as e:
            messagebox.showerror("Error fatal",f'Ocurrió un error: {e}')

    def place_tree(self,nombre, apellido):
        """
        Creates a TreeView to display the complete transaction history for the person.
        Height is set to 18 to match the main screen tree for consistency.
        """
        tree_frame=ttk.LabelFrame(self, text=f"{self.nombre.upper()} {self.apellido.upper()}", padding=(5, 5))
        tree_frame.grid(row=0, column=1, sticky='nsew', padx=(10,10), pady=(20,20))
        # Set height=18 to match the main screen tree height for consistency
        self.tree=ttk.Treeview(tree_frame, height=18)
        self.tree.grid(row=0, column=0, sticky='nsew', padx=(10,10), pady=(0,0))
        # Limpia cualquier entrada anterior en el TreeView para evitar duplicaciones o datos obsoletos.
        for i in self.tree.get_children():
            self.tree.delete(i) 

        df=main.consultar_tabla_persona(nombre, apellido)
        # Agrega y configura las columnas del TreeView basándose en las columnas del DataFrame.
        columns = list(df.columns)
        self.tree["show"] = "headings"
        self.tree['columns'] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100,anchor='center')

        # Ajustes específicos para algunas columnas, estableciendo un ancho personalizado para mejorar la visibilidad.
        self.tree.column('id', width=15)
        self.tree.column('deuda_total',width=90)
        self.tree.column('transaccion',width=90)
        self.tree.column('fecha',width=90)
        self.tree.column('descripcion',width=250)

        # Inserta los datos del DataFrame en el TreeView fila por fila.
        for index, row in df.iterrows():
            row['deuda_total'] = f"${float(row['deuda_total']):,.2f}"
            row['transaccion'] = f"${float(row['transaccion']):,.2f}"
            self.tree.insert("", tk.END, values=list(row))


        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0,column=1,sticky='ns')

class NumericEntry(ttk.Entry):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        
        # Configurar la validación de la entrada
        vcmd = (self.register(self._validate), '%P')
        self.config(validate='key', validatecommand=vcmd)

    def _validate(self, P):
        """
        Método de validación que permite solo la entrada de números y un punto decimal.
        P es el valor de la entrada después del cambio propuesto.
        """
        if P == "" or P == "-":
            return True
        try:
            float(P)
            return True
        except ValueError:
            return False

App("Contabilidad")