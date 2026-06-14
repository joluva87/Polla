import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Admin Polla 2026", page_icon="⚙️", layout="centered")

# --- BUSCADOR AUTOMÁTICO DE EXCEL ---
excel_detectado = None
for archivo in os.listdir("."):
    if "polla" in archivo.lower() and archivo.endswith(".xlsx"):
        excel_detectado = archivo
        break

if not excel_detectado:
    st.error("❌ No se encontró el archivo de Excel en tu GitHub.")
    st.stop()

# --- CARGA ULTRA SEGURA DETECTANDO CABECERAS ---
@st.cache_data(ttl=2)
def cargar_datos_seguros():
    try:
        df_partidos = pd.read_excel(excel_detectado, sheet_name="PARTIDOS", header=None, engine="openpyxl")
        df_puntos_raw = pd.read_excel(excel_detectado, sheet_name="PUNTUACION", header=None, engine="openpyxl")
        
        # Buscar en qué fila se encuentran las palabras clave "NOMBRES" y "PUNTOS"
        fila_cabecera = None
        col_nombres_idx = None
        col_puntos_idx = None
        
        for idx_fila in range(len(df_puntos_raw)):
            valores_fila = [str(v).strip().upper() for v in df_puntos_raw.iloc[idx_fila].values]
            # Buscar coincidencias parciales para evitar fallos por espacios invisibles
            if any("NOMBRE" in v for v in valores_fila) and any("PUNTO" in v for v in valores_fila):
                fila_cabecera = idx_fila
                # Identificar los índices exactos de las columnas
                for idx_col, v in enumerate(valores_fila):
                    if "NOMBRE" in v: col_nombres_idx = idx_col
                    if "PUNTO" in v: col_puntos_idx = idx_col
                break
                
        if fila_cabecera is None:
            return df_partidos, None, f"No se encontró una fila con las columnas 'NOMBRES' y 'PUNTOS' en la pestaña PUNTUACION. Columnas leídas en fila 0: {list(df_puntos_raw.iloc[0].values)}"

        # Reconstruir el DataFrame limpio basándonos en los índices hallados
        datos_limpios = df_puntos_raw.iloc[fila_cabecera + 1:].reset_index(drop=True)
        df_puntos = pd.DataFrame({
            "NOMBRES": datos_limpios[col_nombres_idx],
            "PUNTOS": datos_limpios[col_puntos_idx]
        })
        
        # Guardar metadatos para poder sobreescribir el archivo original correctamente luego
        st.session_state["fila_cabecera"] = fila_cabecera
        st.session_state["col_nombres_idx"] = col_nombres_idx
        st.session_state["col_puntos_idx"] = col_puntos_idx
        st.session_state["df_puntos_raw"] = df_puntos_raw
        
        return df_partidos, df_puntos, None
    except Exception as e:
        return None, None, str(e)

df_original, df_puntuacion_original, error_msg = cargar_datos_seguros()

if error_msg:
    st.error(f"⚠️ Error de compatibilidad: {error_msg}")
    st.stop()

# Extraer la lista de partidos disponibles mapeando el archivo horizontalmente
lista_partidos = []
for col_idx in range(2, df_original.shape[1] - 11, 5):
    equipo_l = df_original.iloc[0, col_idx]
    equipo_v = df_original.iloc[0, col_idx + 1]
    
    if pd.notna(equipo_l) and pd.notna(equipo_v):
        goles_l_actual = df_original.iloc[1, col_idx]
        goles_v_actual = df_original.iloc[1, col_idx + 1]
        
        lista_partidos.append({
            "id": col_idx,
            "texto": f"{str(equipo_l).strip()} vs {str(equipo_v).strip()}",
            "goles_l": int(goles_l_actual) if pd.notna(goles_l_actual) else 0,
            "goles_v": int(goles_v_actual) if pd.notna(goles_v_actual) else 0,
            "jugado": pd.notna(goles_l_actual)
        })

# --- INTERFAZ GRÁFICA ---
st.title("⚽ Administrador Polla 2026")
tab1, tab2 = st.tabs(["📝 Cargar Goles", "🏆 Ver Posiciones"])

