import streamlit as st
from supabase import create_client, Client
import urllib.parse
import time

# --- CONFIGURACIÓN DE CONEXIÓN SEGURA ---
# Intentamos leer de st.secrets (para la nube) o directo (para local)
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    # Estos son tus datos que pasaste antes
    URL = "https://hodkvspfzoyobjkwefxf.supabase.co"
    KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhvZGt2c3Bmem95b2JrendlZnhmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA5ODgyMDksImV4cCI6MjA4NjU2NDIwOX0.K6x_hR-xLPO1YbOEIm3F6PUpLoKv29_vLM3pLT59Fwg"

supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Draft Master Cloud", page_icon="⚽")

# --- PESTAÑAS ---
tab_reg, tab_vot, tab_admin = st.tabs(["📝 Registro", "⭐ Calificar", "⚙️ Armar Equipos"])

# 1. REGISTRO
with tab_reg:
    st.header("Nuevo Jugador")
    with st.form("registro"):
        nombre = st.text_input("Nombre")
        grupo = st.selectbox("Grupo", ["Fútbol Martes", "Fútbol Jueves", "Amigos"])
        posiciones = st.multiselect("Posiciones", ["Arquero", "Defensor", "Mediocampista", "Delantero"])
        if st.form_submit_button("Guardar"):
            if nombre and posiciones:
                data = {"nombre": nombre, "grupo": grupo, "posicion": " / ".join(posiciones), "nivel": 5.0}
                supabase.table("usuarios").insert(data).execute()
                st.success("¡Registrado en la nube!")
                st.rerun()

# 2. VOTACIÓN (Habilidades diferenciadas)
with tab_vot:
    st.header("Calificaciones")
    res = supabase.table("usuarios").select("*").execute()
    jugadores = res.data
    
    sk_jug = ["Velocidad", "Tiro", "Resistencia", "Defensa", "Pase"] # Simplificadas para el ejemplo
    sk_arq = ["Reflejos", "Salidas", "Saque", "Ubicación", "Mano a Mano"]

    for p in jugadores:
        es_arq = "Arquero" in p['posicion']
        with st.expander(f"⭐ {p['nombre']} ({'Arquero' if es_arq else 'Jugador'})"):
            votos = []
            lista = sk_arq if es_arq else sk_jug
            for s in lista:
                n = st.radio(f"{s}", [1,2,3,4,5,6,7,8,9,10], index=4, horizontal=True, key=f"s_{s}_{p['id']}")
                votos.append(n)
            
            nuevo_nivel = sum(votos) / len(votos)
            if st.button(f"Actualizar nivel de {p['nombre']}", key=f"btn_{p['id']}"):
                supabase.table("usuarios").update({"nivel": nuevo_nivel}).eq("id", p['id']).execute()
                st.toast("Nivel actualizado!")

# 3. ADMIN (Generador con Diferencia de Nivel)
with tab_admin:
    st.header("Generador")
    res = supabase.table("usuarios").select("*").execute()
    presentes = [p for p in res.data if st.checkbox(f"{p['nombre']}", key=f"chk_{p['id']}")]
    
    if st.button("⚖️ Armar"):
        arqs = [j for j in presentes if "Arquero" in j['posicion']]
        ots = [j for j in presentes if "Arquero" not in j['posicion']]
        ots.sort(key=lambda x: x['nivel'], reverse=True)
        
        eq_a, eq_b = [], []
        for i, a in enumerate(arqs): (eq_a if i % 2 == 0 else eq_b).append(a)
        for j in ots: (eq_a if sum(x['nivel'] for x in eq_a) <= sum(x['nivel'] for x in eq_b) else eq_b).append(j)
        
        # UI Resultados y WhatsApp (igual que antes)
        st.write("Equipos listos en consola y listos para enviar.")
        sum_a, sum_b = sum(x['nivel'] for x in eq_a), sum(x['nivel'] for x in eq_b)
        st.metric("Equilibrio", f"Dif: {abs(sum_a - sum_b):.1f}")