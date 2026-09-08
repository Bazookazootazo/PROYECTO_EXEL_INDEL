# a lo largo del código se importan las librerías necesarias para la aplicación
# estas tienen un alias para facilitar su uso en el código
import os
import customtkinter as ctk
import tkinter as tk 
from tkinter import filedialog, messagebox
import pandas as pd

# Configuración de la apariencia de la aplicación
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

# Crear la ventana principal de la aplicación 
app = ctk.CTk()
app.title("Procesar documentos")
app.geometry("600x600")

ruta_archivo = []  # Variable global para almacenar la ruta del archivo seleccionado

# Función para subir un archivo
def procesar_archivo():
    if not ruta_archivo:
        messagebox.showwarning("Advertencia", "No has subido ningún archivo.")
        return
    
    lista_archivos=[]
    
    try:
        # Leer el archivo seleccionado según su extensión
        for ruta in ruta_archivo:
            _, extension = os.path.splitext(ruta)
        
            if ruta.endswith('.csv'):
                df=pd.read_csv(ruta, sep=';', encoding='utf-8-sig', dtype=str)
            else:
                df=pd.read_excel(ruta)

            df=df.iloc[:, [0, 2, 3]]# indico a pandas que solo quiero conservar esas columnas 
            df.columns = ['fecha', 'codigo', 'nombre']
            lista_archivos.append(df)

        df_final=pd.concat(lista_archivos, ignore_index=True)
        df_final=df_final.drop_duplicates()
        print(df_final.head())
       
    except Exception as e:
        tk.messagebox.showerror("Error", f"No se pudo subir el archivo: {e}")

    ruta_guardado=tk.filedialog.asksaveasfilename(title="Guardar archivo como...", defaultextension=".csv", filetypes=[("Archivos CSV", "*.csv"),("Archivos Excel", "*.xlsx *.xls")])
    if ruta_guardado:
        try:
            if ruta_guardado.endswith('.csv'):
                 with open(ruta_guardado, 'w', encoding='utf-8-sig', newline='') as f:
                    f.write('sep=;\n')
                    df_final.to_csv(f, index=False, sep=';')
            else:
                df_final.to_excel(ruta_guardado, index=False)
        except Exception as e:
            tk.messagebox.showerror("Error", f"No se pudo guardar el archivo: {e}")

btn_subir=ctk.CTkButton(master=app, text="Subir archivo(s)", fg_color="blue", hover_color="darkblue", text_color="white", command=procesar_archivo)
btn_subir.place(relx=0.5, rely=0.5, anchor="center")

#establece el tipo o tipos de archivos que se pueden seleccionar en el cuadro de diálogo de selección de archivos.
def subir_archivo():
    global ruta_archivo
    ruta_nueva=tk.filedialog.askopenfilenames(title="Selecciona los archivos",filetypes=[("Archivos CSV", "*.csv"),("Archivos Excel", "*.xlsx *.xls")])

    if ruta_nueva:
        for ruta in ruta_nueva:
            if ruta not in ruta_archivo:
                ruta_archivo.append(ruta)
        actualizar_lista_archivos()

btn_subirArchivo=ctk.CTkButton(master=app, text="Seleccionar archivo", fg_color="green", hover_color="darkgreen", text_color="white", command=subir_archivo)
btn_subirArchivo.place(relx=0.5, rely=0.4, anchor="center")

#actualiza el contenido del cuadro de texto con la lista de archivos
def actualizar_lista_archivos():
    lista_archivos_subidos.configure(state="normal")
    lista_archivos_subidos.delete("1.0", "end")

    if ruta_archivo:
        lista_limpia=[f"{indice}.{os.path.basename(ruta)}" for indice, ruta in enumerate(ruta_archivo, start=1)]
        texto_limpio="\n".join(lista_limpia)
        lista_archivos_subidos.insert("1.0", texto_limpio)
    else:
        lista_archivos_subidos.insert("1.0", "No hay archivos seleccionados")

    lista_archivos_subidos.configure(state="disabled")

lista_archivos_subidos=ctk.CTkTextbox(master=app, width=380, height=200)
lista_archivos_subidos.place(relx=0.5, rely=0.7, anchor="center")
lista_archivos_subidos.insert("1.0", "No hay archivos seleccionados")
lista_archivos_subidos.configure(state="disabled")

#inicia el bucle principal de la aplicación, es decir el GUI (ventana)
app.mainloop()