with tab1:
    st.subheader("Registrar Resultado Oficial")
    opciones_partido = {p["id"]: f"{'✅' if p['jugado'] else '⏳'} {p['texto']}" for p in lista_partidos}
    partido_seleccionado_id = st.selectbox("Selecciona el partido:", opciones_partido.keys(), format_func=lambda x: opciones_partido[x])
    
    info_partido = next(p for p in lista_partidos if p["id"] == partido_seleccionado_id)
    st.write(f"Marcador actual en el sistema: **{info_partido['goles_l']} - {info_partido['goles_v']}**")
    
    col1, col2 = st.columns(2)
    with col1:
        nuevos_goles_l = st.number_input(f"Goles Local", min_value=0, max_value=20, value=info_partido["goles_l"], step=1, key="l_g_v3")
    with col2:
        nuevos_goles_v = st.number_input(f"Goles Visitante", min_value=0, max_value=20, value=info_partido["goles_v"], step=1, key="v_g_v3")
        
    if st.button("💾 Guardar y Recalcular Puntos", type="primary"):
        df_original.iloc[1, partido_seleccionado_id] = nuevos_goles_l
        df_original.iloc[1, partido_seleccionado_id + 1] = nuevos_goles_v
        
        # Recalcular puntos totales por jugador basado en las filas de apuestas
        tabla_puntos_actualizada = {}
        for c_idx in range(2, df_original.shape[1] - 11, 5):
            real_l = df_original.iloc[1, c_idx]
            real_v = df_original.iloc[1, c_idx + 1]
            
            if pd.notna(real_l) and pd.notna(real_v):
                real_l, real_v = int(real_l), int(real_v)
                for fila_idx in range(2, df_original.shape[0]):
                    jugador = df_original.iloc[fila_idx, c_idx]
                    if pd.isna(jugador): continue
                    
                    pron_l = df_original.iloc[fila_idx, c_idx + 1]
                    pron_v = df_original.iloc[fila_idx, c_idx + 2]
                    
                    if pd.notna(pron_l) and pd.notna(pron_v):
                        pron_l, pron_v = int(pron_l), int(pron_v)
                        pts = 0
                        if pron_l == real_l and pron_v == real_v:
                            pts = 5
                        else:
                            t_p = 1 if pron_l > pron_v else (0 if pron_l == pron_v else -1)
                            t_r = 1 if real_l > real_v else (0 if real_l == real_v else -1)
                            if t_p == t_r:
                                pts = 3 if (pron_l - pron_v) == (real_l - real_v) else 2
                        
                        df_original.iloc[fila_idx, c_idx + 3] = pts
                        nombre_limpio = str(jugador).strip().upper()
                        tabla_puntos_actualizada[nombre_limpio] = tabla_puntos_actualizada.get(nombre_limpio, 0) + pts

        # Sincronizar de vuelta mapeando sobre la matriz original recibida de Excel
        df_salida_puntos = st.session_state["df_puntos_raw"].copy()
        start_row = st.session_state["fila_cabecera"] + 1
        c_nom = st.session_state["col_nombres_idx"]
        c_pts = st.session_state["col_puntos_idx"]
        
        for i in range(start_row, len(df_salida_puntos)):
            val_nombre = df_salida_puntos.iloc[i, c_nom]
            if pd.notna(val_nombre):
                nom_key = str(val_nombre).strip().upper()
                if nom_key in tabla_puntos_actualizada:
                    df_salida_puntos.iloc[i, c_pts] = tabla_puntos_actualizada[nom_key]
        
        # Escribir y guardar manteniendo la estructura original intacta
        with pd.ExcelWriter(excel_detectado, engine="openpyxl") as writer:
            df_original.to_excel(writer, sheet_name="PARTIDOS", index=False, header=False)
            df_salida_puntos.to_excel(writer, sheet_name="PUNTUACION", index=False, header=False)
            
        st.success("⚽ ¡Marcadores y posiciones actualizados con éxito en el Excel!")
        st.cache_data.clear()
        st.rerun()

with tab2:
    st.subheader("🏆 Tabla de Posiciones Oficial")
    vista_tabla = df_puntuacion_original[["NOMBRES", "PUNTOS"]].dropna(subset=["NOMBRES"])
    # Convertir a numérico para ordenar correctamente los puntajes elevados
    vista_tabla["PUNTOS"] = pd.to_numeric(vista_tabla["PUNTOS"], errors="coerce").fillna(0).astype(int)
    st.dataframe(vista_tabla.sort_values(by="PUNTOS", ascending=False), hide_index=True, use_container_width=True)
                     
