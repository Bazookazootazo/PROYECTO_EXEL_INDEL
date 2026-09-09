import os
import customtkinter as ctk
import tkinter as tk 
from tkinter import filedialog, messagebox
import pandas as pd

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Procesar Documentos - Control de Acceso")

# Configurar pantalla completa
app.after(10, lambda: app.wm_state('zoomed'))

ruta_archivo = []

# --- FUNCIONES DE LÓGICA (Se mantienen iguales) ---
def cargar_dataframe(ruta):
    _, extension = os.path.splitext(ruta)
    ext = extension.lower()
    if ext == '.csv':
        try:
            return pd.read_csv(ruta, sep=';', encoding='utf-8-sig', dtype=str)
        except Exception:
            return pd.read_csv(ruta, sep=',', encoding='latin1', dtype=str)
    elif ext in ['.xlsx', '.xls']:
        return pd.read_excel(ruta, dtype=str)
    else:
        raise ValueError(f"Formato no soportado: {extension}")

def extraer_columnas_relevantes(df):
    posibles_fechas = ['Data e Hora (Logs de Acesso)', 'Fecha', 'fecha', 'Data/Hora']
    posibles_codigos = ['Código (Usuário)', 'Codigo', 'codigo', 'ID', 'Matrícula']
    posibles_nombres = ['Nome (Usuário)', 'Nombre', 'nombre', 'Usuario']

    col_fecha = next((c for c in df.columns if any(p in str(c) for p in posibles_fechas)), None)
    col_codigo = next((c for c in df.columns if any(p in str(c) for p in posibles_codigos)), None)
    col_nombre = next((c for c in df.columns if any(p in str(c) for p in posibles_nombres)), None)

    if col_fecha and col_codigo and col_nombre:
        df_sub = df[[col_fecha, col_codigo, col_nombre]].copy()
    else:
        df_sub = df.iloc[:, [0, 2, 3]].copy()

    df_sub.columns = ['fecha', 'codigo', 'nombre']
    return df_sub

def filtrar_ponchadas_15min(df_grupo):
    filas_validas = []
    ultima_ponchada = None
    for _, fila in df_grupo.iterrows():
        fecha_actual = fila['fecha_dt']
        if ultima_ponchada is None or (fecha_actual - ultima_ponchada) > pd.Timedelta(minutes=15):
            filas_validas.append(fila)
            ultima_ponchada = fecha_actual
    return pd.DataFrame(filas_validas)

def procesar_archivo():
    if not ruta_archivo:
        messagebox.showwarning("Advertencia", "No has seleccionado ningún archivo.")
        return
    
    lista_archivos = []
    try:
        lbl_estado.configure(text="Procesando archivos...", text_color="#E6A100")
        app.update()

        for ruta in ruta_archivo:
            df = cargar_dataframe(ruta)
            df_limpio = extraer_columnas_relevantes(df)
            lista_archivos.append(df_limpio)

        df_final = pd.concat(lista_archivos, ignore_index=True)
        for col in df_final.columns:
            df_final[col] = df_final[col].astype(str).str.strip()

        df_final['fecha_dt'] = pd.to_datetime(df_final['fecha'], dayfirst=True, errors='coerce')
        df_final = df_final.dropna(subset=['fecha_dt']).sort_values(by='fecha_dt', ascending=True)

        df_filtrado = (
            df_final.groupby('codigo', group_keys=False)
            .apply(filtrar_ponchadas_15min)
            .sort_values(by='fecha_dt', ascending=True)
            .reset_index(drop=True)
        )

        df_filtrado['fecha'] = df_filtrado['fecha_dt'].dt.strftime('%d/%m/%Y %H:%M')
        df_final = df_filtrado.drop(columns=['fecha_dt'])

    except Exception as e:
        lbl_estado.configure(text="Error durante el procesamiento", text_color="#D9534F")
        messagebox.showerror("Error de Procesamiento", f"Ocurrió un problema al procesar los archivos:\n{e}")
        return

    ruta_guardado = filedialog.asksaveasfilename(
        title="Guardar archivo como...",
        defaultextension=".csv",
        filetypes=[("Archivos CSV", "*.csv"), ("Archivos Excel", "*.xlsx")]
    )

    if ruta_guardado:
        try:
            if ruta_guardado.endswith('.csv'):
                with open(ruta_guardado, 'w', encoding='utf-8-sig', newline='') as f:
                    f.write('sep=;\n')
                    df_final.to_csv(f, index=False, sep=';')
            else:
                df_final.to_excel(ruta_guardado, index=False)
            
            lbl_estado.configure(text="¡Procesamiento completado con éxito!", text_color="#5CB85C")
            messagebox.showinfo("Éxito", "El archivo fue procesado y guardado correctamente.")
        except Exception as e:
            lbl_estado.configure(text="Error al guardar el archivo", text_color="#D9534F")
            messagebox.showerror("Error al Guardar", f"No se pudo guardar el archivo:\n{e}")

