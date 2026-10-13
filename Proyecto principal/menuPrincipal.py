import customtkinter as ctk
from gestion_docente.prueba2 import VentanaGestionDocentes
from subir_archivos import VentanaSubirArchivos
from utilerias.paleta_colores import colores, fuentes

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Menú de Inicio - Control de Acceso")
app.configure(fg_color=colores.BG_VENTANA)

# --- 1. CONFIGURACIÓN Y CENTRADO DE LA VENTANA PRINCIPAL ---
ANCHO, ALTO = 960, 840

def centrar_ventana(ventana, ancho, alto):
    ventana.update_idletasks()
    pos_x = int((ventana.winfo_screenwidth() / 2) - (ancho / 2))
    pos_y = int((ventana.winfo_screenheight() / 2) - (alto / 2))
    ventana.geometry(f"{ancho}x{alto}+{pos_x}+{pos_y}")

centrar_ventana(app, ANCHO, ALTO)
app.resizable(False, False)

# Referencias para las ventanas secundarias
ventana_docentes = None
ventana_subir = None

# --- 2. FUNCIÓN CORREGIDA PARA VOLVER AL MENÚ ---
def volver_al_menu(ventana_secundaria):
    if ventana_secundaria and ventana_secundaria.winfo_exists():
        ventana_secundaria.destroy()
    
    # Restaurar la ventana principal 'app'
    app.deiconify()               # Vuelve a mostrar el menú principal
    app.wm_state('normal')        # Asegura estado no maximizado
    centrar_ventana(app, ANCHO, ALTO)  # Vuelve a centrarlo si fuera necesario


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


def salir():
    """Cierra la aplicación por completo."""
    app.destroy()


# --- DISEÑO DEL MENÚ PRINCIPAL ---

main_card = ctk.CTkFrame(
    master=app,
    corner_radius=22,
    fg_color=colores.BG_PANEL,
    border_width=1,
    border_color=colores.BORDE,
)
main_card.pack(fill="both", expand=True, padx=28, pady=28)

# Franja de acento superior
franja_acento = ctk.CTkFrame(
    master=main_card, corner_radius=0, fg_color=colores.ACENTO, height=4
)
franja_acento.pack(fill="x", side="top")

# Encabezado
header_frame = ctk.CTkFrame(master=main_card, fg_color="transparent")
header_frame.pack(fill="x", pady=(34, 22), padx=30)

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
    font=fuentes.titulo(size=28),
    text_color=colores.TEXTO_PRIMARIO,
)
lbl_titulo.pack(pady=(4, 0))

lbl_subtitulo = ctk.CTkLabel(
    master=header_frame,
    text="Selecciona un módulo para continuar",
    font=fuentes.subtitulo(size=14),
    text_color=colores.TEXTO_SECUNDARIO,
)
lbl_subtitulo.pack(pady=(6, 0))

# Contenedor de Tarjetas de Opciones (Disposición en 2 columnas)
cards_container = ctk.CTkFrame(master=main_card, fg_color="transparent")
cards_container.pack(fill="both", expand=True, padx=30, pady=10)
cards_container.grid_columnconfigure((0, 1), weight=1, uniform="col")

# Tarjeta 1: Procesar Archivos
card_subir = ctk.CTkFrame(
    master=cards_container,
    corner_radius=16,
    fg_color=colores.BG_PANEL_ALT,
    border_width=1,
    border_color=colores.BORDE,
)
card_subir.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

icono_subir_bg = ctk.CTkFrame(
    master=card_subir, fg_color=colores.ACENTO_SUAVE, corner_radius=14,
    width=64, height=64,
)
icono_subir_bg.pack(pady=(26, 12))
icono_subir_bg.pack_propagate(False)

lbl_icon_subir = ctk.CTkLabel(
    master=icono_subir_bg, text="📊", font=ctk.CTkFont(size=28)
)
lbl_icon_subir.pack(expand=True)

lbl_title_subir = ctk.CTkLabel(
    master=card_subir,
    text="Limpiar y guardar archivos de asistencia",
    font=fuentes.seccion(size=17),
    text_color=colores.TEXTO_PRIMARIO,
)
lbl_title_subir.pack()

lbl_desc_subir = ctk.CTkLabel(
    master=card_subir,
    text="importa, limpia y guarda archivos de \nasistencia para la generacion de reportes.",
    font=fuentes.cuerpo(size=12),
    text_color=colores.TEXTO_SECUNDARIO,
    justify="center",
)
lbl_desc_subir.pack(pady=(6, 18))

btn_subir = ctk.CTkButton(
    master=card_subir,
    text="Abrir Módulo",
    font=fuentes.boton(size=13),
    height=40,
    corner_radius=10,
    fg_color=colores.ACENTO,
    hover_color=colores.ACENTO_HOVER,
    text_color=colores.TEXTO_SOBRE_ACENTO,
    command=abrir_subir_archivos,
)
btn_subir.pack(fill="x", padx=22, pady=(0, 22))

