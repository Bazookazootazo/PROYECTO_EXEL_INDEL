from CTkMessagebox import CTkMessagebox

def _centrar_y_mostrar(msg_box):
    """Fuerza el centrado y ajuste visual óptimo del CTkMessagebox"""
    try:
        msg_box.update_idletasks()
        width = msg_box.winfo_width()
        height = msg_box.winfo_height()
        screen_width = msg_box.winfo_screenwidth()
        screen_height = msg_box.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        msg_box.geometry(f"+{x}+{y}")
    except Exception:
        pass

def mostrar_exito(titulo, mensaje, master=None):
    msg = CTkMessagebox(
        master=master, 
        title=titulo, 
        message=mensaje, 
        icon="check", 
        option_1="Aceptar",
        corner_radius=12
    )
    _centrar_y_mostrar(msg)
    return msg.get()

def mostrar_advertencia(titulo, mensaje, master=None):
    msg = CTkMessagebox(
        master=master, 
        title=titulo, 
        message=mensaje, 
        icon="warning", 
        option_1="Entendido",
        corner_radius=12
    )
    _centrar_y_mostrar(msg)
    return msg.get()

def mostrar_error(titulo, mensaje, master=None):
    msg = CTkMessagebox(
        master=master, 
        title=titulo, 
        message=mensaje, 
        icon="cancel", 
        option_1="Aceptar",
        corner_radius=12
    )
    _centrar_y_mostrar(msg)
    return msg.get()

def mostrar_pregunta(titulo, mensaje, master=None):
    msg = CTkMessagebox(
        master=master, 
        title=titulo, 
        message=mensaje, 
        icon="question", 
        option_1="Cancelar", 
        option_2="Sí",
        corner_radius=12
    )
    _centrar_y_mostrar(msg)
    respuesta = msg.get()
    return respuesta == "Sí"