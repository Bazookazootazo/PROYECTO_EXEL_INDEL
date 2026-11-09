import customtkinter as ctk
from gestion_docente.catalogos import recargar_areas
from utilerias import database as db
from utilerias.messagebox_variados import mostrar_advertencia, mostrar_error, mostrar_pregunta
from utilerias.paleta_colores import colores, fuentes


class VentanaAreas(ctk.CTkToplevel):
    """Sub-CRUD de áreas: agregar, renombrar y eliminar (solo si no tienen docentes)."""

    def __init__(self, parent, on_change_callback=None):
        super().__init__(parent)
        self.on_change_callback = on_change_callback

        self.title("Áreas")
        self.geometry("460x520")
        self.minsize(420, 400)
        self.configure(fg_color=colores.BG_VENTANA)
        self.grab_set()
        self.focus_force()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        panel = ctk.CTkFrame(self, corner_radius=16, fg_color=colores.BG_PANEL, border_width=1, border_color=colores.BORDE)
        panel.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(panel, text="Áreas", font=fuentes.seccion(size=18), text_color=colores.TEXTO_PRIMARIO).grid(row=0, column=0, pady=(18, 10))

        alta = ctk.CTkFrame(panel, fg_color="transparent")
        alta.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        alta.grid_columnconfigure(0, weight=1)
        self.ent_nueva = ctk.CTkEntry(
            alta, placeholder_text="Nombre del área nueva", height=36, corner_radius=9,
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA, border_color=colores.BORDE,
        )
        self.ent_nueva.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.ent_nueva.bind("<Return>", lambda e: self.agregar())
        ctk.CTkButton(
            alta, text="Agregar", width=90, height=36, corner_radius=10, font=fuentes.boton(size=13),
            fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER, command=self.agregar,
        ).grid(row=0, column=1)

        self.lista = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.lista.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 14))
        self.lista.grid_columnconfigure(0, weight=1)

        self.refrescar()

    def refrescar(self):
        for w in self.lista.winfo_children():
            w.destroy()
        try:
            areas = db.obtener_areas()
        except Exception as e:
            mostrar_error("Error", f"No se pudieron cargar las áreas:\n{e}", master=self)
            return

        if not areas:
            ctk.CTkLabel(self.lista, text="Aún no hay áreas. Agrega la primera arriba.",
                         font=fuentes.pequena(size=12), text_color=colores.TEXTO_SECUNDARIO).grid(row=0, column=0, pady=20)
        for i, area in enumerate(areas):
            fila = ctk.CTkFrame(self.lista, fg_color=colores.COLOR_TARJETA, corner_radius=8,
                                border_width=1, border_color=colores.COLOR_TARJETA_BORDE)
            fila.grid(row=i, column=0, sticky="ew", pady=2, padx=2)
            fila.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(fila, text=area["nombre"], anchor="w", font=fuentes.cuerpo(size=13),
                         text_color=colores.TEXTO_PRIMARIO).grid(row=0, column=0, sticky="w", padx=(12, 4), pady=(8, 0))
            ctk.CTkLabel(fila, text=f"{area['docentes']} docente(s)", anchor="w", font=fuentes.pequena(size=10),
                         text_color=colores.TEXTO_TENUE).grid(row=1, column=0, sticky="w", padx=(12, 4), pady=(0, 8))
            ctk.CTkButton(
                fila, text="Renombrar", width=90, height=28, corner_radius=8, font=fuentes.pequena(size=11),
                fg_color=colores.COLOR_BTN_EDITAR, hover_color=colores.COLOR_BTN_EDITAR_HOVER,
                command=lambda a=area: self.renombrar(a),
            ).grid(row=0, column=1, rowspan=2, padx=4)
            ctk.CTkButton(
                fila, text="Eliminar", width=80, height=28, corner_radius=8, font=fuentes.pequena(size=11),
                fg_color=colores.COLOR_BTN_ELIMINAR, hover_color=colores.COLOR_BTN_ELIMINAR_HOVER,
                command=lambda a=area: self.eliminar(a),
            ).grid(row=0, column=2, rowspan=2, padx=(0, 8))

    def _ejecutar(self, accion, *args):
        """Corre la operación; si sale bien sincroniza catálogo, lista y pantalla principal."""
        try:
            accion(*args)
        except ValueError as e:
            mostrar_advertencia("Atención", str(e), master=self)
            return False
        except Exception as e:
            mostrar_error("Error", f"Ocurrió un problema:\n{e}", master=self)
            return False
        recargar_areas()
        self.refrescar()
        if self.on_change_callback:
            self.on_change_callback()
        return True

    def _nombre_valido(self, nombre):
        if not nombre:
            mostrar_advertencia("Atención", "Escribe el nombre del área.", master=self)
        elif len(nombre) > 100:
            mostrar_advertencia("Atención", "El nombre no puede pasar de 100 caracteres.", master=self)
        else:
            return True
        return False

    def agregar(self):
        nombre = " ".join(self.ent_nueva.get().split())
        if self._nombre_valido(nombre) and self._ejecutar(db.agregar_area, nombre):
            self.ent_nueva.delete(0, "end")

    def renombrar(self, area):
        nuevo = ctk.CTkInputDialog(text=f"Nuevo nombre para «{area['nombre']}»:", title="Renombrar área").get_input()
        nuevo = " ".join((nuevo or "").split())
        if nuevo and nuevo != area["nombre"] and self._nombre_valido(nuevo):
            self._ejecutar(db.renombrar_area, area["id_area"], nuevo)

    def eliminar(self, area):
        if mostrar_pregunta("Eliminar área", f"¿Eliminar el área «{area['nombre']}»?", master=self):
            self._ejecutar(db.eliminar_area, area["id_area"])