def subir_archivo():
    global ruta_archivo
    rutas_nuevas = filedialog.askopenfilenames(
        title="Selecciona los archivos",
        filetypes=[
            ("Todos los archivos soportados", "*.csv *.xlsx *.xls"),
            ("Archivos CSV", "*.csv"),
            ("Archivos Excel", "*.xlsx *.xls")
        ]
    )

    if rutas_nuevas:
        for ruta in rutas_nuevas:
            if ruta not in ruta_archivo:
                ruta_archivo.append(ruta)
        actualizar_lista_archivos()

def limpiar_lista():
    global ruta_archivo
    ruta_archivo = []
    actualizar_lista_archivos()
    lbl_estado.configure(text="Esperando archivos...", text_color="gray")

def actualizar_lista_archivos():
    lista_archivos_subidos.configure(state="normal")
    lista_archivos_subidos.delete("1.0", "end")

    if ruta_archivo:
        lista_limpia = [f"  •  {os.path.basename(ruta)}" for ruta in ruta_archivo]
        texto_limpio = "\n".join(lista_limpia)
        lista_archivos_subidos.insert("1.0", texto_limpio)
        lbl_contador.configure(text=f"Archivos cargados: {len(ruta_archivo)}")
    else:
        lista_archivos_subidos.insert("1.0", "No hay archivos seleccionados")
        lbl_contador.configure(text="Archivos cargados: 0")

    lista_archivos_subidos.configure(state="disabled")

# --- DISEÑO DE INTERFAZ MEJORADO ---

# Contenedor Tarjeta Principal
main_card = ctk.CTkFrame(master=app, corner_radius=15, width=900, height=650)
main_card.place(relx=0.5, rely=0.5, anchor="center")

# Título y Subtítulo
lbl_titulo = ctk.CTkLabel(
    master=main_card, 
    text="Control de Accesos - Registro de Docentes", 
    font=ctk.CTkFont(size=26, weight="bold")
)
lbl_titulo.pack(pady=(30, 5))

lbl_subtitulo = ctk.CTkLabel(
    master=main_card, 
    text="Sube los archivos CSV o Excel para unificar y filtrar ponchadas duplicadas (15 min)", 
    font=ctk.CTkFont(size=14),
    text_color="gray"
)
lbl_subtitulo.pack(pady=(0, 20))

# Panel de trabajo en 2 columnas (Izquierda: Botones | Derecha: Lista)
work_frame = ctk.CTkFrame(master=main_card, fg_color="transparent")
work_frame.pack(fill="both", expand=True, padx=40, pady=10)

# Columna Izquierda (Acciones)
left_frame = ctk.CTkFrame(master=work_frame, fg_color="transparent")
left_frame.pack(side="left", fill="y", padx=(0, 20), pady=10)

btn_subir_archivo = ctk.CTkButton(
    master=left_frame, 
    text="Seleccionar Archivo(s)", 
    fg_color="#1F6AA5", 
    hover_color="#144870", 
    font=("Arial", 15, "bold"),
    width=220,
    height=45,
    command=subir_archivo
)
btn_subir_archivo.pack(pady=(20, 10))

btn_limpiar = ctk.CTkButton(
    master=left_frame, 
    text="Limpiar Lista", 
    fg_color="#D9534F", 
    hover_color="#A93226", 
    font=("Arial", 15, "bold"),
    width=220,
    height=45,
    command=limpiar_lista
)
btn_limpiar.pack(pady=10)

btn_procesar = ctk.CTkButton(
    master=left_frame, 
    text="Procesar y Guardar", 
    fg_color="#27AE60", 
    hover_color="#1E8449", 
    font=("Arial", 15, "bold"),
    width=220,
    height=50,
    command=procesar_archivo
)
btn_procesar.pack(pady=(30, 10))

# Columna Derecha (Visualización de lista)
right_frame = ctk.CTkFrame(master=work_frame, fg_color="transparent")
right_frame.pack(side="right", fill="both", expand=True, pady=10)

lbl_contador = ctk.CTkLabel(
    master=right_frame, 
    text="Archivos cargados: 0", 
    font=ctk.CTkFont(size=13, weight="bold")
)
lbl_contador.pack(anchor="w", pady=(0, 5))

lista_archivos_subidos = ctk.CTkTextbox(
    master=right_frame, 
    corner_radius=10, 
    font=("Arial", 13),
    border_width=1,
    border_color="#333333"
)
lista_archivos_subidos.pack(fill="both", expand=True)
lista_archivos_subidos.insert("1.0", "No hay archivos seleccionados")
lista_archivos_subidos.configure(state="disabled")

# Barra de estado inferior
lbl_estado = ctk.CTkLabel(
    master=main_card, 
    text="Esperando archivos...", 
    font=ctk.CTkFont(size=12, weight="bold"),
    text_color="gray"
)
lbl_estado.pack(pady=(10, 20))

app.mainloop()