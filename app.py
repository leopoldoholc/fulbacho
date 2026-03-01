import streamlit as st
from supabase import create_client
import random
import string
import urllib.parse
import json

st.set_page_config(page_title="Fulbacho Pro", page_icon="⚽", layout="wide")

# =====================================================
# 🔌 CONEXIÓN
# =====================================================
@st.cache_resource
def init_connection():
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"].strip()
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_connection()

def generar_codigo():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

EMOJIS_COLORES = {
    "Azul": "🔵", "Rojo": "🔴", "Blanco": "⚪", "Negro": "⚫", 
    "Verde": "🟢", "Amarillo": "🟡", "Naranja": "🟠", "Violeta": "🟣", "Celeste": "👕"
}

# =====================================================
# 🔐 AUTH & SESSION
# =====================================================
if "user" not in st.session_state: st.session_state.user = None

def manejar_oauth():
    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]
        try:
            supabase.auth.exchange_code_for_session({"auth_code": code})
            session = supabase.auth.get_session()
            if session and session.user: st.session_state.user = session.user
            st.query_params.clear()
            st.rerun()
        except: pass

manejar_oauth()
if not st.session_state.user:
    st.title("⚽ Fulbacho Pro")
    if st.button("Iniciar sesión con Google", type="primary"):
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": "https://fulbacho.streamlit.app"}
        })
        st.link_button("👉 Continuar con Google", response.url)
    st.stop()

user = st.session_state.user

# Sync Usuario
try:
    existing = supabase.table("usuarios").select("*").eq("id", user.id).execute()
    if not existing.data:
        supabase.table("usuarios").insert({
            "id": user.id, "nombre": user.user_metadata.get("full_name", user.email), "email": user.email
        }).execute()
except: pass

# =====================================================
# 🏟️ VISTA GRUPOS
# =====================================================
def vista_grupos():
    st.header("🏟️ Mis Grupos")
    res = supabase.table("grupo_miembros").select("rol, grupos(*)").eq("usuario_id", user.id).execute()
    
    if res.data:
        cols = st.columns(2)
        for i, item in enumerate(res.data):
            g = item['grupos']
            if not g: continue
            with cols[i % 2]:
                with st.container(border=True):
                    try:
                        info = json.loads(g.get('tipo_cancha', '{}'))
                        conf_a, conf_b = info.get('color_a', 'Blanco'), info.get('color_b', 'Negro')
                        modalidad = info.get('mod', 'Fútbol')
                    except:
                        conf_a, conf_b, modalidad = 'Blanco', 'Negro', g.get('tipo_cancha', 'Fútbol')

                    st.subheader(f"🏆 {g['nombre']}")
                    st.write(f"{EMOJIS_COLORES[conf_a]} vs {EMOJIS_COLORES[conf_b]}")
                    st.caption(f"Modalidad: {modalidad}")
                    st.code(f"Código: {g['codigo_invitacion']}")
    else:
        st.info("Aún no sos parte de ningún grupo.")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Crear Grupo")
        with st.form("crear_g"):
            n = st.text_input("Nombre")
            res_mod = supabase.table("modalidades").select("*").execute()
            mods = {m['id']: m['nombre'] for m in res_mod.data} if res_mod.data else {1: "Fútbol 5"}
            m_id = st.selectbox("Modalidad", options=list(mods.keys()), format_func=lambda x: mods[x])
            if st.form_submit_button("Crear"):
                if n:
                    cod = generar_codigo()
                    meta = json.dumps({"mod": mods[m_id], "color_a": "Blanco", "color_b": "Negro"})
                    new = supabase.table("grupos").insert({"nombre": n, "tipo_cancha": meta, "codigo_invitacion": cod}).execute()
                    if new.data:
                        supabase.table("grupo_miembros").insert({"grupo_id": new.data[0]['id'], "usuario_id": user.id, "rol": "admin"}).execute()
                        st.rerun()
    with c2:
        st.subheader("Unirse")
        with st.form("unir_g"):
            cod_in = st.text_input("Código")
            if st.form_submit_button("Unirse"):
                g_res = supabase.table("grupos").select("id").eq("codigo_invitacion", cod_in).execute()
                if g_res.data:
                    supabase.table("grupo_miembros").upsert({"grupo_id": g_res.data[0]['id'], "usuario_id": user.id, "rol": "miembro"}).execute()
                    st.rerun()

# =====================================================
# 📝 VISTA PERFIL
# =====================================================
def vista_perfil():
    st.header("📝 Mi Perfil")
    u_data = supabase.table("usuarios").select("*").eq("id", user.id).single().execute().data
    with st.container(border=True):
        nuevo_n = st.text_input("Nombre", value=u_data['nombre'])
        pos_db = supabase.table("posiciones").select("*").execute().data or []
        opciones = {p['id']: f"{p['nombre']} ({p['categoria']})" for p in pos_db}
        actuales = supabase.table("usuario_posiciones").select("posicion_id").eq("usuario_id", user.id).execute()
        ids_act = [a['posicion_id'] for a in actuales.data]
        sel = st.multiselect("Posiciones", options=list(opciones.keys()), default=[p for p in ids_act if p in opciones], format_func=lambda x: opciones[x])
        if st.button("Guardar"):
            supabase.table("usuarios").update({"nombre": nuevo_n}).eq("id", user.id).execute()
            supabase.table("usuario_posiciones").delete().eq("usuario_id", user.id).execute()
            if sel:
                supabase.table("usuario_posiciones").insert([{"usuario_id": user.id, "posicion_id": pid} for pid in sel]).execute()
            st.success("¡Guardado!")

