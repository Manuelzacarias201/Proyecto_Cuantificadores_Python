import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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

REL_OPS = [RelOp.EQ, RelOp.GT, RelOp.LT, RelOp.GE, RelOp.LE, RelOp.NE, 
           RelOp.CONTAINS, RelOp.STARTS_WITH, RelOp.ENDS_WITH]

class LogicOp:
    NOT = "NOT"
    AND = "AND"
    OR = "OR"
    IMPLIES = "IMPLIES"
    XOR = "XOR"
    BICONDITIONAL = "BICONDITIONAL"

LOGIC_OPS = [LogicOp.NOT, LogicOp.AND, LogicOp.OR, LogicOp.IMPLIES, LogicOp.XOR, LogicOp.BICONDITIONAL]

class SimplePredicate:
    """P(X,Y) o P(X,const). Estructura serializable en dict."""
    def __init__(self, name, attr, op, lhs_var, rhs):
        self.type = "simple"
        self.name = name          # "P"
        self.attr = attr          # columna del df
        self.op = op              # RelOp
        self.lhs_var = lhs_var    # "X"
        self.rhs = rhs            # {"type":"var","var":"Y"} o {"type":"const","value":..}

    def caption(self):
        if self.rhs["type"] == "var":
            return f"{self.name}(X,Y): X.{self.attr} {self.op} Y.{self.attr}"
        else:
            return f"{name}(X): X.{self.attr} {self.op} {self.rhs['value']}"

