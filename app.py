import streamlit as st
from st_supabase_connection import SupabaseConnection
import urllib.parse

st.set_page_config(page_title="Draft Master Pro", page_icon="⚽")

# --- CONEXIÓN ---
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error("Error de conexión. Revisá los Secrets.")
    st.stop()

st.title("⚽ Draft Master Pro")

# --- LECTURA DE DATOS REFORZADA ---
try:
    # Intentamos traer los datos
    res = conn.table("usuarios").select("*").execute()
    jugadores = res.data if res.data else []
    if jugadores:
        st.success(f"¡Se encontraron {len(jugadores)} jugadores!")
except Exception as e:
    st.error(f"Error técnico al leer la tabla: {e}")
    st.info("💡 Si el error dice 'Policy', tenés que activar las RLS en Supabase.")
    jugadores = []

# 1. REGISTRO (Adaptado a tus columnas)
with tab_reg:
    st.header("Nuevo Jugador")
    with st.form("registro"):
        nom = st.text_input("Nombre Completo")
        email = st.text_input("Email (Opcional)")
        # Tu tabla usa un ARRAY de texto para posiciones
        pos = st.multiselect("Posiciones Preferidas", ["Arquero", "Defensor", "Mediocampista", "Delantero"])
        
        if st.form_submit_button("Registrar"):
            if nom and pos:
                try:
                    conn.table("usuarios").insert({
                        "nombre": nom,
                        "email": email,
                        "posiciones_preferidas": pos  # Se manda como lista de Python
                    }).execute()
                    st.success(f"¡{nom} registrado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al insertar: {e}")

# 2. CALIFICAR (Usando tu estructura)
with tab_vot:
    st.header("Nivel de juego")
    if not jugadores:
        st.info("Registrá al menos un jugador para verlo aquí.")
    else:
        for j in jugadores:
            # Mostramos las posiciones que vienen del ARRAY
            pos_str = ", ".join(j['posiciones_preferidas']) if j['posiciones_preferidas'] else "Sin posición"
            with st.expander(f"⭐ {j['nombre']} ({pos_str})"):
                st.write("Aquí podrías calificar, pero tu tabla actual no tiene el campo 'nivel'.")
                st.info("Tip: Agregá una columna llamada 'nivel' (tipo float8) en Supabase para guardar puntajes.")

# 3. ADMIN
with tab_admin:
    st.header("Armar Partido")
    presentes = []
    for j in jugadores:
        if st.checkbox(f"{j['nombre']}", key=f"chk_{j['id']}"):
            presentes.append(j)
            
    if st.button("⚖️ Generar Equipos"):
        if len(presentes) < 2:
            st.error("Seleccioná más jugadores.")
        else:
            # Reparto simple 50/50 ya que no tenemos 'nivel' todavía
            import random
            random.shuffle(presentes)
            mitad = len(presentes) // 2
            eq_a = presentes[:mitad]
            eq_b = presentes[mitad:]
            
            c1, c2 = st.columns(2)
            c1.success("🔵 Equipo A")
            for x in eq_a: c1.write(f"- {x['nombre']}")
            c2.error("🔴 Equipo B")
            for x in eq_b: c2.write(f"- {x['nombre']}")

