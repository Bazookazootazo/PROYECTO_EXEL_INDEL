import os
import re
import csv
import io
import datetime
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd


class VentanaSubirArchivos(ctk.CTkToplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.title("Procesar Documentos - Control de Acceso")
        self.geometry("1100x720")
        
        # Traer al frente y enfocar
        self.after(10, lambda: self.wm_state('zoomed'))
        self.focus()

        # Atributos de estado
        self.ruta_archivo = []

        # Construcción de la interfaz gráfica
        self._crear_interfaz()

    # --- FUNCIONES DE LÓGICA DE NEGOCIO (MÉTODOS ESTÁTICOS / AUXILIARES) ---

    @staticmethod
    def _detectar_encoding_por_bom(ruta):
        with open(ruta, 'rb') as f:
            inicio = f.read(4)
        if inicio.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        if inicio.startswith(b'\xff\xfe\x00\x00') or inicio.startswith(b'\x00\x00\xfe\xff'):
            return 'utf-32'
        if inicio.startswith(b'\xff\xfe') or inicio.startswith(b'\xfe\xff'):
            return 'utf-16'
        return None

    @staticmethod
    def detectar_delimitador_manual(muestra_texto):
        candidatos = [';', ',', '\t', '|']
        mejor_delim = None
        mejor_score = -1.0

        for delim in candidatos:
            try:
                lector = csv.reader(io.StringIO(muestra_texto), delimiter=delim)
                conteos = [len(fila) for fila in lector if any(campo.strip() for campo in fila)]
            except csv.Error:
                continue
            if not conteos:
                continue

            moda = max(set(conteos), key=conteos.count)
            if moda <= 1:
                continue

            consistencia = conteos.count(moda) / len(conteos)
            score = consistencia * moda
            if score > mejor_score:
                mejor_score = score
                mejor_delim = delim

        return mejor_delim

    @staticmethod
    def _leer_csv_tolerante(ruta, encoding, delimitador):
        with open(ruta, 'r', encoding=encoding, newline='') as f:
            lector = csv.reader(f, delimiter=delimitador)
            filas = [fila for fila in lector]

        if not filas:
            return None

        encabezado = filas[0]
        n_cols = len(encabezado)
        if n_cols <= 1:
            return None

        filas_normalizadas = []
        for fila in filas[1:]:
            if not any(campo.strip() for campo in fila):
                continue
            if len(fila) > n_cols:
                extra = fila[n_cols:]
                if any(campo.strip() for campo in extra):
                    fila = fila[:n_cols - 1] + [delimitador.join(fila[n_cols - 1:])]
                else:
                    fila = fila[:n_cols]
            elif len(fila) < n_cols:
                fila = fila + [''] * (n_cols - len(fila))
            filas_normalizadas.append(fila)

        if not filas_normalizadas:
            return None

        return pd.DataFrame(filas_normalizadas, columns=encabezado)

    def cargar_dataframe(self, ruta):
        _, extension = os.path.splitext(ruta)
        ext = extension.lower()

        if ext == '.csv':
            encoding_bom = self._detectar_encoding_por_bom(ruta)
            encodings = ([encoding_bom] if encoding_bom else []) + ['utf-8-sig', 'utf-8', 'cp1252', 'latin1']
            vistos = set()
            encodings = [e for e in encodings if e and not (e in vistos or vistos.add(e))]

            for encoding in encodings:
                try:
                    with open(ruta, 'r', encoding=encoding, errors='strict') as f:
                        muestra = f.read(32768)
                except (UnicodeDecodeError, LookupError):
                    continue
                if not muestra.strip():
                    continue

                delimitador = self.detectar_delimitador_manual(muestra)
                if delimitador is None:
                    continue
                try:
                    df = self._leer_csv_tolerante(ruta, encoding, delimitador)
                except (UnicodeDecodeError, csv.Error):
                    continue
                if df is not None and len(df.columns) > 1:
                    return df

            for encoding in encodings:
                try:
                    df = pd.read_csv(ruta, sep=None, engine='python', encoding=encoding, dtype=str)
                    if len(df.columns) > 1:
                        return df
                except Exception:
                    continue

            raise ValueError(
                "No se pudo determinar el delimitador ni la codificación del "
                "archivo CSV. Verifica que el archivo tenga un formato de tabla válido."
            )

        elif ext in ['.xlsx', '.xls']:
            return pd.read_excel(ruta)
        else:
            raise ValueError(f"Formato no soportado: {extension}")

    @staticmethod
    def extraer_columnas_relevantes(df):
        posibles_fechas = ['data e hora', 'fecha', 'data/hora', 'date', 'time', 'hora', 'fecha/hora']
        posibles_codigos = ['código', 'codigo', 'id', 'matrícula', 'matricula', 'no.', 'número', 'numero', 'usuario', 'no_emp']
        posibles_nombres = ['nome', 'nombre', 'name', 'empleado', 'docente', 'persona']

        col_fecha = next((c for c in df.columns if any(p in str(c).lower() for p in posibles_fechas)), None)
        col_codigo = next((c for c in df.columns if any(p in str(c).lower() for p in posibles_codigos)), None)
        col_nombre = next((c for c in df.columns if any(p in str(c).lower() for p in posibles_nombres)), None)

        if col_fecha and col_codigo and col_nombre:
            df_sub = df[[col_fecha, col_codigo, col_nombre]].copy()
        else:
            if len(df.columns) >= 4:
                df_sub = df.iloc[:, [0, 2, 3]].copy()
            elif len(df.columns) == 3:
                df_sub = df.iloc[:, [0, 1, 2]].copy()
            else:
                df_sub = df.copy()

        df_sub.columns = ['fecha', 'codigo', 'nombre']
        return df_sub

    @staticmethod
    def detectar_orden_fecha(valores_fecha):
        for val in valores_fecha:
            if isinstance(val, (pd.Timestamp, datetime.datetime, datetime.date)):
                continue
            match = re.search(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})', str(val))
            if match:
                primero, segundo, _ = match.groups()
                primero, segundo = int(primero), int(segundo)
                if primero > 12:
                    return True
                if segundo > 12:
                    return False
        return True

    @staticmethod
    def procesar_fecha_robusta(val, dia_primero=True):
        if pd.isna(val):
            return pd.NaT

        if isinstance(val, (pd.Timestamp, datetime.datetime, datetime.date)):
            return pd.Timestamp(val)

        val_str = str(val).strip()

        match = re.search(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\s*(\d{1,2}:\d{2}(?::\d{2})?)', val_str)
        if match:
            primero, segundo, anio, hora = match.groups()
            if len(anio) == 2:
                anio = '20' + anio
            dia, mes = (primero, segundo) if dia_primero else (segundo, primero)
            dia = dia.zfill(2)
            mes = mes.zfill(2)
            iso_str = f"{anio}-{mes}-{dia} {hora}"
            return pd.to_datetime(iso_str, errors='coerce')

        return pd.to_datetime(val_str, dayfirst=dia_primero, errors='coerce')

    # --- MÉTODOS DE CONTROL DE INTERFAZ ---

    def procesar_archivo(self):
        if not self.ruta_archivo:
            messagebox.showwarning("Advertencia", "No has seleccionado ningún archivo.", parent=self)
            return

        lista_archivos = []
        try:
            self.actualizar_estado("Procesando archivos...", "#E6A100")
            self.update()

            for ruta in self.ruta_archivo:
                df = self.cargar_dataframe(ruta)
                df_limpio = self.extraer_columnas_relevantes(df)
                lista_archivos.append(df_limpio)

            df_final = pd.concat(lista_archivos, ignore_index=True)

            for col in ['codigo', 'nombre']:
                df_final[col] = df_final[col].apply(lambda x: str(x).strip() if pd.notna(x) else x)

            dia_primero = self.detectar_orden_fecha(df_final['fecha'].tolist())

            df_final['fecha_dt'] = df_final['fecha'].apply(lambda v: self.procesar_fecha_robusta(v, dia_primero))
            df_final = df_final.dropna(subset=['fecha_dt']).sort_values(by='fecha_dt', ascending=True)

            if df_final.empty:
                raise ValueError("No se pudieron extraer datos válidos. Revisa la estructura del archivo cargado.")

            dfs_filtrados = []
            for codigo, grupo in df_final.groupby('codigo'):
                filas_validas = []
                ultima_ponchada = None
                for _, fila in grupo.iterrows():
                    fecha_actual = fila['fecha_dt']
                    if ultima_ponchada is None or (fecha_actual - ultima_ponchada) > pd.Timedelta(minutes=15):
                        filas_validas.append(fila)
                        ultima_ponchada = fecha_actual
                if filas_validas:
                    dfs_filtrados.append(pd.DataFrame(filas_validas))

            if dfs_filtrados:
                df_filtrado = pd.concat(dfs_filtrados, ignore_index=True).sort_values(by='fecha_dt', ascending=True).reset_index(drop=True)
            else:
                df_filtrado = pd.DataFrame(columns=df_final.columns)

            df_filtrado['fecha'] = df_filtrado['fecha_dt'].dt.strftime('%d/%m/%Y %H:%M:%S')
            df_final = df_filtrado.drop(columns=['fecha_dt'])

        except Exception as e:
            self.actualizar_estado("Error durante el procesamiento", "#D9534F")
            messagebox.showerror("Error de Procesamiento", f"Ocurrió un problema al procesar los archivos:\n{e}", parent=self)
            return

        ruta_guardado = filedialog.asksaveasfilename(
            title="Guardar archivo como...",
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Archivos Excel", "*.xlsx")],
            parent=self
        )

        if ruta_guardado:
            try:
                if ruta_guardado.endswith('.csv'):
                    with open(ruta_guardado, 'w', encoding='utf-8-sig', newline='') as f:
                        f.write('sep=;\n')
                        df_final.to_csv(f, index=False, sep=';')
                else:
                    df_final.to_excel(ruta_guardado, index=False)

                self.actualizar_estado("¡Procesamiento completado con éxito!", "#5CB85C")
                messagebox.showinfo("Éxito", "El archivo fue procesado y guardado correctamente.", parent=self)
            except Exception as e:
                self.actualizar_estado("Error al guardar el archivo", "#D9534F")
                messagebox.showerror("Error al Guardar", f"No se pudo guardar el archivo:\n{e}", parent=self)

    def subir_archivo(self):
        rutas_nuevas = filedialog.askopenfilenames(
            title="Selecciona los archivos",
            filetypes=[
                ("Todos los archivos soportados", "*.csv *.xlsx *.xls"),
                ("Archivos CSV", "*.csv"),
                ("Archivos Excel", "*.xlsx *.xls")
            ],
            parent=self
        )

        if rutas_nuevas:
            for ruta in rutas_nuevas:
                if ruta not in self.ruta_archivo:
                    self.ruta_archivo.append(ruta)
            self.actualizar_lista_archivos()

    def limpiar_lista(self):
        self.ruta_archivo = []
        self.actualizar_lista_archivos()
        self.actualizar_estado("Esperando archivos...", "#777777")

    def actualizar_lista_archivos(self):
        self.lista_archivos_subidos.configure(state="normal")
        self.lista_archivos_subidos.delete("1.0", "end")

        if self.ruta_archivo:
            lista_limpia = [f"  📄  {os.path.basename(ruta)}" for ruta in self.ruta_archivo]
            texto_limpio = "\n\n".join(lista_limpia)
            self.lista_archivos_subidos.insert("1.0", texto_limpio)
            self.lbl_contador.configure(text=f"Archivos listos para procesar: {len(self.ruta_archivo)}")
            self.actualizar_estado("Archivos cargados. Listo para procesar.", "#1F6AA5")
        else:
            self.lista_archivos_subidos.insert("1.0", "No hay archivos seleccionados")
            self.lbl_contador.configure(text="Archivos listos para procesar: 0")

        self.lista_archivos_subidos.configure(state="disabled")

    def actualizar_estado(self, texto, color):
        self.lbl_estado_dot.configure(text_color=color)
        self.lbl_estado_texto.configure(text=texto)

    def salir(self):
        """Cierra la ventana actual y regresa al menú principal."""
        self.destroy()
        if self.parent and self.parent.winfo_exists():
            self.parent.deiconify()
            self.parent.after(10, lambda: self.parent.wm_state("zoomed"))
    # --- DISEÑO DE LA INTERFAZ ---

    def _crear_interfaz(self):
        main_card = ctk.CTkFrame(master=self, corner_radius=20, width=1100, height=720, border_width=1, border_color="#2B2B2B")
        main_card.place(relx=0.5, rely=0.5, anchor="center")

        header_frame = ctk.CTkFrame(master=main_card, fg_color="#1E222A", corner_radius=15, height=90)
        header_frame.pack(fill="x", padx=25, pady=(25, 15))

        lbl_icon = ctk.CTkLabel(master=header_frame, text="📊", font=ctk.CTkFont(size=36))
        lbl_icon.pack(side="left", padx=(25, 15), pady=15)

        title_box = ctk.CTkFrame(master=header_frame, fg_color="transparent")
        title_box.pack(side="left", fill="y", pady=15)

        lbl_titulo = ctk.CTkLabel(
            master=title_box,
            text="Procesador de Control de Accesos",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        lbl_titulo.pack(anchor="w")

        lbl_subtitulo = ctk.CTkLabel(
            master=title_box,
            text="Unificación de reportes y depuración automática de checadas duplicadas",
            font=ctk.CTkFont(size=13),
            text_color="#A0A5B5"
        )
        lbl_subtitulo.pack(anchor="w")

        work_frame = ctk.CTkFrame(master=main_card, fg_color="transparent")
        work_frame.pack(fill="both", expand=True, padx=25, pady=10)

        left_frame = ctk.CTkFrame(master=work_frame, fg_color="transparent", width=320)
        left_frame.pack(side="left", fill="y", padx=(0, 20))

        actions_group = ctk.CTkFrame(master=left_frame, corner_radius=12, fg_color="#1A1C23", border_width=1, border_color="#2D313E")
        actions_group.pack(fill="x", pady=(0, 15), ipady=10)

        lbl_sec_acciones = ctk.CTkLabel(master=actions_group, text="Acciones", font=ctk.CTkFont(size=15, weight="bold"))
        lbl_sec_acciones.pack(anchor="w", padx=20, pady=(15, 10))

        btn_subir_archivo = ctk.CTkButton(
            master=actions_group,
            text="Seleccionar Archivo(s)",
            fg_color="#1F6AA5",
            hover_color="#144870",
            font=("Arial", 14, "bold"),
            height=42,
            command=self.subir_archivo
        )
        btn_subir_archivo.pack(fill="x", padx=20, pady=8)

        btn_limpiar = ctk.CTkButton(
            master=actions_group,
            text="Limpiar Lista",
            fg_color="#3A3D4A",
            hover_color="#4F5366",
            text_color="#E0E0E0",
            font=("Arial", 14, "bold"),
            height=40,
            command=self.limpiar_lista
        )
        btn_limpiar.pack(fill="x", padx=20, pady=4)

        btn_procesar = ctk.CTkButton(
            master=actions_group,
            text="Procesar y Guardar",
            fg_color="#27AE60",
            hover_color="#1E8449",
            font=("Arial", 14, "bold"),
            height=48,
            command=self.procesar_archivo
        )
        btn_procesar.pack(fill="x", padx=20, pady=(8, 10))

        btn_salir = ctk.CTkButton(
            master=actions_group,
            text="Salir",
            fg_color="#AE2727",
            hover_color="#841E1E",
            font=("arial", 14, "bold"),
            height=48,
            command=self.salir
        )
        btn_salir.pack(fill="x", padx=20, pady=2)

        right_frame = ctk.CTkFrame(master=work_frame, fg_color="#1A1C23", corner_radius=12, border_width=1, border_color="#2D313E")
        right_frame.pack(side="right", fill="both", expand=True)

        list_header = ctk.CTkFrame(master=right_frame, fg_color="transparent")
        list_header.pack(fill="x", padx=20, pady=(15, 10))

        self.lbl_contador = ctk.CTkLabel(
            master=list_header,
            text="Archivos listos para procesar: 0",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_contador.pack(side="left")

        self.lista_archivos_subidos = ctk.CTkTextbox(
            master=right_frame,
            corner_radius=8,
            font=("Arial", 13),
            fg_color="#111217",
            border_width=1,
            border_color="#252833"
        )
        self.lista_archivos_subidos.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.lista_archivos_subidos.insert("1.0", "No hay archivos seleccionados")
        self.lista_archivos_subidos.configure(state="disabled")

        status_bar = ctk.CTkFrame(master=main_card, fg_color="#16181E", corner_radius=10, height=40)
        status_bar.pack(fill="x", padx=25, pady=(5, 20))

        self.lbl_estado_dot = ctk.CTkLabel(master=status_bar, text="●", font=ctk.CTkFont(size=16), text_color="#777777")
        self.lbl_estado_dot.pack(side="left", padx=(15, 5))

        self.lbl_estado_texto = ctk.CTkLabel(
            master=status_bar,
            text="Esperando archivos...",
            font=ctk.CTkFont(size=12),
            text_color="#A0A5B5"
        )
        self.lbl_estado_texto.pack(side="left")


# Permite ejecutar este archivo directamente para hacer pruebas sin abrir el menú principal
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.withdraw()  # Oculta la ventana raíz de prueba
    ventana = VentanaSubirArchivos(root)
    ventana.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()