import math
import customtkinter as ctk
import database as db
from crud_docente import VentanaCrudProfesor
from utilerias.messagebox_variados import mostrar_exito, mostrar_advertencia, mostrar_error, mostrar_pregunta
from utilerias.paleta_colores import colores, fuentes
from tkinter import filedialog

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VentanaGestionDocentes(ctk.CTkToplevel):
    DIAS_MAPPING = {"Lunes": 1, "Martes": 2, "Miércoles": 3, "Jueves": 4, "Viernes": 5}
    ELEMENTOS_POR_PAGINA = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.profesores_cache = []
        self.profesores_filtrados = []
        self.profesor_seleccionado = None
        self.pagina_actual = 1
        self.pool_tarjetas = []
        self._configurar_ventana()
        self._construir_panel_izquierdo()
        self._construir_panel_derecho()
        self.cargar_lista_profesores()

    def _configurar_ventana(self):
        self.title("Gestión Docente y Horarios")
        self.geometry("1100x700")
        self.configure(fg_color=colores.BG_VENTANA)
        self.after(10, lambda: self.wm_state('zoomed'))
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

    def _construir_panel_izquierdo(self):
        panel = ctk.CTkFrame(self, corner_radius=16, fg_color=colores.BG_PANEL, border_width=1, border_color=colores.BORDE)
        panel.grid(row=0, column=0, sticky="nsew", padx=(15, 7), pady=15)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(3, weight=1)

        encabezado = ctk.CTkFrame(panel, fg_color="transparent")
        encabezado.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        ctk.CTkLabel(encabezado, text="👥  Gestión Docente", font=fuentes.seccion(size=17), text_color=colores.TEXTO_PRIMARIO).pack(anchor="w")
        ctk.CTkLabel(encabezado, text="Catálogo de profesores y horarios", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO).pack(anchor="w", pady=(2, 0))

        # Contenedor de botones superior
        btn_frame_acciones = ctk.CTkFrame(panel, fg_color="transparent")
        btn_frame_acciones.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        btn_frame_acciones.grid_columnconfigure(0, weight=1)
        btn_frame_acciones.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_frame_acciones, text="+ Nuevo Docente", command=self.abrir_ventana_registro,
            font=fuentes.boton(size=13), height=38, corner_radius=10,
            fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))

        # Contenedor para botones de acciones
        btn_frame_acciones = ctk.CTkFrame(panel, fg_color="transparent")
        btn_frame_acciones.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        btn_frame_acciones.grid_columnconfigure(0, weight=1)
        btn_frame_acciones.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_frame_acciones, text="+  Nuevo Docente", command=self.abrir_ventana_registro,
            font=fuentes.boton(size=13), height=38, corner_radius=10,
            fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))

        # Botón único e inteligente
        ctk.CTkButton(
            btn_frame_acciones, text="📁  Importar Datos", command=self.cargar_archivo_masivo,
            font=fuentes.boton(size=13), height=38, corner_radius=10,
            fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER,
        ).grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.container_profesores = ctk.CTkFrame(panel, fg_color="transparent")
        self.container_profesores.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 5))
        self.container_profesores.grid_columnconfigure(0, weight=1)
        
        for r in range(self.ELEMENTOS_POR_PAGINA):
            self.container_profesores.grid_rowconfigure(r, weight=1, uniform="grupo_botones")
            
        self._crear_pool_tarjetas()
        
        nav_frame = ctk.CTkFrame(panel, fg_color="transparent")
        nav_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=(5, 15))
        
        self.btn_prev = ctk.CTkButton(
            nav_frame, text="←  Anterior", width=90, height=32, corner_radius=8,
            font=fuentes.cuerpo(size=12), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
            command=self.pagina_anterior,
        )
        self.btn_prev.pack(side="left")
        self.lbl_paginacion = ctk.CTkLabel(nav_frame, text="Pág 1 / 1", font=fuentes.boton(size=12), text_color=colores.TEXTO_SECUNDARIO)
        self.lbl_paginacion.pack(side="left", expand=True)
        self.btn_next = ctk.CTkButton(
            nav_frame, text="Siguiente  →", width=90, height=32, corner_radius=8,
            font=fuentes.cuerpo(size=12), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
            command=self.pagina_siguiente,
        )
        self.btn_next.pack(side="right")

    def _crear_pool_tarjetas(self):
        for i in range(self.ELEMENTOS_POR_PAGINA):
            card = ctk.CTkFrame(self.container_profesores, fg_color=colores.COLOR_TARJETA, corner_radius=10, border_width=1, border_color=colores.COLOR_TARJETA_BORDE, cursor="hand2")
            card.grid(row=i, column=0, sticky="ew", pady=2, padx=2)
            card.grid_columnconfigure(0, weight=1)
            card.grid_columnconfigure(1, weight=0)
            
            lbl_nombre = ctk.CTkLabel(card, text="", anchor="w", font=fuentes.boton(size=12), text_color=colores.TEXTO_PRIMARIO, height=16)
            lbl_nombre.grid(row=0, column=0, sticky="ew", padx=12, pady=(6, 1))
            
            lbl_area = ctk.CTkLabel(card, text="", anchor="w", font=fuentes.pequena(size=10), text_color=colores.COLOR_TEXTO_AREA, height=14)
            lbl_area.grid(row=1, column=0, sticky="ew", padx=12, pady=(1, 6))
            
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.grid(row=0, column=1, rowspan=2, sticky="e", padx=(0, 10))
            btn_edit = ctk.CTkButton(btn_frame, text="Editar", width=32, height=26, corner_radius=7, font=fuentes.pequena(size=11), fg_color=colores.COLOR_BTN_EDITAR, hover_color=colores.COLOR_BTN_EDITAR_HOVER)
            btn_edit.pack(side="left", padx=2)
            btn_del = ctk.CTkButton(btn_frame, text="Eliminar", width=32, height=26, corner_radius=7, font=fuentes.pequena(size=11), fg_color=colores.COLOR_BTN_ELIMINAR, hover_color=colores.COLOR_BTN_ELIMINAR_HOVER)
            btn_del.pack(side="left", padx=2)
            
            self.pool_tarjetas.append({"frame": card, "lbl_nombre": lbl_nombre, "lbl_area": lbl_area, "btn_edit": btn_edit, "btn_del": btn_del, "btn_frame": btn_frame})

    def _construir_panel_derecho(self):
        panel = ctk.CTkFrame(self, corner_radius=16, fg_color=colores.BG_PANEL, border_width=1, border_color=colores.BORDE)
        panel.grid(row=0, column=1, sticky="nsew", padx=(7, 15), pady=15)

        encabezado = ctk.CTkFrame(panel, fg_color="transparent")
        encabezado.pack(fill="x", padx=18, pady=(18, 10))
        
        frame_titulo = ctk.CTkFrame(encabezado, fg_color="transparent")
        frame_titulo.pack(fill="x")

        self.lbl_prof_seleccionado = ctk.CTkLabel(frame_titulo, text="🗓  Horario Semanal", font=fuentes.seccion(size=17), text_color=colores.TEXTO_PRIMARIO)
        self.lbl_prof_seleccionado.pack(side="left", anchor="w")

        # Botón para regresar al menú principal
        btn_volver_menu = ctk.CTkButton(
            frame_titulo, text="Volver al Menu principal", width=120, height=32, corner_radius=8,
            font=fuentes.boton(size=12), fg_color=colores.NEUTRO,
            hover_color=colores.NEUTRO_HOVER, command=self.regresar_al_menu
        )
        btn_volver_menu.pack(side="right", anchor="e")

        ctk.CTkLabel(encabezado, text="Selecciona un docente de la lista para ver o editar su horario", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO).pack(anchor="w", pady=(2, 0))

        horario_form = ctk.CTkFrame(panel, corner_radius=12, fg_color=colores.BG_PANEL_ALT, border_width=1, border_color=colores.BORDE_SUAVE)
        horario_form.pack(fill="x", padx=15, pady=(4, 12), ipady=10)

        self.cmb_dia = ctk.CTkOptionMenu(
            horario_form, values=list(self.DIAS_MAPPING.keys()), width=120, height=34,
            font=fuentes.cuerpo(size=12), fg_color=colores.BG_ENTRADA,
            button_color=colores.ACENTO, button_hover_color=colores.ACENTO_HOVER,
        )
        self.cmb_dia.pack(side="left", padx=(12, 6), pady=4)
        
        self.ent_entrada = ctk.CTkEntry(
            horario_form, width=90, height=34, placeholder_text="07:00",
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA, border_color=colores.BORDE,
        )
        self.ent_entrada.pack(side="left", padx=5)
        self.aplicar_formato_hora(self.ent_entrada)
        
        self.ent_salida = ctk.CTkEntry(
            horario_form, width=90, height=34, placeholder_text="12:00",
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA, border_color=colores.BORDE,
        )
        self.ent_salida.pack(side="left", padx=5)
        self.aplicar_formato_hora(self.ent_salida)
        
        ctk.CTkButton(
            horario_form, text="+  Agregar Turno", command=self.guardar_horario,
            height=34, corner_radius=9, font=fuentes.boton(size=12),
            fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER,
        ).pack(side="left", padx=(5, 12), fill="x", expand=True)
        
        self.scroll_horarios = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.scroll_horarios.pack(fill="both", expand=True, padx=10, pady=(0, 15))

    def regresar_al_menu(self):
        if self.parent:
            self.parent.wm_state('normal')  
            self.parent.deiconify()          
        self.destroy()                       

    def cargar_lista_profesores(self):
        try:
            self.profesores_cache = db.obtener_profesores()
            self.filtrar_profesores()
        except Exception as e:
            mostrar_error("Error de Conexión", f"No se pudo conectar a la base de datos:\n{e}", master=self)

    def filtrar_profesores(self, *args):
        query = self.var_busqueda.get().strip().lower()
        self.profesores_filtrados = [p for p in self.profesores_cache if query in p['nombre'].lower() or query in p['area'].lower()] if query else self.profesores_cache.copy()
        self.pagina_actual = 1
        self.renderizar_pagina()

    def abrir_ventana_registro(self):
        VentanaCrudProfesor(self, on_success_callback=self.cargar_lista_profesores)

    def abrir_ventana_edicion(self, profesor):
        VentanaCrudProfesor(self, profesor_a_editar=profesor, on_success_callback=self.cargar_lista_profesores)

    def eliminar_docente(self, profesor):
        respuesta = mostrar_pregunta("Confirmar Eliminación", f"¿Estás seguro de eliminar a {profesor['nombre']}?\nSe borrarán también todos sus horarios asignados.", master=self)
        if not respuesta:
            return
        try:
            db.eliminar_profesor(profesor['id_profesor'])
            if self.profesor_seleccionado and self.profesor_seleccionado['id_profesor'] == profesor['id_profesor']:
                self.profesor_seleccionado = None
                self.lbl_prof_seleccionado.configure(text="Horario Semanal")
                for child in self.scroll_horarios.winfo_children():
                    child.destroy()
            self.cargar_lista_profesores()
            mostrar_exito("Éxito", "Eliminado correctamente.", master=self)
        except Exception as e:
            mostrar_error("Error", f"No se pudo eliminar:\n{e}", master=self)

    def seleccionar_profesor(self, profesor):
        self.profesor_seleccionado = profesor
        self.lbl_prof_seleccionado.configure(text=f"🗓  Horario: {profesor['nombre'].title()}")
        inicio = (self.pagina_actual - 1) * self.ELEMENTOS_POR_PAGINA
        pagina_items = self.profesores_filtrados[inicio:inicio + self.ELEMENTOS_POR_PAGINA]
        for i, prof in enumerate(pagina_items):
            if i < len(self.pool_tarjetas):
                es_sel = prof['id_profesor'] == profesor['id_profesor']
                item = self.pool_tarjetas[i]
                item["frame"].configure(fg_color=colores.COLOR_SELECCIONADO if es_sel else colores.COLOR_TARJETA, border_color=colores.COLOR_SELECCIONADO_BORDE if es_sel else colores.COLOR_TARJETA_BORDE)
                item["lbl_area"].configure(text_color=colores.COLOR_TEXTO_AREA_SEL if es_sel else colores.COLOR_TEXTO_AREA)
        self.cargar_horarios_profesor()

    def total_paginas(self):
        return math.ceil(len(self.profesores_filtrados) / self.ELEMENTOS_POR_PAGINA) or 1

    def renderizar_pagina(self):
        inicio = (self.pagina_actual - 1) * self.ELEMENTOS_POR_PAGINA
        pagina_items = self.profesores_filtrados[inicio:inicio + self.ELEMENTOS_POR_PAGINA]
        
        for i in range(self.ELEMENTOS_POR_PAGINA):
            item = self.pool_tarjetas[i]
            card = item["frame"]
            lbl_nombre = item["lbl_nombre"]
            lbl_area = item["lbl_area"]
            
            if i < len(pagina_items):
                prof = pagina_items[i]
                seleccionado = self.profesor_seleccionado and self.profesor_seleccionado['id_profesor'] == prof['id_profesor']
                
                lbl_nombre.configure(text=f"{prof['nombre'].title()}")
                lbl_area.configure(text=f"{prof['area'].title()}")
                
                card.configure(
                    fg_color=colores.COLOR_SELECCIONADO if seleccionado else colores.COLOR_TARJETA, 
                    border_color=colores.COLOR_SELECCIONADO_BORDE if seleccionado else colores.COLOR_TARJETA_BORDE,
                    border_width=2 if seleccionado else 1,
                    cursor="hand2"
                )
                lbl_area.configure(text_color=colores.COLOR_TEXTO_AREA_SEL if seleccionado else colores.COLOR_TEXTO_AREA)
                
                item["btn_edit"].configure(command=lambda p=prof: self.abrir_ventana_edicion(p))
                item["btn_del"].configure(command=lambda p=prof: self.eliminar_docente(p))
                
                cmd = lambda e, p=prof: self.seleccionar_profesor(p)
                card.bind("<Button-1>", cmd)
                lbl_nombre.bind("<Button-1>", cmd)
                lbl_area.bind("<Button-1>", cmd)
                
                card.grid()
                item["btn_frame"].grid()
            else:
                card.configure(fg_color="transparent", border_width=0, cursor="arrow")
                lbl_nombre.configure(text="")
                lbl_area.configure(text="")
                item["btn_frame"].grid_remove()
                card.unbind("<Button-1>")
                lbl_nombre.unbind("<Button-1>")
                lbl_area.unbind("<Button-1>")
                
        total_pags = self.total_paginas()
        self.lbl_paginacion.configure(text=f"Pág {self.pagina_actual} / {total_pags}")
        
        self.btn_prev.configure(state="normal" if self.pagina_actual > 1 else "disabled")
        self.btn_next.configure(state="normal" if self.pagina_actual < total_pags else "disabled")
        
        self.container_profesores.update_idletasks()

    def pagina_anterior(self):
        if self.pagina_actual > 1:
            self.pagina_actual -= 1
            self.renderizar_pagina()

    def pagina_siguiente(self):
        if self.pagina_actual < self.total_paginas():
            self.pagina_actual += 1
            self.renderizar_pagina()

    def cargar_horarios_profesor(self):
        for child in self.scroll_horarios.winfo_children():
            child.destroy()
        if not self.profesor_seleccionado:
            return
        horarios = db.obtener_horarios_profesor(self.profesor_seleccionado['id_profesor'])
        if not horarios:
            ctk.CTkLabel(self.scroll_horarios, text="📭  No hay horarios asignados", font=fuentes.cuerpo(size=13), text_color=colores.TEXTO_TENUE).pack(pady=20)
            return
        for h in horarios:
            row = ctk.CTkFrame(self.scroll_horarios, fg_color=colores.COLOR_TARJETA, corner_radius=10, border_width=1, border_color=colores.COLOR_TARJETA_BORDE, height=40)
            row.pack(fill="x", pady=4, padx=2)
            texto_horario = f"🕑  {h['nombre_dia']}   ·   Entrada {h['hora_entrada']} hrs   ·   Salida {h['hora_salida']} hrs"
            ctk.CTkLabel(row, text=texto_horario, font=fuentes.cuerpo(size=13), text_color=colores.TEXTO_PRIMARIO).pack(side="left", padx=15, pady=8)
            ctk.CTkButton(row, text="Eliminar", width=70, height=28, corner_radius=7, font=fuentes.pequena(size=11), fg_color=colores.COLOR_BTN_ELIMINAR, hover_color=colores.COLOR_BTN_ELIMINAR_HOVER, command=lambda hid=h['id_horario']: self.borrar_horario(hid)).pack(side="right", padx=10)

    def guardar_horario(self):
        if not self.profesor_seleccionado:
            mostrar_advertencia("Atención", "Primero selecciona a alguien de la lista.", master=self)
            return
        id_dia = self.DIAS_MAPPING[self.cmb_dia.get()]
        entrada = self.ent_entrada.get().strip()
        salida = self.ent_salida.get().strip()
        if not entrada or not salida:
            mostrar_advertencia("Atención", "Ingresa la hora de entrada y salida (Ej: 08:00 y 16:00).", master=self)
            return
        try:
            db.agregar_horario(self.profesor_seleccionado['id_profesor'], id_dia, entrada, salida)
            self.ent_entrada.delete(0, 'end')
            self.ent_salida.delete(0, 'end')
            self.cargar_horarios_profesor()
        except Exception as e:
            mostrar_error("Error", f"No se pudo guardar el horario:\n{e}", master=self)

    def borrar_horario(self, id_horario):
        try:
            db.eliminar_horario(id_horario)
            self.cargar_horarios_profesor()
        except Exception as e:
            mostrar_error("Error", f"No se pudo eliminar el bloque:\n{e}", master=self)

    def validar_tecla_hora(self, P, S, d):
        if d == '1': 
            if len(S) == 1 and not S.isdigit():
                return False
            if len(S) > 1 and not all(c.isdigit() or c == ':' for c in S):
                return False
            digitos = "".join(c for c in P if c.isdigit())
            if len(digitos) > 4:
                return False
        return True

    def aplicar_formato_hora(self, entry_widget):
        vcmd = (self.register(self.validar_tecla_hora), '%P', '%S', '%d')
        entry_widget.configure(validate="key", validatecommand=vcmd)

        def _on_key_release(event):
            if event.keysym in ("BackSpace", "Delete"):
                texto = entry_widget.get()
                if texto.endswith(":"):
                    entry_widget.configure(validate="none") 
                    entry_widget.delete(0, "end")
                    entry_widget.insert(0, texto[:-1])
                    entry_widget.configure(validate="key") 
                return

            if event.keysym in ("Left", "Right", "Up", "Down", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"):
                return

            texto_actual = entry_widget.get()
            digitos = "".join(c for c in texto_actual if c.isdigit())[:4]

            if not digitos:
                return

            if len(digitos) >= 2 and int(digitos[:2]) > 23:
                digitos = "23" + digitos[2:]

            if len(digitos) == 3 and int(digitos) > 5:
                digitos = digitos[:2] + "5"
            elif len(digitos) == 4 and int(digitos[2:4]) > 59:
                digitos = digitos[:2] + "59"

            nuevo_texto = digitos if len(digitos) <= 2 else f"{digitos[:2]}:{digitos[2:]}"

            if texto_actual != nuevo_texto:
                entry_widget.configure(validate="none")
                entry_widget.delete(0, "end")
                entry_widget.insert(0, nuevo_texto)
                entry_widget.configure(validate="key")

        entry_widget.bind("<KeyRelease>", _on_key_release)


def cargar_archivo_masivo(self):
        tipos_archivo = [
            ("Archivos Excel y CSV", "*.xlsx *.csv"), 
            ("Todos los archivos", "*.*")
        ]
        ruta_archivo = filedialog.askopenfilename(
            title="Seleccionar documento de Docentes/Horarios", 
            filetypes=tipos_archivo
        )

        if not ruta_archivo:
            return

        # Llamamos al motor inteligente (ya no necesita que le digamos qué tipo de carga es)
        exito, mensaje = db.procesar_carga_masiva_inteligente(ruta_archivo)

        if exito:
            mostrar_exito("Resumen de Importación", mensaje, master=self)
            
            # Recargar la lista visual de profesores (pool_tarjetas)
            self.cargar_lista_profesores()
            
            # Si el usuario tenía seleccionado a un docente en el panel derecho, refrescar su horario
            if self.profesor_seleccionado:
                # Actualizar los datos en caché del profesor seleccionado
                for p in self.profesores_filtrados:
                    if p['id_profesor'] == self.profesor_seleccionado['id_profesor']:
                        self.profesor_seleccionado = p
                        break
                self.cargar_horarios_profesor()
        else:
            mostrar_error("Error en el archivo", mensaje, master=self)

if __name__ == "__main__":
    app = VentanaGestionDocentes()
    app.mainloop()