import streamlit as st
from supabase import create_client, Client
import urllib.parse

# --- 1. INTENTO DE CONEXIÓN (CON RED DE SEGURIDAD) ---
def conectar_supabase():
    try:
        # Buscamos en los Secrets de Streamlit Cloud
        url = st.secrets["SUPABASE_URL"].strip()
        key = st.secrets["SUPABASE_KEY"].strip()
        return create_client(url, key)
    except Exception:
        # Si no los encuentra, devolvemos None para mostrar un error amigable
        return None

# Inicializamos la conexión
supabase = conectar_supabase()

# --- 2. CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Draft Master Pro", page_icon="⚽")

if supabase is None:
    st.error("🚨 ERROR: No se encontraron las credenciales de Supabase.")
    st.info("""
    **Para arreglar esto:**
    1. Anda a tu panel de Streamlit Cloud.
    2. En tu App, toca 'Manage App' -> 'Settings' -> 'Secrets'.
    3. Asegurate de que diga exactamente:
    ```toml
    SUPABASE_URL = "tu_url_aqui"
    SUPABASE_KEY = "tu_key_aqui"
    ```
    """)
    st.stop() # Frenamos la app hasta que se arreglen los Secrets

st.title("⚽ Draft Master Pro")

tab_reg, tab_vot, tab_admin = st.tabs(["📝 Registro", "⭐ Calificar", "⚙️ Armar Equipos"])

# --- 3. PESTAÑA DE REGISTRO ---
with tab_reg:
    st.header("Sumate al equipo")
    with st.form("registro"):
        nombre = st.text_input("Nombre / Apodo")
        posiciones = st.multiselect("Posiciones", ["Arquero", "Defensor", "Mediocampista", "Delantero"])
        grupo = st.selectbox("Grupo", ["Fútbol Martes", "Fútbol Jueves", "Amigos"])
        
        if st.form_submit_button("Registrar Jugador"):
            if nombre and posiciones:
                data = {
                    "nombre": nombre,
                    "posicion": " / ".join(posiciones),
                    "grupo": grupo,
                    "nivel": 5.0
                }
                supabase.table("usuarios").insert(data).execute()
                st.success(f"¡{nombre} registrado con éxito!")
                st.balloons()
            else:
                st.warning("Completá todos los campos.")

# --- 4. PESTAÑA DE VOTACIÓN ---
with tab_vot:
    st.header("Calificaciones (Un clic)")
    res = supabase.table("usuarios").select("*").execute()
    jugadores = res.data if res.data else []

    if not jugadores:
        st.info("No hay jugadores registrados.")
    else:
        # Habilidades por puesto
        sk_jug = ["Velocidad", "Habilidad", "Resistencia", "Fuerza", "Visión", "Defensa", "Esfuerzo"]
        sk_arq = ["Reflejos", "Salidas", "Saque", "Ubicación", "Mano a Mano", "Seguridad"]

        for j in jugadores:
            es_arq = "Arquero" in j['posicion']
            with st.expander(f"⭐ {j['nombre']} ({'Arquero' if es_arq else 'Jugador'})"):
                lista = sk_arq if es_arq else sk_jug
                votos = []
                for s in lista:
                    n = st.radio(f"{s}", [1,2,3,4,5,6,7,8,9,10], index=4, horizontal=True, key=f"s_{s}_{j['id']}")
                    votos.append(n)
                
                promedio = sum(votos) / len(votos)
                if st.button(f"Guardar Promedio: {promedio:.2f}", key=f"btn_{j['id']}"):
                    supabase.table("usuarios").update({"nivel": promedio}).eq("id", j['id']).execute()
                    st.toast("¡Nivel actualizado!")

# --- 5. PESTAÑA ADMIN (EQUIPOS) ---
with tab_admin:
    st.header("Armado de Equipos")
    res_admin = supabase.table("usuarios").select("*").execute()
    presentes = []
    if res_admin.data:
        for p in res_admin.data:
            if st.checkbox(f"{p['nombre']} ({p['posicion']})", key=f"p_{p['id']}"):
                presentes.append(p)

    if st.button("⚖️ Generar Equipos"):
        if len(presentes) < 2:
            st.error("Faltan jugadores para el partido.")
        else:
            arqs = [x for x in presentes if "Arquero" in x['posicion']]
            ots = [x for x in presentes if "Arquero" not in x['posicion']]
            ots.sort(key=lambda x: x['nivel'], reverse=True)
            
            eq_a, eq_b = [], []
            for i, a in enumerate(arqs): (eq_a if i%2==0 else eq_b).append(a)
            for o in ots: (eq_a if sum(x['nivel'] for x in eq_a) <= sum(x['nivel'] for x in eq_b) else eq_b).append(o)
            
            col1, col2 = st.columns(2)
            with col1:
                st.success("🔵 **Equipo A**")
                for x in eq_a: st.write(f"- {x['nombre']}")
            with col2:
                st.error("🔴 **Equipo B**")
                for x in eq_b: st.write(f"- {x['nombre']}")

            # WhatsApp
            msg = f"⚽ *Equipos del día*\n\n🔵 *EQUIPO A:*\n" + "\n".join([f"- {j['nombre']}" for j in eq_a])
            msg += f"\n\n🔴 *EQUIPO B:*\n" + "\n".join([f"- {j['nombre']}" for j in eq_b])
            st.link_button("📲 Enviar a WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}")
