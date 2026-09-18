import customtkinter as ctk

from gestion_docentes import VentanaGestionDocentes
from subir_archivos import VentanaSubirArchivos

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Menú de Inicio - Control de Acceso")

# Configuración de ventana fija y centrada (sin pantalla completa)
ANCHO, ALTO = 800, 550
app.geometry(f"{ANCHO}x{ALTO}")
app.resizable(False, False)

# Referencias para las ventanas secundarias
ventana_docentes = None
ventana_subir = None


def volver_al_menu(ventana_secundaria):
    """Destruye la ventana secundaria y vuelve a mostrar el menú principal."""
    ventana_secundaria.destroy()
    app.deiconify()


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
    corner_radius=20,
    fg_color="#14161D",
    border_width=1,
    border_color="#2B2D38",
)
main_card.pack(fill="both", expand=True, padx=25, pady=25)

# Encabezado
header_frame = ctk.CTkFrame(master=main_card, fg_color="transparent")
header_frame.pack(fill="x", pady=(30, 20), padx=30)

lbl_titulo = ctk.CTkLabel(
    master=header_frame,
    text="Control de Acceso Docente",
    font=ctk.CTkFont(size=26, weight="bold"),
    text_color="#FFFFFF",
)
lbl_titulo.pack()

lbl_subtitulo = ctk.CTkLabel(
    master=header_frame,
    text="Seleccione un módulo para continuar",
    font=ctk.CTkFont(size=14),
    text_color="#8F96A3",
)
lbl_subtitulo.pack(pady=(5, 0))

# Contenedor de Tarjetas de Opciones (Disposición en 2 columnas)
cards_container = ctk.CTkFrame(master=main_card, fg_color="transparent")
cards_container.pack(fill="both", expand=True, padx=30, pady=10)
cards_container.grid_columnconfigure((0, 1), weight=1, uniform="col")

# Tarjeta 1: Procesar Archivos
card_subir = ctk.CTkFrame(
    master=cards_container,
    corner_radius=15,
    fg_color="#1E222D",
    border_width=1,
    border_color="#2A2F3D",
)
card_subir.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

lbl_icon_subir = ctk.CTkLabel(
    master=card_subir, text="📊", font=ctk.CTkFont(size=36)
)
lbl_icon_subir.pack(pady=(20, 5))

lbl_title_subir = ctk.CTkLabel(
    master=card_subir,
    text="Procesar Registros",
    font=ctk.CTkFont(size=16, weight="bold"),
)
lbl_title_subir.pack()

lbl_desc_subir = ctk.CTkLabel(
    master=card_subir,
    text="Importa, limpia y depura las\nchecadas de asistencia (CSV/Excel).",
    font=ctk.CTkFont(size=12),
    text_color="#9A9FB0",
)
lbl_desc_subir.pack(pady=(5, 15))

btn_subir = ctk.CTkButton(
    master=card_subir,
    text="Abrir Módulo",
    font=ctk.CTkFont(size=13, weight="bold"),
    height=38,
    fg_color="#1F6AA5",
    hover_color="#144870",
    command=abrir_subir_archivos,
)
btn_subir.pack(fill="x", padx=20, pady=(0, 20))

# Tarjeta 2: Gestión de Docentes
card_docentes = ctk.CTkFrame(
    master=cards_container,
    corner_radius=15,
    fg_color="#1E222D",
    border_width=1,
    border_color="#2A2F3D",
)
card_docentes.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

lbl_icon_docentes = ctk.CTkLabel(
    master=card_docentes, text="👨‍🏫", font=ctk.CTkFont(size=36)
)
lbl_icon_docentes.pack(pady=(20, 5))

lbl_title_docentes = ctk.CTkLabel(
    master=card_docentes,
    text="Gestión de Docentes",
    font=ctk.CTkFont(size=16, weight="bold"),
)
lbl_title_docentes.pack()

lbl_desc_docentes = ctk.CTkLabel(
    master=card_docentes,
    text="Administra el catálogo de\nprofesores, asignaturas y horarios.",
    font=ctk.CTkFont(size=12),
    text_color="#9A9FB0",
)
lbl_desc_docentes.pack(pady=(5, 15))

btn_docentes = ctk.CTkButton(
    master=card_docentes,
    text="Abrir Módulo",
    font=ctk.CTkFont(size=13, weight="bold"),
    height=38,
    fg_color="#27AE60",
    hover_color="#1E8449",
    command=abrir_gestion_docentes,
)
btn_docentes.pack(fill="x", padx=20, pady=(0, 20))

# Pie de página: Botón Salir
footer_frame = ctk.CTkFrame(master=main_card, fg_color="transparent")
footer_frame.pack(fill="x", padx=40, pady=(10, 20))

btn_salir = ctk.CTkButton(
    master=footer_frame,
    text="Cerrar Aplicación",
    font=ctk.CTkFont(size=13, weight="bold"),
    height=36,
    width=160,
    fg_color="#3A3D4A",
    hover_color="#C0392B",
    text_color="#E0E0E0",
    command=salir,
)
btn_salir.pack(side="right")

app.mainloop()