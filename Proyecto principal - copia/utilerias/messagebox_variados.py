from CTkMessagebox import CTkMessagebox

def _centrar_y_mostrar(msg_box, master=None):
    """Centra el CTkMessagebox de forma precisa respecto a la ventana activa"""
    try:
        msg_box.update_idletasks()
        w = msg_box.winfo_width()
        h = msg_box.winfo_height()
        
        if master and master.winfo_exists():
            master.update_idletasks()
            mw = master.winfo_width()
            mh = master.winfo_height()
            mx = master.winfo_rootx()
            my = master.winfo_rooty()
            
            # Si la ventana padre está maximizada o en pantalla completa, centrar en su área visible
            x = mx + (mw - w) // 2
            y = my + (mh - h) // 2
        else:
            sw = msg_box.winfo_screenwidth()
            sh = msg_box.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2
            
        msg_box.geometry(f"+{max(0, x)}+{max(0, y)}")
        msg_box.lift()
        msg_box.focus_force()
    except Exception:
        pass

def mostrar_exito(titulo, mensaje, master=None):
    msg = CTkMessagebox(master=master, title=titulo, message=mensaje, icon="check", option_1="Aceptar", corner_radius=12)
    _centrar_y_mostrar(msg, master)
    return msg.get()

def mostrar_advertencia(titulo, mensaje, master=None):
    msg = CTkMessagebox(master=master, title=titulo, message=mensaje, icon="warning", option_1="Entendido", corner_radius=12)
    _centrar_y_mostrar(msg, master)
    return msg.get()

def mostrar_error(titulo, mensaje, master=None):
    msg = CTkMessagebox(master=master, title=titulo, message=mensaje, icon="cancel", option_1="Aceptar", corner_radius=12)
    _centrar_y_mostrar(msg, master)
    return msg.get()

def mostrar_pregunta(titulo, mensaje, master=None):
    msg = CTkMessagebox(master=master, title=titulo, message=mensaje, icon="question", option_1="Cancelar", option_2="Sí", corner_radius=12)
    _centrar_y_mostrar(msg, master)
    return msg.get() == "Sí"