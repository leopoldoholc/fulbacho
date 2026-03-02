import streamlit as st
from supabase import create_client
import random
import string
import urllib.parse
import json

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
if "grupo_seleccionado" not in st.session_state: st.session_state.grupo_seleccionado = None

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
            session = supabase.auth.get_session()
            if session and session.user: st.session_state.user = session.user
            st.query_params.clear()
            st.rerun()
        except: pass

manejar_oauth()

if not st.session_state.user:
    st.title("⚽ Fulbacho Pro")
    st.subheader("La app para los que no quieren líos al armar el fulbo.")
    if st.button("Iniciar sesión con Google", type="primary"):
        res = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": "https://fulbacho.streamlit.app"}
        })
        st.link_button("👉 Continuar", res.url)
    st.stop()

user = st.session_state.user

# --- UTILIDADES ---
EMOJIS_COLORES = {"Azul": "🔵", "Rojo": "🔴", "Blanco": "⚪", "Negro": "⚫", "Verde": "🟢", "Amarillo": "🟡", "Naranja": "🟠", "Violeta": "🟣", "Celeste": "👕"}

def obtener_meta(grupo_obj):
    raw = grupo_obj.get('tipo_cancha', '')
    default = {"mod": "F5", "color_a": "Blanco", "color_b": "Negro"}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else default
    except: return default

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
                    st.write(f"{EMOJIS_COLORES.get(meta['color_a'], '⚪')} vs {EMOJIS_COLORES.get(meta['color_b'], '⚫')}")
                    
                    if item['rol'] == 'admin':
                        c1, c2 = st.columns(2)
                        if c1.button(f"⚙️ Config", key=f"btn_adm_{g['id']}", use_container_width=True):
                            ir_a("⚙️ Admin", g['id'])
                        if c2.button(f"📅 Equipos", key=f"btn_part_{g['id']}", use_container_width=True):
                            ir_a("📅 Partidos", g['id'])
                    else:
                        st.caption(f"Modalidad: {meta.get('mod')} | Código: {g['codigo_invitacion']}")
    else:
        st.info("No sos parte de ningún grupo. ¡Creá uno o unite!")

    st.divider()
    with st.expander("➕ Opciones de Grupo"):
        col_c, col_u = st.columns(2)
        with col_c:
            with st.form("crear_g"):
                n = st.text_input("Nombre del nuevo grupo")
                if st.form_submit_button("Crear Grupo"):
                    if n:
                        cod = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                        meta_init = json.dumps({"mod": "F5", "color_a": "Blanco", "color_b": "Negro"})
                        new = supabase.table("grupos").insert({"nombre": n, "tipo_cancha": meta_init, "codigo_invitacion": cod}).execute()
                        if new.data:
                            supabase.table("grupo_miembros").insert({"grupo_id": new.data[0]['id'], "usuario_id": user.id, "rol": "admin"}).execute()
                            st.rerun()
        with col_u:
            with st.form("unir_g"):
                cod_in = st.text_input("Código de invitación")
                if st.form_submit_button("Unirme"):
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
        nuevo_n = st.text_input("Nombre / Apodo", value=u_data['nombre'])
        if st.button("Guardar Cambios"):
            supabase.table("usuarios").update({"nombre": nuevo_n}).eq("id", user.id).execute()
            st.success("¡Perfil actualizado!")

# =====================================================
# ⚙️ VISTA ADMIN
# =====================================================
def vista_admin():
    st.header("⚙️ Gestión de Grupo")
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_g.data:
        st.warning("No sos administrador de ningún grupo.")
        return
    
    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    idx = list(opciones.keys()).index(st.session_state.grupo_seleccionado) if st.session_state.grupo_seleccionado in opciones else 0
    g_sel = st.selectbox("Grupo a gestionar:", options=list(opciones.keys()), format_func=lambda x: opciones[x], index=idx)
    grupo_actual = next(g['grupos'] for g in admin_g.data if g['grupo_id'] == g_sel)

    t1, t2, t3 = st.tabs(["👥 Miembros", "➕ Invitados", "🎨 Configuración"])
    
    with t1:
        miembros = supabase.table("grupo_miembros").select("rol, usuarios(nombre)").eq("grupo_id", g_sel).execute().data
        for m in miembros: st.write(f"• **{m['usuarios']['nombre']}** ({m['rol']})")
    
    with t2:
        st.subheader("Carga rápida de invitados")
        with st.form("inv", clear_on_submit=True):
            inv_n = st.text_input("Nombre del Jugador")
            if st.form_submit_button("Agregar"):
                if inv_n:
                    res = supabase.table("usuarios").insert({"nombre": inv_n}).execute()
                    if res.data:
                        supabase.table("grupo_miembros").insert({"grupo_id": g_sel, "usuario_id": res.data[0]['id'], "rol": "invitado"}).execute()
                        st.success(f"{inv_n} agregado.")
                        st.rerun()
    with t3:
        meta = obtener_meta(grupo_actual)
        c1, c2 = st.columns(2)
        na = c1.selectbox("Color Equipo A", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta['color_a']))
        nb = c2.selectbox("Color Equipo B", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta['color_b']))
        if st.button("Guardar Estética"):
            meta['color_a'], meta['color_b'] = na, nb
            supabase.table("grupos").update({"tipo_cancha": json.dumps(meta)}).eq("id", g_sel).execute()
            st.success("Colores guardados en la base de datos.")

