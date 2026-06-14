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

# --- CARGA ULTRA SEGURA POR POSICIÓN DE COLUMNA ---
@st.cache_data(ttl=2)
def cargar_datos_seguros():
    try:
        df_partidos = pd.read_excel(excel_detectado, sheet_name="PARTIDOS", header=None, engine="openpyxl")
        
        # Cargamos la pestaña PUNTUACION sin cabeceras (fuerza bruta por posición)
        df_puntos_raw = pd.read_excel(excel_detectado, sheet_name="PUNTUACION", header=None, engine="openpyxl")
        
        # Buscar en qué fila empieza la lista real de jugadores
        # Buscamos una fila donde se mencione la palabra "NOMBRE" o "PUNTO" para saber dónde arranca
        fila_datos_inicio = 0
        idx_col_nombres = 2  # Por defecto la columna 2 (C)
        idx_col_puntos = 3   # Por defecto la columna 3 (D)
        
        for idx_fila in range(len(df_puntos_raw)):
            valores_fila = [str(v).strip().upper() for v in df_puntos_raw.iloc[idx_fila].values]
            if any("NOMBRE" in v for v in valores_fila) or any("PUNTO" in v for v in valores_fila):
                fila_datos_inicio = idx_fila + 1
                for idx_col, v in enumerate(valores_fila):
                    if "NOMBRE" in v: idx_col_nombres = idx_col
                    if "PUNTO" in v: idx_col_puntos = idx_col
                break

        # Extraer limpiamente las columnas usando sus posiciones numéricas exactas
        df_puntos = pd.DataFrame({
            "NOMBRES": df_puntos_raw.iloc[fila_datos_inicio:, idx_col_nombres],
            "PUNTOS": df_puntos_raw.iloc[fila_datos_inicio:, idx_col_puntos]
        }).reset_index(drop=True)
        
        # Limpiar filas completamente vacías
        df_puntos = df_puntos.dropna(subset=["NOMBRES"])
        df_puntos["NOMBRES"] = df_puntos["NOMBRES"].astype(str).str.strip()
        
        # Guardar estos índices en memoria para la fase de guardado
        st.session_state["fila_inicio"] = fila_datos_inicio
        st.session_state["c_nom_idx"] = idx_col_nombres
        st.session_state["c_pts_idx"] = idx_col_puntos
        st.session_state["matriz_puntos_original"] = df_puntos_raw
        
        return df_partidos, df_puntos, None
    except Exception as e:
        return None, None, str(e)

df_original, df_puntuacion_original, error_msg = cargar_datos_seguros()

if error_msg:
    st.error(f"⚠️ Error al abrir el archivo: {error_msg}")
    st.stop()

# Extraer la lista de partidos de la pestaña horizontal
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
        nuevos_goles_l = st.number_input(f"Goles Local", min_value=0, max_value=20, value=info_partido["goles_l"], step=1, key="l_g_v4")
    with col2:
        nuevos_goles_v = st.number_input(f"Goles Visitante", min_value=0, max_value=20, value=info_partido["goles_v"], step=1, key="v_g_v4")
        
    if st.button("💾 Guardar y Recalcular Puntos", type="primary"):
        df_original.iloc[1, partido_seleccionado_id] = nuevos_goles_l
        df_original.iloc[1, partido_seleccionado_id + 1] = nuevos_goles_v
        
        # Recalcular puntos de los participantes en la pestaña PARTIDOS
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

        # Escribir de vuelta los datos calculados en la matriz original de PUNTUACION
        df_salida_puntos = st.session_state["matriz_puntos_original"].copy()
        start_row = st.session_state["fila_inicio"]
        c_nom = st.session_state["c_nom_idx"]
        c_pts = st.session_state["c_pts_idx"]
        
        for i in range(start_row, len(df_salida_puntos)):
            val_nombre = df_salida_puntos.iloc[i, c_nom]
            if pd.notna(val_nombre):
                nom_key = str(val_nombre).strip().upper()
                if nom_key in tabla_puntos_actualizada:
                    df_salida_puntos.iloc[i, c_pts] = int(tabla_puntos_actualizada[nom_key])
        
        # Guardar en el archivo físico .xlsx
        with pd.ExcelWriter(excel_detectado, engine="openpyxl") as writer:
            df_original.to_excel(writer, sheet_name="PARTIDOS", index=False, header=False)
            df_salida_puntos.to_excel(writer, sheet_name="PUNTUACION", index=False, header=False)
            
        st.success("⚽ ¡Marcadores y posiciones actualizados con éxito!")
        st.cache_data.clear()
        st.rerun()

with tab2:
    st.subheader("🏆 Tabla de Posiciones Oficial")
    # Convertir a numérico seguro para ordenar
    df_puntuacion_original["PUNTOS"] = pd.to_numeric(df_puntuacion_original["PUNTOS"], errors="coerce").fillna(0).astype(int)
    st.dataframe(df_puntuacion_original.sort_values(by="PUNTOS", ascending=False), hide_index=True, use_container_width=True)
