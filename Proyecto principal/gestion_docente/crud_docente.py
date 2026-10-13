import customtkinter as ctk
from gestion_docente.catalogos import AREAS, TIPOS
from utilerias import database as db
from utilerias.messagebox_variados import mostrar_advertencia, mostrar_error, mostrar_exito
from utilerias.paleta_colores import colores, fuentes

class VentanaCrudProfesor(ctk.CTkToplevel):
    AREAS_INSTITUCION = list(AREAS)         # única fuente: catalogos.py

    def __init__(self, parent, profesor_a_editar=None, on_success_callback=None):
        super().__init__(parent)
        
        self.profesor_a_editar = profesor_a_editar
        self.on_success_callback = on_success_callback
        
        modo_edicion = self.profesor_a_editar is not None
        titulo_ventana = "Editar Docente" if modo_edicion else "Registrar Docente"
        titulo_lbl = "Modificar Datos" if modo_edicion else "Alta de Docente"
        texto_btn = "Guardar cambios" if modo_edicion else "Registrar docente"

        self.title(titulo_ventana)
        self.geometry("450x460")
        self.minsize(420, 440)
        self.resizable(True, True)
        self.configure(fg_color=colores.BG_VENTANA)
        
        self.grab_set()
        self.focus_force()

        # Configuración de grilla principal responsiva
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(self, corner_radius=16, fg_color=colores.BG_PANEL, border_width=1, border_color=colores.BORDE)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # Encabezado visual
        encabezado = ctk.CTkFrame(main_frame, fg_color="transparent")
        encabezado.pack(fill="x", padx=20, pady=(20, 10))
        
        icono = "✏️" if modo_edicion else "🧑‍🏫"
        ctk.CTkLabel(
            encabezado, text=f"{icono}  {titulo_lbl}",
            font=fuentes.seccion(size=18), text_color=colores.TEXTO_PRIMARIO,
            anchor="w"
        ).pack(fill="x")
        ctk.CTkLabel(
            encabezado, text="Completa o modifica la información del docente",
            font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO,
            anchor="w"
        ).pack(fill="x", pady=(2, 0))

        # Contenedor del Formulario
        form_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Campo: Nombre completo
        ctk.CTkLabel(form_frame, text="Nombre completo", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO, anchor="w").pack(fill="x", pady=(0, 3))
        self.ent_nombre = ctk.CTkEntry(
            form_frame, placeholder_text="Ej. Juan Pérez López", height=36, corner_radius=9,
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA, border_color=colores.BORDE,
        )
        self.ent_nombre.pack(fill="x", pady=(0, 12))

        # Campo: Área
        ctk.CTkLabel(form_frame, text="Área de adscripción", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO, anchor="w").pack(fill="x", pady=(0, 3))
        self.cmb_area = ctk.CTkOptionMenu(
            form_frame, values=self.AREAS_INSTITUCION, height=36, corner_radius=9,
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA,
            button_color=colores.ACENTO, button_hover_color=colores.ACENTO_HOVER,
        )
        self.cmb_area.pack(fill="x", pady=(0, 12))

        # Campo: Tipo de docente
        ctk.CTkLabel(form_frame, text="Tipo de docente", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO, anchor="w").pack(fill="x", pady=(0, 3))
        self.cmb_tipo = ctk.CTkOptionMenu(
            form_frame, values=list(TIPOS), height=36, corner_radius=9,
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA,
            button_color=colores.ACENTO, button_hover_color=colores.ACENTO_HOVER,
        )
        self.cmb_tipo.pack(fill="x", pady=(0, 15))

        # Pie de página / Botones de acción alineados (Patrón consistente)
        pie = ctk.CTkFrame(main_frame, fg_color="transparent")
        pie.pack(fill="x", padx=20, pady=(0, 20))
        pie.grid_columnconfigure(0, weight=1)
        pie.grid_columnconfigure(1, weight=1)

        btn_cancelar = ctk.CTkButton(
            pie, text="Cancelar", height=38, corner_radius=10,
            font=fuentes.boton(size=13), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
            command=self.destroy,
        )
        btn_cancelar.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        color_btn_guardar = colores.ACENTO if modo_edicion else colores.EXITO
        color_hover_guardar = colores.ACENTO_HOVER if modo_edicion else colores.EXITO_HOVER

        btn_guardar = ctk.CTkButton(
            pie, text=texto_btn, height=38, corner_radius=10,
            font=fuentes.boton(size=13),
            fg_color=color_btn_guardar, hover_color=color_hover_guardar,
            command=self.guardar_profesor,
        )
        btn_guardar.grid(row=0, column=1, sticky="ew", padx=(6, 0))

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