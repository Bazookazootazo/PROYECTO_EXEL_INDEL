import customtkinter as ctk
from gestion_docente import operaciones_bloque as ops
from gestion_docente.catalogos import AREAS, DIAS, NOMBRE_DIA, TIPOS, TURNOS
from utilerias.campo_hora import aplicar_formato_hora
from utilerias.messagebox_variados import mostrar_error, mostrar_exito, mostrar_pregunta
from utilerias.paleta_colores import colores, fuentes

SIN_CAMBIO = "sin cambio"

ACCIONES = {
    "datos": dict(titulo="Actualización masiva de datos generales", boton="Aplicar cambios", destructiva=False,
                  color=colores.ACENTO, hover=colores.ACENTO_HOVER),
    "asignar": dict(titulo="Asignación masiva de horario(s)", boton="Asignar horario(s)", destructiva=False,
                    color=colores.EXITO, hover=colores.EXITO_HOVER),
    "quitar": dict(titulo="Quitar masivamente horarios", boton="Aplicar cambios", destructiva=True,
                   color=colores.ADVERTENCIA, hover=colores.ADVERTENCIA_HOVER),
}

class VentanaBloque(ctk.CTkToplevel):
    def __init__(self, parent, accion, profesores, horarios, on_success_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.accion, self.profesores, self.horarios = accion, profesores, horarios
        self.on_success_callback = on_success_callback
        self.plan = None

        if accion == "eliminar":
            self.withdraw()
            plan = ops.planificar_eliminar(self.profesores, self.horarios)
            if plan.aplicable:
                mensaje = (
                    f"Se eliminarán todos los docentes seleccionados ({len(self.profesores)}) "
                    f"más sus horarios asociados.\n\n"
                    f"Procure confirmar si está seguro de la acción."
                )
                if mostrar_pregunta("Baja masiva de docentes", mensaje, master=parent):
                    try:
                        resultado = ops.aplicar(plan)
                        if self.on_success_callback:
                            self.on_success_callback()
                        mostrar_exito(resultado.titulo, resultado.mensaje, master=parent)
                    except ops.ErrorOperacion as e:
                        mostrar_error("Error de Operación", str(e), master=parent)
            self.destroy()
            return

        self.cfg = ACCIONES[accion]

        self.title(self.cfg["titulo"])
        self.geometry("485x420")
        self.minsize(485, 420)
        self.resizable(True, True)
        self.configure(fg_color=colores.BG_VENTANA)
        
        self.grab_set()
        self.focus_force()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.bind("<Escape>", lambda e: self.destroy())
        self._centrar_ventana(parent, 485, 420)

        main_frame = ctk.CTkFrame(self, corner_radius=14, fg_color=colores.BG_PANEL, border_width=1, border_color=colores.BORDE)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        encabezado = ctk.CTkFrame(main_frame, fg_color="transparent")
        encabezado.pack(fill="x", padx=16, pady=(14, 8))
        
        ctk.CTkLabel(
            encabezado, text=self.cfg['titulo'],
            font=fuentes.seccion(size=16), text_color=colores.TEXTO_PRIMARIO,
            anchor="center"
        ).pack(fill="x")

        self.form_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self.form_frame.grid_columnconfigure(0, weight=1)

        {"datos": self._params_datos, "asignar": self._params_asignar,
         "quitar": self._params_quitar}.get(accion, lambda: None)()
         
        pie = ctk.CTkFrame(main_frame, fg_color="transparent")
        pie.pack(fill="x", padx=16, pady=(0, 14))
        pie.grid_columnconfigure(0, weight=1)

        self.lbl_estado = ctk.CTkLabel(pie, text="", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO,
                                       anchor="w", justify="left")
        self.lbl_estado.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        btns_frame = ctk.CTkFrame(pie, fg_color="transparent")
        btns_frame.grid(row=0, column=1, sticky="e")

        btn_cancelar = ctk.CTkButton(
            btns_frame, text="Cancelar", height=34, corner_radius=8,
            font=fuentes.boton(size=12), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
            command=self.destroy, width=90
        )
        btn_cancelar.pack(side="left", padx=(0, 8))

        self.btn_aplicar = ctk.CTkButton(
            btns_frame, text=self.cfg["boton"], height=34, corner_radius=8,
            font=fuentes.boton(size=12),
            fg_color=self.cfg["color"], hover_color=self.cfg["hover"],
            command=self._aplicar, width=130
        )
        self.btn_aplicar.pack(side="left")

        self.recalcular()

    def _centrar_ventana(self, parent, ancho, alto):
        self.update_idletasks()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - ancho) // 2
            y = py + (ph - alto) // 2
        except Exception:
            x, y = 100, 100
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _tarjeta(self, titulo, subtitulo=None):
        card = ctk.CTkFrame(self.form_frame, corner_radius=10, fg_color=colores.BG_PANEL_ALT, border_width=1, border_color=colores.BORDE_SUAVE)
        card.pack(fill="x", pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)
        
        lbl_t = ctk.CTkLabel(card, text=titulo, font=fuentes.boton(size=11), text_color=colores.TEXTO_PRIMARIO, anchor="w")
        lbl_t.pack(fill="x", padx=12, pady=(10, 2 if subtitulo else 8))
        
        if subtitulo:
            lbl_sub = ctk.CTkLabel(card, text=subtitulo, font=fuentes.pequena(size=10), text_color=colores.TEXTO_SECUNDARIO, anchor="w", justify="left")
            lbl_sub.pack(fill="x", padx=12, pady=(0, 8))
            card.bind("<Configure>", lambda e, l=lbl_sub: l.configure(wraplength=e.width - 24))
        return card

    def _menu(self, padre, valores, ancho=150):
        return ctk.CTkOptionMenu(padre, values=valores, width=ancho, height=32, font=fuentes.cuerpo(size=11),
                                 fg_color=colores.BG_ENTRADA, button_color=colores.ACENTO,
                                 button_hover_color=colores.ACENTO_HOVER, command=self.recalcular)

    def _params_datos(self):
        card = self._tarjeta("Nuevos datos para los docentes seleccionados")
        fila = ctk.CTkFrame(card, fg_color="transparent")
        fila.pack(fill="x", padx=12, pady=(0, 10))
        fila.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.cmb_area, self.cmb_tipo, self.cmb_turno = None, None, None
        
        campos = [
            ("Área", list(AREAS), "cmb_area"),
            ("Tipo", list(TIPOS), "cmb_tipo"),
            ("Turno", list(TURNOS), "cmb_turno")
        ]
        
        for idx, (etiqueta, valores, atributo) in enumerate(campos):
            sub = ctk.CTkFrame(fila, fg_color="transparent")
            sub.grid(row=0, column=idx, sticky="ew", padx=(0, 6 if idx < 2 else 0))
            ctk.CTkLabel(sub, text=etiqueta, font=fuentes.pequena(size=10), text_color=colores.TEXTO_TENUE).pack(anchor="w", pady=(0, 2))
            menu = self._menu(sub, [SIN_CAMBIO, *valores], 150)
            menu.set(SIN_CAMBIO)
            menu.pack(anchor="w", fill="x")
            setattr(self, atributo, menu)

    def _params_asignar(self):
        card = self._tarjeta("Asigna los nuevos horarios a los docentes selecciondos")
        
        dias_frame = ctk.CTkFrame(card, fg_color="transparent")
        dias_frame.pack(fill="x", padx=12, pady=(0, 8))
        
        for col in range(5):
            dias_frame.grid_columnconfigure(col, weight=1)

        self.var_dias = {}
        for idx, (nombre, id_dia) in enumerate(DIAS.items()):
            var = ctk.BooleanVar(value=False)
            chk = ctk.CTkCheckBox(
                dias_frame, text=nombre[:3], variable=var, command=self.recalcular, 
                checkbox_width=16, checkbox_height=16, 
                fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
                border_color=colores.BORDE_CLARO, font=fuentes.cuerpo(size=11)
            )
            chk.grid(row=0, column=idx, padx=2, sticky="w")
            self.var_dias[id_dia] = var

        horas_frame = ctk.CTkFrame(card, fg_color="transparent")
        horas_frame.pack(fill="x", padx=12, pady=(0, 8))
        self.ent_entrada, self.ent_salida = None, None
        
        for etiqueta, atributo, ejemplo in (("Entrada", "ent_entrada", "07:00"), ("Salida", "ent_salida", "16:00")):
            sub = ctk.CTkFrame(horas_frame, fg_color="transparent")
            sub.pack(side="left", padx=(0, 12))
            ctk.CTkLabel(sub, text=etiqueta, font=fuentes.pequena(size=10), text_color=colores.TEXTO_TENUE).pack(anchor="w", pady=(0, 2))
            entrada = ctk.CTkEntry(sub, width=100, height=32, placeholder_text=ejemplo, font=fuentes.cuerpo(size=12),
                                   fg_color=colores.BG_ENTRADA, border_color=colores.BORDE)
            entrada.pack(anchor="w")
            aplicar_formato_hora(entrada)
            entrada.bind("<KeyRelease>", self.recalcular)
            setattr(self, atributo, entrada)

        self.var_traslape = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(card, text="¿Permitir asignar horario a docentes que ya cuenten con uno para los días seleccionados?", variable=self.var_traslape,
                        command=self.recalcular, checkbox_width=16, checkbox_height=16, fg_color=colores.ACENTO,
                        hover_color=colores.ACENTO_HOVER, border_color=colores.BORDE_CLARO,
                        font=fuentes.pequena(size=10), text_color=colores.TEXTO_SECUNDARIO).pack(anchor="w", padx=12, pady=(0, 10))

    def _params_quitar(self):
        turnos = ops.turnos_en_seleccion(self.profesores, self.horarios)
        card = self._tarjeta("Selecciona un dia y horario a quitar")
        self.var_turnos = {}
        
        if not turnos:
            ctk.CTkLabel(card, text="No se encontraron horarios activos.", font=fuentes.cuerpo(size=11),
                         text_color=colores.TEXTO_TENUE).pack(padx=12, pady=(0, 10))
            return
            
        marcar = ctk.CTkFrame(card, fg_color="transparent")
        marcar.pack(fill="x", padx=12, pady=(0, 6))
        for texto, valor in (("Marcar todos", True), ("Desmarcar todos", False)):
            ctk.CTkButton(marcar, text=texto, width=100, height=24, corner_radius=6, font=fuentes.pequena(size=10),
                          fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
                          command=lambda v=valor: self._marcar_turnos(v)).pack(side="left", padx=(0, 6))
                          
        turnos_container = ctk.CTkFrame(card, fg_color="transparent")
        turnos_container.pack(fill="x", padx=12, pady=(0, 8))
        turnos_container.grid_columnconfigure(0, weight=1)

        for clave, quienes in turnos:
            var = ctk.BooleanVar(value=False)
            dia, entrada, salida = clave
            fila = ctk.CTkFrame(turnos_container, fg_color="transparent")
            fila.pack(fill="x", pady=1)
            fila.grid_columnconfigure(0, weight=1)
            
            ctk.CTkCheckBox(fila, text=f"{NOMBRE_DIA[dia]}    {entrada} – {salida}", variable=var, command=self.recalcular,
                            checkbox_width=16, checkbox_height=16, fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
                            border_color=colores.BORDE_CLARO, font=fuentes.cuerpo(size=11)).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(fila, text=f"{len(quienes)} docente(s)", font=fuentes.pequena(size=10),
                         text_color=colores.TEXTO_TENUE).grid(row=0, column=1, sticky="e")
            self.var_turnos[clave] = var

    def _marcar_turnos(self, valor):
        for var in self.var_turnos.values():
            var.set(valor)
        self.recalcular()

    def recalcular(self, *_):
        a = self.accion
        if a == "datos":
            valor = lambda m: None if not m or m.get() == SIN_CAMBIO else m.get()
            plan = ops.planificar_datos(self.profesores, valor(self.cmb_area), valor(self.cmb_tipo), valor(self.cmb_turno))
        elif a == "asignar":
            dias = [i for i, v in self.var_dias.items() if v.get()]
            plan = ops.planificar_asignacion(self.profesores, self.horarios, dias, self.ent_entrada.get(),
                                             self.ent_salida.get(), self.var_traslape.get())
        elif a == "quitar":
            plan = ops.planificar_quitar(self.profesores, self.horarios, {c for c, v in self.var_turnos.items() if v.get()})
            if not self.var_turnos:
                plan.error = "No hay horarios disponibles para procesar."
        else:
            plan = ops.Plan("eliminar")
            
        self.plan = plan
        
        self.btn_aplicar.configure(state="normal" if plan.aplicable else "disabled")
        if plan.error:
            self.lbl_estado.configure(text=plan.error)
        elif not plan.cambios:
            self.lbl_estado.configure(text="No se detectan cambios aplicables.")
        else:
            self.lbl_estado.configure(text=plan.resumen)

    def _aplicar(self):
        plan = self.plan
        if not plan or not plan.aplicable:
            return
        if self.cfg["destructiva"] and not mostrar_pregunta(
                self.cfg["titulo"], f"{plan.resumen}\n\nEsta acción es irreversible. ¿Desea continuar?", master=self):
            return

        self.btn_aplicar.configure(state="disabled", text="Aplicando…")
        self.update_idletasks()
        try:
            resultado = ops.aplicar(plan)
        except ops.ErrorOperacion as e:
            self.btn_aplicar.configure(state="normal", text=self.cfg["boton"])
            mostrar_error("Error de Operación", str(e), master=self)
            return

        if self.on_success_callback:
            self.on_success_callback()
        mostrar_exito(resultado.titulo, resultado.mensaje, master=self)
        self.destroy()