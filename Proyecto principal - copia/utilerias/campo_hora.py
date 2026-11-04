"""Máscara de hora militar (HH:MM) para cualquier CTkEntry: se escribe 0700 y queda 07:00."""


def _validar_tecla(P, S, d):
    """Solo deja teclear dígitos y ':' y un máximo de 4 dígitos."""
    if d == '1':
        if len(S) == 1 and not S.isdigit():
            return False
        if len(S) > 1 and not all(c.isdigit() or c == ':' for c in S):
            return False
        if len("".join(c for c in P if c.isdigit())) > 4:
            return False
    return True


def aplicar_formato_hora(entry):
    entry.configure(validate="key", validatecommand=(entry.register(_validar_tecla), '%P', '%S', '%d'))

    def reemplazar(texto):
        entry.configure(validate="none")
        entry.delete(0, "end")
        entry.insert(0, texto)
        entry.configure(validate="key")

    def al_soltar_tecla(event):
        if event.keysym in ("BackSpace", "Delete"):
            texto = entry.get()
            if texto.endswith(":"):
                reemplazar(texto[:-1])
            return
        if event.keysym in ("Left", "Right", "Up", "Down", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return

        texto_actual = entry.get()
        digitos = "".join(c for c in texto_actual if c.isdigit())[:4]
        if not digitos:
            return

        if len(digitos) >= 2 and int(digitos[:2]) > 23:
            digitos = "23" + digitos[2:]
        if len(digitos) == 3 and int(digitos[2]) > 5:          # decena de minutos: 0-5
            digitos = digitos[:2] + "5"
        elif len(digitos) == 4 and int(digitos[2:4]) > 59:
            digitos = digitos[:2] + "59"

        nuevo = digitos if len(digitos) <= 2 else f"{digitos[:2]}:{digitos[2:]}"
        if texto_actual != nuevo:
            reemplazar(nuevo)

    entry.bind("<KeyRelease>", al_soltar_tecla)