import streamlit as st
from supabase import create_client
import random, string, urllib.parse, json

# --- CONFIG ---
st.set_page_config(page_title="Fulbacho Pro", page_icon="⚽", layout="wide")

@st.cache_resource
def init_connection():
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"].strip()
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_connection()

# --- ESTADOS ---
if "user" not in st.session_state: st.session_state.user = None
if "vista_actual" not in st.session_state: st.session_state.vista_actual = "🏟️ Grupos"
if "grupo_seleccionado" not in st.session_state: st.session_state.grupo_seleccionado = None

# Capturar invitación por URL
if "unirse" in st.query_params:
    st.session_state.invitacion_pendiente = st.query_params["unirse"]

def ir_a(vista, grupo_id=None):
    st.session_state.vista_actual = vista
    if grupo_id: st.session_state.grupo_seleccionado = grupo_id
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

# --- CHEQUEO DE PERFIL CON POSICIONES_CONFIG ---
def check_perfil_completo():
    try:
        u = supabase.table("usuarios").select("nombre, usuario_posiciones(id)").eq("id", user.id).single().execute()
        if not u.data or not u.data.get('nombre') or not u.data.get('usuario_posiciones'):
            return False, u.data
        return True, u.data
    except: return False, None

perfil_ok, u_db = check_perfil_completo()

if not perfil_ok:
    st.warning("⚠️ ¡Bienvenido! Configurá tu ficha de jugador.")
    with st.container(border=True):
        nuevo_n = st.text_input("Tu Nombre/Apodo", value=user.user_metadata.get("full_name", ""))
        
        # Traemos todas las posiciones únicas de la tabla de configuración
        pos_cfg = supabase.table("posiciones_config").select("nombre_posicion").execute().data
        opciones_p = sorted(list(set([p['nombre_posicion'] for p in pos_cfg])))
        
        sel_p = st.multiselect("Tus Posiciones", opciones_p)
        
        if st.button("Guardar Perfil y Empezar 🚀", type="primary"):
            if nuevo_n and sel_p:
                supabase.table("usuarios").upsert({"id": user.id, "nombre": nuevo_n, "email": user.email}).execute()
                # OJO: Aquí vinculamos por nombre a la tabla posiciones si existe, o guardamos texto
                # Para simplificar y usar tu config, buscamos los IDs que correspondan a esos nombres
                res_ids = supabase.table("posiciones_config").select("id").in_("nombre_posicion", sel_p).execute().data
                ids_finales = list(set([r['id'] for r in res_ids]))
                
                supabase.table("usuario_posiciones").delete().eq("usuario_id", user.id).execute()
                supabase.table("usuario_posiciones").insert([{"usuario_id": user.id, "posicion_id": pid} for pid in ids_finales]).execute()
                
                if "invitacion_pendiente" in st.session_state:
                    cod = st.session_state.invitacion_pendiente
                    gr = supabase.table("grupos").select("id").eq("codigo_invitacion", cod).execute()
                    if gr.data:
                        supabase.table("grupo_miembros").upsert({"grupo_id": gr.data[0]['id'], "usuario_id": user.id, "rol": "miembro"}).execute()
                        del st.session_state.invitacion_pendiente
                st.rerun()
            else: st.error("Faltan datos.")
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
    else: st.info("No tenés grupos.")
    st.divider()
    with st.expander("➕ Opciones de Grupo"):
        c1, c2 = st.columns(2)
        with c1:
            with st.form("crear"):
                n = st.text_input("Nombre Grupo")
                mod = st.selectbox("Tipo de Cancha", ["Fútbol 5", "Fútbol 8"])
                if st.form_submit_button("Crear"):
                    cod = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    meta_init = json.dumps({"mod": mod, "color_a": "Blanco", "color_b": "Negro"})
                    new = supabase.table("grupos").insert({"nombre": n, "tipo_cancha": meta_init, "codigo_invitacion": cod}).execute()
                    if new.data:
                        supabase.table("grupo_miembros").insert({"grupo_id": new.data[0]['id'], "usuario_id": user.id, "rol": "admin"}).execute()
                        st.rerun()
        with c2:
            with st.form("unir"):
                ci = st.text_input("Código")
                if st.form_submit_button("Unirme"):
                    gr = supabase.table("grupos").select("id").eq("codigo_invitacion", ci).execute()
                    if gr.data:
                        supabase.table("grupo_miembros").upsert({"grupo_id": gr.data[0]['id'], "usuario_id": user.id, "rol": "miembro"}).execute()
                        st.rerun()

