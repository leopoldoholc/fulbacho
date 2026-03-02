import streamlit as st
from supabase import create_client
import random, string, urllib.parse, json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Fulbacho Pro", page_icon="⚽", layout="wide")

@st.cache_resource
def init_connection():
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"].strip()
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_connection()

# --- ESTADOS DE SESIÓN ---
if "user" not in st.session_state: st.session_state.user = None
if "vista_actual" not in st.session_state: st.session_state.vista_actual = "🏟️ Grupos"
if "grupo_seleccionado" not in st.session_state: st.session_state.selected_group_id = None

if "unirse" in st.query_params:
    st.session_state.invitacion_pendiente = st.query_params["unirse"]

def ir_a(vista, grupo_id=None):
    st.session_state.vista_actual = vista
    st.session_state.selected_group_id = grupo_id
    st.rerun()

# --- AUTH ---
def manejar_oauth():
    qp = st.query_params
    if "code" in qp:
        try:
            supabase.auth.exchange_code_for_session({"auth_code": qp["code"]})
            st.query_params.clear()
            st.rerun()
        except: pass

manejar_oauth()
session = supabase.auth.get_session()
if session and session.user:
    st.session_state.user = session.user
else:
    st.title("⚽ Fulbacho Pro")
    if st.button("Iniciar con Google", type="primary"):
        res = supabase.auth.sign_in_with_oauth({"provider": "google", "options": {"redirect_to": "https://fulbacho.streamlit.app"}})
        st.link_button("👉 Click para continuar", res.url)
    st.stop()

user = st.session_state.user

# --- CHEQUEO DE PERFIL OBLIGATORIO ---
def check_perfil_completo():
    try:
        # Buscamos nombre y posiciones
        u = supabase.table("usuarios").select("nombre, usuario_posiciones(id)").eq("id", user.id).single().execute()
        if not u.data or not u.data.get('nombre') or not u.data.get('usuario_posiciones'):
            return False, u.data
        return True, u.data
    except: return False, None

perfil_ok, u_db = check_perfil_completo()

if not perfil_ok:
    st.warning("⚠️ ¡Bienvenido! Configurá tu perfil de jugador.")
    with st.container(border=True):
        nuevo_n = st.text_input("Tu Nombre/Apodo", value=user.user_metadata.get("full_name", ""))
        
        # Intentamos traer de posiciones_config
        pos_cfg = supabase.table("posiciones_config").select("id, nombre_posicion").execute().data
        if pos_cfg:
            opciones_dict = {p['id']: p['nombre_posicion'] for p in pos_cfg}
            sel_p = st.multiselect("Tus Posiciones", list(opciones_dict.keys()), format_func=lambda x: opciones_dict[x])
            
            if st.button("Guardar y Empezar 🚀", type="primary"):
                if nuevo_n and sel_p:
                    try:
                        # 1. Upsert Usuario
                        supabase.table("usuarios").upsert({"id": user.id, "nombre": nuevo_n, "email": user.email}).execute()
                        
                        # 2. Guardar Posiciones con manejo de error específico
                        supabase.table("usuario_posiciones").delete().eq("usuario_id", user.id).execute()
                        
                        # Intentamos insertar. Si falla, el bloque except atrapará el error de la DB
                        supabase.table("usuario_posiciones").insert([{"usuario_id": user.id, "posicion_id": pid} for pid in sel_p]).execute()
                        
                        # 3. Auto-unión
                        if "invitacion_pendiente" in st.session_state:
                            cod = st.session_state.invitacion_pendiente
                            gr = supabase.table("grupos").select("id").eq("codigo_invitacion", cod).execute()
                            if gr.data:
                                supabase.table("grupo_miembros").upsert({"grupo_id": gr.data[0]['id'], "usuario_id": user.id, "rol": "miembro"}).execute()
                                del st.session_state.invitacion_pendiente
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error de Base de Datos: {e}")
                        st.info("💡 Tip: Es probable que la tabla 'usuario_posiciones' todavía apunte a la tabla vieja. Revisá las Foreign Keys en Supabase.")
                else: st.error("Faltan datos.")
        else:
            st.error("No se encontraron posiciones en 'posiciones_config'. ¿Corriste el script SQL?")
    st.stop()

