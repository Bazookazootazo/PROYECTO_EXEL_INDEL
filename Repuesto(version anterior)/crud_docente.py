import customtkinter as ctk
from tkinter import messagebox
import database as db
from utilerias.messagebox_variados import mostrar_exito, mostrar_advertencia, mostrar_error, mostrar_pregunta

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
        self.geometry("400x350")
        self.resizable(False, False)
        
        self.grab_set()
        self.focus_force()

        main_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="#2A2E39")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(
            main_frame, text=titulo_lbl, 
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#3B8ED0"
        ).pack(pady=(15, 10))

        self.ent_nombre = ctk.CTkEntry(main_frame, placeholder_text="Nombre completo...")
        self.ent_nombre.pack(fill="x", padx=20, pady=6)

        ctk.CTkLabel(main_frame, text="Área:", font=ctk.CTkFont(size=12), text_color="#A0AAB0", anchor="w").pack(fill="x", padx=20, pady=(4, 0))
        self.cmb_area = ctk.CTkOptionMenu(main_frame, values=self.AREAS_INSTITUCION)
        self.cmb_area.pack(fill="x", padx=20, pady=(0, 6))

        ctk.CTkLabel(main_frame, text="Tipo de Docente:", font=ctk.CTkFont(size=12), text_color="#A0AAB0", anchor="w").pack(fill="x", padx=20, pady=(4, 0))
        self.cmb_tipo = ctk.CTkOptionMenu(main_frame, values=["Tiempo Completo", "Asignatura"])
        self.cmb_tipo.pack(fill="x", padx=20, pady=(0, 10))

        btn_guardar = ctk.CTkButton(
            main_frame, text=texto_btn, fg_color="#27AE60", hover_color="#1E8449", command=self.guardar_profesor
        )
        btn_guardar.pack(fill="x", padx=20, pady=(10, 15))

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