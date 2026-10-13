from CTkMessagebox import CTkMessagebox

def mostrar_exito(titulo, mensaje, master=None):
    return CTkMessagebox(master=master, title=titulo, message=mensaje, icon="check", option_1="Aceptar").get()

def mostrar_advertencia(titulo, mensaje, master=None):
    return CTkMessagebox(master=master, title=titulo, message=mensaje, icon="warning", option_1="Entendido").get()

def mostrar_error(titulo, mensaje, master=None):
    return CTkMessagebox(master=master, title=titulo, message=mensaje, icon="cancel", option_1="Aceptar").get()

def mostrar_pregunta(titulo, mensaje, master=None):
    msg = CTkMessagebox(master=master, title=titulo, message=mensaje, icon="question", option_1="Cancelar", option_2="Sí")
    respuesta = msg.get()
    return respuesta == "Sí"