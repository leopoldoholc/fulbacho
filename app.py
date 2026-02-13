import streamlit as st
from supabase import create_client, Client
import urllib.parse
import time

# --- 1. CONEXIÓN A BASE DE DATOS ---
# Usamos st.secrets para conectar con Supabase en la nube
try:
    # Estas deben coincidir con lo que pegaste en la pestaña Secrets
    URL_DB = st.secrets["SUPABASE_URL"]
    KEY_DB = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL_DB, KEY_DB)
except Exception as e:
    st.error("⚠️ Error de configuración en los Secrets de Streamlit.")
    st.info("Asegurate de que en Secrets diga: SUPABASE_URL y SUPABASE_KEY")
    st.stop()

# --- 2. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Draft Master Pro", page_icon="⚽")
st.title("⚽ Draft Master Pro")

tab_reg, tab_vot, tab_admin = st.tabs(["📝 Registro", "⭐ Calificar", "⚙️ Armar Equipos"])

# --- 3. PESTAÑA DE REGISTRO ---
with tab_reg:
    st.header("Sumate al partido")
    with st.form("registro_pibe"):
        nombre = st.text_input("Tu Nombre o Apodo")
        grupo = st.selectbox("Elegí tu grupo", ["Fútbol Martes", "Fútbol Jueves", "Amigos"])
        posiciones = st.multiselect("Posiciones", ["Arquero", "Defensor", "Mediocampista", "Delantero"])
        
        if st.form_submit_button("Registrarme"):
            if nombre and posiciones:
                # El ID se genera automático en Supabase o lo mandamos
                data = {
                    "nombre": nombre,
                    "grupo": grupo,
                    "posicion": " / ".join(posiciones),
                    "nivel": 5.0
                }
                supabase.table("usuarios").insert(data).execute()
                st.success(f"¡Vamo {nombre}! Ya estás en la base de datos.")
                st.balloons()
            else:
                st.warning("Faltan datos, che.")

# --- 4. PESTAÑA DE VOTACIÓN ---
with tab_vot:
    st.header("Calificá a la banda")
    # Traemos los jugadores de la base de datos
    res = supabase.table("usuarios").select("*").execute()
    jugadores = res.data if res.data else []

    if not jugadores:
        st.info("No hay nadie anotado todavía.")
    else:
        sk_jug = ["Velocidad", "Habilidad", "Resistencia", "Fuerza", "Visión", "Defensa", "Esfuerzo"]
        sk_arq = ["Reflejos", "Salidas", "Saque", "Ubicación", "Mano a Mano", "Seguridad"]

        for p in jugadores:
            es_arq = "Arquero" in p['posicion']
            with st.expander(f"⭐ {p['nombre']} ({'Arquero' if es_arq else 'Jugador'})"):
                lista_skills = sk_arq if es_arq else sk_jug
                votos = []
                
                # Sistema de 1 solo clic (radio horizontal)
                for s in lista_skills:
                    n = st.radio(f"**{s}**", [1,2,3,4,5,6,7,8,9,10], index=4, horizontal=True, key=f"s_{s}_{p['id']}")
                    votos.append(n)
                
                promedio = sum(votos) / len(votos)
                if st.button(f"Guardar Nivel: {promedio:.2f}", key=f"btn_{p['id']}"):
                    supabase.table("usuarios").update({"nivel": promedio}).eq("id", p['id']).execute()
                    st.toast(f"¡Nivel de {p['nombre']} actualizado!")

# --- 5. PESTAÑA ADMIN (EQUIPOS) ---
with tab_admin:
    st.header("Generador de Equipos")
    res_admin = supabase.table("usuarios").select("*").execute()
    jugadores_admin = res_admin.data
    
    if not jugadores_admin:
        st.write("Nada por aquí...")
    else:
        st.write("¿Quiénes vinieron hoy?")
        presentes = []
        for j in jugadores_admin:
            if st.checkbox(f"{j['nombre']} ({j['posicion']})", key=f"check_{j['id']}"):
                presentes.append(j)
        
        if st.button("⚖️ Armar Equipos Parejos"):
            if len(presentes) < 2:
                st.error("Seleccioná al menos 2, sino no hay partido.")
            else:
                # Lógica de Arqueros
                arqs = [p for p in presentes if "Arquero" in p['posicion']]
                ots = [p for p in presentes if "Arquero" not in p['posicion']]
                ots.sort(key=lambda x: x['nivel'], reverse=True)
                
                eq_a, eq_b = [], []
                for i, a in enumerate(arqs): (eq_a if i % 2 == 0 else eq_b).append(a)
                for o in ots: (eq_a if sum(x['nivel'] for x in eq_a) <= sum(x['nivel'] for x in eq_b) else eq_b).append(o)
                
                # Resultados
                col1, col2 = st.columns(2)
                with col1:
                    st.success("🔵 **EQUIPO A**")
                    for x in eq_a: st.write(f"- {x['nombre']}")
                with col2:
                    st.error("🔴 **EQUIPO B**")
                    for x in eq_b: st.write(f"- {x['nombre']}")
                
                # WhatsApp
                txt = f"⚽ *Equipos del día*\n\n🔵 *EQUIPO A:*\n" + "\n".join([f"- {j['nombre']}" for j in eq_a])
                txt += f"\n\n🔴 *EQUIPO B:*\n" + "\n".join([f"- {j['nombre']}" for j in eq_b])
                st.link_button("📲 Enviar a WhatsApp", f"https://wa.me/?text={urllib.parse.quote(txt)}")
