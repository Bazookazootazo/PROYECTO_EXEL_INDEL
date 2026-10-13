"""
Diálogo de acciones en bloque sobre los docentes seleccionados.

Ventana polimórfica optimizada para la gestión masiva (cambio de datos, asignación,
retiro de turnos y bajas de personal) con vista previa en tiempo real.
"""
import customtkinter as ctk

from gestion_docente import operaciones_bloque as ops
from gestion_docente.catalogos import AREAS, DIAS, NOMBRE_DIA, TIPOS
from utilerias.campo_hora import aplicar_formato_hora
from utilerias.messagebox_variados import mostrar_advertencia, mostrar_error, mostrar_exito, mostrar_pregunta
from utilerias.paleta_colores import colores, fuentes

SIN_CAMBIO = "— sin cambio —"

ACCIONES = {
    "datos": dict(icono="✏️", titulo="Actualización Masiva de Área y Tipo", boton="Aplicar cambios", destructiva=False,
                  color=colores.ACENTO, hover=colores.ACENTO_HOVER,
                  ayuda="Modifica el Área de adscripción y/o el Tipo de docente para todos los registros seleccionados."),
    "asignar": dict(icono="🗓", titulo="Asignación de Turno Común", boton="Asignar turno", destructiva=False,
                    color=colores.EXITO, hover=colores.EXITO_HOVER,
                    ayuda="Asigna el mismo horario y días especificados a todos los docentes marcados."),
    "quitar": dict(icono="✂️", titulo="Retirar o Limpiar Turnos", boton="Aplicar cambios", destructiva=True,
                   color=colores.ADVERTENCIA, hover=colores.ADVERTENCIA_HOVER,
                   ayuda="Seleccione los turnos que desea retirar de la agenda de los docentes seleccionados."),
    "eliminar": dict(icono="🗑", titulo="Baja Masiva de Docentes", boton="Eliminar docentes", destructiva=True,
                     color=colores.PELIGRO, hover=colores.PELIGRO_HOVER,
                     ayuda="Da de baja permanentemente a los docentes seleccionados junto con su carga horaria."),
}
MAX_ITEMS = 8