# =====================================================
# 📅 VISTA PARTIDOS (v2.6 - BALANCE POR POSICIÓN)
# =====================================================
def vista_partidos():
    st.header("📅 Armado de Equipos Inteligente")
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_g.data:
        st.info("Sección para administradores.")
        return
    
    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    idx = list(opciones.keys()).index(st.session_state.grupo_seleccionado) if st.session_state.grupo_seleccionado in opciones else 0
    g_sel = st.selectbox("Grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x], index=idx, key="psel_v26")
    
    grupo_info = next(g['grupos'] for g in admin_g.data if g['grupo_id'] == g_sel)
    meta = obtener_meta(grupo_info)
    
    # Traemos jugadores Y sus posiciones (con manejo de errores por si no tienen)
    res_m = supabase.table("grupo_miembros").select("usuarios(id, nombre, usuario_posiciones(posiciones(nombre)))").eq("grupo_id", g_sel).execute()
    
    j_disp = []
    for item in res_m.data:
        u = item.get('usuarios')
        if u:
            # Extraemos las posiciones de forma segura
            pos_raw = u.get('usuario_posiciones', [])
            posiciones = [p['posiciones']['nombre'] for p in pos_raw if p.get('posiciones')]
            u['lista_pos'] = posiciones
            u['es_arquero'] = any("Arquero" in p for p in posiciones)
            j_disp.append(u)
    
    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.subheader("1. Convocados")
        def toggle():
            for j in j_disp: st.session_state[f"c{j['id']}"] = st.session_state[f"all_{g_sel}"]
        st.checkbox("Seleccionar todos", key=f"all_{g_sel}", on_change=toggle)
        
        conv = []
        for j in j_disp:
            label = j['nombre']
            if j['lista_pos']: label += f" ({', '.join([p[:3].upper() for p in j['lista_pos']])})"
            if st.checkbox(label, key=f"c{j['id']}"):
                conv.append(j)
        st.metric("Jugando", len(conv))
    
    with col2:
        st.subheader("2. Nivelación")
        if not conv:
            st.warning("Seleccioná jugadores a la izquierda.")
        else:
            niv = {c['id']: st.radio(f"Nivel {c['nombre']}", options=range(1,11), index=4, horizontal=True, key=f"l{c['id']}") for c in conv}
            
            if st.button("🪄 Armar Equipos Balanceados", type="primary", use_container_width=True):
                # --- LÓGICA DE BALANCEO ---
                arqueros = [j for j in conv if j['es_arquero']]
                jugadores_campo = [j for j in conv if not j['es_arquero']]
                
                # Ordenar ambos grupos por nivel
                arqueros = sorted(arqueros, key=lambda x: niv[x['id']], reverse=True)
                jugadores_campo = sorted(jugadores_campo, key=lambda x: niv[x['id']], reverse=True)
                
                ea, eb = [], []
                
                # 1. Repartir arqueros primero
                for i, arq in enumerate(arqueros):
                    if i % 2 == 0: ea.append(arq)
                    else: eb.append(arq)
                
                # 2. Repartir el resto (serpiente para nivelar)
                # Si el equipo A ya tiene más gente (por los arqueros), empezamos por el B
                empezar_en_a = len(ea) <= len(eb)
                
                for i, jug in enumerate(jugadores_campo):
                    if (i % 2 == 0) == empezar_en_a: ea.append(jug)
                    else: eb.append(jug)
                
                # --- MOSTRAR RESULTADOS ---
                ca, cb = st.columns(2)
                emo_a, emo_b = EMOJIS_COLORES.get(meta['color_a'], '⚪'), EMOJIS_COLORES.get(meta['color_b'], '⚫')
                
                def format_nombre(j):
                    pos = f" [{j['lista_pos'][0][:3].upper()}]" if j['lista_pos'] else ""
                    return f"• {j['nombre']}{pos}"

                ca.success(f"{emo_a} EQUIPO A")
                for x in ea: ca.write(format_nombre(x))
                
                cb.error(f"{emo_b} EQUIPO B")
                for x in eb: cb.write(format_nombre(x))
                
                # --- WHATSAPP TÁCTICO ---
                txt_a = "\n".join([format_nombre(j) for j in ea])
                txt_b = "\n".join([format_nombre(j) for j in eb])
                msg = f"⚽ *FULBACHO: {opciones[g_sel].upper()}*\n\n*{meta['color_a'].upper()} {emo_a}:*\n{txt_a}\n\n*{meta['color_b'].upper()} {emo_b}:*\n{txt_b}"
                st.link_button("📲 Enviar a WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)
# =====================================================
# 🎛️ NAVEGACIÓN Y RENDER
# =====================================================
st.sidebar.title("⚽ Fulbacho Pro")
if st.sidebar.button("Cerrar Sesión"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

vistas = ["🏟️ Grupos", "📝 Perfil", "⚙️ Admin", "📅 Partidos"]
idx_nav = vistas.index(st.session_state.vista_actual)
nav = st.radio("Menú", vistas, index=idx_nav, horizontal=True, label_visibility="collapsed")

if nav != st.session_state.vista_actual:
    st.session_state.vista_actual = nav
    st.rerun()

# RENDER DE VISTAS
if st.session_state.vista_actual == "🏟️ Grupos": vista_grupos()
elif st.session_state.vista_actual == "📝 Perfil": vista_perfil()
elif st.session_state.vista_actual == "⚙️ Admin": vista_admin()
elif st.session_state.vista_actual == "📅 Partidos": vista_partidos()

