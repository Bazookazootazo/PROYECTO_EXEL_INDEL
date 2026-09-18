import math
import customtkinter as ctk
import database as db
from crud_docente import VentanaCrudProfesor
from utilerias.messagebox_variados import mostrar_exito, mostrar_advertencia, mostrar_error, mostrar_pregunta
from utilerias.paleta_colores import colores

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VentanaGestionDocentes(ctk.CTk):
    DIAS_MAPPING = {"Lunes": 1, "Martes": 2, "Miércoles": 3, "Jueves": 4, "Viernes": 5}
    ELEMENTOS_POR_PAGINA = 10

    def __init__(self):
        super().__init__()
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
        self.after(10, lambda: self.wm_state('zoomed'))
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

    def _construir_panel_izquierdo(self):
        panel = ctk.CTkFrame(self, corner_radius=15)
        panel.grid(row=0, column=0, sticky="nsew", padx=(15, 7), pady=15)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(3, weight=1)
        
        ctk.CTkLabel(panel, text="Gestión Docente", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        ctk.CTkButton(panel, text="Nuevo Docente", command=self.abrir_ventana_registro).grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 8))
        
        self.var_busqueda = ctk.StringVar()
        self.var_busqueda.trace_add("write", self.filtrar_profesores)
        ctk.CTkEntry(panel, placeholder_text="Buscar por nombre o área...", textvariable=self.var_busqueda).grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))
        
        self.container_profesores = ctk.CTkFrame(panel, fg_color="transparent")
        self.container_profesores.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 5))
        self.container_profesores.grid_columnconfigure(0, weight=1)
        
        for r in range(self.ELEMENTOS_POR_PAGINA):
            self.container_profesores.grid_rowconfigure(r, weight=1, uniform="grupo_botones")
            
        self._crear_pool_tarjetas()
        
        nav_frame = ctk.CTkFrame(panel, fg_color="transparent")
        nav_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=(5, 15))
        
        self.btn_prev = ctk.CTkButton(nav_frame, text="Anterior", width=80, command=self.pagina_anterior)
        self.btn_prev.pack(side="left")
        self.lbl_paginacion = ctk.CTkLabel(nav_frame, text="Pág 1 / 1", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_paginacion.pack(side="left", expand=True)
        self.btn_next = ctk.CTkButton(nav_frame, text="Siguiente", width=80, command=self.pagina_siguiente)
        self.btn_next.pack(side="right")

    def _crear_pool_tarjetas(self):
        for i in range(self.ELEMENTOS_POR_PAGINA):
            card = ctk.CTkFrame(self.container_profesores, fg_color=colores.COLOR_TARJETA, corner_radius=8, border_width=1, border_color=colores.COLOR_TARJETA_BORDE, cursor="hand2")
            card.grid(row=i, column=0, sticky="ew", pady=1, padx=2)
            card.grid_columnconfigure(0, weight=1)
            card.grid_columnconfigure(1, weight=0)
            
            lbl_nombre = ctk.CTkLabel(card, text="", anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color="#FFFFFF", height=16)
            lbl_nombre.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 1))
            
            lbl_area = ctk.CTkLabel(card, text="", anchor="w", font=ctk.CTkFont(size=10), text_color=colores.COLOR_TEXTO_AREA, height=14)
            lbl_area.grid(row=1, column=0, sticky="ew", padx=10, pady=(1, 5))
            
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.grid(row=0, column=1, rowspan=2, sticky="e", padx=(0, 10))
            btn_edit = ctk.CTkButton(btn_frame, text="Editar", width=30, fg_color=colores.COLOR_BTN_EDITAR, hover_color=colores.COLOR_BTN_EDITAR_HOVER)
            btn_edit.pack(side="left", padx=2)
            btn_del = ctk.CTkButton(btn_frame, text="Eliminar", width=30, fg_color=colores.COLOR_BTN_ELIMINAR, hover_color=colores.COLOR_BTN_ELIMINAR_HOVER)
            btn_del.pack(side="left", padx=2)
            
            self.pool_tarjetas.append({"frame": card, "lbl_nombre": lbl_nombre, "lbl_area": lbl_area, "btn_edit": btn_edit, "btn_del": btn_del, "btn_frame": btn_frame})

    def _construir_panel_derecho(self):
        panel = ctk.CTkFrame(self, corner_radius=15)
        panel.grid(row=0, column=1, sticky="nsew", padx=(7, 15), pady=15)
        
        self.lbl_prof_seleccionado = ctk.CTkLabel(panel, text="Horario Semanal", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_prof_seleccionado.pack(anchor="w", padx=15, pady=(15, 10))
        
        horario_form = ctk.CTkFrame(panel, fg_color="transparent")
        horario_form.pack(fill="x", padx=15, pady=(0, 10))
        
        self.cmb_dia = ctk.CTkOptionMenu(horario_form, values=list(self.DIAS_MAPPING.keys()), width=120)
        self.cmb_dia.pack(side="left", padx=(0, 5))
        
        self.ent_entrada = ctk.CTkEntry(horario_form, width=90, placeholder_text="07:00")
        self.ent_entrada.pack(side="left", padx=5)
        self.aplicar_formato_hora(self.ent_entrada)
        
        self.ent_salida = ctk.CTkEntry(horario_form, width=90, placeholder_text="12:00")
        self.ent_salida.pack(side="left", padx=5)
        self.aplicar_formato_hora(self.ent_salida)
        
        ctk.CTkButton(horario_form, text="+ Agregar Turno", command=self.guardar_horario).pack(side="left", padx=(5, 0), fill="x", expand=True)
        
        self.scroll_horarios = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.scroll_horarios.pack(fill="both", expand=True, padx=10, pady=(0, 15))

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
        self.lbl_prof_seleccionado.configure(text=f"Horario: {profesor['nombre'].title()}")
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
                    border_width=1,
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
            ctk.CTkLabel(self.scroll_horarios, text="No hay horarios asignados", text_color="#777777").pack(pady=20)
            return
        for h in horarios:
            row = ctk.CTkFrame(self.scroll_horarios, fg_color=colores.COLOR_TARJETA, height=40)
            row.pack(fill="x", pady=4, padx=2)
            texto_horario = f" {h['nombre_dia']} - Entrada: {h['hora_entrada']} hrs - Salida: {h['hora_salida']} hrs"
            ctk.CTkLabel(row, text=texto_horario, font=ctk.CTkFont(size=13)).pack(side="left", padx=15, pady=8)
            ctk.CTkButton(row, text="Eliminar", width=70, fg_color=colores.COLOR_BTN_ELIMINAR, hover_color=colores.COLOR_BTN_ELIMINAR_HOVER, command=lambda hid=h['id_horario']: self.borrar_horario(hid)).pack(side="right", padx=10)

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

if __name__ == "__main__":
    app = VentanaGestionDocentes()
    app.mainloop()