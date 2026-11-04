import os
import re
import csv
import io
import datetime
import unicodedata
import threading
from difflib import SequenceMatcher
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import mysql.connector
from generar_reporte import VentanaGenerarReporte

ANCHO, ALTO = 1100, 720

def centrar_ventana(ventana, ancho, alto):
    ventana.update_idletasks()
    pos_x = int((ventana.winfo_screenwidth() / 2) - (ancho / 2))
    pos_y = int((ventana.winfo_screenheight() / 2) - (alto / 2))
    ventana.geometry(f"{ancho}x{alto}+{pos_x}+{pos_y}")

from utilerias.paleta_colores import colores, fuentes
ventana_generar = None
    
def volver_al_menu(ventana_secundaria):
      if ventana_secundaria and ventana_secundaria.winfo_exists():
        ventana_secundaria.destroy()
    
      ventana.deiconify()
      ventana.wm_state('normal')
      centrar_ventana(ventana, ANCHO, ALTO)

class VentanaSubirArchivos(ctk.CTkToplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.title("Procesar Documentos - Control de Acceso")
        self.configure(fg_color=colores.BG_VENTANA)

        self.state('zoomed') 
        self.resizable(True, True)

        self.focus()
        self.lift()
        self.ruta_archivo = []
        self._crear_interfaz()

    @staticmethod
    def obtener_conexion_bd():
        return mysql.connector.connect(
            host="localhost",
            user="root",        
            password="",        
            database="control_asistencia" 
        )

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

            raise ValueError("No se pudo determinar el delimitador ni la codificación del archivo CSV.")

        elif ext in ['.xlsx', '.xls']:
            return pd.read_excel(ruta)
        else:
            raise ValueError(f"Formato no soportado: {extension}")

    @staticmethod
    def extraer_columnas_relevantes(df):
        posibles_fechas = ['data e hora', 'fecha', 'data/hora', 'date', 'time', 'hora', 'fecha/hora']
        posibles_nombres = ['nome', 'nombre', 'name', 'empleado', 'docente', 'persona']

        col_fecha = next((c for c in df.columns if any(p in str(c).lower() for p in posibles_fechas)), None)
        col_nombre = next((c for c in df.columns if any(p in str(c).lower() for p in posibles_nombres)), None)

        if col_fecha and col_nombre:
            df_sub = df[[col_fecha, col_nombre]].copy()
        else:
            if len(df.columns) >= 2:
                df_sub = df.iloc[:, [0, 1]].copy()
            else:
                df_sub = df.copy()

        df_sub.columns = ['fecha', 'nombre']
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

    # --- FUNCIONES DE COINCIDENCIA DIFUSA OPTIMIZADAS ---
    @staticmethod
    def _normalizar_texto(texto):
        if not texto:
            return ""
        texto = unicodedata.normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('utf-8')
        return " ".join(texto.lower().split())

    def _calcular_similitud(self, norm_bd, norm_arch, palabras_bd):
        if norm_bd == norm_arch:
            return 1.0
        palabras_arch = set(norm_arch.split())
        if not palabras_bd or not palabras_arch:
            return 0.0

        interseccion = palabras_bd.intersection(palabras_arch)
        union = palabras_bd.union(palabras_arch)
        
        jaccard = len(interseccion) / len(union)
        seq_sim = SequenceMatcher(None, norm_bd, norm_arch).ratio()
        return (jaccard * 0.7) + (seq_sim * 0.3)

    def _encontrar_profesor_id(self, nombre_en_archivo, profesores_cache, umbral=0.45):
        norm_arch = self._normalizar_texto(nombre_en_archivo)
        mejor_id = None
        mejor_score = 0.0

        for prof_id, norm_bd, palabras_bd in profesores_cache:
            score = self._calcular_similitud(norm_bd, norm_arch, palabras_bd)
            if score > mejor_score:
                mejor_score = score
                mejor_id = prof_id

        if mejor_score >= umbral:
            return mejor_id
        return None
    # --------------------------------------------------

    def procesar_archivo(self):
        if not self.ruta_archivo:
            messagebox.showwarning("Advertencia", "No has seleccionado ningún archivo.", parent=self)
            return

        # Ejecutar en segundo plano (Threading) para evitar congelar la interfaz con 45k+ registros
        threading.Thread(target=self._ejecutar_proceso_pesado, daemon=True).start()

    def _ejecutar_proceso_pesado(self):
        try:
            self.actualizar_estado("Procesando archivo masivo...", colores.ESTADO_PROCESANDO)
            
            lista_archivos = []
            for ruta in self.ruta_archivo:
                df = self.cargar_dataframe(ruta)
                df_limpio = self.extraer_columnas_relevantes(df)
                lista_archivos.append(df_limpio)

            df_final = pd.concat(lista_archivos, ignore_index=True)

            if 'nombre' in df_final.columns:
                df_final['nombre'] = df_final['nombre'].apply(lambda x: str(x).strip() if pd.notna(x) else x)

            dia_primero = self.detectar_orden_fecha(df_final['fecha'].tolist())
            df_final['fecha_dt'] = df_final['fecha'].apply(lambda v: self.procesar_fecha_robusta(v, dia_primero))
            df_final = df_final.dropna(subset=['fecha_dt']).sort_values(by='fecha_dt', ascending=True)

            if df_final.empty:
                raise ValueError("No se pudieron extraer datos válidos. Revisa la estructura del archivo.")
            
            # Optimización de intervalos de 15 min por docente
            dfs_filtrados = []
            for nombre, grupo in df_final.groupby('nombre'):
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

            self.actualizar_estado("Asociando nombres y guardando en BD...", colores.ESTADO_PROCESANDO)

            conn = self.obtener_conexion_bd()
            cursor = conn.cursor()

            cursor.execute("SELECT id_profesor, nombre FROM profesores")
            profesores_brutos = cursor.fetchall()
            
            # Precalcular caché de profesores para velocidad extrema
            profesores_cache = [
                (p_id, self._normalizar_texto(p_nom), set(self._normalizar_texto(p_nom).split()))
                for p_id, p_nom in profesores_brutos
            ]

            # Caché de nombres unicos del archivo para no recalcular similitud 45,000 veces
            cache_nombres_archivo = {}

            registros_a_insertar = []
            profesores_no_encontrados = set()

            for _, fila in df_filtrado.iterrows():
                nombre_archivo = str(fila['nombre']).strip()
                
                if nombre_archivo not in cache_nombres_archivo:
                    cache_nombres_archivo[nombre_archivo] = self._encontrar_profesor_id(nombre_archivo, profesores_cache, umbral=0.45)

                id_profesor = cache_nombres_archivo[nombre_archivo]

                if id_profesor:
                    fecha_mysql = fila['fecha_dt'].strftime('%Y-%m-%d %H:%M:%S')
                    registros_a_insertar.append((id_profesor, fecha_mysql))
                else:
                    profesores_no_encontrados.add(nombre_archivo)

            registros_insertados = 0
            if registros_a_insertar:
                sql_insert = "INSERT IGNORE INTO checadas (id_profesor, fecha_hora) VALUES (%s, %s)"
                cursor.executemany(sql_insert, registros_a_insertar)
                conn.commit()
                registros_insertados = cursor.rowcount

            cursor.close()
            conn.close()

            self.actualizar_estado("¡Procesamiento masivo completado!", colores.ESTADO_EXITO)
            
            mensaje = f"Se procesaron y guardaron {registros_insertados} registros correctamente." 
            if profesores_no_encontrados:
                mensaje += f"\n\nNota: Hubo {len(profesores_no_encontrados)} nombre(s) que no coincidieron con ningún docente:"
                for p_no in list(profesores_no_encontrados)[:5]:
                    mensaje += f"\n- {p_no}"

            messagebox.showinfo("Éxito", mensaje, parent=self)
            self.limpiar_lista()

        except Exception as err:
            self.actualizar_estado("Error durante el procesamiento", colores.ESTADO_ERROR)
            messagebox.showerror("Error", f"Ocurrió un error inesperado:\n{err}", parent=self)

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
        self.actualizar_estado("Esperando archivos...", colores.ESTADO_INACTIVO)

    def actualizar_lista_archivos(self):
        self.lista_archivos_subidos.configure(state="normal")
        self.lista_archivos_subidos.delete("1.0", "end")

        if self.ruta_archivo:
            lista_limpia = [f"  📄  {os.path.basename(ruta)}" for ruta in self.ruta_archivo]
            texto_limpio = "\n\n".join(lista_limpia)
            self.lista_archivos_subidos.insert("1.0", texto_limpio)
            self.lbl_contador.configure(text=f"Archivos listos para procesar: {len(self.ruta_archivo)}")
            self.actualizar_estado("Archivos cargados. Listo para procesar.", colores.ESTADO_INFO)
        else:
            self.lista_archivos_subidos.insert("1.0", "No hay archivos seleccionados")
            self.lbl_contador.configure(text="Archivos listos para procesar: 0")

        self.lista_archivos_subidos.configure(state="disabled")

    def actualizar_estado(self, texto, color):
        self.lbl_estado_dot.configure(text_color=color)
        self.lbl_estado_texto.configure(text=texto)

    def regresar_al_menu(self):
        if self.parent:
            self.parent.wm_state('normal')
            self.parent.deiconify()
        self.destroy()

    def ir_generar_reporte(self):
        global ventana_generar
        if ventana_generar is None or not ventana_generar.winfo_exists():
                self.withdraw()
                ventana_generar = VentanaGenerarReporte(self)
                ventana_generar.protocol(
                "WM_DELETE_WINDOW", lambda: volver_al_menu(ventana_generar)
                )
        else:
                ventana_generar.focus()

    def _crear_interfaz(self):
        main_card = ctk.CTkFrame(
            master=self, 
            corner_radius=20, 
            fg_color=colores.BG_PANEL, 
            border_width=1, 
            border_color=colores.BORDE
        )
        main_card.pack(fill="both", expand=True, padx=15, pady=15)

        franja_acento = ctk.CTkFrame(master=main_card, corner_radius=0, fg_color=colores.ACENTO, height=4)
        franja_acento.pack(fill="x", side="top")

        header_frame = ctk.CTkFrame(master=main_card, fg_color=colores.BG_PANEL_ALT, corner_radius=15, height=90, border_width=1, border_color=colores.BORDE_SUAVE)
        header_frame.pack(fill="x", padx=25, pady=(20, 15))

        icono_bg = ctk.CTkFrame(master=header_frame, fg_color=colores.ACENTO_SUAVE, corner_radius=14, width=58, height=58)
        icono_bg.pack(side="left", padx=(22, 15), pady=15)
        icono_bg.pack_propagate(False)
        lbl_icon = ctk.CTkLabel(master=icono_bg, text="📊", font=ctk.CTkFont(size=26))
        lbl_icon.pack(expand=True)

        title_box = ctk.CTkFrame(master=header_frame, fg_color="transparent")
        title_box.pack(side="left", fill="y", pady=15)

        lbl_titulo = ctk.CTkLabel(
            master=title_box,
            text="Procesador de Control de Accesos",
            font=fuentes.titulo(size=22),
            text_color=colores.TEXTO_PRIMARIO,
        )
        lbl_titulo.pack(anchor="w")

        lbl_subtitulo = ctk.CTkLabel(
            master=title_box,
            text="Depuracion de checadas de docentes y generacion de reportes de asistencia, favor de agregar el archivo de registro de checadas (CSV/Excel) para procesar.",
            font=fuentes.cuerpo(size=13),
            text_color=colores.TEXTO_SECUNDARIO,
        )
        lbl_subtitulo.pack(anchor="w", pady=(2, 0))

        work_frame = ctk.CTkFrame(master=main_card, fg_color="transparent")
        work_frame.pack(fill="both", expand=True, padx=25, pady=10)

        left_frame = ctk.CTkFrame(master=work_frame, fg_color="transparent", width=320)
        left_frame.pack(side="left", fill="y", padx=(0, 20))

        actions_group = ctk.CTkFrame(master=left_frame, corner_radius=14, fg_color=colores.BG_PANEL_ALT, border_width=1, border_color=colores.BORDE_SUAVE)
        actions_group.pack(fill="x", pady=(0, 15), ipady=10)

        lbl_sec_acciones = ctk.CTkLabel(master=actions_group, text="ACCIONES", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO)
        lbl_sec_acciones.pack(anchor="w", padx=20, pady=(16, 10))

        btn_subir_archivo = ctk.CTkButton(
            master=actions_group,
            text="Seleccionar Archivo",
            fg_color=colores.ACENTO,
            hover_color=colores.ACENTO_HOVER,
            font=fuentes.boton(size=14),
            corner_radius=10,
            height=42,
            command=self.subir_archivo
        )
        btn_subir_archivo.pack(fill="x", padx=20, pady=8)

        btn_procesar = ctk.CTkButton(
            master=actions_group,
            text="Procesar y Guardar",
            fg_color=colores.EXITO,
            hover_color=colores.EXITO_HOVER,
            font=fuentes.boton(size=14),
            corner_radius=10,
            height=48,
            command=self.procesar_archivo
        )
        btn_procesar.pack(fill="x", padx=20, pady=(8))

        btn_limpiar = ctk.CTkButton(
            master=actions_group,
            text="Limpiar Lista",
            fg_color=colores.NEUTRO,
            hover_color=colores.NEUTRO_HOVER,
            text_color=colores.TEXTO_PRIMARIO,
            font=fuentes.boton(size=14),
            corner_radius=10,
            height=40,
            command=self.limpiar_lista
        )
        btn_limpiar.pack(fill="x", padx=20, pady=8)
        right_frame = ctk.CTkFrame(master=work_frame, fg_color=colores.BG_PANEL_ALT, corner_radius=14, border_width=1, border_color=colores.BORDE_SUAVE)
        right_frame.pack(side="right", fill="both", expand=True)

        list_header = ctk.CTkFrame(master=right_frame, fg_color="transparent")
        list_header.pack(fill="x", padx=20, pady=(16, 10))

        self.lbl_contador = ctk.CTkLabel(
            master=list_header,
            text="Archivos listos para procesar: 0",
            font=fuentes.seccion(size=14),
            text_color=colores.TEXTO_PRIMARIO,
        )
        self.lbl_contador.pack(side="left")

        self.lista_archivos_subidos = ctk.CTkTextbox(
            master=right_frame,
            corner_radius=10,
            font=fuentes.monoespaciada(size=13),
            fg_color=colores.BG_ENTRADA,
            text_color=colores.TEXTO_SECUNDARIO,
            border_width=1,
            border_color=colores.BORDE
        )
        self.lista_archivos_subidos.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.lista_archivos_subidos.insert("1.0", "No hay archivos seleccionados")
        self.lista_archivos_subidos.configure(state="disabled")

        status_bar = ctk.CTkFrame(master=main_card, fg_color=colores.BG_ENTRADA, corner_radius=10, height=40, border_width=1, border_color=colores.BORDE_SUAVE)
        status_bar.pack(fill="x", padx=25, pady=(5, 20))

        self.lbl_estado_dot = ctk.CTkLabel(master=status_bar, text="●", font=ctk.CTkFont(size=16), text_color=colores.ESTADO_INACTIVO)
        self.lbl_estado_dot.pack(side="left", padx=(16, 6))

        self.lbl_estado_texto = ctk.CTkLabel(
            master=status_bar,
            text="Esperando archivos...",
            font=fuentes.cuerpo(size=12),
            text_color=colores.TEXTO_SECUNDARIO,
        )
        self.lbl_estado_texto.pack(side="left")

        footer_frame = ctk.CTkFrame(master=main_card, fg_color="transparent")
        footer_frame.pack(fill="x", padx=25, pady=(0, 15))

        btn_volver_al_menu = ctk.CTkButton(
            master=footer_frame,
            text="Volver al menu principal",
            font=fuentes.boton(size=13),
            height=36,
            width=170,
            corner_radius=10,
            fg_color=colores.NEUTRO,
            hover_color=colores.NEUTRO_HOVER,
            text_color=colores.TEXTO_PRIMARIO,
            command=self.regresar_al_menu
        )
        btn_volver_al_menu.pack(side="right")

        btn_generar_reporte = ctk.CTkButton(
            master=footer_frame,
            text="generar Reporte de Asistencia",
            font=fuentes.boton(size=13),
            height=36,
            width=170,
            corner_radius=10,
            fg_color="#EEA942",
            hover_color="#AA7526",
            text_color=colores.TEXTO_SOBRE_ACENTO,
            command=self.ir_generar_reporte
        )
        btn_generar_reporte.pack(side="right", padx=(0, 10))

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.withdraw()
    ventana = VentanaSubirArchivos(root)
    ventana.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()