# =====================================================
# ⚙️ VISTA ADMIN
# =====================================================
def vista_admin():
    st.header("⚙️ Gestión de Grupo")
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    
    if not admin_g.data:
        st.warning("No sos administrador.")
        return
    
    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    g_sel = st.selectbox("Seleccionar Grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x])
    grupo_actual = next(g['grupos'] for g in admin_g.data if g['grupo_id'] == g_sel)

    t1, t2, t3 = st.tabs(["👥 Miembros", "➕ Invitados", "🎨 Configuración"])
    
    with t1:
        miembros = supabase.table("grupo_miembros").select("rol, usuarios(nombre)").eq("grupo_id", g_sel).execute()
        lista_nombres = [m['usuarios']['nombre'].lower() for m in miembros.data if m['usuarios']]
        for m in miembros.data: 
            st.write(f"• **{m['usuarios']['nombre']}** ({m['rol']})")
    
    with t2:
        st.subheader("Carga de invitados")
        with st.form("inv", clear_on_submit=True):
            inv_n = st.text_input("Nombre del Jugador")
            if st.form_submit_button("Agregar al plantel"):
                if not inv_n: st.error("Escribí un nombre.")
                elif inv_n.lower() in lista_nombres:
                    st.warning(f"⚠️ El jugador '{inv_n}' ya existe.")
                else:
                    res = supabase.table("usuarios").insert({"nombre": inv_n}).execute()
                    if res.data:
                        supabase.table("grupo_miembros").insert({"grupo_id": g_sel, "usuario_id": res.data[0]['id'], "rol": "invitado"}).execute()
                        st.success(f"✅ {inv_n} agregado.")
                        st.rerun()
    
    with t3:
        st.subheader("Personalización del Grupo")
        try: meta = json.loads(grupo_actual.get('tipo_cancha', '{}'))
        except: meta = {"mod": "Fútbol", "color_a": "Blanco", "color_b": "Negro"}

        c1, c2 = st.columns(2)
        with c1: new_a = st.selectbox("Color Equipo A", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta.get('color_a', 'Blanco')), key="new_a")
        with c2: new_b = st.selectbox("Color Equipo B", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta.get('color_b', 'Negro')), key="new_b")
        
        if st.button("Guardar Cambios de Estética"):
            meta['color_a'], meta['color_b'] = new_a, new_b
            supabase.table("grupos").update({"tipo_cancha": json.dumps(meta)}).eq("id", g_sel).execute()
            st.success("Guardado.")
            st.rerun()

# =====================================================
# 📅 VISTA PARTIDOS
# =====================================================
def vista_partidos():
    st.header("📅 Armado de Equipos")
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_g.data:
        st.info("Solo administradores.")
        return
    
    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    g_sel = st.selectbox("Grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x], key="psel")
    grupo_info = next(g['grupos'] for g in admin_g.data if g['grupo_id'] == g_sel)

    try: meta = json.loads(grupo_info.get('tipo_cancha', '{}'))
    except: meta = {"color_a": "Blanco", "color_b": "Negro"}
    
    emo_a, emo_b = EMOJIS_COLORES[meta.get('color_a', 'Blanco')], EMOJIS_COLORES[meta.get('color_b', 'Negro')]

    res_m = supabase.table("grupo_miembros").select("usuarios(id, nombre)").eq("grupo_id", g_sel).execute()
    j_disp = [m['usuarios'] for m in res_m.data if m['usuarios']]
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🙋‍♂️ Convocados")
        # --- EL BOTÓN DE SELECCIONAR TODOS ---
        sel_all = st.checkbox("✅ Seleccionar todos los del grupo")
        
        conv = []
        for j in j_disp:
            # Si sel_all es True, el default del checkbox es True
            if st.checkbox(j['nombre'], key=f"c{j['id']}", value=sel_all):
                conv.append(j)
        
        st.divider()
        st.metric("Total jugando", len(conv))
    
    with col2:
        if len(conv) >= 2:
            st.subheader("⚖️ Nivelación")
            niv = {c['id']: st.slider(f"{c['nombre']}", 1, 10, 5, key=f"l{c['id']}") for c in conv}
            
            if st.button("🪄 Armar Equipos", type="primary"):
                orden = sorted(conv, key=lambda x: niv[x['id']], reverse=True)
                ea, eb = [], []
                for i, jug in enumerate(orden): (ea if i % 2 == 0 else eb).append(jug)
                
                st.divider()
                ca, cb = st.columns(2)
                with ca:
                    st.markdown(f"### {emo_a} {meta.get('color_a', 'A').upper()}")
                    for x in ea: st.write(f"• {x['nombre']}")
                with cb:
                    st.markdown(f"### {emo_b} {meta.get('color_b', 'B').upper()}")
                    for x in eb: st.write(f"• {x['nombre']}")
                
                msg = f"⚽ *¡HAY FULBACHO EN {opciones[g_sel].upper()}!* ⚽\n\n"
                msg += f"{emo_a} *EQUIPO {meta.get('color_a', 'A').upper()}:*\n" + "\n".join([f"• {j['nombre']}" for j in ea])
                msg += f"\n\n{emo_b} *EQUIPO {meta.get('color_b', 'B').upper()}:*\n" + "\n".join([f"• {j['nombre']}" for j in eb])
                msg += f"\n\n📍 _¡A transpirar la camiseta!_"
                st.link_button("📲 Mandar por WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}")

# =====================================================
# 🎛️ MAIN
# =====================================================
st.sidebar.title("⚽ Fulbacho Pro")
if st.sidebar.button("Cerrar Sesión"): logout()

tabs = st.tabs(["🏟️ Grupos", "📝 Perfil", "⚙️ Admin", "📅 Partidos"])
with tabs[0]: vista_grupos()
with tabs[1]: vista_perfil()
with tabs[2]: vista_admin()
with tabs[3]: vista_partidos()