# --- UTILIDADES ---
EMOJIS_COLORES = {"Azul": "🔵", "Rojo": "🔴", "Blanco": "⚪", "Negro": "⚫", "Verde": "🟢", "Amarillo": "🟡", "Naranja": "🟠", "Violeta": "🟣", "Celeste": "👕"}
def obtener_meta(g):
    try: return json.loads(g.get('tipo_cancha', '{}'))
    except: return {"mod": "Fútbol 5", "color_a": "Blanco", "color_b": "Negro"}

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
                    meta = obtener_meta(g)
                    st.subheader(f"🏆 {g['nombre']}")
                    st.write(f"{EMOJIS_COLORES.get(meta.get('color_a'), '⚪')} vs {EMOJIS_COLORES.get(meta.get('color_b'), '⚫')}")
                    if item['rol'] == 'admin':
                        c1, c2 = st.columns(2)
                        if c1.button("⚙️ Config", key=f"g_adm_{g['id']}", use_container_width=True): ir_a("⚙️ Admin", g['id'])
                        if c2.button("📅 Equipos", key=f"g_part_{g['id']}", use_container_width=True): ir_a("📅 Partidos", g['id'])
                    else: st.caption(f"Código: {g['codigo_invitacion']}")
    else: st.info("No tenés grupos activos.")
    
    st.divider()
    with st.expander("➕ Crear o Unirse"):
        c1, c2 = st.columns(2)
        with c1:
            with st.form("crear"):
                n = st.text_input("Nombre Grupo")
                mod = st.selectbox("Modalidad", ["Fútbol 5", "Fútbol 8"])
                if st.form_submit_button("Crear Grupo"):
                    cod = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    meta_init = json.dumps({"mod": mod, "color_a": "Blanco", "color_b": "Negro"})
                    new = supabase.table("grupos").insert({"nombre": n, "tipo_cancha": meta_init, "codigo_invitacion": cod}).execute()
                    if new.data:
                        supabase.table("grupo_miembros").insert({"grupo_id": new.data[0]['id'], "usuario_id": user.id, "rol": "admin"}).execute()
                        st.rerun()
        with c2:
            with st.form("unir"):
                ci = st.text_input("Código de Invitación")
                if st.form_submit_button("Unirme"):
                    gr = supabase.table("grupos").select("id").eq("codigo_invitacion", ci).execute()
                    if gr.data:
                        supabase.table("grupo_miembros").upsert({"grupo_id": gr.data[0]['id'], "usuario_id": user.id, "rol": "miembro"}).execute()
                        st.rerun()

# =====================================================
# ⚙️ VISTA ADMIN
# =====================================================
def vista_admin():
    st.header("⚙️ Gestión")
    admin_res = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_res.data: return st.info("No sos admin.")
    
    opc = {g['grupo_id']: g['grupos']['nombre'] for g in admin_res.data}
    idx = list(opc.keys()).index(st.session_state.selected_group_id) if st.session_state.selected_group_id in opc else 0
    g_id = st.selectbox("Grupo:", list(opc.keys()), format_func=lambda x: opc[x], index=idx)
    g_act = next(g['grupos'] for g in admin_res.data if g['grupo_id'] == g_id)

    st.success(f"Código Invitación: **{g_act['codigo_invitacion']}**")

    t1, t2, t3 = st.tabs(["👥 Miembros", "🎨 Estética", "🚨 Zona Roja"])
    with t1:
        miemb = supabase.table("grupo_miembros").select("id, usuario_id, usuarios(nombre)").eq("grupo_id", g_id).execute().data
        for m in miemb:
            c1, c2, c3 = st.columns([2, 0.5, 0.5])
            new_n = c1.text_input("Nombre", m['usuarios']['nombre'], key=f"e_{m['id']}", label_visibility="collapsed")
            if c2.button("💾", key=f"s_{m['id']}"):
                supabase.table("usuarios").update({"nombre": new_n}).eq("id", m['usuario_id']).execute()
                st.rerun()
            if m['usuario_id'] != user.id and c3.button("🗑️", key=f"d_{m['id']}"):
                supabase.table("grupo_miembros").delete().eq("id", m['id']).execute()
                st.rerun()
    with t2:
        meta = obtener_meta(g_act)
        c1, c2 = st.columns(2)
        na = c1.selectbox("Color Equipo A", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta['color_a']))
        nb = c2.selectbox("Color Equipo B", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta['color_b']))
        if st.button("Guardar Config"):
            meta.update({"color_a": na, "color_b": nb})
            supabase.table("grupos").update({"tipo_cancha": json.dumps(meta)}).eq("id", g_id).execute()
            st.success("Guardado")
    with t3:
        if st.checkbox("Confirmar borrar grupo") and st.button("ELIMINAR"):
            supabase.table("grupo_miembros").delete().eq("grupo_id", g_id).execute()
            supabase.table("grupos").delete().eq("id", g_id).execute()
            ir_a("🏟️ Grupos")

