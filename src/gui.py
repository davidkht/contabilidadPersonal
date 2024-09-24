import os
import main
from main import script_directory
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

class App(tk.Tk):

    def __init__(self, title):
        super().__init__()
        self.title(title)
        # self.resizable(False,False)
        self.home_geometry=[880,420]
        self.mov_geometry=[950,380]        
        self.default_width = self.home_geometry[0]
        self.extended_width = self.home_geometry[0] + 600
        self.height = self.home_geometry[1]

        self.icono_e_imagen()# Método para establecer el icono de la aplicación

        self.current_frame = None  # Inicialmente no hay frame visible
        
        self.place_widgets()

        main.verificar_y_calcular_intereses()

        self.show_home()# Muestra el primer frame

        # Manejar el evento de cierre de la ventana
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        #Correr la app
        self.mainloop()# Inicia el bucle principal de la aplicación

    def place_widgets(self):

        self.home_button=ttk.Button(self,text="Inicio",image=self.mi_imagen,command= self.show_home)
        self.home_button.grid(row=0,column=0,sticky='w',padx=(10,10),pady=(10,0))

    def place_tree(self):
        self.tree=ttk.Treeview(self.tree_frame,height=13)
        self.tree.grid(row=0,column=0,sticky='nsew',padx=(10,10),pady=(10,10))
        # Limpia cualquier entrada anterior en el TreeView para evitar duplicaciones o datos obsoletos.
        for i in self.tree.get_children():
            self.tree.delete(i) 

        df=main.consultar_deudas()
        # Agrega y configura las columnas del TreeView basándose en las columnas del DataFrame.
        columns = list(df.columns)
        self.tree["show"] = "headings"
        self.tree['columns'] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100,anchor='center')

        # Ajustes específicos para algunas columnas, estableciendo un ancho personalizado para mejorar la visibilidad.
        self.tree.column('id', width=15)
        self.tree.column('nombre', width=70)
        self.tree.column('apellido',width=70)
        self.tree.column('telefono',width=70)
        self.tree.column('email',width=140)
        self.tree.column('monto',width=100)
        self.tree.column('interes',width=60)
        self.tree.column('fecha',width=100)

        # Inserta los datos del DataFrame en el TreeView fila por fila.
        for index, row in df.iterrows():
            # Formatear el valor de 'monto' como moneda
            row['monto'] = f"${float(row['monto']):,.2f}"
            self.tree.insert("", tk.END, values=list(row))


        scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0,column=1,sticky='ns')

    def icono_e_imagen(self):
        # Obtén el directorio del script
        icon_path = os.path.join(script_directory, '..', 'docs', 'icono.ico')
        
        # Verifica si el archivo existe
        if not os.path.exists(icon_path):
            print(f"El archivo {icon_path} no existe.")
            return
        try:
            # Establece el ícono de la ventana
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error al establecer el ícono: {e}")

        imagen_ico = Image.open(os.path.join(script_directory,'..',"docs","miimagen.ico"))
        self.mi_imagen=imagen_ico.resize((32,32))
        self.mi_imagen = ImageTk.PhotoImage(self.mi_imagen)

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

        #Logic
        if self.current_frame:
            self.current_frame.grid_forget()
            self.current_frame.destroy()
            self.current_frame = None

        self.current_frame = HomeFrame(self)
        self.current_frame.grid(row=1, column=0, sticky='nsew')

        #Widgets
        ##Frame for tree 
        self.tree_frame=ttk.LabelFrame(self.current_frame,text="Lista de Deudas")
        self.tree_frame.grid(row=0,column=0,padx=(10,10),pady=(10,10))
        self.place_tree()

        self.right_frame=RightFrame(self.current_frame)
        self.right_frame.grid(row=0,column=1,padx=(10,10),pady=(10,10))
      
        self.geometry(f"{self.home_geometry[0]}x{self.home_geometry[1]}")

    def create_extra_frame(self,parametro,values=None):
        if parametro=="Nuevo":
            self.extra_frame = RegistroFrame(self.current_frame)
            self.extra_frame.grid(row=0,column=3,padx=10,pady=10)
            self.geometry(f"{self.extended_width}x{self.height}")
        elif parametro == "Editar":
            self.extra_frame = EditarFrame(self.current_frame,values)
            self.extra_frame.grid(row=0,column=3,padx=10,pady=10)
            self.geometry(f"{1250}x{self.height}")

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
        if self.current_frame:
            self.current_frame.grid_forget()
            self.current_frame.destroy()
            self.current_frame = None

        self.current_frame = DetallesFrame(self, values)
        self.current_frame.grid(row=1, column=0, sticky='nsew')
        self.geometry("1260x550")

    def borrar_registro(self):
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item)
            values = item['values']
            verificacion=messagebox.askyesno("Borrar Registro?","Está seguro de borrar el registro?",options=(True,False))
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

    def __init__(self,parent):

        super().__init__(parent) 

        self.top_frame=ttk.LabelFrame(self,text='Gestión de Registro')
        self.top_frame.grid(row=0,column=0,padx=(10,10),pady=(10,10))

        self.bottom_frame=ttk.LabelFrame(self,text='Acciones Disponibles')
        self.bottom_frame.grid(row=1,column=0,padx=(10,10),pady=(10,10))

        self.buttons(parent)

    def buttons(self,parent):

        #Top Frame
        self.delete_boton=ttk.Button(self.top_frame,text='Borrar Registro',width=20, 
                                command=self.master.borrar_registro)
        self.delete_boton.grid(row=0,column=0,padx=(10,10),pady=(10,10))

        self.registrar_boton=ttk.Button(self.top_frame,text='Nuevo Registro',width=20, 
                                   command=lambda p="Nuevo": self.master.extra_frame(p)) 
        self.registrar_boton.grid(row=1,column=0,padx=(10,10),pady=(10,10))

        #Bottom Frame
        self.movimiento_boton=ttk.Button(self.bottom_frame,text='Registrar Movimiento',width=20,
                                    command=parent.on_button_click)
        self.movimiento_boton.grid(row=0,column=0,padx=(10,10),pady=(10,10))
        self.consultar_boton=ttk.Button(self.bottom_frame,text='Consultar',width=20, command=parent.mostrar_detalles)
        self.consultar_boton.grid(row=1,column=0,padx=(10,10),pady=(10,10))
        self.editar_boton=ttk.Button(self.bottom_frame,text='Editar',width=20,command=parent.editar)
        self.editar_boton.grid(row=2,column=0,padx=(10,10),pady=(10,10))
        self.exportar_boton = ttk.Button(self.bottom_frame, text='Exportar Datos', width=20, command=self.exportar_datos)
        self.exportar_boton.grid(row=3, column=0, padx=(10, 10), pady=(10, 10))

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
        #Label
        registro_frame=ttk.LabelFrame(self,text="Nuevo registro")
        registro_frame.grid(row=0, column=0,padx=(10,10),pady=(10,10))

        #Variables de texto
        self.nombre_var=tk.StringVar()
        self.apellido_var=tk.StringVar()
        self.tel_var=tk.StringVar()
        self.email_var=tk.StringVar()
        self.monto_var=tk.StringVar()
        self.interes_var=tk.StringVar()

        # Campos de entrada
        ttk.Label(registro_frame, text="Nombre").grid(row=0, column=0,padx=(10,5),pady=(15,5),sticky='nw')
        entry_nombre = ttk.Entry(registro_frame,width=25,textvariable=self.nombre_var)
        entry_nombre.grid(row=0, column=1,padx=(10,5),pady=(15,5),sticky='nw')

        ttk.Label(registro_frame, text="Apellido").grid(row=0, column=2,padx=(10,5),pady=(15,5),sticky='nw')
        entry_apellido = ttk.Entry(registro_frame,width=25,textvariable=self.apellido_var)
        entry_apellido.grid(row=0, column=3,padx=(10,5),pady=(15,5),sticky='nw')

        ttk.Label(registro_frame, text="Teléfono").grid(row=1, column=0,padx=(10,5),pady=(10,5),sticky='nw')
        entry_telefono = ttk.Entry(registro_frame,width=25,textvariable=self.tel_var)
        entry_telefono.grid(row=1, column=1,padx=(10,5),pady=(10,5),sticky='nw')

        ttk.Label(registro_frame, text="Email").grid(row=1, column=2,padx=(10,5),pady=(10,5),sticky='nw')
        entry_email = ttk.Entry(registro_frame,width=25,textvariable=self.email_var)
        entry_email.grid(row=1, column=3,padx=(10,5),pady=(10,5),sticky='nw')

        ttk.Label(registro_frame, text="Monto adeudado").grid(row=2, column=0,padx=(10,5),pady=(10,5),sticky='nw')
        entry_monto = NumericEntry(registro_frame,width=25,textvariable=self.monto_var)
        entry_monto.grid(row=2, column=1,padx=(10,5),pady=(10,5),sticky='nw')

        ttk.Label(registro_frame, text="Tasa de interés").grid(row=2, column=2,padx=(10,5),pady=(10,5),sticky='nw')
        entry_interes = NumericEntry(registro_frame,width=25,textvariable=self.interes_var)
        entry_interes.grid(row=2, column=3,padx=(10,5),pady=(10,5),sticky='nw')

        ttk.Label(registro_frame, text="Descripción").grid(row=3, column=0,padx=(10,5),pady=(10,5),sticky='nw')
        self.entry_descripcion = tk.Text(registro_frame,height=6,width=19)
        self.entry_descripcion.grid(row=3, column=1, rowspan= 3,padx=(10,5),pady=(10,20),sticky='nw')

        #Botones
        guardar=ttk.Button(registro_frame,text="Registrar Deuda",command=self.guardar_registro)
        cancelar=ttk.Button(registro_frame,text="Cancelar Registro",command=self.cancelar_registro)

        guardar.grid(row=3,column=2,columnspan=2,padx=(10,5),pady=(10,5),sticky='nsew')
        cancelar.grid(row=4,column=2,columnspan=2,padx=(10,5),pady=(10,20),sticky='nsew')

    def guardar_registro(self):
        """
        Función para guardar el registro escrito por el usuario en la base de datos.
        Primero verifica que todos los campos estén llenos. Si interés o monto están vacios,
        toma como defecto 0.0 si el usuario acepta. Si no acepta, no hace nada.
        """
        if (self.nombre_var.get() == '' or self.apellido_var.get() == '' 
            or self.tel_var.get()=='' or self.email_var.get()==''):

            messagebox.showerror("Error","Llene todos los campos de información")
        else:
            try:
                main.registrar_persona(self.nombre_var.get(), self.apellido_var.get(),
                               self.tel_var.get(),self.email_var.get(),
                               float(self.monto_var.get()),float(self.interes_var.get()),
                               self.entry_descripcion.get("1.0", tk.END))
                self.master.home()
            except ValueError:
                sin_valor=messagebox.askyesno("Sin Valor","""
                                               No ingresó valores en monto y/o
                                               interés. Se utilizará 0.0 por 
                                               defecto,
                                               ¿Está de acuerdo?""")
                if sin_valor:
                    main.registrar_persona(self.nombre_var.get(), self.apellido_var.get(),
                               self.tel_var.get(),self.email_var.get(),
                               0.0, 0.0, self.entry_descripcion.get("1.0", tk.END))
                    self.master.home()
            except PermissionError:
                messagebox.showerror("Error fatal","No pueden haber registros con el mismo nombre y apellido")

    def cancelar_registro(self):
        self.master.home()

