"""
Sistema de diseño centralizado de la aplicación.

Este módulo concentra todos los colores y tipografías usados por la interfaz
para que todas las ventanas compartan una misma identidad visual coherente.
No contiene lógica de negocio: sólo constantes de estilo.
"""

import customtkinter as ctk


class colores:
    # --- Fondos (de más oscuro/base a más claro/elevado) ---
    BG_VENTANA = "#0E1015"        # Fondo raíz de las ventanas
    BG_PANEL = "#15171F"          # Paneles principales (tarjeta contenedora)
    BG_PANEL_ALT = "#191C25"      # Sub-paneles dentro de un panel
    BG_SUPERFICIE = "#1B1E28"     # Cajas de texto, listas, inputs
    BG_ENTRADA = "#12141B"        # Fondo de campos de entrada / textbox

    # --- Bordes ---
    BORDE = "#262A38"
    BORDE_SUAVE = "#20232E"
    BORDE_CLARO = "#333A4D"

    # --- Acentos de marca ---
    ACENTO = "#4F8FE8"
    ACENTO_HOVER = "#3A6FC2"
    ACENTO_SUAVE = "#1B2C46"

    # --- Estados semánticos ---
    EXITO = "#2FB380"
    EXITO_HOVER = "#22855F"
    ADVERTENCIA = "#E8A23C"
    ADVERTENCIA_HOVER = "#C4841F"
    PELIGRO = "#E1544D"
    PELIGRO_HOVER = "#B33E38"
    NEUTRO = "#2E3241"
    NEUTRO_HOVER = "#3C4256"

    # --- Texto ---
    TEXTO_PRIMARIO = "#F2F4F8"
    TEXTO_SECUNDARIO = "#9AA3B7"
    TEXTO_TENUE = "#6B7387"
    TEXTO_SOBRE_ACENTO = "#FFFFFF"

    # --- Tarjetas de lista (usadas en Gestión Docente) ---
    COLOR_TARJETA = "#191C25"
    COLOR_TARJETA_BORDE = "#262A38"
    COLOR_SELECCIONADO = "#1B2C46"
    COLOR_SELECCIONADO_BORDE = "#4F8FE8"
    COLOR_TEXTO_AREA = "#9AA3B7"
    COLOR_TEXTO_AREA_SEL = "#D7E2F5"

    # --- Botones de acción sobre tarjetas ---
    COLOR_BTN_EDITAR = "#E8A23C"
    COLOR_BTN_EDITAR_HOVER = "#C4841F"
    COLOR_BTN_ELIMINAR = "#E1544D"
    COLOR_BTN_ELIMINAR_HOVER = "#B33E38"

    # --- Semáforo de estado (barra inferior / indicadores) ---
    ESTADO_INACTIVO = "#6B7387"
    ESTADO_PROCESANDO = "#E8A23C"
    ESTADO_EXITO = "#2FB380"
    ESTADO_ERROR = "#E1544D"
    ESTADO_INFO = "#4F8FE8"


class fuentes:
    """Tipografía consistente para toda la aplicación."""
    FAMILIA = "Segoe UI"

    @staticmethod
    def titulo(size=26):
        return ctk.CTkFont(family=fuentes.FAMILIA, size=size, weight="bold")

    @staticmethod
    def subtitulo(size=14):
        return ctk.CTkFont(family=fuentes.FAMILIA, size=size)

    @staticmethod
    def seccion(size=16):
        return ctk.CTkFont(family=fuentes.FAMILIA, size=size, weight="bold")

    @staticmethod
    def cuerpo(size=13):
        return ctk.CTkFont(family=fuentes.FAMILIA, size=size)

    @staticmethod
    def boton(size=13):
        return ctk.CTkFont(family=fuentes.FAMILIA, size=size, weight="bold")

    @staticmethod
    def pequena(size=11):
        return ctk.CTkFont(family=fuentes.FAMILIA, size=size)

    @staticmethod
    def monoespaciada(size=13):
        return ctk.CTkFont(family="Consolas", size=size)
