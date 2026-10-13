import customtkinter as ctk
from tkinter import messagebox
import database as db
from utilerias.messagebox_variados import mostrar_exito, mostrar_advertencia, mostrar_error, mostrar_pregunta
from utilerias.paleta_colores import colores, fuentes

class VentanaCrudProfesor(ctk.CTkToplevel):
    AREAS_INSTITUCION = [
        "Tecnologías de la Información",
        "Mecatrónica",
        "Administración",
        "Recursos Humanos",
        "Ciencias Básicas",
        "Departamento de Prueba"
    ]

    def __init__(self, parent, profesor_a_editar=None, on_success_callback=None):
        super().__init__(parent)
        
        self.profesor_a_editar = profesor_a_editar
        self.on_success_callback = on_success_callback
        
        modo_edicion = self.profesor_a_editar is not None
        titulo_ventana = "Editar Docente" if modo_edicion else "Registrar Docente"
        titulo_lbl = "Modificar Datos" if modo_edicion else "Alta Docente"
        texto_btn = "Actualizar Registro" if modo_edicion else "Guardar Registro"

        self.title(titulo_ventana)
        self.geometry("420x420")
        self.resizable(False, False)
        self.configure(fg_color=colores.BG_VENTANA)
        
        self.grab_set()
        self.focus_force()

        main_frame = ctk.CTkFrame(self, corner_radius=18, fg_color=colores.BG_PANEL, border_width=1, border_color=colores.BORDE)
        main_frame.pack(fill="both", expand=True, padx=18, pady=18)

        icono = "✏️" if modo_edicion else "🧑‍🏫"
        ctk.CTkLabel(
            main_frame, text=f"{icono}  {titulo_lbl}",
            font=fuentes.seccion(size=19), text_color=colores.TEXTO_PRIMARIO,
        ).pack(pady=(22, 4))
        ctk.CTkLabel(
            main_frame, text="Completa los datos del docente",
            font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO,
        ).pack(pady=(0, 18))

        ctk.CTkLabel(main_frame, text="Nombre completo", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO, anchor="w").pack(fill="x", padx=24, pady=(0, 3))
        self.ent_nombre = ctk.CTkEntry(
            main_frame, placeholder_text="Ej. Juan Pérez López", height=36, corner_radius=9,
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA, border_color=colores.BORDE,
        )
        self.ent_nombre.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(main_frame, text="Área", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO, anchor="w").pack(fill="x", padx=24, pady=(0, 3))
        self.cmb_area = ctk.CTkOptionMenu(
            main_frame, values=self.AREAS_INSTITUCION, height=36, corner_radius=9,
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA,
            button_color=colores.ACENTO, button_hover_color=colores.ACENTO_HOVER,
        )
        self.cmb_area.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(main_frame, text="Tipo de docente", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO, anchor="w").pack(fill="x", padx=24, pady=(0, 3))
        self.cmb_tipo = ctk.CTkOptionMenu(
            main_frame, values=["Tiempo Completo", "Asignatura"], height=36, corner_radius=9,
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA,
            button_color=colores.ACENTO, button_hover_color=colores.ACENTO_HOVER,
        )
        self.cmb_tipo.pack(fill="x", padx=24, pady=(0, 18))

        btn_guardar = ctk.CTkButton(
            main_frame, text=texto_btn, height=40, corner_radius=10,
            font=fuentes.boton(size=13),
            fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER,
            command=self.guardar_profesor,
        )
        btn_guardar.pack(fill="x", padx=24, pady=(0, 22))

        if modo_edicion:
            self.ent_nombre.insert(0, self.profesor_a_editar['nombre'])
            self.cmb_area.set(self.profesor_a_editar['area'])
            self.cmb_tipo.set(self.profesor_a_editar['tipo'])

    def guardar_profesor(self):
        nombre = self.ent_nombre.get().strip()
        area = self.cmb_area.get()
        tipo = self.cmb_tipo.get()

        if not nombre:
            mostrar_advertencia("Atención", "Ingresa el nombre completo.", master=self)
            return

        try:
            if self.profesor_a_editar:
                db.actualizar_profesor(self.profesor_a_editar['id_profesor'], nombre, area, tipo)
                msg = "Actualizado correctamente."
            else:
                db.agregar_profesor(nombre, area, tipo)
                msg = "Registrado correctamente."

            mostrar_exito("Éxito", msg, master=self)
            
            if self.on_success_callback:
                self.on_success_callback()
                
            self.after(100, self.destroy)
            
        except Exception as e:
            mostrar_error("Error", f"Ocurrió un problema:\n{e}", master=self)