class EditarFrame(ttk.Frame):
    def __init__(self, parent, values):
        super().__init__(parent)
        self.tel_var = tk.StringVar(value=str(values[3]))
        self.email_var = tk.StringVar(value=str(values[4]))
        self.widgets(values)

    def widgets(self, values):
        frame_test = ttk.LabelFrame(self,text="Editar información de:")
        frame_test.grid(row=0, column=0)

        # Crear una fuente en negrita
        bold_font = ("TkDefaultFont", 12, "bold")

        name_label = ttk.Label(frame_test, text=f"{values[1]} {values[2]}",font=bold_font)
        name_label.grid(row=0, column=0, columnspan=2, sticky='nsew', padx=10, pady=10)

        ttk.Label(frame_test, text="Teléfono").grid(row=1, column=0, pady=5, padx=(15,0),sticky='w')
        ttk.Label(frame_test, text="Email").grid(row=2, column=0, pady=5, padx=(15,0),sticky='w')

        entry_tel = ttk.Entry(frame_test, textvariable=self.tel_var, width=25)
        entry_tel.grid(row=1, column=1, pady=5, padx=(0,15),sticky='w')

        entry_email = ttk.Entry(frame_test, textvariable=self.email_var, width=25)
        entry_email.grid(row=2, column=1, pady=5, padx=(0,15),sticky='w')

        boton_ok = ttk.Button(frame_test, text='OK', width=20,
                              command=lambda: self.aceptar_cambios_editar_registro(
                                  values[1], values[2], self.tel_var.get(), self.email_var.get()))

        boton_ok.grid(row=3, column=1, pady=10, padx=(5,20), sticky='e')

        boton_cancelar = ttk.Button(frame_test, text='Cancelar', width=20,
                                    command=self.master.home)
        boton_cancelar.grid(row=3, column=0, pady=10, padx=(20,5), sticky='w')

    def aceptar_cambios_editar_registro(self, nombre, apellido, telefono, email):

        main.editar_registro(nombre, apellido, telefono, email)
        self.master.home()

