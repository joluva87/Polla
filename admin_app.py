import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Admin Polla 2026", page_icon="⚙️", layout="centered")

# --- EVITAR ERROR DE ZIP CORRUPTO ---
excel_detectado = None
for archivo in os.listdir("."):
    if "polla" in archivo.lower() and archivo.endswith(".xlsx"):
        excel_detectado = archivo
        break

if not excel_detectado:
    st.error("❌ No se encontró el archivo de Excel en tu GitHub.")
    st.stop()

# Carga segura con manejo de errores de empaquetado
@st.cache_data(ttl=5)
def cargar_datos_seguros():
    try:
        df_partidos = pd.read_excel(excel_detectado, sheet_name="PARTIDOS", header=None, engine="openpyxl")
        df_puntos = pd.read_excel(excel_detectado, sheet_name="PUNTUACION", engine="openpyxl")
        return df_partidos, df_puntos, None
    except Exception as e:
        return None, None, str(e)

df_original, df_puntuacion_original, error_msg = cargar_datos_seguros()

if error_msg:
    st.error("⚠️ El archivo Excel subió corrupto a GitHub.")
    st.info("💡 Solución: Elimina el archivo .xlsx de tu GitHub y vuélvelo a subir desde tu celular sin interrumpir la carga.")
    st.stop()

# Extraer la lista de partidos disponibles
lista_partidos = []
for col_idx in range(2, df_original.shape[1] - 11, 5):
    equipo_l = df_original.iloc[0, col_idx]
    equipo_v = df_original.iloc[0, col_idx + 1]
    
    if pd.notna(equipo_l) and pd.notna(equipo_v):
        goles_l_actual = df_original.iloc[1, col_idx]
        goles_v_actual = df_original.iloc[1, col_idx + 1]
        
        lista_partidos.append({
            "id": col_idx,
            "texto": f"{equipo_l} vs {equipo_v}",
            "goles_l": int(goles_l_actual) if pd.notna(goles_l_actual) else 0,
            "goles_v": int(goles_v_actual) if pd.notna(goles_v_actual) else 0,
            "jugado": pd.notna(goles_l_actual)
        })

# --- INTERFAZ ---
st.title("⚙️ Panel de Control Mundial 2026")
tab1, tab2 = st.tabs(["⚽ Ingresar Marcador", "📊 Tabla de Posiciones"])

with tab1:
    st.subheader("Registrar Resultado Oficial")
    opciones_partido = {p["id"]: f"{'✅ ' if p['jugado'] else '⏳ '} {p['texto']}" for p in lista_partidos}
    partido_seleccionado_id = st.selectbox("Selecciona el partido:", opciones_partido.keys(), format_func=lambda x: opciones_partido[x])
    
    info_partido = next(p for p in lista_partidos if p["id"] == partido_seleccionado_id)
    st.write(f"Marcador actual: **{info_partido['goles_l']} - {info_partido['goles_v']}**")
    
    col1, col2 = st.columns(2)
    with col1:
        nuevos_goles_l = st.number_input(f"Goles Local", min_value=0, max_value=20, value=info_partido["goles_l"], step=1, key="l_g")
    with col2:
        nuevos_goles_v = st.number_input(f"Goles Visitante", min_value=0, max_value=20, value=info_partido["goles_v"], step=1, key="v_g")
        
    if st.button("💾 Guardar Marcador", type="primary"):
        df_original.iloc[1, partido_seleccionado_id] = nuevos_goles_l
        df_original.iloc[1, partido_seleccionado_id + 1] = nuevos_goles_v
        
        # Recalcular puntos de la polla
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
                        tabla_puntos_actualizada[str(jugador).strip().upper()] = tabla_puntos_actualizada.get(str(jugador).strip().upper(), 0) + pts

        for i, row in df_puntuacion_original.iterrows():
            nom = str(row['NOMBRES']).strip().upper()
            if nom in tabla_puntos_actualizada:
                df_puntuacion_original.at[i, 'PUNTOS'] = tabla_puntos_actualizada[nom]
        
        with pd.ExcelWriter(excel_detectado, engine="openpyxl") as writer:
            df_original.to_excel(writer, sheet_name="PARTIDOS", index=False, header=False)
            df_puntuacion_original.to_excel(writer, sheet_name="PUNTUACION", index=False)
            
        st.success("¡Resultados calculados y guardados!")
        st.cache_data.clear()
        st.rerun()

with tab2:
    st.subheader("🏆 Tabla de Posiciones")
    st.dataframe(df_puntuacion_original.sort_values(by="PUNTOS", ascending=False), hide_index=True)
    
