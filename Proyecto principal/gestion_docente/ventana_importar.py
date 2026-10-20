
from tkinter import filedialog
import customtkinter as ctk
from gestion_docente.importador import Importacion
from utilerias.messagebox_variados import mostrar_error, mostrar_exito, mostrar_pregunta
from utilerias.paleta_colores import colores, fuentes

TIPOS_ARCHIVO = [("Excel y CSV", "*.xlsx *.xls *.csv"), ("Todos los archivos", "*.*")]
NINGUNA = "— ninguna —"
CAMPOS_UI = {"nombre": "Nombre del docente (obligatorio)", "area": "Área", "tipo": "Tipo", "turno": "Turno",
             "dia": "Día", "entrada": "Entrada", "salida": "Salida", "horario": "Horario (07:00-12:00)"}

def VentanaImportar(parent, on_success_callback=None):
    """Punto de entrada: el usuario elige su archivo tal como lo tiene y pasa directo a la revisión."""
    ruta = filedialog.askopenfilename(parent=parent, title="Selecciona el archivo a importar", filetypes=TIPOS_ARCHIVO)
    if not ruta:
        return None
    try:
        importacion = Importacion(ruta)
    except Exception as e:
        mostrar_error("No se pudo leer el archivo", str(e), master=parent)
        return None
    return VentanaRevision(parent, importacion, on_success_callback=on_success_callback)


