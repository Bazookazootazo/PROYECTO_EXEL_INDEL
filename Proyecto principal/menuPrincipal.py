import ctypes
import customtkinter as ctk
from gestion_docente.prueba2 import VentanaGestionDocentes
from subir_archivos import VentanaSubirArchivos
from utilerias.paleta_colores import colores, fuentes
from generar_reporte import VentanaGenerarReporte
from registro_checadas import VentanaRegistroChecadas

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Menú de Inicio - Control de Acceso")
app.configure(fg_color=colores.BG_VENTANA)

# --- CONFIGURACIÓN Y CENTRADO CORREGIDO ---
ANCHO, ALTO = 900, 680

def centrar_ventana(ventana, ancho, alto):
    ventana.update_idletasks()
    
    # Obtener el factor de escalado DPI que customtkinter está aplicando
    scaling = ventana._get_window_scaling()
    
    # Ancho y alto reales escalados
    ancho_escalado = int(ancho * scaling)
    alto_escalado = int(alto * scaling)
    
    # Ancho y alto de la pantalla completa
    sw = ventana.winfo_screenwidth()
    sh = ventana.winfo_screenheight()
    
    # Calcular coordenadas centradas reales
    pos_x = max(0, int((sw - ancho_escalado) / 2))
    pos_y = max(0, int((sh - alto_escalado) / 2))
    
    ventana.geometry(f"{ancho}x{alto}+{pos_x}+{pos_y}")

centrar_ventana(app, ANCHO, ALTO)
app.resizable(True, True)

# Referencias para las ventanas secundarias
ventana_docentes = None
ventana_subir = None
ventana_generar = None
ventana_checadas = None

# --- FUNCIONES DE NAVEGACIÓN ---
def volver_al_menu(ventana_secundaria):
    if ventana_secundaria and ventana_secundaria.winfo_exists():
        ventana_secundaria.destroy()
    
    app.deiconify()
    app.wm_state('normal')
    centrar_ventana(app, ANCHO, ALTO)

def abrir_gestion_docentes():
    global ventana_docentes
    if ventana_docentes is None or not ventana_docentes.winfo_exists():
        app.withdraw()
        ventana_docentes = VentanaGestionDocentes(app)
        ventana_docentes.protocol(
            "WM_DELETE_WINDOW", lambda: volver_al_menu(ventana_docentes)
        )
    else:
        ventana_docentes.focus()

def abrir_subir_archivos():
    global ventana_subir
    if ventana_subir is None or not ventana_subir.winfo_exists():
        app.withdraw()
        ventana_subir = VentanaSubirArchivos(app)
        ventana_subir.protocol(
            "WM_DELETE_WINDOW", lambda: volver_al_menu(ventana_subir)
        )
    else:
        ventana_subir.focus()

def abrir_generar_reporte():
    global ventana_generar
    if ventana_generar is None or not ventana_generar.winfo_exists():
        app.withdraw()
        ventana_generar = VentanaGenerarReporte(app)
        ventana_generar.protocol(
            "WM_DELETE_WINDOW", lambda: volver_al_menu(ventana_generar)
        )
    else:
        ventana_generar.focus()

def abrir_registro_checadas():
    global ventana_checadas
    if ventana_checadas is None or not ventana_checadas.winfo_exists():
        app.withdraw()
        ventana_checadas = VentanaRegistroChecadas(app)
        ventana_checadas.protocol(
            "WM_DELETE_WINDOW", lambda: volver_al_menu(ventana_checadas)
        )
    else:
        ventana_checadas.focus()

def salir():
    app.destroy()

# --- DISEÑO DEL MENÚ PRINCIPAL ---

main_card = ctk.CTkFrame(
    master=app,
    corner_radius=22,
    fg_color=colores.BG_PANEL,
    border_width=1,
    border_color=colores.BORDE,
)
main_card.pack(fill="both", expand=True, padx=15, pady=15)

# Franja de acento superior
franja_acento = ctk.CTkFrame(
    master=main_card, corner_radius=0, fg_color=colores.ACENTO, height=4
)
franja_acento.pack(fill="x", side="top")

# Encabezado
header_frame = ctk.CTkFrame(master=main_card, fg_color="transparent")
header_frame.pack(fill="x", pady=(15, 10), padx=20)

lbl_kicker = ctk.CTkLabel(
    master=header_frame,
    text="SISTEMA DE ASISTENCIA",
    font=fuentes.pequena(size=11),
    text_color=colores.ACENTO,
)
lbl_kicker.pack()

