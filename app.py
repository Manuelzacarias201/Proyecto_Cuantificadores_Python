import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd

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

REL_OPS = [RelOp.EQ, RelOp.GT, RelOp.LT, RelOp.GE, RelOp.LE, RelOp.NE]

class LogicOp:
    NOT = "NOT"
    AND = "AND"
    OR  = "OR"

LOGIC_OPS = [LogicOp.NOT, LogicOp.AND, LogicOp.OR]

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
            return f"{self.name}(X,Y): X tiene '{self.attr}' {self.op} que Y"
        else:
            return f"{self.name}(X): X tiene '{self.attr}' {self.op} {self.rhs['value']}"

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
        self.root.title("Sistema de Consultas Lógicas")
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

        # --- configuraciones / variables ---
        config = ttk.LabelFrame(main, text="Configuración / Variables", padding=8)
        config.grid(row=2, column=0, sticky="nsew", padx=(0,8))
        config.grid_columnconfigure(0, weight=1)

        ttk.Label(config, text="Columna ID (p.ej. Fecha):").grid(row=0, column=0, sticky="w")
        self.id_var = tk.StringVar()
        self.id_combo = ttk.Combobox(config, textvariable=self.id_var, state="readonly", width=30)
        self.id_combo.grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(config, text="Dominio de X / Y: (por defecto = todos los IDs)").grid(row=1, column=0, columnspan=2, sticky="w", pady=(6,0))
        # (para v1, asumimos todo el dominio; UI de subset se podría agregar luego)

        # --- constructor de predicado simple ---
        builder = ttk.LabelFrame(main, text="Predicado simple (fila–fila o contra constante)", padding=8)
        builder.grid(row=2, column=1, sticky="nsew")
        builder.grid_columnconfigure(1, weight=1)

        self.attr_var = tk.StringVar()
        self.lhs_var = tk.StringVar(value="X")
        self.op_var = tk.StringVar(value=RelOp.GT)
        self.rhs_mode = tk.StringVar(value="var")  # "var" o "const"
        self.rhs_var = tk.StringVar(value="Y")
        self.const_entry_var = tk.StringVar()
        self.pred_name_var = tk.StringVar()
        self.preview_var = tk.StringVar(value="Vista previa...")

        rowb = 0
        ttk.Label(builder, text="Atributo:").grid(row=rowb, column=0, sticky="e", padx=4, pady=2)
        self.attr_combo = ttk.Combobox(builder, textvariable=self.attr_var, state="readonly", width=28)
        self.attr_combo.grid(row=rowb, column=1, sticky="w", pady=2)

        rowb += 1
        ttk.Label(builder, text="LHS:").grid(row=rowb, column=0, sticky="e", padx=4, pady=2)
        self.lhs_combo = ttk.Combobox(builder, textvariable=self.lhs_var, values=["X", "Y"], state="readonly", width=6)
        self.lhs_combo.grid(row=rowb, column=1, sticky="w", pady=2)

        rowb += 1
        ttk.Label(builder, text="Operador:").grid(row=rowb, column=0, sticky="e", padx=4, pady=2)
        self.op_combo = ttk.Combobox(builder, textvariable=self.op_var, values=REL_OPS, state="readonly", width=6)
        self.op_combo.grid(row=rowb, column=1, sticky="w", pady=2)

        rowb += 1
        ttk.Label(builder, text="RHS:").grid(row=rowb, column=0, sticky="e", padx=4, pady=2)
        rhs_frame = ttk.Frame(builder)
        rhs_frame.grid(row=rowb, column=1, sticky="w", pady=2)

        ttk.Radiobutton(rhs_frame, text="Variable", variable=self.rhs_mode, value="var", command=self.update_preview).grid(row=0, column=0, padx=2)
        self.rhs_combo = ttk.Combobox(rhs_frame, textvariable=self.rhs_var, values=["X", "Y"], state="readonly", width=6)
        self.rhs_combo.grid(row=0, column=1, padx=4)

        ttk.Radiobutton(rhs_frame, text="Constante", variable=self.rhs_mode, value="const", command=self.update_preview).grid(row=0, column=2, padx=2)
        self.const_entry = ttk.Entry(rhs_frame, textvariable=self.const_entry_var, width=12)
        self.const_entry.grid(row=0, column=3, padx=4)

        rowb += 1
        ttk.Label(builder, text="Nombre del predicado:").grid(row=rowb, column=0, sticky="e", padx=4, pady=2)
        self.pred_name_entry = ttk.Entry(builder, textvariable=self.pred_name_var, width=12)
        self.pred_name_entry.grid(row=rowb, column=1, sticky="w", pady=2)

        rowb += 1
        ttk.Label(builder, textvariable=self.preview_var).grid(row=rowb, column=0, columnspan=2, sticky="w", pady=(4,6))

        rowb += 1
        ttk.Button(builder, text="Guardar predicado", command=self.save_simple_predicate).grid(row=rowb, column=0, columnspan=2, pady=4)

        # --- biblioteca de predicados + compuestos ---
        lib = ttk.LabelFrame(main, text="Biblioteca de predicados / Fórmulas", padding=8)
        lib.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=10)
        lib.grid_columnconfigure(0, weight=1)
        lib.grid_columnconfigure(1, weight=1)

        left = ttk.Frame(lib)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        right = ttk.Frame(lib)
        right.grid(row=0, column=1, sticky="nsew")

        # lista de predicados
        ttk.Label(left, text="Predicados/Fórmulas guardados:").grid(row=0, column=0, sticky="w")
        self.pred_list = tk.Listbox(left, height=8)
        self.pred_list.grid(row=1, column=0, sticky="nsew")
        left.grid_rowconfigure(1, weight=1)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.pred_list.yview)
        self.pred_list.configure(yscrollcommand=sb.set)
        sb.grid(row=1, column=1, sticky="ns")
        ttk.Button(left, text="Ver detalle", command=self.show_selected_predicate).grid(row=2, column=0, sticky="w", pady=4)

        # constructor de compuestos
        ttk.Label(right, text="Fórmula compuesta").grid(row=0, column=0, columnspan=2, sticky="w")
        self.comp_op_var = tk.StringVar(value=LogicOp.AND)
        ttk.Label(right, text="Operador lógico:").grid(row=1, column=0, sticky="e", padx=4)
        ttk.Combobox(right, textvariable=self.comp_op_var, values=LOGIC_OPS, state="readonly").grid(row=1, column=1, sticky="w")

        ttk.Label(right, text="Arg1 (nombre):").grid(row=2, column=0, sticky="e", padx=4)
        self.comp_arg1 = tk.Entry(right, width=16)
        self.comp_arg1.grid(row=2, column=1, sticky="w")

        ttk.Label(right, text="Arg2 (nombre):").grid(row=3, column=0, sticky="e", padx=4)
        self.comp_arg2 = tk.Entry(right, width=16)
        self.comp_arg2.grid(row=3, column=1, sticky="w")

        ttk.Label(right, text="Nombre fórmula:").grid(row=4, column=0, sticky="e", padx=4)
        self.comp_name = tk.Entry(right, width=16)
        self.comp_name.grid(row=4, column=1, sticky="w")

        ttk.Button(right, text="Guardar fórmula", command=self.save_compound).grid(row=5, column=0, columnspan=2, pady=6)

        # --- consultas cuantificadas / ejecución ---
        runf = ttk.LabelFrame(main, text="Consulta cuantificada", padding=8)
        runf.grid(row=4, column=0, columnspan=2, sticky="nsew")
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
        result_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(10,0))
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
        ttk.Label(main, textvariable=self.status_var).grid(row=6, column=0, columnspan=2, sticky="w", pady=4)

        # eventos para vista previa
        for var in (self.attr_var, self.lhs_var, self.op_var, self.rhs_mode, self.rhs_var, self.const_entry_var):
            var.trace_add("write", lambda *args: self.update_preview())

    # ---------- dataset ----------
    def load_dataset(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not filename:
            return
        try:
            # intento robusto de lectura; el separador se puede ajustar
            self.data = pd.read_csv(filename)
            # si hay una columna "Fecha", intenta parsear
            if "Fecha" in self.data.columns:
                try:
                    self.data["Fecha"] = pd.to_datetime(self.data["Fecha"], errors="ignore", dayfirst=True)
                except Exception:
                    pass

            self.display_data(self.data)
            # combos de columnas
            cols = list(self.data.columns)
            self.attr_combo["values"] = cols
            self.id_combo["values"] = cols
            # intentar elegir ID por defecto
            default_id = "Fecha" if "Fecha" in cols else cols[0]
            self.id_combo.set(default_id)
            self.id_column = default_id

            self.update_preview()
            messagebox.showinfo("Éxito", "Dataset cargado correctamente")
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
        lhs = self.lhs_var.get() or "X"
        op  = self.op_var.get() or ">"
        if self.rhs_mode.get() == "var":
            rhs_txt = self.rhs_var.get() or "Y"
        else:
            rhs_txt = self.const_entry_var.get() or "<constante>"
        self.preview_var.set(f"Vista previa: {lhs} tiene '{attr}' {op} que {rhs_txt}")

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
        raise ValueError(f"Operador no válido: {op}")

    # ---------- guardar predicados ----------
    def save_simple_predicate(self):
        if self.data is None:
            messagebox.showerror("Error", "Carga un dataset primero.")
            return
        if not self.id_combo.get():
            messagebox.showerror("Error", "Selecciona la columna ID.")
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
        lhs = self.lhs_var.get() or "X"
        op  = self.op_var.get()
        if op not in REL_OPS:
            messagebox.showerror("Error", "Operador inválido.")
            return

        if self.rhs_mode.get() == "var":
            rhs = {"type":"var","var": self.rhs_var.get() or "Y"}
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

        if op == LogicOp.NOT:
            if not a1:
                messagebox.showerror("Error", "NOT requiere Arg1.")
                return
            if a1 not in self.predicates:
                messagebox.showerror("Error", f"Arg1 '{a1}' no existe.")
                return
            args = [a1]
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
            # lhs value
            if pred.lhs_var == "X":
                if x is None: return False
                try:
                    lv = series.loc[x]
                except Exception:
                    # si el df no tiene índice por ID, intentar por máscara
                    lv = series[self.data[self.id_column] == x]
                    lv = lv.iloc[0] if len(lv) else None
            else:  # lhs_var == "Y"
                if y is None: return False
                try:
                    lv = series.loc[y]
                except Exception:
                    lv = series[self.data[self.id_column] == y]
                    lv = lv.iloc[0] if len(lv) else None

            # rhs value
            if pred.rhs["type"] == "var":
                var = pred.rhs["var"]
                if var == "X":
                    rv_id = x
                else:
                    rv_id = y
                if rv_id is None:
                    return False
                try:
                    rv = series.loc[rv_id]
                except Exception:
                    rv = series[self.data[self.id_column] == rv_id]
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
            raise ValueError("Operador lógico no soportado.")
        return False

    def _domains(self):
        """Devuelve dominios de X e Y (para v1: todos los IDs)."""
        if self.data is None or self.id_combo.get() == "":
            return [], []
        idcol = self.id_combo.get()
        ids = list(self.data[idcol])
        # si el ID debe ser índice, lo ponemos:
        if self.data.index.name != idcol:
            try:
                # Si idcol es única, set_index
                if self.data[idcol].is_unique:
                    self.data = self.data.set_index(idcol)
                    self.data.index.name = idcol
                    self.id_column = idcol
                else:
                    self.id_column = idcol
            except Exception:
                self.id_column = idcol
        return ids, ids

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
        # Casos soportados: (∀|∃)X (∀|∃)Y φ(X,Y)
        # También funciona si φ sólo depende de X (constante en RHS).
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
                # φ(Y) cuantificado solo sobre Y (si tiene sentido)
                # Implementación simétrica mínima
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
        messagebox.showinfo("Resultado", message)

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