class VentanaRevision(ctk.CTkToplevel):
    """Muestra cómo se interpretó el archivo y deja confirmar antes de guardar nada."""

    def __init__(self, parent, importacion, on_success_callback=None):
        super().__init__(parent)
        self.importacion = importacion
        self.on_success_callback = on_success_callback

        self.title(f"Revisar importación — {importacion.archivo}")
        self.geometry("820x680")
        self.minsize(700, 500)
        self.configure(fg_color=colores.BG_VENTANA)
        self.grab_set()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

        # Configuración de grilla principal responsiva
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._construir_encabezado()
        
        # Contenedor desplazable con expansión fluida
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 0))
        self.scroll.grid_columnconfigure(0, weight=1)
        
        self._construir_pie()
        self.refrescar()

    # ---------- estructura fija ----------
    def _construir_encabezado(self):
        top = ctk.CTkFrame(self, fg_color=colores.BG_PANEL, corner_radius=14, border_width=1, border_color=colores.BORDE)
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="📄", font=fuentes.seccion(size=22)).grid(row=0, column=0, rowspan=2, padx=(16, 10), pady=14)
        ctk.CTkLabel(top, text=self.importacion.archivo, font=fuentes.seccion(size=15), text_color=colores.TEXTO_PRIMARIO, anchor="w").grid(row=0, column=1, sticky="w", pady=(14, 0))
        
        self.lbl_resumen_archivo = ctk.CTkLabel(top, text="", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO, anchor="w")
        self.lbl_resumen_archivo.grid(row=1, column=1, sticky="w", pady=(0, 14))

        if len(self.importacion.hojas) > 1:
            self.cmb_hoja = ctk.CTkOptionMenu(top, values=self.importacion.hojas, width=160, command=self._cambiar_hoja,
                                             fg_color=colores.BG_ENTRADA, button_color=colores.ACENTO, button_hover_color=colores.ACENTO_HOVER)
            self.cmb_hoja.set(self.importacion.tabla.hoja)
            self.cmb_hoja.grid(row=0, column=2, rowspan=2, padx=16)

    def _construir_pie(self):
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.grid(row=2, column=0, sticky="ew", padx=20, pady=16)
        pie.grid_columnconfigure(0, weight=1)

        self.lbl_estado = ctk.CTkLabel(pie, text="", font=fuentes.pequena(size=11), text_color=colores.ADVERTENCIA, anchor="w")
        self.lbl_estado.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(pie, text="Cancelar", width=110, height=38, corner_radius=10, font=fuentes.boton(size=13),
                      fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER, command=self._cancelar).grid(row=0, column=1, padx=(0, 8))
        
        self.btn_aplicar = ctk.CTkButton(pie, text="Aplicar cambios", width=160, height=38, corner_radius=10, font=fuentes.boton(size=13),
                                         fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER, command=self._aplicar)
        self.btn_aplicar.grid(row=0, column=2)

    # ---------- cuerpo dinámico ----------
    def refrescar(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        imp = self.importacion
        sin_enc = " · sin encabezados (columnas identificadas por su contenido)" if imp.tabla.sin_encabezado else ""
        self.lbl_resumen_archivo.configure(
            text=f"Hoja «{imp.tabla.hoja}» · {len(imp._filas)} fila(s) de datos · interpretada como {imp.descripcion}{sin_enc}"
        )

        self._seccion_mapeo()
        self._seccion_modo()

        self.resultado = imp.analizar()
        if self.resultado.decisiones:
            self._seccion_decisiones()
        self._seccion_resumen()
        if self.resultado.omitidas:
            self._seccion_avisos()

        listo = not self.resultado.problema
        self.btn_aplicar.configure(state="normal" if listo and self.resultado.cambios else "disabled")
        
        if self.resultado.problema:
            self.lbl_estado.configure(text=f"⚠  {self.resultado.problema}")
        elif not self.resultado.cambios:
            self.lbl_estado.configure(text="No hay cambios que aplicar: todo coincide con lo que ya está guardado.")
        else:
            self.lbl_estado.configure(text="")

    def _tarjeta(self, titulo, subtitulo=None):
        card = ctk.CTkFrame(self.scroll, corner_radius=12, fg_color=colores.BG_PANEL_ALT, border_width=1, border_color=colores.BORDE_SUAVE)
        card.pack(fill="x", pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(card, text=titulo, font=fuentes.boton(size=13), text_color=colores.TEXTO_PRIMARIO, anchor="w").pack(fill="x", padx=16, pady=(14, 2 if subtitulo else 12))
        if subtitulo:
            ctk.CTkLabel(card, text=subtitulo, font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO, anchor="w", justify="left").pack(fill="x", padx=16, pady=(0, 12))
        return card

    def _seccion_mapeo(self):
        imp = self.importacion
        subtitulo = ("Tu archivo no trae encabezados: identifiqué cada columna por su contenido. Confirma que sea correcto."
                     if imp.tabla.sin_encabezado else "Confirma que cada dato esté en la columna correcta; puedes cambiarla aquí.")
        card = self._tarjeta("⚙️  Asignación de Columnas", subtitulo)

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 14))
        self._etq_cols = [imp.etiqueta_columna(i) for i in range(len(imp.columnas))]
        opciones = [NINGUNA] + self._etq_cols
        campos = ["nombre", "area", "tipo", "turno"] + ([] if imp.ancho else ["dia", "entrada", "salida", "horario"])
        for n, campo in enumerate(campos):
            sub = ctk.CTkFrame(grid, fg_color="transparent")
            sub.grid(row=n // 4, column=n % 4, sticky="w", padx=(0, 12), pady=4)
            ctk.CTkLabel(sub, text=CAMPOS_UI[campo], font=fuentes.pequena(size=10), text_color=colores.TEXTO_TENUE).pack(anchor="w")
            cmb = ctk.CTkOptionMenu(sub, values=opciones, width=170, height=30, font=fuentes.pequena(size=11),
                                    fg_color=colores.BG_ENTRADA, button_color=colores.ACENTO, button_hover_color=colores.ACENTO_HOVER,
                                    command=lambda val, c=campo: self._remapear(c, val))
            cmb.set(self._etq_cols[imp.mapeo[campo]] if campo in imp.mapeo else NINGUNA)
            cmb.pack(anchor="w")

        if imp.ancho:
            ctk.CTkLabel(card, text=f"Estructura detectada: Formato matricial por columnas ({imp.descripcion.split('(')[1][:-1]}).",
                        font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO, anchor="w").pack(fill="x", padx=16, pady=(0, 14))

    def _remapear(self, campo, valor):
        indice = None if valor == NINGUNA else self._etq_cols.index(valor)
        self.importacion.mapear(campo, indice)
        self.refrescar()

    def _cambiar_hoja(self, hoja):
        self.importacion.usar_hoja(hoja)
        self.refrescar()

    def _seccion_modo(self):
        imp = self.importacion
        edita_datos = any(c in imp.mapeo for c in ("area", "tipo", "turno"))
        if not (edita_datos or imp.hay_horarios):
            return
        card = self._tarjeta("🔄  Docentes que ya existen", "Elige qué hacer cuando el archivo menciona a un docente ya registrado:")
        cont = ctk.CTkFrame(card, fg_color="transparent")
        cont.pack(fill="x", padx=16, pady=(0, 14))

        if edita_datos:
            self.var_datos = ctk.BooleanVar(value=imp.actualizar_datos)
            ctk.CTkCheckBox(cont, text="Actualizar su Área, Tipo y Turno si el archivo trae un dato distinto", variable=self.var_datos,
                            font=fuentes.boton(size=12), text_color=colores.TEXTO_PRIMARIO, fg_color=colores.ACENTO,
                            command=self._cambiar_datos).pack(anchor="w", pady=(2, 8))
        if imp.hay_horarios:
            ctk.CTkLabel(cont, text="Sus horarios:", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO).pack(anchor="w")
            self.var_modo = ctk.StringVar(value=imp.modo)
            for valor, texto in Importacion.MODOS.items():
                peligro = valor == "reemplazar"
                ctk.CTkRadioButton(
                    cont, text=("⚠️ " if peligro else "") + texto, variable=self.var_modo, value=valor, font=fuentes.boton(size=12),
                    text_color=colores.ADVERTENCIA if peligro else colores.TEXTO_PRIMARIO,
                    fg_color=colores.ADVERTENCIA if peligro else colores.ACENTO,
                    hover_color=colores.ADVERTENCIA_HOVER if peligro else colores.ACENTO_HOVER, command=self._cambiar_modo,
                ).pack(anchor="w", pady=2)

    def _cambiar_datos(self):
        self.importacion.actualizar_datos = self.var_datos.get()
        self.refrescar()

    def _cambiar_modo(self):
        self.importacion.modo = self.var_modo.get()
        self.refrescar()

    def _seccion_decisiones(self):
        card = self._tarjeta("⚠️  Validación de Registros Ambiguos", "No estoy seguro de estos datos. Cada uno ya trae mi sugerencia: confírmala o cámbiala.")
        
        for dec in self.resultado.decisiones:
            fila = ctk.CTkFrame(card, fg_color=colores.BG_SUPERFICIE, corner_radius=8)
            fila.pack(fill="x", padx=16, pady=(0, 10))
            
            ctk.CTkLabel(fila, text=dec.titulo, font=fuentes.boton(size=12), text_color=colores.TEXTO_PRIMARIO, anchor="w").pack(fill="x", padx=12, pady=(10, 1))
            
            lbl_detalle = ctk.CTkLabel(fila, text=dec.detalle, font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO, anchor="w", justify="left")
            lbl_detalle.pack(fill="x", padx=12)
            fila.bind("<Configure>", lambda e, l=lbl_detalle: l.configure(wraplength=e.width - 24))

            cmb = ctk.CTkOptionMenu(fila, values=[t for _, t in dec.opciones], width=260, height=30, font=fuentes.pequena(size=11),
                                    fg_color=colores.BG_ENTRADA, button_color=colores.ACENTO, button_hover_color=colores.ACENTO_HOVER,
                                    command=lambda val, k=dec.clave, opts=dec.opciones: self._decidir(k, val, opts))
            cmb.set(next(t for v, t in dec.opciones if v == dec.valor))
            cmb.pack(anchor="w", padx=12, pady=(6, 10))

    def _decidir(self, clave, etiqueta, opciones):
        self.importacion.decisiones[clave] = next(v for v, t in opciones if t == etiqueta)
        self.refrescar()

    def _seccion_resumen(self):
        r = self.resultado
        card = self._tarjeta("📊  Resumen de Impacto Operativo")
        cont = ctk.CTkFrame(card, fg_color="transparent")
        cont.pack(fill="x", padx=16, pady=(0, 14))

        def linea(icono, texto, color=colores.TEXTO_PRIMARIO):
            f = ctk.CTkFrame(cont, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=icono, font=fuentes.cuerpo(size=13), width=22).pack(side="left")
            ctk.CTkLabel(f, text=texto, font=fuentes.cuerpo(size=12), text_color=color, anchor="w").pack(side="left")

        if r.nuevos: linea("🆕", f"{r.nuevos} registro(s) de docente(s) nuevo(s)")
        if r.actualizados: linea("🔄", f"{r.actualizados} docente(s) con cambios de Área, Tipo o Turno")
        if r.turnos_nuevos: linea("🗓", f"{r.turnos_nuevos} nuevo(s) turno(s) por incorporar")
        if r.turnos_quitados: linea("➖", f"{r.turnos_quitados} turno(s) programados para baja (ausentes en archivo)", colores.PELIGRO)
        if r.turnos_ausentes and self.importacion.modo == "agregar":
            linea("ℹ️", f"{r.turnos_ausentes} turno(s) guardados no aparecen en el archivo (se conservan)", colores.TEXTO_SECUNDARIO)
        if r.turnos_iguales: linea("✅", f"{r.turnos_iguales} turno(s) sin modificaciones (coincidentes)")
        if r.omitidos: linea("⏭", f"{r.omitidos} registro(s) omitidos por falta de información obligatoria", colores.ADVERTENCIA)
        if not any((r.nuevos, r.actualizados, r.turnos_nuevos, r.turnos_quitados, r.turnos_iguales, r.omitidos)):
            linea("💤", "No se detectaron cambios ni registros procesables en el archivo.", colores.TEXTO_SECUNDARIO)
        if r.docentes:
            btn = ctk.CTkButton(cont, text="Ver detalle por docente ▾", width=190, height=28, font=fuentes.pequena(size=11),
                                fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER)
            btn.configure(command=lambda: self._alternar_detalle(r.docentes, cont, btn))
            btn.pack(anchor="w", pady=(8, 0))

    def _alternar_detalle(self, detalle, cont, boton):
        if getattr(self, "_detalle_frame", None) and self._detalle_frame.winfo_exists():
            self._detalle_frame.destroy()
            boton.configure(text="Ver detalle por docente ▾")
            return
            
        boton.configure(text="Ocultar detalle ▴")
        self._detalle_frame = ctk.CTkFrame(cont, fg_color="transparent")
        self._detalle_frame.pack(fill="x", pady=(6, 0))
        
        iconos = {"nuevo": "🆕", "actualiza": "🔄", "omitido": "⏭", "existente": "🗓"}
        relevantes = [d for d in detalle if d.estado != "existente" or d.turnos_nuevos or d.turnos_quitar or d.avisos]
        for d in relevantes[:150]:
            partes = [f"{iconos[d.estado]} {d.nombre}"]
            if d.cambios: partes.append(" · ".join(d.cambios))
            if d.turnos_nuevos: partes.append(f"+{len(d.turnos_nuevos)} turno(s)")
            if d.turnos_quitar: partes.append(f"-{len(d.turnos_quitar)} turno(s)")
            if d.nota: partes.append(d.nota)
            for aviso in d.avisos: partes.append(f"⚠ {aviso}")
            
            lbl_det = ctk.CTkLabel(self._detalle_frame, text="   " + "  —  ".join(partes), font=fuentes.pequena(size=11),
                                   text_color=colores.TEXTO_SECUNDARIO, anchor="w", justify="left")
            lbl_det.pack(fill="x", pady=1)
            # Enlace dinámico para adaptabilidad de ancho en el detalle
            self._detalle_frame.bind("<Configure>", lambda e, l=lbl_det: l.configure(wraplength=e.width - 20))
        if len(relevantes) > 150:
            ctk.CTkLabel(self._detalle_frame, text=f"… y {len(relevantes) - 150} más.", font=fuentes.pequena(size=11), text_color=colores.TEXTO_TENUE).pack(anchor="w")

    def _seccion_avisos(self):
        card = self._tarjeta(f"⚠️  {len(self.resultado.omitidas)} fila(s) con algo que no pude leer", "No afectan al resto del archivo.")
        cont = ctk.CTkFrame(card, fg_color="transparent")
        cont.pack(fill="x", padx=16, pady=(0, 14))
        
        for msg in self.resultado.omitidas[:12]:
            lbl_aviso = ctk.CTkLabel(cont, text=f"• {msg}", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO, anchor="w", justify="left")
            lbl_aviso.pack(fill="x", pady=1)
            cont.bind("<Configure>", lambda e, l=lbl_aviso: l.configure(wraplength=e.width - 32))
            
        if len(self.resultado.omitidas) > 12:
            ctk.CTkLabel(cont, text=f"… y {len(self.resultado.omitidas) - 12} más.", font=fuentes.pequena(size=11), text_color=colores.TEXTO_TENUE).pack(anchor="w")

    # ---------- acciones ----------
    def _cancelar(self):
        self.destroy()

    def _aplicar(self):
        r = self.resultado
        pregunta = f"Se aplicarán {r.cambios} cambio(s) a la base de datos."
        if r.turnos_quitados:
            pregunta += f"\n{r.turnos_quitados} turno(s) existentes se eliminarán."
            
        if not mostrar_pregunta("Confirmar importación", pregunta + "\n\n¿Continuar?", master=self):
            return
            
        try:
            # Feedback visual de carga en el botón
            self.btn_aplicar.configure(text="Guardando...", state="disabled")
            self.update_idletasks()
            
            mensaje = self.importacion.aplicar(r)
            mostrar_exito("Importación completada", mensaje, master=self)
            
            if self.on_success_callback:
                self.on_success_callback()
            self._cancelar()
            
        except Exception as e:
            self.btn_aplicar.configure(text="Aplicar cambios", state="normal")
            mostrar_error("No se pudo importar", f"No se aplicó ningún cambio (se revirtió todo):\n{e}", master=self)