lbl_titulo = ctk.CTkLabel(
    master=header_frame,
    text="Control de Acceso Docente",
    font=fuentes.titulo(size=24),
    text_color=colores.TEXTO_PRIMARIO,
)
lbl_titulo.pack(pady=(2, 0))

lbl_subtitulo = ctk.CTkLabel(
    master=header_frame,
    text="Selecciona un módulo para continuar",
    font=fuentes.subtitulo(size=13),
    text_color=colores.TEXTO_SECUNDARIO,
)
lbl_subtitulo.pack(pady=(2, 0))

# Contenedor de Tarjetas de Opciones (Permitir Scroll si falta espacio vertical)
cards_container = ctk.CTkScrollableFrame(master=main_card, fg_color="transparent")
cards_container.pack(fill="both", expand=True, padx=15, pady=5)
cards_container.grid_columnconfigure((0, 1), weight=1, uniform="col")

# Tarjeta 1: Procesar Archivos
card_subir = ctk.CTkFrame(
    master=cards_container,
    corner_radius=16,
    fg_color=colores.BG_PANEL_ALT,
    border_width=1,
    border_color=colores.BORDE,
)
card_subir.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

icono_subir_bg = ctk.CTkFrame(
    master=card_subir, fg_color=colores.ACENTO_SUAVE, corner_radius=14,
    width=50, height=50,
)
icono_subir_bg.pack(pady=(15, 8))
icono_subir_bg.pack_propagate(False)

lbl_icon_subir = ctk.CTkLabel(
    master=icono_subir_bg, text="📊", font=ctk.CTkFont(size=24)
)
lbl_icon_subir.pack(expand=True)

lbl_title_subir = ctk.CTkLabel(
    master=card_subir,
    text="Limpiar y guardar archivos",
    font=fuentes.seccion(size=15),
    text_color=colores.TEXTO_PRIMARIO,
)
lbl_title_subir.pack()

lbl_desc_subir = ctk.CTkLabel(
    master=card_subir,
    text="Importa, limpia y guarda archivos\npara la generación de reportes.",
    font=fuentes.cuerpo(size=11),
    text_color=colores.TEXTO_SECUNDARIO,
    justify="center",
)
lbl_desc_subir.pack(pady=(4, 12))

btn_subir = ctk.CTkButton(
    master=card_subir,
    text="Abrir Módulo",
    font=fuentes.boton(size=12),
    height=36,
    corner_radius=10,
    fg_color=colores.ACENTO,
    hover_color=colores.ACENTO_HOVER,
    text_color=colores.TEXTO_SOBRE_ACENTO,
    command=abrir_subir_archivos,
)
btn_subir.pack(fill="x", padx=15, pady=(0, 15))

# Tarjeta 2: Gestión de Docentes
card_docentes = ctk.CTkFrame(
    master=cards_container,
    corner_radius=16,
    fg_color=colores.BG_PANEL_ALT,
    border_width=1,
    border_color=colores.BORDE,
)
card_docentes.grid(row=0, column=1, padx=8, pady=8, sticky="nsew")

icono_docentes_bg = ctk.CTkFrame(
    master=card_docentes, fg_color="#12352A", corner_radius=14,
    width=50, height=50,
)
icono_docentes_bg.pack(pady=(15, 8))
icono_docentes_bg.pack_propagate(False)

lbl_icon_docentes = ctk.CTkLabel(
    master=icono_docentes_bg, text="👨", font=ctk.CTkFont(size=24)
)
lbl_icon_docentes.pack(expand=True)

lbl_title_docentes = ctk.CTkLabel(
    master=card_docentes,
    text="Gestión de Docentes",
    font=fuentes.seccion(size=15),
    text_color=colores.TEXTO_PRIMARIO,
)
lbl_title_docentes.pack()

lbl_desc_docentes = ctk.CTkLabel(
    master=card_docentes,
    text="Administra el catálogo de\nprofesores, asignaturas y horarios.",
    font=fuentes.cuerpo(size=11),
    text_color=colores.TEXTO_SECUNDARIO,
    justify="center",
)
lbl_desc_docentes.pack(pady=(4, 12))

btn_docentes = ctk.CTkButton(
    master=card_docentes,
    text="Abrir Módulo",
    font=fuentes.boton(size=12),
    height=36,
    corner_radius=10,
    fg_color=colores.EXITO,
    hover_color=colores.EXITO_HOVER,
    text_color=colores.TEXTO_SOBRE_ACENTO,
    command=abrir_gestion_docentes,
)
btn_docentes.pack(fill="x", padx=15, pady=(0, 15))