# =====================================================
# ⚙️ VISTA ADMIN (APB)
# =====================================================
def vista_admin():
    st.header("⚙️ Gestión")
    admin_res = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_res.data: return st.info("No sos admin.")
    
    opc = {g['grupo_id']: g['grupos']['nombre'] for g in admin_res.data}
    idx = list(opc.keys()).index(st.session_state.grupo_seleccionado) if st.session_state.grupo_seleccionado in opc else 0
    g_id = st.selectbox("Grupo:", list(opc.keys()), format_func=lambda x: opc[x], index=idx)
    g_act = next(g['grupos'] for g in admin_res.data if g['grupo_id'] == g_id)

    st.info(f"Código Invitación: **{g_act['codigo_invitacion']}**")

    t1, t2, t3 = st.tabs(["👥 Miembros", "🎨 Estética", "🚨 Zona Roja"])
    with t1:
        miemb = supabase.table("grupo_miembros").select("id, usuario_id, usuarios(nombre)").eq("grupo_id", g_id).execute().data
        for m in miemb:
            c1, c2, c3 = st.columns([2, 1, 1])
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
        na = c1.selectbox("Color A", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta.get('color_a', 'Blanco')))
        nb = c2.selectbox("Color B", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta.get('color_b', 'Negro')))
        if st.button("Guardar Estética"):
            meta.update({"color_a": na, "color_b": nb})
            supabase.table("grupos").update({"tipo_cancha": json.dumps(meta)}).eq("id", g_id).execute()
            st.success("Guardado")
    with t3:
        if st.checkbox("Confirmar borrar grupo") and st.button("ELIMINAR DEFINITIVAMENTE"):
            supabase.table("grupo_miembros").delete().eq("grupo_id", g_id).execute()
            supabase.table("grupos").delete().eq("id", g_id).execute()
            ir_a("🏟️ Grupos")

# =====================================================
# 📅 VISTA PARTIDOS (v3.2 - LÓGICA CONFIG_TABLE)
# =====================================================
def vista_partidos():
    st.header("📅 Armado de Equipos")
    admin_res = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_res.data: return
    
    opc = {g['grupo_id']: g['grupos']['nombre'] for g in admin_res.data}
    idx = list(opc.keys()).index(st.session_state.grupo_seleccionado) if st.session_state.grupo_seleccionado in opc else 0
    g_id = st.selectbox("Grupo:", list(opc.keys()), format_func=lambda x: opc[x], index=idx, key="p_sel")
    g_info = next(g['grupos'] for g in admin_res.data if g['grupo_id'] == g_id)
    meta = obtener_meta(g_info)
    tipo_cancha_actual = meta.get('mod', 'Fútbol 5')
    
    # 1. Cargar opciones de posición según el tipo de cancha desde la tabla de config
    posiciones_cfg = supabase.table("posiciones_config").select("*").eq("tipo_cancha", tipo_cancha_actual).execute().data
    opciones_nombres = [p['nombre_posicion'] for p in posiciones_cfg]
    mapa_categorias = {p['nombre_posicion']: p['categoria'] for p in posiciones_cfg}
    
    # 2. Carga de jugadores
    res_j = supabase.table("grupo_miembros").select("usuarios(id, nombre, usuario_posiciones(posiciones_config(nombre_posicion)))").eq("grupo_id", g_id).execute()
    j_disp = []
    for item in res_j.data:
        u = item.get('usuarios')
        if u:
            pos_raw = u.get('usuario_posiciones', [])
            # Buscamos nombres de posiciones que coincidan con la tabla de config
            nombres = [p['posiciones_config']['nombre_posicion'] for p in pos_raw if p.get('posiciones_config')]
            u['pos_perfil'] = nombres
            j_disp.append(u)

    col1, col2 = st.columns([1, 1.8])
    with col1:
        st.subheader("1. Convocados")
        st.checkbox("Todos", key="all_v32", on_change=lambda: [st.session_state.update({f"c{j['id']}": st.session_state.all_v32}) for j in j_disp])
        conv = [j for j in j_disp if st.checkbox(j['nombre'], key=f"c{j['id']}")]
    
    with col2:
        st.subheader("2. Táctica y Nivel")
        if not conv: st.info("Seleccioná jugadores.")
        else:
            final = {}
            for c in conv:
                with st.container(border=True):
                    c1, c2 = st.columns([1, 2])
                    # Pre-seleccionar si ya tiene una posición de perfil que sirva para esta cancha
                    match = next((p for p in c['pos_perfil'] if p in opciones_nombres), opciones_nombres[0])
                    p_el = c1.selectbox(f"Pos {c['nombre']}", opciones_nombres, index=opciones_nombres.index(match), key=f"p_{c['id']}")
                    n_el = c2.radio(f"Nivel {c['nombre']}", range(1,11), index=4, horizontal=True, key=f"l_{c['id']}", label_visibility="collapsed")
                    
                    cat = mapa_categorias.get(p_el, "MID")
                    final[c['id']] = {"obj": c, "nivel": n_el, "pos": p_el, "es_arq": cat == "GK", "orden": {"GK":0, "DEF":1, "MID":2, "FWD":3}.get(cat, 4)}
            
            if st.button("🪄 Armar", type="primary", use_container_width=True):
                arqs = sorted([v for v in final.values() if v['es_arq']], key=lambda x: x['nivel'], reverse=True)
                resto = sorted([v for v in final.values() if not v['es_arq']], key=lambda x: x['nivel'], reverse=True)
                ea, eb = [], []
                for i, a in enumerate(arqs): (ea if i % 2 == 0 else eb).append(a)
                start_a = len(ea) <= len(eb)
                for i, r in enumerate(resto):
                    if (i % 2 == 0) == start_a: ea.append(r)
                    else: eb.append(r)
                
                # Ordenar por posición para el reporte
                ea = sorted(ea, key=lambda x: x['orden'])
                eb = sorted(eb, key=lambda x: x['orden'])

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
    nn = st.text_input("Nombre", value=u_db['nombre'])
    if st.button("Guardar"):
        supabase.table("usuarios").update({"nombre": nn}).eq("id", user.id).execute()
        st.success("Guardado")
