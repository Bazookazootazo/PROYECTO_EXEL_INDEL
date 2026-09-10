import customtkinter as ctk
from tkinter import messagebox
import database as db

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VentanaGestionDocentes(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gestión de Personal Docente y Horarios")
        self.geometry("1100x700")
        self.after(10, lambda: self.wm_state('zoomed'))

        self.profesores_cache = []
        self.profesor_seleccionado = None

        # Contenedor Principal
        main_card = ctk.CTkFrame(self, corner_radius=20, border_width=1, border_color="#2B2B2B")
        main_card.pack(fill="both", expand=True, padx=20, pady=20)

        # Encabezado
        header = ctk.CTkFrame(main_card, fg_color="#1E222A", corner_radius=15, height=70)
        header.pack(fill="x", padx=20, pady=(20, 10))
        lbl_titulo = ctk.CTkLabel(header, text="Administración de Docentes y Horarios", font=ctk.CTkFont(size=22, weight="bold"))
        lbl_titulo.pack(side="left", padx=20, pady=15)

        # Panel Split (Izquierda: Profesores | Derecha: Horarios)
        content_frame = ctk.CTkFrame(main_card, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # --- SECCIÓN IZQUIERDA: REGISTRO Y LISTA DE PROFESORES ---
        left_panel = ctk.CTkFrame(content_frame, fg_color="#1A1C23", corner_radius=12, width=450)
        left_panel.pack(side="left", fill="both", padx=(0, 10), pady=5)

        lbl_sec_prof = ctk.CTkLabel(left_panel, text="1. Personal Docente", font=ctk.CTkFont(size=16, weight="bold"), text_color="#3B8ED0")
        lbl_sec_prof.pack(anchor="w", padx=15, pady=(15, 5))

        # Formulario Registrar
        form_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        form_frame.pack(fill="x", padx=15, pady=5)

        self.ent_nombre = ctk.CTkEntry(form_frame, placeholder_text="Nombre del docente...")
        self.ent_nombre.pack(fill="x", pady=4)

        self.ent_area = ctk.CTkEntry(form_frame, placeholder_text="Área / Departamento...")
        self.ent_area.pack(fill="x", pady=4)

        btn_guardar_prof = ctk.CTkButton(form_frame, text="Registrar Profesor", fg_color="#27AE60", hover_color="#1E8449", command=self.guardar_profesor)
        btn_guardar_prof.pack(fill="x", pady=(8, 12))

        # Lista de Profesores
        lbl_lista = ctk.CTkLabel(left_panel, text="Selecciona un profesor para ver/asignar horario:", font=ctk.CTkFont(size=12), text_color="#A0A5B5")
        lbl_lista.pack(anchor="w", padx=15, pady=(5, 2))

        self.scroll_profesores = ctk.CTkScrollableFrame(left_panel, fg_color="#111217")
        self.scroll_profesores.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # --- SECCIÓN DERECHA: ASIGNACIÓN DE HORARIOS ---
        right_panel = ctk.CTkFrame(content_frame, fg_color="#1A1C23", corner_radius=12)
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0), pady=5)

        self.lbl_prof_seleccionado = ctk.CTkLabel(right_panel, text="2. Horario Semanal (Selecciona un docente)", font=ctk.CTkFont(size=16, weight="bold"), text_color="#3B8ED0")
        self.lbl_prof_seleccionado.pack(anchor="w", padx=15, pady=(15, 5))

        # Formulario para Agregar Bloque de Horario
        horario_form = ctk.CTkFrame(right_panel, fg_color="transparent")
        horario_form.pack(fill="x", padx=15, pady=5)

        self.cmb_dia = ctk.CTkOptionMenu(horario_form, values=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        self.cmb_dia.pack(side="left", padx=(0, 5))

        self.ent_entrada = ctk.CTkEntry(horario_form, width=80, placeholder_text="07:00")
        self.ent_entrada.pack(side="left", padx=5)

        self.ent_salida = ctk.CTkEntry(horario_form, width=80, placeholder_text="12:00")
        self.ent_salida.pack(side="left", padx=5)

        btn_add_horario = ctk.CTkButton(horario_form, text="+ Agregar Turno", width=110, fg_color="#1F6AA5", command=self.guardar_horario)
        btn_add_horario.pack(side="left", padx=(5, 0))

        # Tabla/Lista de Horarios Asignados
        self.scroll_horarios = ctk.CTkScrollableFrame(right_panel, fg_color="#111217")
        self.scroll_horarios.pack(fill="both", expand=True, padx=15, pady=15)

        # Cargar datos iniciales
        self.cargar_lista_profesores()

    # --- LÓGICA DE PROFESORES ---

    def cargar_lista_profesores(self):
        for child in self.scroll_profesores.winfo_children():
            child.destroy()

        try:
            self.profesores_cache = db.obtener_profesores()
            for prof in self.profesores_cache:
                btn_item = ctk.CTkButton(
                    self.scroll_profesores,
                    text=f"👤 {prof['nombre']}\n   Área: {prof['area']}",
                    anchor="w",
                    fg_color="#1E222A",
                    hover_color="#2D313E",
                    font=ctk.CTkFont(size=13),
                    command=lambda p=prof: self.seleccionar_profesor(p)
                )
                btn_item.pack(fill="x", pady=4, padx=2)
        except Exception as e:
            messagebox.showerror("Error de Conexión", f"No se pudo conectar a XAMPP/MySQL:\n{e}")

    def guardar_profesor(self):
        nombre = self.ent_nombre.get().strip()
        area = self.ent_area.get().strip()

        if not nombre or not area:
            messagebox.showwarning("Atención", "Ingresa el nombre y el área del profesor.")
            return

        try:
            db.agregar_profesor(nombre, area)
            self.ent_nombre.delete(0, 'end')
            self.ent_area.delete(0, 'end')
            self.cargar_lista_profesores()
            messagebox.showinfo("Éxito", "Profesor registrado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar:\n{e}")

    def seleccionar_profesor(self, profesor):
        self.profesor_seleccionado = profesor
        self.lbl_prof_seleccionado.configure(text=f"2. Horario Semanal de: {profesor['nombre']}")
        self.cargar_horarios_profesor()

    # --- LÓGICA DE HORARIOS ---

    def cargar_horarios_profesor(self):
        for child in self.scroll_horarios.winfo_children():
            child.destroy()

        if not self.profesor_seleccionado:
            return

        dias_dict = {"Lunes": 1, "Martes": 2, "Miércoles": 3, "Jueves": 4, "Viernes": 5}
        horarios = db.obtener_horarios_profesor(self.profesor_seleccionado['id_profesor'])

        if not horarios:
            lbl_empty = ctk.CTkLabel(self.scroll_horarios, text="No hay horarios asignados para este docente.", text_color="#777777")
            lbl_empty.pack(pady=20)
            return

        for h in horarios:
            row = ctk.CTkFrame(self.scroll_horarios, fg_color="#1E222A", height=40)
            row.pack(fill="x", pady=4, padx=2)

            lbl_info = ctk.CTkLabel(row, text=f"📅 {h['nombre_dia']}:   Entrada: {h['hora_entrada']} hrs  ➔  Salida: {h['hora_salida']} hrs", font=ctk.CTkFont(size=13))
            lbl_info.pack(side="left", padx=15, pady=8)

            btn_del = ctk.CTkButton(row, text="Eliminar", width=70, fg_color="#D9534F", hover_color="#A93226", command=lambda hid=h['id_horario']: self.borrar_horario(hid))
            btn_del.pack(side="right", padx=10)

    def guardar_horario(self):
        if not self.profesor_seleccionado:
            messagebox.showwarning("Atención", "Primero selecciona un profesor de la lista.")
            return

        dias_dict = {"Lunes": 1, "Martes": 2, "Miércoles": 3, "Jueves": 4, "Viernes": 5}
        dia_nom = self.cmb_dia.get()
        id_dia = dias_dict[dia_nom]
        entrada = self.ent_entrada.get().strip()
        salida = self.ent_salida.get().strip()

        if not entrada or not salida:
            messagebox.showwarning("Atención", "Ingresa la hora de entrada y salida (Ej: 08:00 y 12:00).")
            return

        try:
            db.agregar_horario(self.profesor_seleccionado['id_profesor'], id_dia, entrada, salida)
            self.ent_entrada.delete(0, 'end')
            self.ent_salida.delete(0, 'end')
            self.cargar_horarios_profesor()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el horario:\n{e}")

    def borrar_horario(self, id_horario):
        try:
            db.eliminar_horario(id_horario)
            self.cargar_horarios_profesor()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar el bloque:\n{e}")

if __name__ == "__main__":
    app = VentanaGestionDocentes()
    app.mainloop()