# Tarjeta 2: Gestión de Docentes
card_docentes = ctk.CTkFrame(
    master=cards_container,
    corner_radius=16,
    fg_color=colores.BG_PANEL_ALT,
    border_width=1,
    border_color=colores.BORDE,
)
card_docentes.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

icono_docentes_bg = ctk.CTkFrame(
    master=card_docentes, fg_color="#12352A", corner_radius=14,
    width=64, height=64,
)
icono_docentes_bg.pack(pady=(26, 12))
icono_docentes_bg.pack_propagate(False)

lbl_icon_docentes = ctk.CTkLabel(
    master=icono_docentes_bg, text="👨", font=ctk.CTkFont(size=28)
)
lbl_icon_docentes.pack(expand=True)

lbl_title_docentes = ctk.CTkLabel(
    master=card_docentes,
    text="Gestión de Docentes",
    font=fuentes.seccion(size=17),
    text_color=colores.TEXTO_PRIMARIO,
)
lbl_title_docentes.pack()

lbl_desc_docentes = ctk.CTkLabel(
    master=card_docentes,
    text="Administra el catálogo de\nprofesores, asignaturas y horarios.",
    font=fuentes.cuerpo(size=12),
    text_color=colores.TEXTO_SECUNDARIO,
    justify="center",
)
lbl_desc_docentes.pack(pady=(6, 18))

btn_docentes = ctk.CTkButton(
    master=card_docentes,
    text="Abrir Módulo",
    font=fuentes.boton(size=13),
    height=40,
    corner_radius=10,
    fg_color=colores.EXITO,
    hover_color=colores.EXITO_HOVER,
    text_color=colores.TEXTO_SOBRE_ACENTO,
    command=abrir_gestion_docentes,
)
btn_docentes.pack(fill="x", padx=22, pady=(0, 22))

#tarjeta 3: generacion de reportes
card_generador = ctk.CTkFrame(
    master=cards_container,
    corner_radius=16,
    fg_color=colores.BG_PANEL_ALT,
    border_width=1,
    border_color=colores.BORDE,
)
card_generador.grid(row=1, column=0, columnspan=10,padx=10, pady=10, sticky="nsew")   

icono_generador_bg = ctk.CTkFrame(
    master=card_generador, fg_color="#352A12", corner_radius=14,
    width=64, height=64,
)
icono_generador_bg.pack(pady=(26, 12))
icono_generador_bg.pack_propagate(False)

lbl_icon_generador = ctk.CTkLabel(
    master=icono_generador_bg, text="📋", font=ctk.CTkFont(size=28)
)
lbl_icon_generador.pack(expand=True)

lbl_title_generador = ctk.CTkLabel(
    master=card_generador,
    text="Generacion de reporte de asistencia",
    font=fuentes.seccion(size=17),
    text_color=colores.TEXTO_PRIMARIO,
)
lbl_title_generador.pack()

lbl_desc_generador = ctk.CTkLabel(
    master=card_generador,
    text="Genera reportes quincenales \nsobre la asistencia de los docentes",
    font=fuentes.cuerpo(size=12),
    text_color=colores.TEXTO_SECUNDARIO,
    justify="center",
)
lbl_desc_generador.pack(pady=(6,18))

btn_generador = ctk.CTkButton(
    master=card_generador,
    text="Abrir modulo",
    font=fuentes.boton(size=13),
    height=40,
    corner_radius=10,
    fg_color="#EEA942",
    hover_color="#AA7526",
    text_color=colores.TEXTO_SOBRE_ACENTO,
    command=abrir_gestion_docentes,
)
btn_generador.pack(fill="x", padx=22, pady=(0, 22))
# Separador
separador = ctk.CTkFrame(master=main_card, fg_color=colores.BORDE_SUAVE, height=1)
separador.pack(fill="x", padx=40, pady=(4, 0))

# Pie de página
footer_frame = ctk.CTkFrame(master=main_card, fg_color="transparent")
footer_frame.pack(fill="x", padx=40, pady=(16, 24))

lbl_footer_info = ctk.CTkLabel(
    master=footer_frame,
    text="Control de Acceso Docente",
    font=fuentes.pequena(size=11),
    text_color=colores.TEXTO_TENUE,
)
lbl_footer_info.pack(side="left")

btn_salir = ctk.CTkButton(
    master=footer_frame,
    text="Cerrar Aplicación",
    font=fuentes.boton(size=13),
    height=36,
    width=170,
    corner_radius=10,
    fg_color=colores.NEUTRO,
    hover_color=colores.PELIGRO_HOVER,
    text_color=colores.TEXTO_PRIMARIO,
    command=salir,
)
btn_salir.pack(side="right")

app.mainloop()