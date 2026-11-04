import customtkinter as ctk
from tkinter import filedialog
from utilerias import database as db
from utilerias.paleta_colores import colores, fuentes
from utilerias.messagebox_variados import mostrar_error, mostrar_exito, mostrar_advertencia
from utilerias.importador_horarios import procesar_excel_horarios

class VentanaImportarHorarios(ctk.CTkToplevel):
    def __init__(self, parent=None, on_success_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.on_success_callback = on_success_callback
        self.ruta_archivo = None

        self.title("Importar Horarios Docentes")
        self.geometry("520x350")
        self.configure(fg_color=colores.BG_VENTANA)
        self.resizable(False, False)
        
        self.focus()
        self.grab_set()
        self._construir_interfaz()

    def _construir_interfaz(self):
        main_frame = ctk.CTkFrame(self, fg_color=colores.BG_PANEL, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            main_frame, text="Importar Horarios de Profesores (.xlsx)", 
            font=fuentes.titulo(size=16), text_color=colores.TEXTO_PRIMARIO
        ).pack(anchor="w", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            main_frame, text="Selecciona el archivo Excel. El sistema extraerá de forma automática la hora de entrada y salida correspondiente de cada docente por día.", 
            font=fuentes.cuerpo(size=12), text_color=colores.TEXTO_SECUNDARIO, wraplength=440, justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 15))

        self.btn_archivo = ctk.CTkButton(
            main_frame, text="📁 Seleccionar Archivo Excel", command=self.seleccionar_archivo,
            height=40, font=fuentes.boton(size=13), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER
        )
        self.btn_archivo.pack(fill="x", padx=20, pady=10)

        self.lbl_path = ctk.CTkLabel(main_frame, text="Ningún archivo seleccionado", font=fuentes.pequena(size=11), text_color=colores.TEXTO_TENUE)
        self.lbl_path.pack(anchor="w", padx=20, pady=(0, 20))

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(10, 20))
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_frame, text="Cancelar", command=self.destroy, height=38,
            font=fuentes.boton(size=12), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))

        ctk.CTkButton(
            btn_frame, text="Procesar e Importar", command=self.ejecutar_importacion, height=38,
            font=fuentes.boton(size=12), fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER
        ).grid(row=0, column=1, sticky="ew", padx=(5, 0))

    def seleccionar_archivo(self):
        archivo = filedialog.askopenfilename(title="Seleccionar Horarios", filetypes=[("Archivos Excel", "*.xlsx")], parent=self)
        if archivo:
            self.ruta_archivo = archivo
            self.lbl_path.configure(text=archivo.split("/")[-1], text_color=colores.TEXTO_PRIMARIO)

    def ejecutar_importacion(self):
        if not self.ruta_archivo:
            mostrar_advertencia("Atención", "Por favor selecciona un archivo Excel primero.", master=self)
            return

        try:
            from utilerias.importador_horarios import procesar_excel_horarios, encontrar_coincidencia_profesor
            
            datos_importados = procesar_excel_horarios(self.ruta_archivo)
            profesores_bd = db.obtener_profesores()
            
            importados_count = 0
            for item in datos_importados:
                nombre_excel = item['profesor']
                
                # Búsqueda inteligente por tokens independiente del orden
                id_profesor = encontrar_coincidencia_profesor(nombre_excel, profesores_bd)
                
                if id_profesor:
                    for dia_num, bloques in item['horarios'].items():
                        for entrada, salida in bloques:
                            db.agregar_horario(id_profesor, dia_num, entrada, salida)
                    importados_count += 1

            mostrar_exito("Importación Completa", f"Se importaron correctamente los horarios para {importados_count} docente(s).", master=self)
            if self.on_success_callback:
                self.on_success_callback()
            self.destroy()

        except Exception as e:
            mostrar_error("Error de Importación", f"Ocurrió un error al procesar el archivo:\n{e}", master=self)