# =====================================================
# 📅 VISTA PARTIDOS
# =====================================================
def vista_partidos():
    st.header("📅 Armado de Equipos")
    admin_res = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_res.data: return
    
    opc = {g['grupo_id']: g['grupos']['nombre'] for g in admin_res.data}
    idx = list(opc.keys()).index(st.session_state.selected_group_id) if st.session_state.selected_group_id in opc else 0
    g_id = st.selectbox("Grupo:", list(opc.keys()), format_func=lambda x: opc[x], index=idx, key="p_sel")
    g_info = next(g['grupos'] for g in admin_res.data if g['grupo_id'] == g_id)
    meta = obtener_meta(g_info)
    tipo_cancha = meta.get('mod', 'Fútbol 5')
    
    pos_cfg = supabase.table("posiciones_config").select("*").eq("tipo_cancha", tipo_cancha).execute().data
    nombres_validos = [p['nombre_posicion'] for p in pos_cfg]
    mapa_cats = {p['nombre_posicion']: p['categoria'] for p in pos_cfg}

    res_j = supabase.table("grupo_miembros").select("usuarios(id, nombre, usuario_posiciones(posiciones_config(nombre_posicion)))").eq("grupo_id", g_id).execute()
    j_disp = []
    for item in res_j.data:
        u = item.get('usuarios')
        if u:
            u['pos_perfil'] = [p['posiciones_config']['nombre_posicion'] for p in u.get('usuario_posiciones', []) if p.get('posiciones_config')]
            j_disp.append(u)

    col1, col2 = st.columns([1, 1.8])
    with col1:
        st.subheader("1. Convocados")
        st.checkbox("Todos", key="all_v34", on_change=lambda: [st.session_state.update({f"c{j['id']}": st.session_state.all_v34}) for j in j_disp])
        conv = [j for j in j_disp if st.checkbox(j['nombre'], key=f"c{j['id']}")]
    
    with col2:
        if conv:
            final = {}
            for c in conv:
                with st.container(border=True):
                    c1, c2 = st.columns([1, 2])
                    match = next((p for p in c['pos_perfil'] if p in nombres_validos), nombres_validos[0] if nombres_validos else "Delantero")
                    p_el = c1.selectbox(f"Pos {c['nombre']}", nombres_validos, index=nombres_validos.index(match), key=f"p_{c['id']}")
                    n_el = c2.radio(f"Nivel {c['nombre']}", range(1,11), index=4, horizontal=True, key=f"l_{c['id']}", label_visibility="collapsed")
                    cat = mapa_cats.get(p_el, "MID")
                    final[c['id']] = {"obj": c, "nivel": n_el, "pos": p_el, "cat": cat}
            
            if st.button("🪄 Armar Equipos", type="primary", use_container_width=True):
                arqs = sorted([v for v in final.values() if v['cat'] == "GK"], key=lambda x: x['nivel'], reverse=True)
                resto = sorted([v for v in final.values() if v['cat'] != "GK"], key=lambda x: x['nivel'], reverse=True)
                ea, eb = [], []
                for i, a in enumerate(arqs): (ea if i % 2 == 0 else eb).append(a)
                start_a = len(ea) <= len(eb)
                for i, r in enumerate(resto):
                    if (i % 2 == 0) == start_a: ea.append(r)
                    else: eb.append(r)
                
                c1, c2 = st.columns(2)
                emo_a, emo_b = EMOJIS_COLORES.get(meta['color_a'], '⚪'), EMOJIS_COLORES.get(meta['color_b'], '⚫')
                with c1:
                    st.success(f"{emo_a} EQUIPO A")
                    for x in ea: st.write(f"• {x['obj']['nombre']} ({x['pos'][:3].upper()})")
                with c2:
                    st.error(f"{emo_b} EQUIPO B")
                    for x in eb: st.write(f"• {x['obj']['nombre']} ({x['pos'][:3].upper()})")
                
                msg = f"⚽ *FULBACHO {opc[g_id].upper()}*\n\n*A {emo_a}:*\n" + "\n".join([f"• {j['obj']['nombre']} ({j['pos'][:3].upper()})" for j in ea])
                msg += f"\n\n*B {emo_b}:*\n" + "\n".join([f"• {j['obj']['nombre']} ({j['pos'][:3].upper()})" for j in eb])
                st.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)

# =====================================================
# 🎛️ NAVEGACIÓN
# =====================================================
vistas = ["🏟️ Grupos", "⚙️ Admin", "📅 Partidos", "📝 Perfil"]
nav = st.radio("M", vistas, index=vistas.index(st.session_state.vista_actual), horizontal=True, label_visibility="collapsed")
if nav != st.session_state.vista_actual:
    st.session_state.vista_actual = nav
    st.rerun()

if st.session_state.vista_actual == "🏟️ Grupos": vista_grupos()
elif st.session_state.vista_actual == "⚙️ Admin": vista_admin()
elif st.session_state.vista_actual == "📅 Partidos": vista_partidos()
elif st.session_state.vista_actual == "📝 Perfil":
    st.header("📝 Perfil")
    nn = st.text_input("Nombre", value=u_db['nombre'] if u_db else "")
    if st.button("Guardar"):
        supabase.table("usuarios").update({"nombre": nn}).eq("id", user.id).execute()
        st.success("Guardado")
