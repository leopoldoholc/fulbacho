import streamlit as st
from supabase import create_client, Client
import urllib.parse

# Configuración de página
st.set_page_config(page_title="Draft Master Pro", page_icon="⚽")

# --- CONEXIÓN SEGURA ---
@st.cache_resource
def get_supabase():
    try:
        # Intentamos sacar las credenciales de los Secrets
        url = st.secrets["SUPABASE_URL"].strip()
        key = st.secrets["SUPABASE_KEY"].strip()
        return create_client(url, key)
    except Exception as e:
        return None

supabase = get_supabase()

# --- INTERFAZ ---
st.title("⚽ Draft Master Pro")

if supabase is None:
    st.error("❌ No se pudo conectar a la base de datos.")
    st.info("Revisá que en 'Settings > Secrets' estén SUPABASE_URL y SUPABASE_KEY.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📝 Registro", "⭐ Calificar", "⚙️ Admin"])

# 1. REGISTRO
with tab1:
    with st.form("reg"):
        nom = st.text_input("Nombre")
        pos = st.multiselect("Posición", ["Arquero", "Defensor", "Mediocampista", "Delantero"])
        if st.form_submit_button("Registrar"):
            if nom and pos:
                supabase.table("usuarios").insert({"nombre": nom, "posicion": " / ".join(pos), "nivel": 5.0}).execute()
                st.success("¡Guardado!")
                st.rerun()

# 2. CALIFICAR
with tab2:
    res = supabase.table("usuarios").select("*").execute()
    jugadores = res.data if res.data else []
    for j in jugadores:
        with st.expander(f"Calificar a {j['nombre']}"):
            nuevo_n = st.select_slider("Nivel", options=[i/2 for i in range(2, 21)], value=float(j['nivel']), key=f"n_{j['id']}")
            if st.button("Actualizar", key=f"b_{j['id']}"):
                supabase.table("usuarios").update({"nivel": nuevo_n}).eq("id", j['id']).execute()
                st.toast("Actualizado")

# 3. ADMIN
with tab3:
    if not jugadores:
        st.write("No hay jugadores.")
    else:
        seleccionados = []
        for j in jugadores:
            if st.checkbox(f"{j['nombre']} ({j['posicion']})", key=f"c_{j['id']}"):
                seleccionados.append(j)
        
        if st.button("Armar Equipos"):
            # Lógica simple de arqueros y nivel
            arqs = [x for x in seleccionados if "Arquero" in x['posicion']]
            ots = [x for x in seleccionados if "Arquero" not in x['posicion']]
            ots.sort(key=lambda x: x['nivel'], reverse=True)
            
            eq_a, eq_b = [], []
            for i, a in enumerate(arqs): (eq_a if i%2==0 else eq_b).append(a)
            for o in ots: (eq_a if sum(x['nivel'] for x in eq_a) <= sum(x['nivel'] for x in eq_b) else eq_b).append(o)
            
            c1, c2 = st.columns(2)
            c1.write("🔵 **Equipo A**")
            for x in eq_a: c1.write(f"- {x['nombre']}")
            c2.write("🔴 **Equipo B**")
            for x in eq_b: c2.write(f"- {x['nombre']}")