class VentanaBloque(ctk.CTkToplevel):
    def __init__(self, parent, accion, profesores, horarios, on_success_callback=None):
        super().__init__(parent)
        self.accion, self.profesores, self.horarios = accion, profesores, horarios
        self.cfg = ACCIONES[accion]
        self.on_success_callback = on_success_callback
        self.plan = None

        self.title(self.cfg["titulo"])
        self.geometry("740x760")
        self.minsize(640, 560)
        self.resizable(True, True)
        self.configure(fg_color=colores.BG_VENTANA)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(100, self._tomar_foco)

        self._encabezado()
        self.cuerpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cuerpo.grid(row=1, column=0, sticky="nsew", padx=20, pady=(12, 0))
        self.cuerpo.grid_columnconfigure(0, weight=1)
        
        {"datos": self._params_datos, "asignar": self._params_asignar,
         "quitar": self._params_quitar}.get(accion, lambda: None)()
         
        self._vista_previa()
        self._pie()
        self.recalcular()

    def _tomar_foco(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    # ───────────── Estructura fija ─────────────
    def _encabezado(self):
        cab = ctk.CTkFrame(self, corner_radius=14, fg_color=colores.BG_PANEL, border_width=1, border_color=colores.BORDE)
        cab.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        cab.grid_columnconfigure(0, weight=1)

        lbl_titulo = ctk.CTkLabel(cab, text=f"{self.cfg['icono']}  {self.cfg['titulo']}", font=fuentes.seccion(size=18),
                                  text_color=colores.TEXTO_PRIMARIO, anchor="w")
        lbl_titulo.pack(fill="x", padx=18, pady=(16, 2))
        
        lbl_ayuda = ctk.CTkLabel(cab, text=self.cfg["ayuda"], font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO,
                                   anchor="w", justify="left")
        lbl_ayuda.pack(fill="x", padx=18)
        cab.bind("<Configure>", lambda e, l=lbl_ayuda: l.configure(wraplength=e.width - 36))

        nombres = ", ".join(p["nombre"].title() for p in self.profesores[:4])
        resto = len(self.profesores) - 4
        txt_prof = f"👥  {len(self.profesores)} docente(s) seleccionado(s): {nombres}" + (f" y {resto} más" if resto > 0 else "")
        lbl_prof = ctk.CTkLabel(cab, text=txt_prof, font=fuentes.boton(size=11), text_color=colores.ACENTO, anchor="w", justify="left")
        lbl_prof.pack(fill="x", padx=18, pady=(8, 16))
        cab.bind("<Configure>", lambda e, l=lbl_prof: l.configure(wraplength=e.width - 36))

    def _tarjeta(self, titulo, subtitulo=None):
        card = ctk.CTkFrame(self.cuerpo, corner_radius=12, fg_color=colores.BG_PANEL_ALT, border_width=1, border_color=colores.BORDE_SUAVE)
        card.pack(fill="x", pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)
        
        lbl_t = ctk.CTkLabel(card, text=titulo, font=fuentes.boton(size=13), text_color=colores.TEXTO_PRIMARIO, anchor="w")
        lbl_t.pack(fill="x", padx=16, pady=(14, 2 if subtitulo else 12))
        
        if subtitulo:
            lbl_sub = ctk.CTkLabel(card, text=subtitulo, font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO, anchor="w", justify="left")
            lbl_sub.pack(fill="x", padx=16, pady=(0, 12))
            card.bind("<Configure>", lambda e, l=lbl_sub: l.configure(wraplength=e.width - 32))
        return card

    def _menu(self, padre, valores, ancho=260):
        return ctk.CTkOptionMenu(padre, values=valores, width=ancho, height=34, font=fuentes.cuerpo(size=12),
                                 fg_color=colores.BG_ENTRADA, button_color=colores.ACENTO,
                                 button_hover_color=colores.ACENTO_HOVER, command=self.recalcular)

    def _vista_previa(self):
        card = self._tarjeta("📋  Vista Previa de Impacto Operativo", "Verifique los cambios que se aplicarán antes de confirmar la operación.")
        self.vista = ctk.CTkFrame(card, fg_color="transparent")
        self.vista.pack(fill="x", padx=16, pady=(0, 14))
        self.vista.grid_columnconfigure(0, weight=1)

    def _pie(self):
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.grid(row=2, column=0, sticky="ew", padx=20, pady=16)
        pie.grid_columnconfigure(0, weight=1)
        
        self.lbl_estado = ctk.CTkLabel(pie, text="", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO,
                                       anchor="w", justify="left")
        self.lbl_estado.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        btns_frame = ctk.CTkFrame(pie, fg_color="transparent")
        btns_frame.grid(row=0, column=1, sticky="e")
        
        ctk.CTkButton(btns_frame, text="Cancelar", width=110, height=38, corner_radius=10, font=fuentes.boton(size=13),
                      fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
                      command=self.destroy).pack(side="left", padx=(0, 8))
                      
        self.btn_aplicar = ctk.CTkButton(btns_frame, text=self.cfg["boton"], width=170, height=38, corner_radius=10,
                                         font=fuentes.boton(size=13), fg_color=self.cfg["color"],
                                         hover_color=self.cfg["hover"], command=self._aplicar)
        self.btn_aplicar.pack(side="left")

    # ───────────── Parámetros dinámicos por acción ─────────────
    def _params_datos(self):
        card = self._tarjeta("Configuración de Nuevos Valores", "Seleccione los nuevos datos a aplicar. Mantenga «— sin cambio —» en los campos que no desee modificar.")
        fila = ctk.CTkFrame(card, fg_color="transparent")
        fila.pack(fill="x", padx=16, pady=(0, 14))
        self.cmb_area, self.cmb_tipo = None, None
        
        for etiqueta, valores, atributo in (("Área de adscripción", list(AREAS), "cmb_area"), ("Tipo de docente", list(TIPOS), "cmb_tipo")):
            sub = ctk.CTkFrame(fila, fg_color="transparent")
            sub.pack(side="left", padx=(0, 16), fill="x", expand=True)
            ctk.CTkLabel(sub, text=etiqueta, font=fuentes.pequena(size=10), text_color=colores.TEXTO_TENUE).pack(anchor="w", pady=(0, 3))
            menu = self._menu(sub, [SIN_CAMBIO, *valores], 270 if atributo == "cmb_area" else 200)
            menu.set(SIN_CAMBIO)
            menu.pack(anchor="w", fill="x")
            setattr(self, atributo, menu)

    def _params_asignar(self):
        card = self._tarjeta("Configuración del Turno", "Marque los días correspondientes e ingrese el horario en formato de 24 horas (ej. 07:00 a 12:00).")
        
        dias_frame = ctk.CTkFrame(card, fg_color="transparent")
        dias_frame.pack(fill="x", padx=16, pady=(0, 12))
        self.var_dias = {}
        for nombre, id_dia in DIAS.items():
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(dias_frame, text=nombre, variable=var, command=self.recalcular, checkbox_width=18,
                            checkbox_height=18, fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
                            border_color=colores.BORDE_CLARO, font=fuentes.cuerpo(size=12)).pack(side="left", padx=(0, 12))
            self.var_dias[id_dia] = var

        horas_frame = ctk.CTkFrame(card, fg_color="transparent")
        horas_frame.pack(fill="x", padx=16, pady=(0, 12))
        self.ent_entrada, self.ent_salida = None, None
        
        for etiqueta, atributo, ejemplo in (("Hora de entrada", "ent_entrada", "07:00"), ("Hora de salida", "ent_salida", "16:00")):
            sub = ctk.CTkFrame(horas_frame, fg_color="transparent")
            sub.pack(side="left", padx=(0, 16))
            ctk.CTkLabel(sub, text=etiqueta, font=fuentes.pequena(size=10), text_color=colores.TEXTO_TENUE).pack(anchor="w", pady=(0, 3))
            entrada = ctk.CTkEntry(sub, width=120, height=34, placeholder_text=ejemplo, font=fuentes.cuerpo(size=13),
                                   fg_color=colores.BG_ENTRADA, border_color=colores.BORDE)
            entrada.pack(anchor="w")
            aplicar_formato_hora(entrada)
            entrada.bind("<KeyRelease>", self.recalcular)
            setattr(self, atributo, entrada)

        self.var_traslape = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(card, text="Permitir asignación aun cuando existan horarios previos (solo cuando las horas coincidan)", variable=self.var_traslape,
                        command=self.recalcular, checkbox_width=18, checkbox_height=18, fg_color=colores.ACENTO,
                        hover_color=colores.ACENTO_HOVER, border_color=colores.BORDE_CLARO,
                        font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO).pack(anchor="w", padx=16, pady=(0, 14))

    def _params_quitar(self):
        turnos = ops.turnos_en_seleccion(self.profesores, self.horarios)
        subt = "Marque los turnos que desea retirar. Puede usar los botones rápidos para marcar o desmarcar todos." if turnos else None
        card = self._tarjeta("Turnos Registrados en la Selección", subt)
        self.var_turnos = {}
        
        if not turnos:
            ctk.CTkLabel(card, text="📭  No se encontraron turnos activos en los docentes seleccionados.", font=fuentes.cuerpo(size=12),
                         text_color=colores.TEXTO_TENUE).pack(padx=16, pady=(0, 16))
            return
            
        marcar = ctk.CTkFrame(card, fg_color="transparent")
        marcar.pack(fill="x", padx=16, pady=(0, 8))
        for texto, valor in (("Marcar todos", True), ("Desmarcar todos", False)):
            ctk.CTkButton(marcar, text=texto, width=120, height=28, corner_radius=7, font=fuentes.pequena(size=11),
                          fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
                          command=lambda v=valor: self._marcar_turnos(v)).pack(side="left", padx=(0, 8))
                          
        turnos_container = ctk.CTkScrollableFrame(card, fg_color="transparent", height=180)
        turnos_container.pack(fill="x", padx=16, pady=(0, 14))
        turnos_container.grid_columnconfigure(0, weight=1)

        for clave, quienes in turnos:
            var = ctk.BooleanVar(value=False)
            dia, entrada, salida = clave
            fila = ctk.CTkFrame(turnos_container, fg_color="transparent")
            fila.pack(fill="x", pady=2)
            fila.grid_columnconfigure(0, weight=1)
            
            ctk.CTkCheckBox(fila, text=f"{NOMBRE_DIA[dia]}    {entrada} – {salida}", variable=var, command=self.recalcular,
                            checkbox_width=18, checkbox_height=18, fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
                            border_color=colores.BORDE_CLARO, font=fuentes.cuerpo(size=12)).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(fila, text=f"{len(quienes)} docente(s)", font=fuentes.pequena(size=11),
                         text_color=colores.TEXTO_TENUE).grid(row=0, column=1, sticky="e")
            self.var_turnos[clave] = var

    def _marcar_turnos(self, valor):
        for var in self.var_turnos.values():
            var.set(valor)
        self.recalcular()

    # ───────────── Recálculo y Vista Previa ─────────────
    def recalcular(self, *_):
        a = self.accion
        if a == "datos":
            valor = lambda m: None if m.get() == SIN_CAMBIO else m.get()
            plan = ops.planificar_datos(self.profesores, valor(self.cmb_area), valor(self.cmb_tipo))
        elif a == "asignar":
            dias = [i for i, v in self.var_dias.items() if v.get()]
            plan = ops.planificar_asignacion(self.profesores, self.horarios, dias, self.ent_entrada.get(),
                                             self.ent_salida.get(), self.var_traslape.get())
        elif a == "quitar":
            plan = ops.planificar_quitar(self.profesores, self.horarios, {c for c, v in self.var_turnos.items() if v.get()})
            if not self.var_turnos:
                plan.error = "No hay turnos disponibles para procesar."
        else:
            plan = ops.planificar_eliminar(self.profesores, self.horarios)
        self.plan = plan
        self._mostrar_plan(plan)

    def _mostrar_plan(self, plan):
        for w in self.vista.winfo_children():
            w.destroy()

        if plan.error:
            ctk.CTkLabel(self.vista, text=f"ℹ️  {plan.error}", font=fuentes.cuerpo(size=12), text_color=colores.ADVERTENCIA,
                         anchor="w", justify="left").pack(fill="x", pady=(0, 4))
        else:
            color = {"ok": colores.TEXTO_PRIMARIO, "info": colores.TEXTO_SECUNDARIO, "aviso": colores.ADVERTENCIA}
            for ln in plan.lineas:
                bloque = ctk.CTkFrame(self.vista, fg_color="transparent")
                bloque.pack(fill="x", pady=(0, 6))
                
                lbl_ln = ctk.CTkLabel(bloque, text=f"{ln.icono}  {ln.texto}",
                                      font=fuentes.cuerpo(size=12) if ln.nivel == "info" else fuentes.boton(size=12), 
                                      text_color=color[ln.nivel], anchor="w", justify="left")
                lbl_ln.pack(fill="x")
                bloque.bind("<Configure>", lambda e, l=lbl_ln: l.configure(wraplength=e.width))

                if ln.detalle:
                    visibles = ln.detalle[:MAX_ITEMS]
                    texto = ("\n" if ln.lista else ", ").join(f"•  {d}" if ln.lista else d for d in visibles)
                    if len(ln.detalle) > MAX_ITEMS:
                        texto += f"\n… y {len(ln.detalle) - MAX_ITEMS} más" if ln.lista else f", … y {len(ln.detalle) - MAX_ITEMS} más"
                    lbl_det = ctk.CTkLabel(bloque, text=texto, font=fuentes.pequena(size=11), text_color=colores.TEXTO_TENUE,
                                           anchor="w", justify="left")
                    lbl_det.pack(fill="x", padx=(24, 0), pady=(2, 0))
                    bloque.bind("<Configure>", lambda e, l=lbl_det: l.configure(wraplength=e.width - 24))

        self.btn_aplicar.configure(state="normal" if plan.aplicable else "disabled")
        if plan.error:
            self.lbl_estado.configure(text="")
        elif not plan.cambios:
            self.lbl_estado.configure(text="No se detectan cambios aplicables con los parámetros actuales.")
        else:
            self.lbl_estado.configure(text=plan.resumen)

    # ───────────── Ejecución ─────────────
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
        (mostrar_advertencia if resultado.parcial else mostrar_exito)(resultado.titulo, resultado.mensaje, master=self)
        self.destroy()