# Tarjeta 3: Generación de Reportes
card_generador = ctk.CTkFrame(
    master=cards_container,
    corner_radius=16,
    fg_color=colores.BG_PANEL_ALT,
    border_width=1,
    border_color=colores.BORDE,
)
card_generador.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")   

icono_generador_bg = ctk.CTkFrame(
    master=card_generador, fg_color="#352A12", corner_radius=14,
    width=50, height=50,
)
icono_generador_bg.pack(pady=(15, 8))
icono_generador_bg.pack_propagate(False)

lbl_icon_generador = ctk.CTkLabel(
    master=icono_generador_bg, text="📋", font=ctk.CTkFont(size=24)
)
lbl_icon_generador.pack(expand=True)

lbl_title_generador = ctk.CTkLabel(
    master=card_generador,
    text="Generación de Reporte de Asistencia",
    font=fuentes.seccion(size=15),
    text_color=colores.TEXTO_PRIMARIO,
)
lbl_title_generador.pack()

lbl_desc_generador = ctk.CTkLabel(
    master=card_generador,
    text="Genera reportes quincenales sobre la asistencia de los docentes",
    font=fuentes.cuerpo(size=11),
    text_color=colores.TEXTO_SECUNDARIO,
    justify="center",
)
lbl_desc_generador.pack(pady=(4, 12))

btn_generador = ctk.CTkButton(
    master=card_generador,
    text="Abrir Módulo",
    font=fuentes.boton(size=12),
    height=36,
    corner_radius=10,
    fg_color="#EEA942",
    hover_color="#AA7526",
    text_color=colores.TEXTO_SOBRE_ACENTO,
    command=abrir_generar_reporte,
)
btn_generador.pack(fill="x", padx=15, pady=(0, 15))

# Tarjeta 4: Registro de Checadas
card_checadas = ctk.CTkFrame(
    master=cards_container,
    corner_radius=16,
    fg_color=colores.BG_PANEL_ALT,
    border_width=1,
    border_color=colores.BORDE,
)
card_checadas.grid(row=1, column=1, padx=8, pady=8, sticky="nsew")

icono_checadas_bg = ctk.CTkFrame(
    master=card_checadas, fg_color="#2A1F46", corner_radius=14,
    width=50, height=50,
)
icono_checadas_bg.pack(pady=(15, 8))
icono_checadas_bg.pack_propagate(False)

lbl_icon_checadas = ctk.CTkLabel(
    master=icono_checadas_bg, text="🕒", font=ctk.CTkFont(size=24)
)
lbl_icon_checadas.pack(expand=True)

lbl_title_checadas = ctk.CTkLabel(
    master=card_checadas,
    text="Registro de Checadas",
    font=fuentes.seccion(size=15),
    text_color=colores.TEXTO_PRIMARIO,
)
lbl_title_checadas.pack()

lbl_desc_checadas = ctk.CTkLabel(
    master=card_checadas,
    text="Consulta todas las ponchadas\nguardadas en el sistema.",
    font=fuentes.cuerpo(size=11),
    text_color=colores.TEXTO_SECUNDARIO,
    justify="center",
)
lbl_desc_checadas.pack(pady=(4, 12))

btn_checadas = ctk.CTkButton(
    master=card_checadas,
    text="Abrir Módulo",
    font=fuentes.boton(size=12),
    height=36,
    corner_radius=10,
    fg_color="#8B6CE0",
    hover_color="#6B50B8",
    text_color=colores.TEXTO_SOBRE_ACENTO,
    command=abrir_registro_checadas,
)
btn_checadas.pack(fill="x", padx=15, pady=(0, 15))

# Separador
separador = ctk.CTkFrame(master=main_card, fg_color=colores.BORDE_SUAVE, height=1)
separador.pack(fill="x", padx=20, pady=(2, 0))

# Pie de página
footer_frame = ctk.CTkFrame(master=main_card, fg_color="transparent")
footer_frame.pack(fill="x", padx=20, pady=(8, 12))

lbl_footer_info = ctk.CTkLabel(
    master=footer_frame,
    text="Control de Acceso Docente",
    font=fuentes.pequena(size=10),
    text_color=colores.TEXTO_TENUE,
)
lbl_footer_info.pack(side="left")

btn_salir = ctk.CTkButton(
    master=footer_frame,
    text="Cerrar Aplicación",
    font=fuentes.boton(size=12),
    height=32,
    width=140,
    corner_radius=10,
    fg_color=colores.NEUTRO,
    hover_color=colores.PELIGRO_HOVER,
    text_color=colores.TEXTO_PRIMARIO,
    command=salir,
)
btn_salir.pack(side="right")

app.mainloop()
