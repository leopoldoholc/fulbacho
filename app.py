import streamlit as st
from st_supabase_connection import SupabaseConnection
import urllib.parse

st.set_page_config(page_title="Draft Master Pro", page_icon="⚽")

# --- CONEXIÓN OFICIAL ---
# Forzamos a que la conexión sea lo primero que ocurra
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error("No se pudo conectar a Supabase. Revisá los Secrets.")
    st.stop()

st.title("⚽ Draft Master Pro")

# --- LECTURA DE DATOS ---
try:
    res = conn.table("usuarios").select("*").execute()
    jugadores = res.data if res.data else []
except Exception as e:
    st.warning("Base de datos vacía o error de tabla. Registrá un jugador.")
    jugadores = []

tab_reg, tab_vot, tab_admin = st.tabs(["📝 Registro", "⭐ Calificar", "⚙️ Armar Equipos"])

with tab_reg:
    with st.form("registro"):
        nombre = st.text_input("Nombre")
        posiciones = st.multiselect("Posición", ["Arquero", "Defensor", "Mediocampista", "Delantero"])
        if st.form_submit_button("Registrar"):
            if nombre and posiciones:
                conn.table("usuarios").insert({
                    "nombre": nombre, 
                    "posicion": " / ".join(posiciones),
                    "nivel": 5.0
                }).execute()
                st.success("¡Registrado!")
                st.rerun()

with tab_vot:
    for j in jugadores:
        with st.expander(f"⭐ {j['nombre']}"):
            n = st.select_slider("Nivel", options=[i/2 for i in range(2, 21)], value=float(j['nivel']), key=f"n_{j['id']}")
            if st.button("Guardar", key=f"b_{j['id']}"):
                conn.table("usuarios").update({"nivel": n}).eq("id", j['id']).execute()
                st.toast("Actualizado")

with tab_admin:
    presentes = []
    for j in jugadores:
        if st.checkbox(f"{j['nombre']} ({j['posicion']})", key=f"p_{j['id']}"):
            presentes.append(j)
            
    if st.button("⚖️ Armar Equipos"):
        if len(presentes) < 2:
            st.error("Faltan jugadores.")
        else:
            arqs = [x for x in presentes if "Arquero" in x['posicion']]
            ots = [x for x in presentes if "Arquero" not in x['posicion']]
            ots.sort(key=lambda x: x['nivel'], reverse=True)
            
            eq_a, eq_b = [], []
            for i, a in enumerate(arqs): (eq_a if i%2==0 else eq_b).append(a)
            for o in ots: (eq_a if sum(x['nivel'] for x in eq_a) <= sum(x['nivel'] for x in eq_b) else eq_b).append(o)
            
            c1, c2 = st.columns(2)
            c1.success("🔵 **Equipo A**")
            for x in eq_a: c1.write(f"- {x['nombre']}")
            c2.error("🔴 **Equipo B**")
            for x in eq_b: c2.write(f"- {x['nombre']}")
            
            msg = f"⚽ *Equipos*\n\n🔵 *A:*\n" + "\n".join([f"- {j['nombre']}" for j in eq_a])
            msg += f"\n\n🔴 *B:*\n" + "\n".join([f"- {j['nombre']}" for j in eq_b])
            st.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}")