class CompoundPredicate:
    """φ = NOT P  |  (P AND Q)  |  (P OR Q)"""
    def __init__(self, name, op, args):
        self.type = "compound"
        self.name = name
        self.op = op              # LogicOp
        self.args = args          # lista de refs a nombres de predicados o dicts embebidos

    def caption(self):
        if self.op == LogicOp.NOT:
            return f"{self.name}: NOT({self.args[0]})"
        return f"{self.name}: ({self.args[0]} {self.op} {self.args[1]})"

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

        # --- constructor de predicado simple (SIMPLIFICADO) ---
        builder = ttk.LabelFrame(main, text="Predicado simple", padding=8)
        builder.grid(row=2, column=0, sticky="nsew", padx=(0,8))
        builder.grid_columnconfigure(1, weight=1)

        self.attr_var = tk.StringVar()
        self.op_var = tk.StringVar(value=RelOp.GT)
        self.rhs_mode = tk.StringVar(value="const")
        self.const_entry_var = tk.StringVar()
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
        ttk.Label(builder, text="Comparar con:").grid(row=rowb, column=0, sticky="e", padx=4, pady=2)
        rhs_frame = ttk.Frame(builder)
        rhs_frame.grid(row=rowb, column=1, sticky="w", pady=2)

        ttk.Radiobutton(rhs_frame, text="Constante", variable=self.rhs_mode, value="const", command=self.update_preview).grid(row=0, column=0, padx=2)
        self.const_entry = ttk.Entry(rhs_frame, textvariable=self.const_entry_var, width=12)
        self.const_entry.grid(row=0, column=1, padx=4)

        ttk.Radiobutton(rhs_frame, text="Otra fila (Y)", variable=self.rhs_mode, value="var", command=self.update_preview).grid(row=0, column=2, padx=2)

        rowb += 1
        ttk.Label(builder, text="Nombre:").grid(row=rowb, column=0, sticky="e", padx=4, pady=2)
        self.pred_name_entry = ttk.Entry(builder, textvariable=self.pred_name_var, width=12)
        self.pred_name_entry.grid(row=rowb, column=1, sticky="w", pady=2)

        rowb += 1
        ttk.Label(builder, textvariable=self.preview_var).grid(row=rowb, column=0, columnspan=2, sticky="w", pady=(4,6))

        rowb += 1
        ttk.Button(builder, text="Guardar predicado", command=self.save_simple_predicate).grid(row=rowb, column=0, columnspan=2, pady=4)

        # --- biblioteca de predicados + compuestos (MÁS GRANDE) ---
        lib = ttk.LabelFrame(main, text="Biblioteca de predicados / Fórmulas", padding=8)
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
        self.pred_list = tk.Listbox(lib_main, height=12, width=50)  # Más alto y más ancho
        self.pred_list.grid(row=1, column=0, sticky="nsew", pady=5)
        lib_main.grid_rowconfigure(1, weight=1)
        lib_main.grid_columnconfigure(0, weight=1)
        
        # Scrollbar para la lista
        sb = ttk.Scrollbar(lib_main, orient="vertical", command=self.pred_list.yview)
        self.pred_list.configure(yscrollcommand=sb.set)
        sb.grid(row=1, column=1, sticky="ns")
        
        # Botón para ver detalle
        ttk.Button(lib_main, text="Ver detalle", command=self.show_selected_predicate).grid(row=2, column=0, sticky="w", pady=4)

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

        ttk.Label(runf, text="Selecciona predicado/fórmula (por nombre):").grid(row=0, column=0, sticky="e", padx=4)
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
        for var in (self.attr_var, self.op_var, self.rhs_mode, self.const_entry_var):
            var.trace_add("write", lambda *args: self.update_preview())

        # Configurar pesos de filas y columnas para mejor distribución
        main.grid_rowconfigure(1, weight=2)  # Tabla dataset
        main.grid_rowconfigure(2, weight=1)  # Constructor + Biblioteca
        main.grid_rowconfigure(4, weight=0)  # Operaciones matrices
        main.grid_rowconfigure(5, weight=0)  # Consultas cuantificadas
        main.grid_rowconfigure(6, weight=1)  # Resultados

    # ---------- dataset ----------
    def load_dataset(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")])
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

            self.display_data(self.data)
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

            self.update_preview()
            messagebox.showinfo("Éxito", f"Dataset cargado: {len(self.data)} filas, {len(cols)} columnas\nID automático: {self.id_column}")
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

        # paginado ligero: primeras 2000 filas
        max_rows = min(len(df), 2000)
        for _, row in df.iloc[:max_rows].iterrows():
            tree.insert("", "end", values=list(row))

    # ---------- utilidades ----------
    def update_preview(self):
        attr = self.attr_var.get() or "<atributo>"
        op  = self.op_var.get() or ">"
        if self.rhs_mode.get() == "var":
            rhs_txt = "Y." + attr
        else:
            rhs_txt = self.const_entry_var.get() or "<constante>"
        self.preview_var.set(f"Vista previa: X.{attr} {op} {rhs_txt}")

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
            messagebox.showerror("Error", "Asigna un nombre al predicado (p.ej., P, Q).")
            return
        if name in self.predicates:
            messagebox.showerror("Error", f"Ya existe un predicado llamado '{name}'.")
            return

        attr = self.attr_var.get()
        if not attr:
            messagebox.showerror("Error", "Selecciona un atributo.")
            return
        lhs = "X"  # Simplificado - siempre X
        op  = self.op_var.get()
        if op not in REL_OPS:
            messagebox.showerror("Error", "Operador inválido.")
            return

        if self.rhs_mode.get() == "var":
            rhs = {"type":"var","var": "Y"}
        else:
            # constante -> convertir a dtype de la columna
            series = self.data[attr]
            try:
                value = self._parse_const_for_series(series, self.const_entry_var.get())
            except Exception as e:
                messagebox.showerror("Error", f"Constante inválida: {e}")
                return
            rhs = {"type":"const","value": value}

        sp = SimplePredicate(name, attr, op, lhs, rhs)
        self.predicates[name] = sp
        self.pred_list.insert(tk.END, f"{name} (simple) :: {sp.caption()}")
        self.status_var.set(f"Predicado '{name}' guardado.")
        
        # Actualizar combos de matrices
        self.update_predicate_combos()

    def save_compound(self):
        name = self.comp_name.get().strip()
        if not name:
            messagebox.showerror("Error", "Asigna un nombre a la fórmula.")
            return
        if name in self.predicates:
            messagebox.showerror("Error", f"Ya existe un predicado/fórmula '{name}'.")
            return

        op = self.comp_op_var.get()
        a1 = self.comp_arg1.get().strip()
        a2 = self.comp_arg2.get().strip()

        if op in [LogicOp.NOT, LogicOp.IMPLIES]:
            if not a1:
                messagebox.showerror("Error", f"{op} requiere Arg1.")
                return
            if a1 not in self.predicates:
                messagebox.showerror("Error", f"Arg1 '{a1}' no existe.")
                return
            args = [a1]
            if op == LogicOp.IMPLIES and a2:  # IMPLIES puede tener Arg2 opcional
                if a2 not in self.predicates:
                    messagebox.showerror("Error", f"Arg2 '{a2}' no existe.")
                    return
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
        
        # Actualizar combos de matrices
        self.update_predicate_combos()

    def show_selected_predicate(self):
        sel = self.pred_list.curselection()
        if not sel:
            return
        text = self.pred_list.get(sel[0])
        messagebox.showinfo("Detalle", text)

    # ---------- evaluación ----------
    def _eval_predicate(self, name, x=None, y=None):
        """Evalúa un predicado/fórmula dados IDs concretos (x,y)."""
        pred = self.predicates[name]
        if pred.type == "simple":
            series = self.data[pred.attr]
            # lhs value (siempre X en la versión simplificada)
            if x is None: return False
            try:
                lv = series.loc[x]
            except Exception:
                # si el df no tiene índice por ID, intentar por máscara
                lv = series[self.data[self.id_column] == x]
                lv = lv.iloc[0] if len(lv) else None

            # rhs value
            if pred.rhs["type"] == "var":
                if y is None:
                    return False
                try:
                    rv = series.loc[y]
                except Exception:
                    rv = series[self.data[self.id_column] == y]
                    rv = rv.iloc[0] if len(rv) else None
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
                # P → Q equivale a ¬P ∨ Q
                return (not self._eval_predicate(pred.args[0], x, y)) or self._eval_predicate(pred.args[1] if len(pred.args) > 1 else pred.args[0], x, y)
            if pred.op == LogicOp.XOR:
                # P XOR Q equivale a (P ∨ Q) ∧ ¬(P ∧ Q)
                p_val = self._eval_predicate(pred.args[0], x, y)
                q_val = self._eval_predicate(pred.args[1], x, y)
                return (p_val or q_val) and not (p_val and q_val)
            if pred.op == LogicOp.BICONDITIONAL:
                # P ↔️ Q equivale a (P → Q) ∧ (Q → P)
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

    # ---------- MATRICES NxN ----------
    def generate_truth_matrix(self, predicate_name):
        """Genera matriz NxN de verdad para un predicado"""
        if self.data is None or predicate_name not in self.predicates:
            return None, []
        
        ids = self._get_domain_ids()
        n = len(ids)
        
        # Crear matriz de ceros (falso)
        matrix = np.zeros((n, n), dtype=bool)
        
        # Llenar la matriz evaluando el predicado para cada par (i,j)
        pred = self.predicates[predicate_name]
        for i, x in enumerate(ids):
            for j, y in enumerate(ids):
                if pred.type == "simple" and pred.rhs["type"] == "var":
                    matrix[i][j] = self._eval_predicate(predicate_name, x, y)
                else:
                    # Si es constante o compuesto, solo depende de X
                    matrix[i][j] = self._eval_predicate(predicate_name, x, None)
        
        return matrix, ids

    def _get_domain_ids(self):
        """Obtiene la lista de IDs del dominio"""
        if self.data is None or not self.id_column:
            return []
        return list(self.data[self.id_column])

    def display_matrix(self, matrix, row_labels, col_labels, title):
        """Muestra una matriz en una ventana flotante con colores"""
        matrix_window = tk.Toplevel(self.root)
        matrix_window.title(f"Matriz: {title}")
        matrix_window.geometry("800x600")
        
        # Frame principal
        main_frame = ttk.Frame(matrix_window, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        matrix_window.grid_rowconfigure(0, weight=1)
        matrix_window.grid_columnconfigure(0, weight=1)
        
        # Canvas con scroll
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
        
        # Mostrar matriz
        n_rows, n_cols = matrix.shape
        
        # Encabezados de columnas
        for j, col_label in enumerate(col_labels):
            label = ttk.Label(scrollable_frame, text=str(col_label), background="lightblue", width=12)
            label.grid(row=0, column=j+1, padx=1, pady=1)
        
        # Filas con datos
        for i in range(n_rows):
            # Label de fila
            row_label = ttk.Label(scrollable_frame, text=str(row_labels[i]), background="lightblue", width=12)
            row_label.grid(row=i+1, column=0, padx=1, pady=1)
            
            # Celdas de la matriz
            for j in range(n_cols):
                value = matrix[i][j]
                bg_color = "lightgreen" if value else "lightcoral"
                text = "V" if value else "F"
                cell = tk.Label(scrollable_frame, text=text, bg=bg_color, width=12, height=2,
                              relief="raised", borderwidth=1)
                cell.grid(row=i+1, column=j+1, padx=1, pady=1)
        
        # Empaquetar widgets de scroll
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

    # ---------- OPERADORES MATRICIALES ----------
    def matrix_AND(self, matrix1, matrix2):
        """AND lógico celda a celda"""
        if matrix1.shape != matrix2.shape:
            raise ValueError("Las matrices deben tener la misma dimensión")
        return np.logical_and(matrix1, matrix2)

    def matrix_OR(self, matrix1, matrix2):
        """OR lógico celda a celda"""
        if matrix1.shape != matrix2.shape:
            raise ValueError("Las matrices deben tener la misma dimensión")
        return np.logical_or(matrix1, matrix2)

    def matrix_NOT(self, matrix):
        """NOT lógico celda a celda"""
        return np.logical_not(matrix)

    def matrix_XOR(self, matrix1, matrix2):
        """XOR lógico celda a celda"""
        if matrix1.shape != matrix2.shape:
            raise ValueError("Las matrices deben tener la misma dimensión")
        return np.logical_xor(matrix1, matrix2)

    def matrix_IMPLIES(self, matrix1, matrix2):
        """Condicional lógico (P → Q) = ¬P ∨ Q"""
        if matrix1.shape != matrix2.shape:
            raise ValueError("Las matrices deben tener la misma dimensión")
        return np.logical_or(np.logical_not(matrix1), matrix2)

    def matrix_BICONDITIONAL(self, matrix1, matrix2):
        """Bicondicional lógico (P ↔️ Q) = (P → Q) ∧ (Q → P)"""
        if matrix1.shape != matrix2.shape:
            raise ValueError("Las matrices deben tener la misma dimensión")
        return np.logical_and(
            self.matrix_IMPLIES(matrix1, matrix2),
            self.matrix_IMPLIES(matrix2, matrix1)
        )

    def update_predicate_combos(self):
        """Actualiza los combobox con los predicados disponibles"""
        pred_names = list(self.predicates.keys())
        self.matrix_pred1['values'] = pred_names
        self.matrix_pred2['values'] = pred_names
        self.not_pred['values'] = pred_names

    def show_predicate_matrix(self):
        """Muestra la matriz de verdad de un predicado"""
        pred_name = self.matrix_pred1.get()
        if not pred_name or pred_name not in self.predicates:
            messagebox.showerror("Error", "Selecciona un predicado válido")
            return
        
        matrix, ids = self.generate_truth_matrix(pred_name)
        if matrix is not None:
            self.display_matrix(matrix, ids, ids, f"Matriz de {pred_name}")

    def apply_matrix_operator(self):
        """Aplica operador binario a dos matrices"""
        pred1 = self.matrix_pred1.get()
        pred2 = self.matrix_pred2.get()
        op = self.matrix_op.get()
        
        if not all([pred1, pred2, op]):
            messagebox.showerror("Error", "Selecciona dos predicados y un operador")
            return
        
        matrix1, ids1 = self.generate_truth_matrix(pred1)
        matrix2, ids2 = self.generate_truth_matrix(pred2)
        
        if matrix1 is None or matrix2 is None:
            messagebox.showerror("Error", "No se pudieron generar las matrices")
            return
        
        try:
            if op == "AND":
                result = self.matrix_AND(matrix1, matrix2)
            elif op == "OR":
                result = self.matrix_OR(matrix1, matrix2)
            elif op == "XOR":
                result = self.matrix_XOR(matrix1, matrix2)
            elif op == "IMPLIES":
                result = self.matrix_IMPLIES(matrix1, matrix2)
            elif op == "BICONDITIONAL":
                result = self.matrix_BICONDITIONAL(matrix1, matrix2)
            else:
                messagebox.showerror("Error", "Operador no válido")
                return
            
            self.display_matrix(result, ids1, ids2, f"{pred1} {op} {pred2}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error aplicando operador: {e}")

    def apply_matrix_not(self):
        """Aplica NOT a una matriz"""
        pred_name = self.not_pred.get()
        if not pred_name:
            messagebox.showerror("Error", "Selecciona un predicado")
            return
        
        matrix, ids = self.generate_truth_matrix(pred_name)
        if matrix is not None:
            result = self.matrix_NOT(matrix)
            self.display_matrix(result, ids, ids, f"NOT {pred_name}")

    # ---------- CONSULTAS CUANTIFICADAS ----------
    def execute_quantified_query(self):
        if self.data is None:
            messagebox.showerror("Error", "Carga un dataset primero.")
            return

        formula_name = self.run_formula_name.get().strip()
        if formula_name not in self.predicates:
            messagebox.showerror("Error", "Predicado/Fórmula no encontrado.")
            return

        qx = self.quant_x.get()
        qy = self.quant_y.get()

        ids_x, ids_y = self._domains()
        if not ids_x or not ids_y:
            messagebox.showerror("Error", "No hay dominio para X/Y (revisa la columna ID).")
            return

        # Normaliza cuantificadores
        qx = None if qx == "(ninguno)" else qx
        qy = None if qy == "(ninguno)" else qy

        # Evaluación
        result_summary = ""
        counter_df = None

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
                else:
                    result_summary = f"❌ No se cumple ∃X ∀Y {formula_name}."
                    counter_df = pd.DataFrame({"Y_donde_falla_para_cualquier_X_evaluado": bad_y_for_first})

            elif qx == "∃" and qy == "∃":
                # ∃X ∃Y φ(X,Y)
                witness = None
                for x in ids_x:
                    for y in ids_y:
                        if self._eval_predicate(formula_name, x, y):
                            witness = (x, y)
                            break
                    if witness: break
                if witness:
                    result_summary = f"✅ Se cumple ∃X ∃Y {formula_name}. Testigo (X,Y)={witness}"
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
                else:
                    result_summary = f"❌ No se cumple ∃X {formula_name}."
                    counter_df = pd.DataFrame(columns=["No hay X que satisfaga"])

            elif qx is None and qy in ("∀", "∃"):
                # φ(Y) cuantificado solo sobre Y
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
                else:  # ∃Y
                    witness = None
                    for y in ids_y:
                        if self._eval_predicate(formula_name, None, y):
                            witness = y
                            break
                    if witness is not None:
                        result_summary = f"✅ Se cumple ∃Y {formula_name}. Testigo Y={witness}"
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

            elif qx is None and qy is None:
                # Solo evaluación de la fórmula sin cuantificadores
                result_summary = f"Evaluación de {formula_name} sin cuantificadores"
                all_results = []
                for x in ids_x:
                    for y in ids_y:
                        if self._eval_predicate(formula_name, x, y):
                            all_results.append((x, y))
                if all_results:
                    result_summary += f" - {len(all_results)} pares satisfacen la fórmula"
                    counter_df = pd.DataFrame(all_results, columns=["X", "Y"])
                else:
                    result_summary += " - Ningún par satisface la fórmula"
                    counter_df = pd.DataFrame(columns=["X", "Y"])

            else:
                messagebox.showinfo("Aviso", "Combinación de cuantificadores no implementada en esta versión.")
                return

            # Mostrar resultados
            self.populate_results(counter_df, result_summary)

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
            # limitar filas para UI
            max_rows = min(len(df), 5000)
            for _, row in df.iloc[:max_rows].iterrows():
                self.result_tree.insert("", "end", values=list(row))
            self.last_result_df = df.copy()

        # status
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