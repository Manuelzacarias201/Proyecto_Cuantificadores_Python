import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np

class LogicQueryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Consultas Lógicas")
        self.root.geometry("1200x800")
        
        self.data = None
        self.setup_gui()
    
    def setup_gui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Botón para cargar dataset
        ttk.Button(main_frame, text="Cargar Dataset", command=self.load_dataset).grid(row=0, column=0, pady=5)
        
        # Frame para la tabla
        self.table_frame = ttk.Frame(main_frame)
        self.table_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Frame para construcción de consultas
        query_frame = ttk.LabelFrame(main_frame, text="Constructor de Consultas", padding="5")
        query_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        # Componentes para construir consultas
        self.setup_query_builder(query_frame)
        
        # Área de resultados
        result_frame = ttk.LabelFrame(main_frame, text="Resultados", padding="5")
        result_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        self.result_tree = ttk.Treeview(result_frame)
        self.result_tree.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
    def setup_query_builder(self, frame):
        # Selector de atributo
        ttk.Label(frame, text="Atributo:").grid(row=0, column=0, padx=5)
        self.attr_var = tk.StringVar()
        self.attr_combo = ttk.Combobox(frame, textvariable=self.attr_var, state="readonly")
        self.attr_combo.grid(row=0, column=1, padx=5)
        
        # Selector de operador
        ttk.Label(frame, text="Operador:").grid(row=0, column=2, padx=5)
        self.op_var = tk.StringVar()
        self.op_combo = ttk.Combobox(frame, textvariable=self.op_var, 
                                   values=["=", ">", "<", ">=", "<=", "≠"], 
                                   state="readonly")
        self.op_combo.grid(row=0, column=3, padx=5)
        
        # Entrada de valor
        ttk.Label(frame, text="Valor:").grid(row=0, column=4, padx=5)
        self.value_entry = ttk.Entry(frame)
        self.value_entry.grid(row=0, column=5, padx=5)
        
        # Selector de cuantificador
        ttk.Label(frame, text="Cuantificador:").grid(row=0, column=6, padx=5)
        self.quant_var = tk.StringVar()
        self.quant_combo = ttk.Combobox(frame, textvariable=self.quant_var,
                                      values=["∀ (Para todo)", "∃ (Existe)"],
                                      state="readonly")
        self.quant_combo.grid(row=0, column=7, padx=5)
        
        # Botón de ejecutar consulta
        ttk.Button(frame, text="Ejecutar Consulta", command=self.execute_query).grid(row=0, column=8, padx=5)
    
    def load_dataset(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if filename:
            try:
                self.data = pd.read_csv(filename)
                self.display_data()
                self.update_attribute_list()
                messagebox.showinfo("Éxito", "Dataset cargado correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar el archivo: {str(e)}")
    
    def display_data(self):
        # Limpiar tabla existente
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        
        # Crear nueva tabla
        tree = ttk.Treeview(self.table_frame)
        tree["columns"] = list(self.data.columns)
        tree["show"] = "headings"
        
        # Configurar columnas
        for column in self.data.columns:
            tree.heading(column, text=column)
            tree.column(column, width=100)
        
        # Insertar datos
        for index, row in self.data.iterrows():
            tree.insert("", "end", values=list(row))
        
        # Agregar scrollbars
        yscroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(self.table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        
        # Posicionar elementos
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)
    
    def update_attribute_list(self):
        if self.data is not None:
            self.attr_combo['values'] = list(self.data.columns)
    
    def execute_query(self):
        if self.data is None:
            messagebox.showerror("Error", "Por favor cargue un dataset primero")
            return
        
        # Validar que todos los campos estén completos
        attr = self.attr_var.get()
        if not attr:
            messagebox.showerror("Error", "Por favor seleccione un atributo")
            return
            
        op = self.op_var.get()
        if not op:
            messagebox.showerror("Error", "Por favor seleccione un operador")
            return
            
        value = self.value_entry.get()
        if not value:
            messagebox.showerror("Error", "Por favor ingrese un valor")
            return
            
        quant = self.quant_var.get()
        if not quant:
            messagebox.showerror("Error", "Por favor seleccione un cuantificador")
            return
        
        try:
            # Determinar si el atributo es numérico
            is_numeric = pd.api.types.is_numeric_dtype(self.data[attr])
            
            # Convertir valor a número si el atributo es numérico
            if is_numeric:
                try:
                    value = float(value)
                except ValueError:
                    messagebox.showerror("Error", f"El valor debe ser numérico para el atributo {attr}")
                    return
            
            # Inicializar máscara de filtro
            mask = None
            
            # Construir máscara de filtro según el operador
            if op == "=":
                mask = self.data[attr] == value
            elif op == ">":
                mask = self.data[attr] > value
            elif op == "<":
                mask = self.data[attr] < value
            elif op == ">=":
                mask = self.data[attr] >= value
            elif op == "<=":
                mask = self.data[attr] <= value
            elif op == "≠":
                mask = self.data[attr] != value
                
            if mask is None:
                raise ValueError(f"Operador no válido: {op}")
            
            # Aplicar cuantificador
            if quant.startswith("∀"):
                result = mask.all()
                message = f"Para todo: {'Se cumple' if result else 'No se cumple'}"
            else:  # ∃
                result = mask.any()
                message = f"Existe: {'Se cumple' if result else 'No se cumple'}"
            
            # Mostrar resultados
            filtered_data = self.data[mask]
            self.display_results(filtered_data, message)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al ejecutar la consulta: {str(e)}")
    
    def display_results(self, filtered_data, message):
        # Limpiar resultados anteriores
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        # Configurar columnas
        self.result_tree["columns"] = list(filtered_data.columns)
        self.result_tree["show"] = "headings"
        
        for column in filtered_data.columns:
            self.result_tree.heading(column, text=column)
            self.result_tree.column(column, width=100)
        
        # Insertar datos filtrados
        for index, row in filtered_data.iterrows():
            self.result_tree.insert("", "end", values=list(row))
        
        # Mostrar mensaje de resultado
        messagebox.showinfo("Resultado", message)

if __name__ == "__main__":
    root = tk.Tk()
    app = LogicQueryApp(root)
    root.mainloop()
