import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import pandas as pd
import numpy as np

# ----------------------------
#   Estructuras de predicados
# ----------------------------

class RelOp:
    GT = ">"
    LT = "<"
    EQ = "="
    NE = "!="
    GE = ">="
    LE = "<="
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"

REL_OPS = [
    RelOp.EQ, RelOp.GT, RelOp.LT, RelOp.GE, RelOp.LE, RelOp.NE,
    RelOp.CONTAINS, RelOp.STARTS_WITH, RelOp.ENDS_WITH
]

class LogicOp:
    NOT = "NOT"
    AND = "AND"
    OR = "OR"
    IMPLIES = "IMPLIES"
    XOR = "XOR"
    BICONDITIONAL = "BICONDITIONAL"

LOGIC_OPS = [
    LogicOp.NOT, LogicOp.AND, LogicOp.OR,
    LogicOp.IMPLIES, LogicOp.XOR, LogicOp.BICONDITIONAL
]

class SimplePredicate:
    """p(x,y) o p(x,const). Estructura serializable en dict."""
    def __init__(self, name, attr, op, lhs_var, rhs):
        self.type = "simple"
        self.name = name          # "p" (minúsculas)
        self.attr = attr          # columna del df
        self.op = op              # RelOp
        self.lhs_var = lhs_var    # "X"
        self.rhs = rhs            # {"type":"var","var":"Y"} o {"type":"const","value":..}

    def caption(self):
        # Notación tipo libro: p(x,y): x.attr op y.attr
        if self.rhs["type"] == "var":
            return f'{self.name}(x,y): "{self._describe_comparison(self.attr, self.op)}"'
        else:
            return f'{self.name}(x): "{self._describe_const(self.attr, self.op, self.rhs["value"])}"'

    def _describe_comparison(self, attr, op):
        attr_text = attr
        desc_map = {
            RelOp.GT: f"tiene mayor {attr_text} que y",
            RelOp.LT: f"tiene menor {attr_text} que y",
            RelOp.GE: f"tiene {attr_text} mayor o igual que y",
            RelOp.LE: f"tiene {attr_text} menor o igual que y",
            RelOp.EQ: f"tiene el mismo {attr_text} que y",
            RelOp.NE: f"tiene un {attr_text} diferente al de y",
            RelOp.CONTAINS: f"{attr_text} de x contiene al de y",
            RelOp.STARTS_WITH: f"{attr_text} de x comienza igual que el de y",
            RelOp.ENDS_WITH: f"{attr_text} de x termina igual que el de y",
        }
        return f"x {desc_map.get(op, f'tiene {attr_text} {op} y.{attr_text}')}."

    def _describe_const(self, attr, op, value):
        attr_text = attr
        desc_map = {
            RelOp.GT: f"tiene {attr_text} mayor que {value}",
            RelOp.LT: f"tiene {attr_text} menor que {value}",
            RelOp.GE: f"tiene {attr_text} mayor o igual que {value}",
            RelOp.LE: f"tiene {attr_text} menor o igual que {value}",
            RelOp.EQ: f"tiene {attr_text} igual a {value}",
            RelOp.NE: f"tiene {attr_text} diferente de {value}",
            RelOp.CONTAINS: f"{attr_text} contiene '{value}'",
            RelOp.STARTS_WITH: f"{attr_text} comienza con '{value}'",
            RelOp.ENDS_WITH: f"{attr_text} termina con '{value}'",
        }
        return f"x {desc_map.get(op, f'tiene {attr_text} {op} {value}')}."

class CompoundPredicate:
    """P(x,y) = NOT p(x,y)  |  p(x,y) AND q(x,y)  |  p(x,y) OR q(x,y) ..."""
    def __init__(self, name, op, args):
        self.type = "compound"
        self.name = name          # "P" (mayúsculas)
        self.op = op              # LogicOp
        self.args = args          # lista de nombres de predicados

    def caption(self):
        # Notación tipo libro: P(x,y): p(x,y) AND q(x,y)
        if self.op == LogicOp.NOT:
            # NOT p(x,y)
            return f"{self.name}(x,y): NOT({self.args[0]}(x,y))"
        if self.op == LogicOp.IMPLIES:
            # P(x,y): p(x,y) IMPLIES q(x,y)  (si solo hay un arg, p -> p)
            if len(self.args) == 1:
                return f"{self.name}(x,y): {self.args[0]}(x,y) IMPLIES {self.args[0]}(x,y)"
            return f"{self.name}(x,y): {self.args[0]}(x,y) IMPLIES {self.args[1]}(x,y)"
        if self.op == LogicOp.XOR:
            if len(self.args) == 2:
                return f"{self.name}(x,y): {self.args[0]}(x,y) XOR {self.args[1]}(x,y)"
        if self.op == LogicOp.BICONDITIONAL:
            if len(self.args) == 2:
                return f"{self.name}(x,y): {self.args[0]}(x,y) BICONDITIONAL {self.args[1]}(x,y)"
        # AND / OR genérico
        if len(self.args) == 2:
            return f"{self.name}(x,y): {self.args[0]}(x,y) {self.op} {self.args[1]}(x,y)"
        elif len(self.args) == 1:
            return f"{self.name}(x,y): {self.op}({self.args[0]}(x,y))"
        return f"{self.name}: {self.op}({', '.join(self.args)})"

# ----------------------------
#       App principal
# ----------------------------

class LogicQueryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Consultas Lógicas con Matrices")
        self.root.geometry("1400x900")

        self.data = None
        self.id_column = None       # columna que actúa como ID (p.ej. Fecha)
        self.predicates = {}        # nombre -> SimplePredicate | CompoundPredicate
        self.last_result_df = None  # para exportar

        # referencias a la tabla del dataset para resaltar ejemplos/contraejemplos
        self.data_tree = None
        self.row_id_map = {}

        self.setup_gui()

    # ---------- GUI ----------
    def setup_gui(self):
        main = ttk.Frame(self.root, padding="10")
        main.grid(row=0, column=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # --- fila botones dataset ---
        top = ttk.Frame(main)
        top.grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Button(top, text="Cargar Dataset", command=self.load_dataset).grid(row=0, column=0, padx=5)
        ttk.Button(top, text="Exportar Resultado", command=self.export_results).grid(row=0, column=1, padx=5)

        # --- tabla dataset ---
        self.table_frame = ttk.LabelFrame(main, text="Dataset")
        self.table_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)

        # --- constructor de predicado simple ---
        builder = ttk.LabelFrame(main, text="Predicado simple (FPS)", padding=8)
        builder.grid(row=2, column=0, sticky="nsew", padx=(0,8))
        builder.grid_columnconfigure(1, weight=1)

        self.attr_var = tk.StringVar()
        self.op_var = tk.StringVar(value=RelOp.GT)
        self.rhs_mode = tk.StringVar(value="var")  # Siempre usar modo var (dos variables)
        self.pred_name_var = tk.StringVar()
        self.preview_var = tk.StringVar(value="Vista previa...")

        rowb = 0
        ttk.Label(builder, text="Atributo:").grid(row=rowb, column=0, sticky="e", padx=4, pady=2)
        self.attr_combo = ttk.Combobox(builder, textvariable=self.attr_var, state="readonly", width=28)
        self.attr_combo.grid(row=rowb, column=1, sticky="w", pady=2)

        rowb += 1
        ttk.Label(builder, text="Operador:").grid(row=rowb, column=0, sticky="e", padx=4, pady=2)
        self.op_combo = ttk.Combobox(builder, textvariable=self.op_var, values=REL_OPS, state="readonly", width=12)
        self.op_combo.grid(row=rowb, column=1, sticky="w", pady=2)

        rowb += 1
        # Nota: Todas las FPS son de dos variables (x, y), el modo constante está deshabilitado
        ttk.Label(builder, text="Comparar con:").grid(row=rowb, column=0, sticky="e", padx=4, pady=2)
        ttk.Label(builder, text="Otra fila (y) - Siempre activo", foreground="gray").grid(row=rowb, column=1, sticky="w", pady=2)

        rowb += 1
        ttk.Label(builder, text="Nombre (FPS, minúsculas):").grid(row=rowb, column=0, sticky="e", padx=4, pady=2)
        self.pred_name_entry = ttk.Entry(builder, textvariable=self.pred_name_var, width=12)
        self.pred_name_entry.grid(row=rowb, column=1, sticky="w", pady=2)

        rowb += 1
        ttk.Label(builder, textvariable=self.preview_var).grid(row=rowb, column=0, columnspan=2, sticky="w", pady=(4,6))

        rowb += 1
        ttk.Button(builder, text="Guardar predicado", command=self.save_simple_predicate).grid(row=rowb, column=0, columnspan=2, pady=4)

        # --- biblioteca de predicados + compuestos (MÁS GRANDE) ---
        lib = ttk.LabelFrame(main, text="Biblioteca de predicados / Fórmulas (FPS/FPC)", padding=8)
        lib.grid(row=2, column=1, rowspan=2, sticky="nsew", pady=10, padx=(8,0))
        lib.grid_columnconfigure(0, weight=1)
        lib.grid_rowconfigure(0, weight=1)

        # Frame principal para la biblioteca
        lib_main = ttk.Frame(lib)
        lib_main.grid(row=0, column=0, sticky="nsew")
        lib.grid_rowconfigure(0, weight=1)
        lib.grid_columnconfigure(0, weight=1)

        # Lista de predicados (MÁS GRANDE)
        ttk.Label(lib_main, text="Predicados/Fórmulas guardados:").grid(row=0, column=0, sticky="w", pady=(0,5))
        self.pred_list = tk.Listbox(lib_main, height=12, width=50)
        self.pred_list.grid(row=1, column=0, sticky="nsew", pady=5)
        lib_main.grid_rowconfigure(1, weight=1)
        lib_main.grid_columnconfigure(0, weight=1)
        
        # Scrollbar para la lista
        sb = ttk.Scrollbar(lib_main, orient="vertical", command=self.pred_list.yview)
        self.pred_list.configure(yscrollcommand=sb.set)
        sb.grid(row=1, column=1, sticky="ns")
        
        # Botones para Ver Detalles, Editar y Ver Matriz
        button_frame = ttk.Frame(lib_main)
        button_frame.grid(row=2, column=0, sticky="w", pady=4)

        ttk.Button(button_frame, text="Ver Detalles", 
                   command=self.show_predicate_details_dialog).grid(row=0, column=0, padx=2)
        ttk.Button(button_frame, text="Editar", 
                   command=self.edit_predicate_dialog).grid(row=0, column=1, padx=2)
        ttk.Button(button_frame, text="Ver Matriz", 
                   command=self.show_predicate_matrix_dialog).grid(row=0, column=2, padx=2)

        # --- Constructor de fórmulas compuestas ---
        comp_frame = ttk.LabelFrame(lib_main, text="Constructor de Fórmulas Compuestas (FPC)", padding=8)
        comp_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(10,0))
        comp_frame.grid_columnconfigure(1, weight=1)

        # Variables para fórmulas compuestas
        self.comp_op_var = tk.StringVar(value=LogicOp.AND)
        self.comp_arg1 = tk.StringVar()
        self.comp_arg2 = tk.StringVar()
        self.comp_name = tk.StringVar()

        rowc = 0
        ttk.Label(comp_frame, text="Operador lógico:").grid(row=rowc, column=0, sticky="e", padx=4)
        ttk.Combobox(comp_frame, textvariable=self.comp_op_var, values=LOGIC_OPS, state="readonly", width=12).grid(row=rowc, column=1, sticky="w")

        rowc += 1
        ttk.Label(comp_frame, text="Arg1 (nombre FPS/FPC):").grid(row=rowc, column=0, sticky="e", padx=4)
        ttk.Entry(comp_frame, textvariable=self.comp_arg1, width=16).grid(row=rowc, column=1, sticky="w")

        rowc += 1
        ttk.Label(comp_frame, text="Arg2 (nombre FPS/FPC):").grid(row=rowc, column=0, sticky="e", padx=4)
        ttk.Entry(comp_frame, textvariable=self.comp_arg2, width=16).grid(row=rowc, column=1, sticky="w")

        rowc += 1
        ttk.Label(comp_frame, text="Nombre FPC (mayúsculas):").grid(row=rowc, column=0, sticky="e", padx=4)
        ttk.Entry(comp_frame, textvariable=self.comp_name, width=16).grid(row=rowc, column=1, sticky="w")

        rowc += 1
        ttk.Button(comp_frame, text="Guardar fórmula", command=self.save_compound).grid(row=rowc, column=0, columnspan=2, pady=6)

        # --- Operaciones con Matrices ---
        matrix_frame = ttk.LabelFrame(main, text="Operaciones con Matrices", padding=8)
        matrix_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=10)
        matrix_frame.grid_columnconfigure(1, weight=1)

        # Selección de predicados para operaciones
        ttk.Label(matrix_frame, text="Predicado 1:").grid(row=0, column=0, sticky="e", padx=4)
        self.matrix_pred1 = ttk.Combobox(matrix_frame, width=15, state="readonly")
        self.matrix_pred1.grid(row=0, column=1, sticky="w", pady=2)

        ttk.Label(matrix_frame, text="Predicado 2:").grid(row=1, column=0, sticky="e", padx=4)
        self.matrix_pred2 = ttk.Combobox(matrix_frame, width=15, state="readonly")
        self.matrix_pred2.grid(row=1, column=1, sticky="w", pady=2)

        # Operadores matriciales
        ttk.Label(matrix_frame, text="Operador:").grid(row=0, column=2, sticky="e", padx=4)
        self.matrix_op = ttk.Combobox(matrix_frame, values=["AND", "OR", "XOR", "IMPLIES", "BICONDITIONAL"], 
                                      state="readonly", width=12)
        self.matrix_op.grid(row=0, column=3, sticky="w", pady=2)

        ttk.Button(matrix_frame, text="Ver Matriz", command=self.show_predicate_matrix).grid(row=1, column=2, pady=2)
        ttk.Button(matrix_frame, text="Aplicar Operador", command=self.apply_matrix_operator).grid(row=1, column=3, pady=2)

        # Botón para NOT (solo necesita un predicado)
        ttk.Label(matrix_frame, text="Operador Unario:").grid(row=2, column=0, sticky="e", padx=4)
        self.not_pred = ttk.Combobox(matrix_frame, width=15, state="readonly")
        self.not_pred.grid(row=2, column=1, sticky="w", pady=2)
        ttk.Button(matrix_frame, text="Aplicar NOT", command=self.apply_matrix_not).grid(row=2, column=2, pady=2)

        # --- consultas cuantificadas / ejecución ---
        runf = ttk.LabelFrame(main, text="Consulta cuantificada", padding=8)
        runf.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=10)
        runf.grid_columnconfigure(1, weight=1)

        ttk.Label(runf, text="Predicado/Fórmula (nombre):").grid(row=0, column=0, sticky="e", padx=4)
        self.run_formula_name = tk.Entry(runf, width=18)
        self.run_formula_name.grid(row=0, column=1, sticky="w")

        ttk.Label(runf, text="Cuantificador X:").grid(row=1, column=0, sticky="e", padx=4)
        self.quant_x = tk.StringVar(value="∀")
        ttk.Combobox(runf, textvariable=self.quant_x, values=["∀","∃","(ninguno)"], state="readonly", width=10).grid(row=1, column=1, sticky="w")

        ttk.Label(runf, text="Cuantificador Y:").grid(row=2, column=0, sticky="e", padx=4)
        self.quant_y = tk.StringVar(value="∃")
        ttk.Combobox(runf, textvariable=self.quant_y, values=["∀","∃","(ninguno)"], state="readonly", width=10).grid(row=2, column=1, sticky="w")

        ttk.Button(runf, text="Ejecutar", command=self.execute_quantified_query).grid(row=0, column=2, rowspan=3, padx=10)

        # --- resultados ---
        result_frame = ttk.LabelFrame(main, text="Resultados", padding=6)
        result_frame.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(10,0))
        result_frame.grid_columnconfigure(0, weight=1)
        result_frame.grid_rowconfigure(0, weight=1)

        self.result_tree = ttk.Treeview(result_frame, show="headings")
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        y2 = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_tree.yview)
        x2 = ttk.Scrollbar(result_frame, orient="horizontal", command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=y2.set, xscrollcommand=x2.set)
        y2.grid(row=0, column=1, sticky="ns")
        x2.grid(row=1, column=0, sticky="ew")

        self.status_var = tk.StringVar(value="Listo.")
        ttk.Label(main, textvariable=self.status_var).grid(row=7, column=0, columnspan=2, sticky="w", pady=4)

        # eventos para vista previa
        for var in (self.attr_var, self.op_var):
            var.trace_add("write", lambda *args: self.update_preview())

        # Configurar pesos de filas y columnas para mejor distribución
        main.grid_rowconfigure(1, weight=2)  # Tabla dataset
        main.grid_rowconfigure(2, weight=1)  # Constructor + Biblioteca
        main.grid_rowconfigure(4, weight=0)  # Operaciones matrices
        main.grid_rowconfigure(5, weight=0)  # Consultas cuantificadas
        main.grid_rowconfigure(6, weight=1)  # Resultados

    # ---------- dataset ----------
    def load_dataset(self):
        filename = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if not filename:
            return
        try:
            if filename.endswith('.csv'):
                self.data = pd.read_csv(filename)
            elif filename.endswith('.xlsx'):
                self.data = pd.read_excel(filename)
            else:
                self.data = pd.read_csv(filename)
            
            # Procesamiento mejorado de fechas
            date_columns = [col for col in self.data.columns if 'date' in col.lower() or 'fecha' in col.lower()]
            for col in date_columns:
                try:
                    self.data[col] = pd.to_datetime(self.data[col], errors='coerce')
                except Exception:
                    pass

            cols = list(self.data.columns)
            self.attr_combo["values"] = cols
            
            # Elección inteligente de ID por defecto
            if "Date" in cols:
                self.id_column = "Date"
            elif "Fecha" in cols:
                self.id_column = "Fecha"
            elif any(self.data[col].is_unique for col in cols):
                for col in cols:
                    if self.data[col].is_unique:
                        self.id_column = col
                        break
                else:
                    self.id_column = cols[0]
            else:
                self.id_column = cols[0]

            self.display_data(self.data)
            self.update_preview()
            messagebox.showinfo(
                "Éxito",
                f"Dataset cargado: {len(self.data)} filas, {len(cols)} columnas\nID automático: {self.id_column}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar el archivo: {str(e)}")

    def display_data(self, df):
        # limpiar tabla
        for w in self.table_frame.winfo_children():
            w.destroy()
        tree = ttk.Treeview(self.table_frame, show="headings")
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(self.table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        cols = list(df.columns)
        tree["columns"] = cols
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120)

        # guardar referencia para resaltar
        self.data_tree = tree
        self.row_id_map = {}

        # etiquetas para ejemplos/contraejemplos
        self.data_tree.tag_configure("example", background="lightgreen")
        self.data_tree.tag_configure("counterexample", background="lightcoral")

        # paginado ligero: primeras 2000 filas
        max_rows = min(len(df), 2000)
        for _, row in df.iloc[:max_rows].iterrows():
            values = list(row)
            item_id = tree.insert("", "end", values=values)
            if self.id_column in df.columns:
                id_val = row[self.id_column]
                self.row_id_map[id_val] = item_id

    # ---------- utilidades ----------
    def update_preview(self):
        attr = self.attr_var.get() or "<atributo>"
        op  = self.op_var.get() or ">"
        # Todas las FPS son de dos variables (x, y)
        rhs_txt = f"y.{attr}"
        self.preview_var.set(f"Vista previa: p(x,y): x.{attr} {op} {rhs_txt}")

    def _parse_const_for_series(self, series, raw):
        """Convierte constantes según dtype de la serie; si falla, devuelve string."""
        if raw is None or raw == "":
            raise ValueError("Constante vacía.")
        s = str(raw).strip()

        # booleanos
        low = s.lower()
        if pd.api.types.is_bool_dtype(series):
            if low in {"true","1","t","sí","si","y"}: return True
            if low in {"false","0","f","no","n"}: return False
            raise ValueError("El valor debe ser booleano (true/false)")

        # numéricos
        if pd.api.types.is_integer_dtype(series):
            return int(float(s))
        if pd.api.types.is_float_dtype(series):
            return float(s)

        # fechas
        if pd.api.types.is_datetime64_any_dtype(series):
            try:
                return pd.to_datetime(s, dayfirst=True, errors="raise")
            except Exception:
                pass

        # texto por defecto
        return s

    def _compare(self, a, b, op):
        try:
            if pd.isna(a) or pd.isna(b):
                return False
        except Exception:
            pass
        if op == RelOp.EQ: return a == b
        if op == RelOp.NE: return a != b
        if op == RelOp.GT: return a >  b
        if op == RelOp.LT: return a <  b
        if op == RelOp.GE: return a >= b
        if op == RelOp.LE: return a <= b
        if op == RelOp.CONTAINS:
            return str(b).lower() in str(a).lower()
        if op == RelOp.STARTS_WITH:
            return str(a).lower().startswith(str(b).lower())
        if op == RelOp.ENDS_WITH:
            return str(a).lower().endswith(str(b).lower())
        raise ValueError(f"Operador no válido: {op}")

    def _get_attr_map(self, attr):
        """Devuelve dict id -> valor atributo para mostrar en matrices."""
        if self.data is None or self.id_column not in self.data.columns or attr not in self.data.columns:
            return {}
        return dict(zip(self.data[self.id_column], self.data[attr]))

    def _resolve_predicate_name_input(self, name):
        """Intenta resolver nombres sin importar mayúsculas/minúsculas."""
        if not name:
            return None
        if name in self.predicates:
            return name
        low = name.lower()
        up = name.upper()
        if low in self.predicates:
            return low
        if up in self.predicates:
            return up
        return None

    def _rename_predicate(self, old_name, new_name):
        """Renombra un predicado en self.predicates y actualiza referencias."""
        if old_name == new_name or old_name not in self.predicates:
            return
        pred = self.predicates.pop(old_name)
        pred.name = new_name
        self.predicates[new_name] = pred
        # Actualizar referencias en todas las fórmulas compuestas
        for p in self.predicates.values():
            if getattr(p, "type", None) == "compound":
                p.args = [new_name if a == old_name else a for a in p.args]

    def highlight_dataset_rows(self, example_ids=None, counterexample_ids=None):
        """Resalta filas del dataset como ejemplos (verde) y contraejemplos (rojo)."""
        if self.data_tree is None:
            return
        example_ids = set(example_ids or [])
        counterexample_ids = set(counterexample_ids or [])

        # limpiar tags
        for item in self.data_tree.get_children():
            self.data_tree.item(item, tags=())

        # ejemplos
        for id_val in example_ids:
            item = self.row_id_map.get(id_val)
            if item:
                self.data_tree.item(item, tags=("example",))

        # contraejemplos (tienen prioridad)
        for id_val in counterexample_ids:
            item = self.row_id_map.get(id_val)
            if item:
                self.data_tree.item(item, tags=("counterexample",))

    # ---------- guardar predicados ----------
    def save_simple_predicate(self):
        if self.data is None:
            messagebox.showerror("Error", "Carga un dataset primero.")
            return
        if not self.id_column:
            messagebox.showerror("Error", "No se pudo determinar la columna ID automáticamente.")
            return

        name = self.pred_name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Asigna un nombre al predicado (p.ej., p, q).")
            return
        name = name.lower()  # FPS en minúsculas
        if name in self.predicates:
            messagebox.showerror("Error", f"Ya existe un predicado llamado '{name}'.")
            return

        attr = self.attr_var.get()
        if not attr:
            messagebox.showerror("Error", "Selecciona un atributo.")
            return
        lhs = "X"
        op  = self.op_var.get()
        if op not in REL_OPS:
            messagebox.showerror("Error", "Operador inválido.")
            return

        # Todas las FPS son de dos variables (x, y) - modo constante deshabilitado
        rhs = {"type":"var","var": "Y"}

        sp = SimplePredicate(name, attr, op, lhs, rhs)
        self.predicates[name] = sp
        self.pred_list.insert(tk.END, f"{name} (simple) :: {sp.caption()}")
        self.status_var.set(f"Predicado '{name}' guardado.")
        
        # Limpiar campos después de guardar
        self.pred_name_var.set("")
        
        # Actualizar combos de matrices
        self.update_predicate_combos()

    def save_compound(self):
        name = self.comp_name.get().strip()
        if not name:
            messagebox.showerror("Error", "Asigna un nombre a la fórmula compuesta.")
            return
        name = name.upper()  # FPC en mayúsculas
        if name in self.predicates:
            messagebox.showerror("Error", f"Ya existe un predicado/fórmula '{name}'.")
            return

        op = self.comp_op_var.get()
        a1_raw = self.comp_arg1.get().strip()
        a2_raw = self.comp_arg2.get().strip()

        a1 = self._resolve_predicate_name_input(a1_raw)
        a2 = self._resolve_predicate_name_input(a2_raw) if a2_raw else None

        if op in [LogicOp.NOT, LogicOp.IMPLIES]:
            if not a1:
                messagebox.showerror("Error", f"{op} requiere Arg1 válido.")
                return
            args = [a1]
            if op == LogicOp.IMPLIES and a2:
                args.append(a2)
        else:
            if not a1 or not a2:
                messagebox.showerror("Error", f"{op} requiere Arg1 y Arg2.")
                return
            if a1 not in self.predicates or a2 not in self.predicates:
                messagebox.showerror("Error", "Arg1 o Arg2 no existen en la biblioteca.")
                return
            args = [a1, a2]

        cp = CompoundPredicate(name, op, args)
        self.predicates[name] = cp
        self.pred_list.insert(tk.END, f"{name} (compuesta) :: {cp.caption()}")
        self.status_var.set(f"Fórmula '{name}' guardada.")
        
        # Limpiar campos después de guardar
        self.comp_name.set("")
        self.comp_arg1.set("")
        self.comp_arg2.set("")
        
        # Actualizar combos de matrices
        self.update_predicate_combos()

    # ---------- NUEVO: Ver Matriz de cualquier proposición ----------
    def show_predicate_matrix_dialog(self):
        """Muestra diálogo para seleccionar y ver matriz de cualquier predicado"""
        if not self.predicates:
            messagebox.showinfo("Información", "No hay predicados definidos")
            return
        
        matrix_window = tk.Toplevel(self.root)
        matrix_window.title("Ver Matriz de Predicado")
        matrix_window.geometry("300x150")
        
        ttk.Label(matrix_window, text="Seleccionar predicado:").pack(pady=10)
        
        pred_var = tk.StringVar()
        pred_combo = ttk.Combobox(matrix_window, textvariable=pred_var, 
                                  values=list(self.predicates.keys()), state="readonly")
        pred_combo.pack(pady=5)
        
        def show_matrix():
            pred_name = pred_var.get()
            if not pred_name:
                messagebox.showerror("Error", "Selecciona un predicado")
                return
            
            if self.data is not None and len(self.data) > 50:
                if not messagebox.askyesno(
                    "Advertencia", 
                    f"El dataset tiene {len(self.data)} filas. "
                    f"Generar la matriz puede tomar tiempo. ¿Continuar?"
                ):
                    return
            
            matrix, ids = self.generate_truth_matrix(pred_name)
            if matrix is not None:
                self.display_matrix(matrix, ids, ids, f"Matriz de {pred_name}", predicate_name=pred_name)
                matrix_window.destroy()
        
        ttk.Button(matrix_window, text="Ver Matriz", command=show_matrix).pack(pady=10)

    def show_predicate_details_dialog(self):
        """Muestra diálogo para ver detalles de cualquier predicado"""
        if not self.predicates:
            messagebox.showinfo("Información", "No hay predicados definidos")
            return
        
        details_window = tk.Toplevel(self.root)
        details_window.title("Ver Detalles de Predicado")
        details_window.geometry("400x300")
        
        ttk.Label(details_window, text="Seleccionar predicado:").pack(pady=10)
        
        pred_var = tk.StringVar()
        pred_combo = ttk.Combobox(details_window, textvariable=pred_var, 
                                  values=list(self.predicates.keys()), state="readonly")
        pred_combo.pack(pady=5)
        
        details_frame = ttk.Frame(details_window)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        details_text = tk.Text(details_frame, height=10, width=50)
        scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=details_text.yview)
        details_text.configure(yscrollcommand=scrollbar.set)
        
        details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def update_details(*args):
            pred_name = pred_var.get()
            if pred_name in self.predicates:
                pred = self.predicates[pred_name]
                details_text.delete(1.0, tk.END)
                
                if pred.type == "simple":
                    details_text.insert(tk.END, f"Nombre: {pred.name}\n")
                    details_text.insert(tk.END, f"Tipo: Predicado Simple (FPS)\n")
                    details_text.insert(tk.END, f"Atributo: {pred.attr}\n")
                    details_text.insert(tk.END, f"Operador: {pred.op}\n")
                    details_text.insert(tk.END, f"Variable izquierda: {pred.lhs_var}\n")
                    
                    if pred.rhs["type"] == "var":
                        details_text.insert(tk.END, f"Variable derecha: {pred.rhs['var']}\n")
                    else:
                        details_text.insert(tk.END, f"Constante: {pred.rhs['value']}\n")
                        
                    details_text.insert(tk.END, f"\nFórmula: {pred.caption()}")
                    
                else:  # compound
                    details_text.insert(tk.END, f"Nombre: {pred.name}\n")
                    details_text.insert(tk.END, f"Tipo: Fórmula Compuesta (FPC)\n")
                    details_text.insert(tk.END, f"Operador: {pred.op}\n")
                    details_text.insert(tk.END, f"Argumentos: {pred.args}\n")
                    details_text.insert(tk.END, f"\nFórmula: {pred.caption()}")
        
        pred_var.trace_add("write", update_details)
        
        ttk.Button(details_window, text="Cerrar", command=details_window.destroy).pack(pady=10)

    # ---------- Editar Predicado ----------
    def edit_predicate_dialog(self):
        """Permite editar un predicado existente"""
        if not self.predicates:
            messagebox.showinfo("Información", "No hay predicados definidos")
            return
        
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Editar Predicado")
        edit_window.geometry("400x300")
        
        ttk.Label(edit_window, text="Seleccionar predicado a editar:").pack(pady=10)
        
        pred_var = tk.StringVar()
        pred_combo = ttk.Combobox(edit_window, textvariable=pred_var, 
                                  values=list(self.predicates.keys()), state="readonly")
        pred_combo.pack(pady=5)
        
        edit_frame = ttk.Frame(edit_window)
        edit_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def load_predicate_for_editing():
            pred_name = pred_var.get()
            if pred_name not in self.predicates:
                return
            
            pred = self.predicates[pred_name]
            
            for widget in edit_frame.winfo_children():
                widget.destroy()
            
            if pred.type == "simple":
                self._setup_simple_predicate_editing(edit_frame, pred, pred_name)
            else:
                self._setup_compound_predicate_editing(edit_frame, pred, pred_name)
        
        pred_var.trace_add("write", lambda *args: load_predicate_for_editing())
        
        ttk.Button(edit_window, text="Cerrar", command=edit_window.destroy).pack(pady=10)

    def _setup_simple_predicate_editing(self, parent, pred, original_name):
        """Configura interfaz para editar predicado simple"""
        row = 0
        
        ttk.Label(parent, text="Nombre (minúsculas):").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        name_var = tk.StringVar(value=pred.name)
        name_entry = ttk.Entry(parent, textvariable=name_var, width=20)
        name_entry.grid(row=row, column=1, sticky="w", pady=2)
        row += 1
        
        ttk.Label(parent, text="Atributo:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        attr_var = tk.StringVar(value=pred.attr)
        attr_combo = ttk.Combobox(
            parent, textvariable=attr_var, 
            values=list(self.data.columns) if self.data is not None else [],
            state="readonly", width=20
        )
        attr_combo.grid(row=row, column=1, sticky="w", pady=2)
        row += 1
        
        ttk.Label(parent, text="Operador:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        op_var = tk.StringVar(value=pred.op)
        op_combo = ttk.Combobox(parent, textvariable=op_var, values=REL_OPS, 
                                state="readonly", width=20)
        op_combo.grid(row=row, column=1, sticky="w", pady=2)
        row += 1
        
        # Todas las FPS son de dos variables (x, y) - modo constante deshabilitado
        ttk.Label(parent, text="Comparar con:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        ttk.Label(parent, text="Otra fila (y) - Siempre activo", foreground="gray").grid(row=row, column=1, sticky="w", pady=2)
        row += 1
        
        def save_changes():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showerror("Error", "El nombre no puede estar vacío")
                return
            new_name = new_name.lower()
            
            if new_name != original_name and new_name in self.predicates:
                messagebox.showerror("Error", f"Ya existe un predicado llamado '{new_name}'")
                return
            
            pred.attr = attr_var.get()
            pred.op = op_var.get()
            # Todas las FPS son de dos variables (x, y) - modo constante deshabilitado
            pred.rhs = {"type": "var", "var": "Y"}
            
            if new_name != original_name:
                self._rename_predicate(original_name, new_name)
            
            self._refresh_predicate_list()
            parent.winfo_toplevel().destroy()
            messagebox.showinfo("Éxito", f"Predicado '{new_name}' actualizado")
        
        ttk.Button(parent, text="Guardar Cambios", command=save_changes).grid(
            row=row, column=0, columnspan=2, pady=10
        )

    def _setup_compound_predicate_editing(self, parent, pred, original_name):
        """Configura interfaz para editar predicado compuesto"""
        row = 0
        
        ttk.Label(parent, text="Nombre (mayúsculas):").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        name_var = tk.StringVar(value=pred.name)
        name_entry = ttk.Entry(parent, textvariable=name_var, width=20)
        name_entry.grid(row=row, column=1, sticky="w", pady=2)
        row += 1
        
        ttk.Label(parent, text="Operador:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        op_var = tk.StringVar(value=pred.op)
        op_combo = ttk.Combobox(parent, textvariable=op_var, values=LOGIC_OPS, 
                                state="readonly", width=20)
        op_combo.grid(row=row, column=1, sticky="w", pady=2)
        row += 1
        
        ttk.Label(parent, text="Argumento 1:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        arg1_var = tk.StringVar(value=pred.args[0] if pred.args else "")
        arg1_combo = ttk.Combobox(
            parent, textvariable=arg1_var, 
            values=list(self.predicates.keys()), width=20
        )
        arg1_combo.grid(row=row, column=1, sticky="w", pady=2)
        row += 1
        
        ttk.Label(parent, text="Argumento 2:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        arg2_var = tk.StringVar(value=pred.args[1] if len(pred.args) > 1 else "")
        arg2_combo = ttk.Combobox(
            parent, textvariable=arg2_var, 
            values=list(self.predicates.keys()), width=20
        )
        arg2_combo.grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        def on_op_change(*args):
            op = op_var.get()
            if op == LogicOp.NOT:
                arg2_combo.config(state="disabled")
            else:
                arg2_combo.config(state="normal")

        op_var.trace_add("write", on_op_change)
        on_op_change()

        def save_changes():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showerror("Error", "El nombre no puede estar vacío")
                return
            new_name = new_name.upper()
            
            if new_name != original_name and new_name in self.predicates:
                messagebox.showerror("Error", f"Ya existe un predicado llamado '{new_name}'")
                return
            
            new_op = op_var.get()
            a1 = self._resolve_predicate_name_input(arg1_var.get().strip())
            a2 = self._resolve_predicate_name_input(arg2_var.get().strip()) if arg2_var.get().strip() else None

            if new_op in [LogicOp.NOT, LogicOp.IMPLIES]:
                if not a1:
                    messagebox.showerror("Error", "Argumento 1 no válido")
                    return
                new_args = [a1]
                if new_op == LogicOp.IMPLIES and a2:
                    new_args.append(a2)
            else:
                if not a1 or not a2:
                    messagebox.showerror("Error", "Se requieren 2 argumentos para este operador")
                    return
                if a1 not in self.predicates or a2 not in self.predicates:
                    messagebox.showerror("Error", "Argumentos no válidos")
                    return
                new_args = [a1, a2]

            pred.op = new_op
            pred.args = new_args

            if new_name != original_name:
                self._rename_predicate(original_name, new_name)
            
            self._refresh_predicate_list()
            parent.winfo_toplevel().destroy()
            messagebox.showinfo("Éxito", f"Fórmula '{new_name}' actualizada")
        
        ttk.Button(parent, text="Guardar Cambios", command=save_changes).grid(
            row=row, column=0, columnspan=2, pady=10
        )

    def _refresh_predicate_list(self):
        """Actualiza la lista de predicados en la interfaz"""
        self.pred_list.delete(0, tk.END)
        for name, pred in self.predicates.items():
            if pred.type == "simple":
                self.pred_list.insert(tk.END, f"{name} (simple) :: {pred.caption()}")
            else:
                self.pred_list.insert(tk.END, f"{name} (compuesta) :: {pred.caption()}")
        
        self.update_predicate_combos()

    # ---------- evaluación ----------
    def _eval_predicate(self, name, x=None, y=None):
        """Evalúa un predicado/fórmula dados IDs concretos (x,y)."""
        pred = self.predicates[name]
        if pred.type == "simple":
            series = self.data[pred.attr]
            if x is None:
                return False
            # valor de X
            try:
                lv = series.loc[self.data[self.id_column] == x].iloc[0]
            except Exception:
                return False

            # valor de Y o constante
            if pred.rhs["type"] == "var":
                if y is None:
                    return False
                try:
                    rv = series.loc[self.data[self.id_column] == y].iloc[0]
                except Exception:
                    return False
            else:
                rv = pred.rhs["value"]

            try:
                return self._compare(lv, rv, pred.op)
            except Exception:
                return False

        # compuesta
        if pred.type == "compound":
            if pred.op == LogicOp.NOT:
                return not self._eval_predicate(pred.args[0], x, y)
            if pred.op == LogicOp.AND:
                return self._eval_predicate(pred.args[0], x, y) and self._eval_predicate(pred.args[1], x, y)
            if pred.op == LogicOp.OR:
                return self._eval_predicate(pred.args[0], x, y) or self._eval_predicate(pred.args[1], x, y)
            if pred.op == LogicOp.IMPLIES:
                return (not self._eval_predicate(pred.args[0], x, y)) or \
                    self._eval_predicate(pred.args[1] if len(pred.args) > 1 else pred.args[0], x, y)
            if pred.op == LogicOp.XOR:
                p_val = self._eval_predicate(pred.args[0], x, y)
                q_val = self._eval_predicate(pred.args[1], x, y)
                return (p_val or q_val) and not (p_val and q_val)
            if pred.op == LogicOp.BICONDITIONAL:
                p_val = self._eval_predicate(pred.args[0], x, y)
                q_val = self._eval_predicate(pred.args[1], x, y)
                return p_val == q_val
            raise ValueError("Operador lógico no soportado.")
        return False

    def _domains(self):
        """Devuelve dominios de X e Y (para v1: todos los IDs)."""
        if self.data is None or not self.id_column:
            return [], []
        ids = list(self.data[self.id_column])
        return ids, ids

    # ---------- MATRICES NxN (OPTIMIZADO) ----------
    def generate_truth_matrix(self, predicate_name):
        """Genera matriz NxN de verdad para un predicado."""
        if self.data is None or predicate_name not in self.predicates:
            return None, []
        
        ids = self._get_domain_ids()
        n_original = len(ids)
        n = n_original
        
        max_size = 100
        if n > max_size:
            ids = ids[:max_size]
            n = max_size
            messagebox.showwarning(
                "Advertencia", 
                f"Dataset muy grande. Mostrando matriz {max_size}x{max_size} en lugar de {n_original}x{n_original}"
            )
        
        matrix = np.zeros((n, n), dtype=bool)
        
        pred = self.predicates[predicate_name]
        
        if n > 20:
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Generando Matriz")
            progress_window.geometry("300x100")
            ttk.Label(progress_window, text="Generando matriz, por favor espere...").pack(pady=10)
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=n)
            progress_bar.pack(pady=10, padx=20, fill=tk.X)
            progress_window.update()
        
        for i, x in enumerate(ids):
            for j, y in enumerate(ids):
                matrix[i][j] = self._eval_predicate(predicate_name, x, y)
            if n > 20:
                progress_var.set(i + 1)
                progress_window.update()
        
        if n > 20:
            progress_window.destroy()
        
        return matrix, ids

    def _get_domain_ids(self):
        """Obtiene la lista de IDs del dominio"""
        if self.data is None or not self.id_column:
            return []
        return list(self.data[self.id_column])

    def display_matrix(self, matrix, row_labels, col_labels, title, predicate_name=None):
        """Muestra una matriz en una ventana flotante con información adicional."""
        matrix_window = tk.Toplevel(self.root)
        matrix_window.title(f"Matriz: {title}")
        matrix_window.geometry("1000x650")
        
        main_frame = ttk.Frame(matrix_window, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        matrix_window.grid_rowconfigure(0, weight=1)
        matrix_window.grid_columnconfigure(0, weight=1)

        # Determinar predicado y preparar encabezados
        if predicate_name and predicate_name in self.predicates:
            pred = self.predicates[predicate_name]
        else:
            pred = None
        header_lines = [title]
        if pred is not None:
            header_lines = [f"Predicado {pred.name}: {pred.caption()}"]
        if self.id_column:
            header_lines.append(f"Columna ID: {self.id_column}")
        ttk.Label(
            main_frame,
            text="\n".join(header_lines),
            font=("TkDefaultFont", 10, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Ajuste de orientación: columnas corresponden a X, filas corresponden a Y
        display_cols = list(row_labels)
        display_rows = list(col_labels)
        matrix_to_render = matrix.T

        current_row = 1

        # Parte superior: tablas de valores de atributo para FPS
        if pred is not None and getattr(pred, "type", None) == "simple" and pred.rhs["type"] == "var":
            attr = pred.attr
            attr_map = self._get_attr_map(attr)

            info_frame = ttk.Frame(main_frame)
            info_frame.grid(row=current_row, column=0, sticky="ew", pady=(0,10))
            info_frame.grid_columnconfigure(0, weight=1)
            info_frame.grid_columnconfigure(1, weight=1)

            ttk.Label(info_frame, text=f"Valores de atributo para X (x.{attr}):").grid(row=0, column=0, sticky="w")
            ttk.Label(info_frame, text=f"Valores de atributo para Y (y.{attr}):").grid(row=0, column=1, sticky="w")

            x_tree = ttk.Treeview(info_frame, show="headings", height=min(len(display_cols), 8))
            x_tree["columns"] = ("var", "id", "val")
            x_tree.heading("var", text="Var")
            x_tree.heading("id", text="ID")
            x_tree.heading("val", text=f"{attr}")
            x_tree.column("var", width=40)
            x_tree.column("id", width=120)
            x_tree.column("val", width=180)
            x_tree.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

            y_tree = ttk.Treeview(info_frame, show="headings", height=min(len(display_rows), 8))
            y_tree["columns"] = ("var", "id", "val")
            y_tree.heading("var", text="Var")
            y_tree.heading("id", text="ID")
            y_tree.heading("val", text=f"{attr}")
            y_tree.column("var", width=40)
            y_tree.column("id", width=120)
            y_tree.column("val", width=180)
            y_tree.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

            for xid in display_cols:
                x_tree.insert("", "end", values=("x", xid, attr_map.get(xid, "")))
            for yid in display_rows:
                y_tree.insert("", "end", values=("y", yid, attr_map.get(yid, "")))

            current_row += 1  # siguiente fila para la matriz

        # Canvas con scroll para la matriz
        canvas = tk.Canvas(main_frame)
        scrollbar_y = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(main_frame, orient="horizontal", command=canvas.xview)
        
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        n_rows, n_cols = matrix_to_render.shape

        # Etiquetas de ejes
        axis_y = tk.Label(
            scrollable_frame,
            text="y",
            bg="lightgrey",
            width=12,
            relief="raised",
            borderwidth=1
        )
        axis_y.grid(row=0, column=0, padx=1, pady=1)

        axis_x = tk.Label(
            scrollable_frame,
            text="x",
            bg="lightgrey",
            width=12,
            relief="raised",
            borderwidth=1
        )
        axis_x.grid(row=0, column=1, columnspan=n_cols, sticky="we", padx=1, pady=1)

        # Encabezados de columnas: IDs de X
        for j, col_label in enumerate(display_cols):
            label = tk.Label(scrollable_frame, text=f"x={col_label}", bg="lightblue", width=12, relief="raised")
            label.grid(row=1, column=j+1, padx=1, pady=1)

        # Filas con datos (IDs de Y)
        for i in range(n_rows):
            row_label = tk.Label(scrollable_frame, text=f"y={display_rows[i]}", bg="lightblue", width=12, relief="raised")
            row_label.grid(row=i+2, column=0, padx=1, pady=1)
            
            for j in range(n_cols):
                value = matrix_to_render[i][j]
                bg_color = "lightgreen" if value else "lightcoral"
                text = "V" if value else "F"
                cell = tk.Label(
                    scrollable_frame, text=text, bg=bg_color, width=4, height=1,
                    relief="raised", borderwidth=1
                )
                cell.grid(row=i+2, column=j+1, padx=1, pady=1)
        
        canvas.grid(row=current_row, column=0, sticky="nsew")
        scrollbar_y.grid(row=current_row, column=1, sticky="ns")
        scrollbar_x.grid(row=current_row+1, column=0, sticky="ew")

        main_frame.grid_rowconfigure(current_row, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

    # ---------- OPERADORES MATRICIALES ----------
    def matrix_AND(self, matrix1, matrix2):
        if matrix1.shape != matrix2.shape:
            raise ValueError("Las matrices deben tener la misma dimensión")
        return np.logical_and(matrix1, matrix2)

    def matrix_OR(self, matrix1, matrix2):
        if matrix1.shape != matrix2.shape:
            raise ValueError("Las matrices deben tener la misma dimensión")
        return np.logical_or(matrix1, matrix2)

    def matrix_NOT(self, matrix):
        return np.logical_not(matrix)

    def matrix_XOR(self, matrix1, matrix2):
        if matrix1.shape != matrix2.shape:
            raise ValueError("Las matrices deben tener la misma dimensión")
        return np.logical_xor(matrix1, matrix2)

    def matrix_IMPLIES(self, matrix1, matrix2):
        if matrix1.shape != matrix2.shape:
            raise ValueError("Las matrices deben tener la misma dimensión")
        return np.logical_or(np.logical_not(matrix1), matrix2)

    def matrix_BICONDITIONAL(self, matrix1, matrix2):
        if matrix1.shape != matrix2.shape:
            raise ValueError("Las matrices deben tener la misma dimensión")
        return np.logical_and(
            self.matrix_IMPLIES(matrix1, matrix2),
            self.matrix_IMPLIES(matrix2, matrix1)
        )

    def update_predicate_combos(self):
        pred_names = list(self.predicates.keys())
        self.matrix_pred1['values'] = pred_names
        self.matrix_pred2['values'] = pred_names
        self.not_pred['values'] = pred_names

    def show_predicate_matrix(self):
        """Muestra la matriz de verdad de un predicado seleccionado en el panel de matrices"""
        pred_name = self.matrix_pred1.get()
        if not pred_name or pred_name not in self.predicates:
            messagebox.showerror("Error", "Selecciona un predicado válido")
            return
        
        if self.data is not None and len(self.data) > 50:
            if not messagebox.askyesno(
                "Advertencia", 
                f"El dataset tiene {len(self.data)} filas. "
                f"Generar la matriz puede tomar tiempo. ¿Continuar?"
            ):
                return
        
        matrix, ids = self.generate_truth_matrix(pred_name)
        if matrix is not None:
            self.display_matrix(matrix, ids, ids, f"Matriz de {pred_name}", predicate_name=pred_name)

    def apply_matrix_operator(self):
        """Aplica operador binario a dos matrices y guarda con nombre (FPC nueva)"""
        pred1 = self.matrix_pred1.get()
        pred2 = self.matrix_pred2.get()
        op = self.matrix_op.get()
        
        if not all([pred1, pred2, op]):
            messagebox.showerror("Error", "Selecciona dos predicados y un operador")
            return
        
        if self.data is not None and len(self.data) > 50:
            if not messagebox.askyesno(
                "Advertencia", 
                f"El dataset tiene {len(self.data)} filas. "
                f"Generar las matrices puede tomar tiempo. ¿Continuar?"
            ):
                return
        
        result_name = simpledialog.askstring(
            "Nombre del Resultado", 
            "Ingresa un nombre para guardar el resultado (FPC, mayúsculas):",
            parent=self.root
        )
        if not result_name:
            return
        
        result_name = result_name.upper()
        if result_name in self.predicates:
            messagebox.showerror("Error", f"Ya existe un predicado llamado '{result_name}'")
            return
        
        matrix1, ids1 = self.generate_truth_matrix(pred1)
        matrix2, ids2 = self.generate_truth_matrix(pred2)
        
        if matrix1 is None or matrix2 is None:
            messagebox.showerror("Error", "No se pudieron generar las matrices")
            return
        
        try:
            if op == "AND":
                result = self.matrix_AND(matrix1, matrix2)
                logic_op = LogicOp.AND
            elif op == "OR":
                result = self.matrix_OR(matrix1, matrix2)
                logic_op = LogicOp.OR
            elif op == "XOR":
                result = self.matrix_XOR(matrix1, matrix2)
                logic_op = LogicOp.XOR
            elif op == "IMPLIES":
                result = self.matrix_IMPLIES(matrix1, matrix2)
                logic_op = LogicOp.IMPLIES
            elif op == "BICONDITIONAL":
                result = self.matrix_BICONDITIONAL(matrix1, matrix2)
                logic_op = LogicOp.BICONDITIONAL
            else:
                messagebox.showerror("Error", "Operador no válido")
                return
            
            comp_pred = CompoundPredicate(result_name, logic_op, [pred1, pred2])
            self.predicates[result_name] = comp_pred
            
            self.pred_list.insert(tk.END, f"{result_name} (compuesta) :: {comp_pred.caption()}")
            self.update_predicate_combos()
            
            self.display_matrix(result, ids1, ids2, f"{result_name} ({pred1} {op} {pred2})", predicate_name=result_name)
            messagebox.showinfo("Éxito", f"Operación guardada como: {result_name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error aplicando operador: {e}")

    def apply_matrix_not(self):
        """Aplica NOT a una matriz y guarda con nombre"""
        pred_name = self.not_pred.get()
        if not pred_name:
            messagebox.showerror("Error", "Selecciona un predicado")
            return
        
        if self.data is not None and len(self.data) > 50:
            if not messagebox.askyesno(
                "Advertencia", 
                f"El dataset tiene {len(self.data)} filas. "
                f"Generar la matriz puede tomar tiempo. ¿Continuar?"
            ):
                return
        
        result_name = simpledialog.askstring(
            "Nombre del Resultado", 
            "Ingresa un nombre para guardar el resultado (FPC, mayúsculas):",
            parent=self.root
        )
        if not result_name:
            return
        
        result_name = result_name.upper()
        if result_name in self.predicates:
            messagebox.showerror("Error", f"Ya existe un predicado llamado '{result_name}'")
            return
        
        matrix, ids = self.generate_truth_matrix(pred_name)
        if matrix is not None:
            result = self.matrix_NOT(matrix)
            
            comp_pred = CompoundPredicate(result_name, LogicOp.NOT, [pred_name])
            self.predicates[result_name] = comp_pred
            
            self.pred_list.insert(tk.END, f"{result_name} (compuesta) :: {comp_pred.caption()}")
            self.update_predicate_combos()
            
            self.display_matrix(result, ids, ids, f"{result_name} (NOT {pred_name})", predicate_name=result_name)
            messagebox.showinfo("Éxito", f"Operación guardada como: {result_name}")

    # ---------- CONSULTAS CUANTIFICADAS ----------
    def execute_quantified_query(self):
        if self.data is None:
            messagebox.showerror("Error", "Carga un dataset primero.")
            return

        formula_raw = self.run_formula_name.get().strip()
        formula_name = self._resolve_predicate_name_input(formula_raw)
        if not formula_name:
            messagebox.showerror("Error", f"Predicado/Fórmula '{formula_raw}' no encontrado.")
            return

        qx = self.quant_x.get()
        qy = self.quant_y.get()

        ids_x, ids_y = self._domains()
        if not ids_x or not ids_y:
            messagebox.showerror("Error", "No hay dominio para X/Y (revisa la columna ID).")
            return

        qx = None if qx == "(ninguno)" else qx
        qy = None if qy == "(ninguno)" else qy

        result_summary = ""
        counter_df = None
        example_ids = set()
        counter_ids = set()

        try:
            if qx == "∀" and qy == "∃":
                # ∀X ∃Y φ(X,Y)
                bad_x = []
                good_pairs = []
                for x in ids_x:
                    ok = False
                    for y in ids_y:
                        if self._eval_predicate(formula_name, x, y):
                            ok = True
                            good_pairs.append((x, y))
                            break
                    if not ok:
                        bad_x.append(x)
                if len(bad_x) == 0:
                    result_summary = f"✅ Se cumple ∀X ∃Y {formula_name}"
                else:
                    result_summary = f"❌ No se cumple ∀X ∃Y {formula_name}. Contraejemplos (X sin Y que satisfaga): {len(bad_x)}"
                    counter_df = pd.DataFrame({"X_sin_testigo_Y": bad_x})
                # ejemplos y contraejemplos
                for x, y in good_pairs:
                    example_ids.add(x)
                    example_ids.add(y)
                counter_ids.update(bad_x)

            elif qx == "∀" and qy is None:
                # ∀X φ(X)
                bad_x = []
                for x in ids_x:
                    if not self._eval_predicate(formula_name, x, None):
                        bad_x.append(x)
                if len(bad_x) == 0:
                    result_summary = f"✅ Se cumple ∀X {formula_name}"
                else:
                    result_summary = f"❌ No se cumple ∀X {formula_name}. Contraejemplos: {len(bad_x)}"
                    counter_df = pd.DataFrame({"X_contraejemplo": bad_x})
                counter_ids.update(bad_x)
                example_ids.update(set(ids_x) - set(bad_x))

            elif qx == "∃" and qy == "∀":
                # ∃X ∀Y φ(X,Y)
                witness = None
                bad_y_for_first = []
                for x in ids_x:
                    all_ok = True
                    bad_y = []
                    for y in ids_y:
                        if not self._eval_predicate(formula_name, x, y):
                            all_ok = False
                            bad_y.append(y)
                    if all_ok:
                        witness = x
                        break
                    else:
                        if not bad_y_for_first:
                            bad_y_for_first = bad_y
                if witness is not None:
                    result_summary = f"✅ Se cumple ∃X ∀Y {formula_name}. Testigo X={witness}"
                    example_ids.add(witness)
                    example_ids.update(ids_y)
                else:
                    result_summary = f"❌ No se cumple ∃X ∀Y {formula_name}."
                    counter_df = pd.DataFrame({"Y_donde_falla_para_cualquier_X_evaluado": bad_y_for_first})
                    counter_ids.update(bad_y_for_first)

            elif qx == "∃" and qy == "∃":
                # ∃X ∃Y φ(X,Y)
                witness = None
                for x in ids_x:
                    for y in ids_y:
                        if self._eval_predicate(formula_name, x, y):
                            witness = (x, y)
                            break
                    if witness:
                        break
                if witness:
                    result_summary = f"✅ Se cumple ∃X ∃Y {formula_name}. Testigo (X,Y)={witness}"
                    example_ids.update(witness)
                else:
                    result_summary = f"❌ No se cumple ∃X ∃Y {formula_name}."
                    counter_df = pd.DataFrame(columns=["No hay pares (X,Y) que satisfagan"])

            elif qx == "∃" and qy is None:
                # ∃X φ(X)
                witness = None
                for x in ids_x:
                    if self._eval_predicate(formula_name, x, None):
                        witness = x
                        break
                if witness is not None:
                    result_summary = f"✅ Se cumple ∃X {formula_name}. Testigo X={witness}"
                    example_ids.add(witness)
                else:
                    result_summary = f"❌ No se cumple ∃X {formula_name}."
                    counter_df = pd.DataFrame(columns=["No hay X que satisfaga"])

            elif qx is None and qy in ("∀", "∃"):
                # Formalmente, tu FPS depende de X; estos casos quedan limitados
                if qy == "∀":
                    bad_y = []
                    for y in ids_y:
                        if not self._eval_predicate(formula_name, None, y):
                            bad_y.append(y)
                    if len(bad_y) == 0:
                        result_summary = f"✅ Se cumple ∀Y {formula_name}"
                    else:
                        result_summary = f"❌ No se cumple ∀Y {formula_name}. Contraejemplos: {len(bad_y)}"
                        counter_df = pd.DataFrame({"Y_contraejemplo": bad_y})
                        counter_ids.update(bad_y)
                else:  # ∃Y
                    witness = None
                    for y in ids_y:
                        if self._eval_predicate(formula_name, None, y):
                            witness = y
                            break
                    if witness is not None:
                        result_summary = f"✅ Se cumple ∃Y {formula_name}. Testigo Y={witness}"
                        example_ids.add(witness)
                    else:
                        result_summary = f"❌ No se cumple ∃Y {formula_name}."
                        counter_df = pd.DataFrame(columns=["No hay Y que satisfaga"])

            elif qx == "∀" and qy == "∀":
                # ∀X ∀Y φ(X,Y)
                bad_pairs = []
                for x in ids_x:
                    for y in ids_y:
                        if not self._eval_predicate(formula_name, x, y):
                            bad_pairs.append((x, y))
                if len(bad_pairs) == 0:
                    result_summary = f"✅ Se cumple ∀X ∀Y {formula_name}"
                else:
                    result_summary = f"❌ No se cumple ∀X ∀Y {formula_name}. Pares que fallan: {len(bad_pairs)}"
                    counter_df = pd.DataFrame(bad_pairs, columns=["X", "Y"])
                    for x, y in bad_pairs:
                        counter_ids.add(x)
                        counter_ids.add(y)

            elif qx is None and qy is None:
                # Evaluación sin cuantificadores: listar pares que satisfacen
                result_summary = f"Evaluación de {formula_name} sin cuantificadores"
                all_results = []
                for x in ids_x:
                    for y in ids_y:
                        if self._eval_predicate(formula_name, x, y):
                            all_results.append((x, y))
                if all_results:
                    result_summary += f" - {len(all_results)} pares satisfacen la fórmula"
                    counter_df = pd.DataFrame(all_results, columns=["X", "Y"])
                    for x, y in all_results:
                        example_ids.add(x)
                        example_ids.add(y)
                else:
                    result_summary += " - Ningún par satisface la fórmula"
                    counter_df = pd.DataFrame(columns=["X", "Y"])

            else:
                messagebox.showinfo("Aviso", "Combinación de cuantificadores no implementada en esta versión.")
                return

            # Mostrar resultados
            self.populate_results(counter_df, result_summary)
            # Resaltar ejemplos/contraejemplos en el dataset
            self.highlight_dataset_rows(example_ids, counter_ids)

        except Exception as e:
            messagebox.showerror("Error", f"Fallo en evaluación: {e}")

    def populate_results(self, df, message):
        # limpia
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

        if df is None or len(getattr(df, "columns", [])) == 0:
            self.result_tree["columns"] = ["Resultado"]
            self.result_tree.heading("Resultado", text="Resultado")
            self.result_tree.column("Resultado", width=800)
            self.result_tree.insert("", "end", values=[message])
            self.last_result_df = pd.DataFrame({"Resultado":[message]})
        else:
            cols = list(df.columns)
            self.result_tree["columns"] = cols
            for c in cols:
                self.result_tree.heading(c, text=c)
                self.result_tree.column(c, width=200)
            max_rows = min(len(df), 5000)
            for _, row in df.iloc[:max_rows].iterrows():
                self.result_tree.insert("", "end", values=list(row))
            self.last_result_df = df.copy()

        self.status_var.set(message)

    def export_results(self):
        if self.last_result_df is None or len(self.last_result_df) == 0:
            messagebox.showerror("Error", "No hay resultados para exportar.")
            return
        fname = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if not fname:
            return
        try:
            self.last_result_df.to_csv(fname, index=False)
            messagebox.showinfo("Éxito", "Resultados exportados.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

# ----------------------------
#           Main
# ----------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = LogicQueryApp(root)
    root.mainloop()