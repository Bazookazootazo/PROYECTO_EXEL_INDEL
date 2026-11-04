import pandas as pd
import re

def procesar_excel_horarios(ruta_archivo):
    """
    Procesa archivos Excel institucionales de horarios, propagando celdas combinadas 
    verticalmente (ffill) para capturar con absoluta precisión los bloques que abarcan 
    múltiples filas (materias de varias horas).
    """
    xls = pd.ExcelFile(ruta_archivo)
    resultados = []
    
    dias_map = {
        'lunes': 1, 'martes': 2, 'miércoles': 3, 'miercoles': 3,
        'jueves': 4, 'viernes': 5
    }
    
    time_pattern_dash = re.compile(r'^(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})$')
    time_pattern_spaces = re.compile(r'^(\d{1,2}:\d{2})\s+(\d{1,2}:\d{2})$')
    text_time_pattern = re.compile(r'(\d{1,2}:\d{2})\s*(?:a|-)\s*(\d{1,2}:\d{2})')
    time_hour_pattern = re.compile(r'^\d{1,2}:\d{2}$')

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        
        # 1. Extraer nombre del profesor
        profesor_nombre = None
        for r_idx, row in df.iterrows():
            if r_idx > 15: 
                break
            vals = [str(v).strip() for v in row.values if pd.notna(v)]
            for i, v in enumerate(vals):
                if 'profesor' in v.lower() and i + 1 < len(vals):
                    val_s = vals[i+1]
                    if val_s.lower() not in ['nombre', 'nan', '']:
                        profesor_nombre = val_s
                        break
            if profesor_nombre: 
                break
        
        if not profesor_nombre or profesor_nombre.lower() == 'nombre':
            continue

        # 2. Encontrar columnas de días y filas con horas de la cuadrícula
        day_col_indices = {}
        time_rows_data = []
        
        for r_idx, row in df.iterrows():
            for c_idx, val in enumerate(row):
                val_str = str(val).strip().lower()
                if val_str in dias_map:
                    day_col_indices[dias_map[val_str]] = c_idx
            
            val_0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
            match_dash = time_pattern_dash.match(val_0)
            match_spaces = time_pattern_spaces.match(val_0)
            
            if match_dash:
                time_rows_data.append((r_idx, match_dash.group(1), match_dash.group(2)))
            elif match_spaces:
                time_rows_data.append((r_idx, match_spaces.group(1), match_spaces.group(2)))
            else:
                val_1 = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
                if time_hour_pattern.match(val_0) and time_hour_pattern.match(val_1):
                    time_rows_data.append((r_idx, val_0, val_1))
                else:
                    time_rows_data.append((r_idx, None, None))

        # Propagar verticalmente las celdas combinadas de las columnas de días para que 
        # las materias que ocupan múltiples filas abarquen todo su rango real.
        df_dias_llenados = df.copy()
        for c_idx in day_col_indices.values():
            df_dias_llenados[c_idx] = df_dias_llenados[c_idx].ffill()

        # 3. Recopilar y unificar la jornada real por día
        horarios_por_dia = {}
        
        for day_num, c_idx in day_col_indices.items():
            active_times = []
            for r_idx, t_ini, t_fin in time_rows_data:
                if c_idx < len(df_dias_llenados.columns):
                    cell_val = df_dias_llenados.iloc[r_idx, c_idx]
                    if pd.notna(cell_val) and str(cell_val).strip() != '':
                        cell_str = str(cell_val)
                        
                        matches_texto = text_time_pattern.findall(cell_str)
                        if matches_texto:
                            for m_ini, m_fin in matches_texto:
                                active_times.append((m_ini, m_fin))
                        elif t_ini and t_fin:
                            active_times.append((t_ini, t_fin))
            
            if active_times:
                def t_minutos(t):
                    try:
                        h, m = map(int, t.split(':'))
                        return h * 60 + m
                    except:
                        return 0
                
                active_times.sort(key=lambda x: t_minutos(x[0]))
                
                # Unificar bloques contiguos o con huecos de hasta 120 minutos (jornada continua)
                blocks = []
                curr_start, curr_end = active_times[0]
                
                for next_start, next_end in active_times[1:]:
                    gap = t_minutos(next_start) - t_minutos(curr_end)
                    if gap <= 120:
                        if t_minutos(next_end) > t_minutos(curr_end):
                            curr_end = next_end
                    else:
                        blocks.append((curr_start, curr_end))
                        curr_start, curr_end = next_start, next_end
                blocks.append((curr_start, curr_end))
                
                horarios_por_dia[day_num] = blocks

        if horarios_por_dia:
            resultados.append({
                'profesor': profesor_nombre.strip(),
                'horarios': horarios_por_dia
            })
        
    return resultados


def encontrar_coincidencia_profesor(nombre_excel, profesores_bd):
    """Compara nombres por tokens ignorando acentos y títulos académicos."""
    titulos = {'m.s.c.', 'm.c.', 'ing.', 'lic.', 'm.a.', 'dr.', 'prof.', 'mtra.', 'mtro.'}
    
    def extraer_tokens(nombre):
        if not nombre:
            return set()
        limpio = nombre.lower()
        for a, b in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u')]:
            limpio = limpio.replace(a, b)
        palabras = [p.strip() for p in limpio.split() if p.strip()]
        return {p for p in palabras if p not in titulos}

    tokens_excel = extraer_tokens(nombre_excel)
    if not tokens_excel:
        return None

    mejor_id = None
    max_coincidencias = 0

    for prof in profesores_bd:
        id_p = prof.get('id_profesor') or prof.get('id')
        nombre_db = prof.get('nombre', '')
        tokens_db = extraer_tokens(nombre_db)
        
        if not tokens_db:
            continue

        coincidencias = len(tokens_excel.intersection(tokens_db))
        min_requerido = min(2, len(tokens_excel), len(tokens_db))
        if coincidencias >= min_requerido and coincidencias > max_coincidencias:
            max_coincidencias = coincidencias
            mejor_id = id_p

    return mejor_id