class HomeFrame(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent)

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

    def __init__(self,parent,values):

        super().__init__(parent)        
        self.nombre   = values[1]
        self.apellido = values[2]
        self.monto    = values[5]

        self.widgets()

    def widgets(self):

        #LabelFrame
        self.mov_frame=ttk.LabelFrame(self,text='Nuevo Movimiento')
        self.mov_frame.grid(row=0,column=1,padx=10,pady=20)
        #Labels
        ttk.Label(self.mov_frame,text="Deuda actual").grid(row=1,column=0,padx=10,pady=10,sticky='nw')
        ttk.Label(self.mov_frame,text="Movimiento").grid(row=2,column=0,padx=10,pady=10,sticky='nw')
        ttk.Label(self.mov_frame,text="Deuda actualizada").grid(row=4,column=0,padx=10,pady=10,sticky='nw')
        ttk.Label(self.mov_frame,text="Descripción").grid(row=5,column=0,padx=10,pady=10,sticky='nw')


        #Entries
        self.deuda_var = tk.DoubleVar(value=float(self.monto.replace("$", "").replace(",", "")))
        deuda_entry=ttk.Entry(self.mov_frame,textvariable=self.deuda_var,state='readonly')
        deuda_entry.grid(row=1,column=1,padx=10,pady=10,sticky='nsew')
        

        self.movimiento_entry_value=tk.DoubleVar(value=0.0)
        movimiento_entry=NumericEntry(self.mov_frame,textvariable=self.movimiento_entry_value,width=20)
        movimiento_entry.grid(row=2,column=1,padx=(0,10),pady=10,sticky='ns')
        self.movimiento_entry_value.trace_add("write", self.update_value)

        self.nuevadeuda_entry_var = tk.DoubleVar()

        nuevadeuda_entry=ttk.Entry(self.mov_frame,textvariable=self.nuevadeuda_entry_var,state='readonly')
        nuevadeuda_entry.grid(row=4,column=1,padx=10,pady=10,sticky='nsew')


        self.descr_entry=tk.Text(self.mov_frame,height=3,width=20)
        self.descr_entry.grid(row=5,column=1,padx=(10,10),pady=10,sticky='ns')

        #Buttons
        borrar=ttk.Button(self.mov_frame,text="Limpiar",command=self.limpiar_datos)
        guardar=ttk.Button(self.mov_frame,text="Guardar",command=self.save_and_close)

        borrar.grid(row= 6,column=0,padx=10,pady=10,sticky='nsew')
        guardar.grid(row= 6,column=1,padx=10,pady=10,sticky='nsew')

        #Botones de suma
        mas=ttk.Button(self.mov_frame,text='+',width=2,command=lambda x=True:self.suma(x))
        menos=ttk.Button(self.mov_frame,text='-',width=2,command=lambda x=False:self.suma(x))
        mas.grid(row=2,column=1,sticky='e',padx=(0,10))
        menos.grid(row=2,column=1,sticky='w',padx=(0,0))
        #Tree
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

        tree_frame=ttk.LabelFrame(self,text=f"{self.nombre.upper()} {self.apellido.upper()}")
        tree_frame.grid(row=0,column=0,sticky='nsew',padx=(10,10),pady=(10,10))
        self.tree=ttk.Treeview(tree_frame)
        self.tree.grid(row=0,column=0,sticky='nsew',padx=(10,10),pady=(10,10))
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
    def __init__(self,master,values):
        super().__init__(master)
        self.nombre   = values[1]
        self.apellido = values[2]
        self.telefono = values[3]
        self.email    = values[4]
        self.monto    = values[5]
        self.interes  = values[6]
        self.widgets_detalles()

    def widgets_detalles(self):
        #Treeview
        self.place_tree(self.nombre,self.apellido)

        #LabelFrame
        detalles_frame=ttk.LabelFrame(self,text='Movimientos')
        detalles_frame.grid(row=0,column=0,padx=10,pady=20,rowspan=2,sticky='nsew')

        output_path = 'historial_movimientos.png'
        main.generar_grafica(self.nombre, self.apellido, output_path)

        # Cargar la imagen generada
        img = Image.open(output_path)
        img_tk = ImageTk.PhotoImage(img)

        # Mostrar la imagen en un Label
        label = tk.Label(detalles_frame, image=img_tk,width=600)
        label.image = img_tk  # Mantener una referencia a la imagen para evitar que se recoja la basura
        label.grid(row=0, column=0, columnspan=2,rowspan=2, padx=10, pady=10)

        #LabelFrame
        botones_frame=ttk.LabelFrame(self,text='Acciones')
        botones_frame.grid(row=1,column=1,padx=5,pady=(5,30),sticky='nsew')

        label_telefono=ttk.Label(botones_frame,text=f"¿Llamar?: {str(self.telefono)[0:3]}-{str(self.telefono)[3:6]}-{str(self.telefono)[6:]}")
        label_telefono.grid(row=1,column=3,columnspan=1,sticky='nsew',padx=(10, 10))

        boton_exportar = ttk.Button(botones_frame,text='Exportar',
                                  command=lambda n=self.nombre,a=self.apellido : self.exportar(n,a))
        boton_email    = ttk.Button(botones_frame,text='Enviar E-mail',
                                  command=lambda n=self.nombre,a=self.apellido,e=self.email:self.enviar_email(n,a,e))
        
        boton_exportar.grid(row=0, column=0, columnspan=2,padx=(10, 10), pady=(20, 20),sticky='nsew')
        boton_email.grid(row=0, column=2,columnspan=2, padx=(10, 10), pady=(20, 20),sticky='nsew')

        # Configurar peso para expansión
        botones_frame.columnconfigure(0, weight=1)
        botones_frame.columnconfigure(1, weight=1)
        botones_frame.columnconfigure(2, weight=1)
        botones_frame.columnconfigure(3, weight=1)
        botones_frame.rowconfigure(1,weight=1)

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

        tree_frame=ttk.LabelFrame(self,text=f"{self.nombre.upper()} {self.apellido.upper()}")
        tree_frame.grid(row=0,column=1,sticky='nsew',padx=(10,10),pady=(20,20))
        self.tree=ttk.Treeview(tree_frame,height=12)
        self.tree.grid(row=0,column=0,sticky='nsew',padx=(10,10),pady=(0,0))
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