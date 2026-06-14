import streamlit as st
import pandas as pd
import os

# Configuración de interfaz móvil
st.set_page_config(page_title="Admin Polla 2026", page_icon="⚙️", layout="centered")

EXCEL_FILE = "Polla mundial 2026.xlsx"

if not os.path.exists(EXCEL_FILE):
    st.error(f"No se encontró el archivo '{EXCEL_FILE}' en el directorio actual.")
    st.stop()

# Funciones de carga de datos
@st.cache_data(ttl=10)
def cargar_partidos():
    # Leer la hoja de partidos manteniendo la estructura original
    df = pd.read_excel(EXCEL_FILE, sheet_name="PARTIDOS", header=None)
    return df

def guardar_cambios(df_partidos, df_puntuacion):
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl", mode="w") as writer:
        df_partidos.to_excel(writer, sheet_name="PARTIDOS", index=False, header=False)
        df_puntuacion.to_excel(writer, sheet_name="PUNTUACION", index=False)
    st.cache_data.clear()

# --- PROCESAMIENTO DE LA INFORMACIÓN ---
df_original = cargar_partidos()
df_puntuacion_original = pd.read_excel(EXCEL_FILE, sheet_name="PUNTUACION")

# Extraer la lista de partidos disponibles mapeando las columnas horizontales
lista_partidos = []
# Saltamos de 5 en 5 columnas según la estructura del Excel
for col_idx in range(2, df_original.shape[1] - 11, 5):
    equipo_l = df_original.iloc[0, col_idx]
    equipo_v = df_original.iloc[0, col_idx + 1]
    
    if pd.notna(equipo_l) and pd.notna(equipo_v):
        # Verificar si ya tiene resultado guardado en la Fila 1
        goles_l_actual = df_original.iloc[1, col_idx]
        goles_v_actual = df_original.iloc[1, col_idx + 1]
        
        lista_partidos.append({
            "id": col_idx,
            "texto": f"{equipo_l} vs {equipo_v}",
            "goles_l": int(goles_l_actual) if pd.notna(goles_l_actual) else 0,
            "goles_v": int(goles_v_actual) if pd.notna(goles_v_actual) else 0,
            "jugado": pd.notna(goles_l_actual)
        })

# --- INTERFAZ GRÁFICA ---
st.title("⚙️ Panel de Control Mundial 2026")
st.markdown("Actualiza marcadores oficiales desde tu teléfono. El sistema recalculará los puntos de todos.")

tab1, tab2 = st.tabs(["⚽ Ingresar Marcador", "📊 Tabla de Posiciones"])

with tab1:
    st.subheader("Registrar Resultado Oficial FIFA")
    
    # Selector de partido optimizado para pantallas táctiles
    opciones_partido = {p["id"]: f"{'✅ ' if p['jugado'] else '⏳ '} {p['texto']}" for p in lista_partidos}
    partido_seleccionado_id = st.selectbox("Selecciona el partido finalizado:", opciones_partido.keys(), format_func=lambda x: opciones_partido[x])
    
    # Obtener datos del partido seleccionado
    info_partido = next(p for p in lista_partidos if p["id"] == partido_seleccionado_id)
    
    st.info(f"Marcador actual en el Excel: **{info_partido['goles_l']} - {info_partido['goles_v']}**")
    
    # Campos numéricos de goles
    col1, col2 = st.columns(2)
    with col1:
        nuevos_goles_l = st.number_input(f"Goles {df_original.iloc[0, partido_seleccionado_id]}", min_value=0, max_value=20, value=info_partido["goles_l"], step=1)
    with col2:
        nuevos_goles_v = st.number_input(f"Goles {df_original.iloc[0, partido_seleccionado_id + 1]}", min_value=0, max_value=20, value=info_partido["goles_v"], step=1)
        
    if st.button("💾 Guardar y Recalcular Polla", type="primary"):
        # 1. Actualizar el marcador real en la Fila 1 del DataFrame
        df_original.iloc[1, partido_seleccionado_id] = nuevos_goles_l
        df_original.iloc[1, partido_seleccionado_id + 1] = nuevos_goles_v
        
        # 2. Recalcular los puntos individuales de cada participante
        tabla_puntos_actualizada = {}
        
        for c_idx in range(2, df_original.shape[1] - 11, 5):
            real_l = df_original.iloc[1, c_idx]
            real_v = df_original.iloc[1, c_idx + 1]
            
            # Solo procesar si el partido ya se jugó
            if pd.notna(real_l) and pd.notna(real_v):
                real_l, real_v = int(real_l), int(real_v)
                
                # Evaluar las apuestas de los jugadores de las filas inferiores
                for fila_idx in range(2, df_original.shape[0]):
                    jugador = df_original.iloc[fila_idx, c_idx]
                    if pd.isna(jugador): continue
                    
                    pron_l = df_original.iloc[fila_idx, c_idx + 1]
                    pron_v = df_original.iloc[fila_idx, c_idx + 2]
                    
                    if pd.notna(pron_l) and pd.notna(pron_v):
                        pron_l, pron_v = int(pron_l), int(pron_v)
                        pts_partido = 0
                        
                        # REGLAS RECALCULO:
                        # Marcador Exacto = 5 pts
                        if pron_l == real_l and pron_v == real_v:
                            pts_partido = 5
                        else:
                            # Tendencia = 2 pts
                            t_pron = 1 if pron_l > pron_v else (0 if pron_l == pron_v else -1)
                            t_real = 1 if real_l > real_v else (0 if real_l == real_v else -1)
                            if t_pron == t_real:
                                # Diferencia de goles = +1 pt
                                pts_partido = 3 if (pron_l - pron_v) == (real_l - real_v) else 2
                        
                        # Escribir los puntos en la columna "PUNTOS" correspondiente del jugador
                        df_original.iloc[fila_idx, c_idx + 3] = pts_partido
                        tabla_puntos_actualizada[str(jugador).strip().upper()] = tabla_puntos_actualizada.get(str(jugador).strip().upper(), 0) + pts_partido

        # 3. Sincronizar los nuevos totales con la pestaña 'PUNTUACION'
        for i, row in df_puntuacion_original.iterrows():
            nombre_puntuacion = str(row['NOMBRES']).strip().upper()
            if nombre_puntuacion in tabla_puntos_actualizada:
                df_puntuacion_original.at[i, 'PUNTOS'] = tabla_puntos_actualizada[nombre_puntuacion]
        
        # 4. Impactar los cambios directamente en el archivo físico .xlsx
        guardar_cambios(df_original, df_puntuacion_original)
        st.success("¡Resultados guardados, fórmulas aplicadas y archivo Excel actualizado!")
        st.rerun()

with tab2:
    st.subheader("🏆 Posiciones en Tiempo Real")
    st.write("Datos extraídos directamente de la pestaña 'PUNTUACION':")
    st.dataframe(df_puntuacion_original.sort_values(by="PUNTOS", ascending=False), hide_index=True)
