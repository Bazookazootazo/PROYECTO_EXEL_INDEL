"""
Diálogo de acciones en bloque sobre los docentes seleccionados.

Una sola ventana sirve para las cinco acciones (cambiar Área/Tipo, asignar turno, quitar turno,
limpiar agenda, eliminar docentes). Siempre es igual de predecible:
  1. Eliges qué quieres hacer (parámetros arriba).
  2. La VISTA PREVIA se actualiza sola y dice exactamente qué pasará y a quién (y qué NO se aplicará y por qué).
  3. Nada se guarda hasta presionar el botón; todo ocurre en una sola transacción.
"""
import customtkinter as ctk

from gestion_docente import operaciones_bloque as ops
from gestion_docente.catalogos import AREAS, DIAS, NOMBRE_DIA, TIPOS
from utilerias.campo_hora import aplicar_formato_hora
from utilerias.messagebox_variados import mostrar_advertencia, mostrar_error, mostrar_exito, mostrar_pregunta
from utilerias.paleta_colores import colores, fuentes

SIN_CAMBIO = "— sin cambio —"

ACCIONES = {
    "datos": dict(icono="✏️", titulo="Cambiar Área / Tipo", boton="Aplicar cambios", destructiva=False,
                  color=colores.ACENTO, hover=colores.ACENTO_HOVER,
                  ayuda="Aplica el mismo Área y/o Tipo a todos los docentes seleccionados."),
    "asignar": dict(icono="🗓", titulo="Asignar turno común", boton="Asignar turno", destructiva=False,
                    color=colores.EXITO, hover=colores.EXITO_HOVER,
                    ayuda="Agrega el mismo turno (por ejemplo, una junta de academia) a todos los seleccionados."),
    "quitar": dict(icono="✂️", titulo="Quitar turnos", boton="Quitar turnos", destructiva=True,
                   color=colores.ADVERTENCIA, hover=colores.ADVERTENCIA_HOVER,
                   ayuda="Quita de la agenda de los seleccionados los turnos que marques."),
    "limpiar": dict(icono="🧹", titulo="Limpiar agenda", boton="Limpiar agenda", destructiva=True,
                    color=colores.PELIGRO, hover=colores.PELIGRO_HOVER,
                    ayuda="Borra los turnos de los seleccionados (por ejemplo, por una baja). Desmarca los que quieras conservar."),
    "eliminar": dict(icono="🗑", titulo="Eliminar docentes", boton="Eliminar docentes", destructiva=True,
                     color=colores.PELIGRO, hover=colores.PELIGRO_HOVER,
                     ayuda="Elimina a los docentes seleccionados junto con sus horarios."),
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
        self.geometry("700x720")
        self.minsize(620, 540)
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
         "quitar": self._params_quitar, "limpiar": self._params_quitar}.get(accion, lambda: None)()
        self._vista_previa()
        self._pie()
        self.recalcular()

    def _tomar_foco(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    # ───────────── estructura ─────────────
    def _encabezado(self):
        cab = ctk.CTkFrame(self, corner_radius=14, fg_color=colores.BG_PANEL, border_width=1, border_color=colores.BORDE)
        cab.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        ctk.CTkLabel(cab, text=f"{self.cfg['icono']}  {self.cfg['titulo']}", font=fuentes.seccion(size=18),
                     text_color=colores.TEXTO_PRIMARIO, anchor="w").pack(fill="x", padx=18, pady=(16, 2))
        ctk.CTkLabel(cab, text=self.cfg["ayuda"], font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO,
                     anchor="w", justify="left", wraplength=620).pack(fill="x", padx=18)
        nombres = ", ".join(p["nombre"].title() for p in self.profesores[:4])
        resto = len(self.profesores) - 4
        ctk.CTkLabel(cab, text=f"👥  {len(self.profesores)} docente(s): {nombres}" + (f" y {resto} más" if resto > 0 else ""),
                     font=fuentes.boton(size=11), text_color=colores.ACENTO, anchor="w", justify="left",
                     wraplength=620).pack(fill="x", padx=18, pady=(8, 16))

    def _tarjeta(self, titulo, subtitulo=None):
        card = ctk.CTkFrame(self.cuerpo, corner_radius=12, fg_color=colores.BG_PANEL_ALT, border_width=1, border_color=colores.BORDE_SUAVE)
        card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(card, text=titulo, font=fuentes.boton(size=13), text_color=colores.TEXTO_PRIMARIO,
                     anchor="w").pack(fill="x", padx=16, pady=(14, 2 if subtitulo else 10))
        if subtitulo:
            ctk.CTkLabel(card, text=subtitulo, font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO,
                         anchor="w", justify="left", wraplength=620).pack(fill="x", padx=16, pady=(0, 10))
        return card

    def _menu(self, padre, valores, ancho=260):
        return ctk.CTkOptionMenu(padre, values=valores, width=ancho, height=34, font=fuentes.cuerpo(size=12),
                                 fg_color=colores.BG_ENTRADA, button_color=colores.ACENTO,
                                 button_hover_color=colores.ACENTO_HOVER, command=self.recalcular)

    def _vista_previa(self):
        card = self._tarjeta("📋  Vista previa — esto es lo que va a pasar")
        self.vista = ctk.CTkFrame(card, fg_color="transparent")
        self.vista.pack(fill="x")

    def _pie(self):
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.grid(row=2, column=0, sticky="ew", padx=20, pady=16)
        pie.grid_columnconfigure(0, weight=1)
        self.lbl_estado = ctk.CTkLabel(pie, text="", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO,
                                       anchor="w", justify="left", wraplength=360)
        self.lbl_estado.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(pie, text="Cancelar", width=110, height=38, corner_radius=10, font=fuentes.boton(size=13),
                      fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
                      command=self.destroy).grid(row=0, column=1, padx=(0, 8))
        self.btn_aplicar = ctk.CTkButton(pie, text=self.cfg["boton"], width=170, height=38, corner_radius=10,
                                         font=fuentes.boton(size=13), fg_color=self.cfg["color"],
                                         hover_color=self.cfg["hover"], command=self._aplicar)
        self.btn_aplicar.grid(row=0, column=2)

    # ───────────── parámetros de cada acción ─────────────
    def _params_datos(self):
        card = self._tarjeta("Nuevos valores", "Deja «— sin cambio —» en lo que no quieras modificar.")
        fila = ctk.CTkFrame(card, fg_color="transparent")
        fila.pack(fill="x", padx=16, pady=(0, 14))
        self.cmb_area, self.cmb_tipo = None, None
        for etiqueta, valores, atributo in (("Área", list(AREAS), "cmb_area"), ("Tipo", list(TIPOS), "cmb_tipo")):
            sub = ctk.CTkFrame(fila, fg_color="transparent")
            sub.pack(side="left", padx=(0, 16))
            ctk.CTkLabel(sub, text=etiqueta, font=fuentes.pequena(size=10), text_color=colores.TEXTO_TENUE).pack(anchor="w")
            menu = self._menu(sub, [SIN_CAMBIO, *valores], 270 if atributo == "cmb_area" else 190)
            menu.set(SIN_CAMBIO)
            menu.pack(anchor="w")
            setattr(self, atributo, menu)

    def _params_asignar(self):
        card = self._tarjeta("Turno a asignar", "Marca uno o varios días; la hora se escribe en formato 24 h (0700 → 07:00).")
        dias = ctk.CTkFrame(card, fg_color="transparent")
        dias.pack(fill="x", padx=16, pady=(0, 10))
        self.var_dias = {}
        for nombre, id_dia in DIAS.items():
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(dias, text=nombre, variable=var, command=self.recalcular, width=90, checkbox_width=20,
                            checkbox_height=20, fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
                            border_color=colores.BORDE_CLARO, font=fuentes.cuerpo(size=12)).pack(side="left", padx=(0, 10))
            self.var_dias[id_dia] = var

        horas = ctk.CTkFrame(card, fg_color="transparent")
        horas.pack(fill="x", padx=16, pady=(0, 10))
        self.ent_entrada, self.ent_salida = None, None
        for etiqueta, atributo, ejemplo in (("Entrada", "ent_entrada", "07:00"), ("Salida", "ent_salida", "12:00")):
            sub = ctk.CTkFrame(horas, fg_color="transparent")
            sub.pack(side="left", padx=(0, 16))
            ctk.CTkLabel(sub, text=etiqueta, font=fuentes.pequena(size=10), text_color=colores.TEXTO_TENUE).pack(anchor="w")
            entrada = ctk.CTkEntry(sub, width=100, height=34, placeholder_text=ejemplo, font=fuentes.cuerpo(size=13),
                                   fg_color=colores.BG_ENTRADA, border_color=colores.BORDE)
            entrada.pack(anchor="w")
            aplicar_formato_hora(entrada)
            entrada.bind("<KeyRelease>", self.recalcular)           # se suma a la máscara (CTkEntry.bind agrega, no reemplaza)
            setattr(self, atributo, entrada)

        self.var_traslape = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(card, text="Agregarlo también a quienes ya tengan un turno que se traslape", variable=self.var_traslape,
                        command=self.recalcular, checkbox_width=20, checkbox_height=20, fg_color=colores.ACENTO,
                        hover_color=colores.ACENTO_HOVER, border_color=colores.BORDE_CLARO,
                        font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO).pack(anchor="w", padx=16, pady=(0, 14))

    def _params_quitar(self):
        turnos = ops.turnos_en_seleccion(self.profesores, self.horarios)
        card = self._tarjeta("Turnos que tienen los seleccionados",
                             "Solo aparecen turnos que realmente existen; el número es a cuántos de los seleccionados pertenece." if turnos else None)
        self.var_turnos = {}
        if not turnos:
            ctk.CTkLabel(card, text="📭  Los docentes seleccionados no tienen turnos registrados.", font=fuentes.cuerpo(size=12),
                         text_color=colores.TEXTO_TENUE).pack(padx=16, pady=(0, 16))
            return
        marcar = ctk.CTkFrame(card, fg_color="transparent")
        marcar.pack(fill="x", padx=16, pady=(0, 6))
        for texto, valor in (("Marcar todos", True), ("Ninguno", False)):
            ctk.CTkButton(marcar, text=texto, width=100, height=26, corner_radius=7, font=fuentes.pequena(size=11),
                          fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
                          command=lambda v=valor: self._marcar_turnos(v)).pack(side="left", padx=(0, 6))
        for clave, quienes in turnos:
            var = ctk.BooleanVar(value=self.accion == "limpiar")
            dia, entrada, salida = clave
            fila = ctk.CTkFrame(card, fg_color="transparent")
            fila.pack(fill="x", padx=16, pady=3)
            fila.grid_columnconfigure(0, weight=1)
            ctk.CTkCheckBox(fila, text=f"{NOMBRE_DIA[dia]}   {entrada}–{salida}", variable=var, command=self.recalcular,
                            checkbox_width=20, checkbox_height=20, fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
                            border_color=colores.BORDE_CLARO, font=fuentes.cuerpo(size=12)).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(fila, text=f"{len(quienes)} docente(s)", font=fuentes.pequena(size=11),
                         text_color=colores.TEXTO_TENUE).grid(row=0, column=1, sticky="e")
            self.var_turnos[clave] = var
        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    def _marcar_turnos(self, valor):
        for var in self.var_turnos.values():
            var.set(valor)
        self.recalcular()

    # ───────────── vista previa ─────────────
    def recalcular(self, *_):
        a = self.accion
        if a == "datos":
            valor = lambda m: None if m.get() == SIN_CAMBIO else m.get()
            plan = ops.planificar_datos(self.profesores, valor(self.cmb_area), valor(self.cmb_tipo))
        elif a == "asignar":
            dias = [i for i, v in self.var_dias.items() if v.get()]
            plan = ops.planificar_asignacion(self.profesores, self.horarios, dias, self.ent_entrada.get(),
                                             self.ent_salida.get(), self.var_traslape.get())
        elif a in ("quitar", "limpiar"):
            plan = ops.planificar_quitar(self.profesores, self.horarios, {c for c, v in self.var_turnos.items() if v.get()})
            if not self.var_turnos:
                plan.error = "No hay turnos que quitar."
        else:
            plan = ops.planificar_eliminar(self.profesores, self.horarios)
        self.plan = plan
        self._mostrar_plan(plan)

    def _mostrar_plan(self, plan):
        for w in self.vista.winfo_children():
            w.destroy()

        if plan.error:
            ctk.CTkLabel(self.vista, text=f"ℹ️  {plan.error}", font=fuentes.cuerpo(size=12), text_color=colores.ADVERTENCIA,
                         anchor="w", justify="left", wraplength=620).pack(fill="x", padx=16, pady=(0, 14))
        else:
            color = {"ok": colores.TEXTO_PRIMARIO, "info": colores.TEXTO_SECUNDARIO, "aviso": colores.ADVERTENCIA}
            for ln in plan.lineas:
                bloque = ctk.CTkFrame(self.vista, fg_color="transparent")
                bloque.pack(fill="x", padx=16, pady=(0, 8))
                ctk.CTkLabel(bloque, text=f"{ln.icono}  {ln.texto}",
                             font=fuentes.cuerpo(size=12) if ln.nivel == "info" else fuentes.boton(size=12), text_color=color[ln.nivel],
                             anchor="w", justify="left", wraplength=620).pack(fill="x")
                if ln.detalle:
                    visibles = ln.detalle[:MAX_ITEMS]
                    texto = ("\n" if ln.lista else ", ").join(f"•  {d}" if ln.lista else d for d in visibles)
                    if len(ln.detalle) > MAX_ITEMS:
                        texto += f"\n… y {len(ln.detalle) - MAX_ITEMS} más" if ln.lista else f", … y {len(ln.detalle) - MAX_ITEMS} más"
                    ctk.CTkLabel(bloque, text=texto, font=fuentes.pequena(size=11), text_color=colores.TEXTO_TENUE,
                                 anchor="w", justify="left", wraplength=600).pack(fill="x", padx=(26, 0), pady=(2, 0))
            ctk.CTkFrame(self.vista, height=6, fg_color="transparent").pack()

        self.btn_aplicar.configure(state="normal" if plan.aplicable else "disabled")
        if plan.error:
            self.lbl_estado.configure(text="")
        elif not plan.cambios:
            self.lbl_estado.configure(text="No hay nada que cambiar con estos datos.")
        else:
            self.lbl_estado.configure(text=plan.resumen)

    # ───────────── aplicar ─────────────
    def _aplicar(self):
        plan = self.plan
        if not plan or not plan.aplicable:
            return
        if self.cfg["destructiva"] and not mostrar_pregunta(
                self.cfg["titulo"], f"{plan.resumen}\n\nEsta acción no se puede deshacer. ¿Continuar?", master=self):
            return

        self.btn_aplicar.configure(state="disabled", text="Aplicando…")
        self.update_idletasks()
        try:
            resultado = ops.aplicar(plan)
        except ops.ErrorOperacion as e:
            self.btn_aplicar.configure(state="normal", text=self.cfg["boton"])
            mostrar_error("No se aplicó ningún cambio", str(e), master=self)
            return

        if self.on_success_callback:
            self.on_success_callback()
        (mostrar_advertencia if resultado.parcial else mostrar_exito)(resultado.titulo, resultado.mensaje, master=self)
        self.destroy()