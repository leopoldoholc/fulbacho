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
# ⚙️ VISTA ADMIN (v2.9 - CON CÓDIGO Y COMPARTIR)
# =====================================================
def vista_admin():
    st.header("⚙️ Gestión de Grupo")
    
    # 1. Traer grupos que administro
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    
    if not admin_g.data:
        st.warning("No sos administrador de ningún grupo.")
        return
    
    opciones = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    
    # Pre-selección por atajo de la home
    idx = 0
    if st.session_state.grupo_seleccionado in opciones:
        idx = list(opciones.keys()).index(st.session_state.grupo_seleccionado)
    
    g_sel = st.selectbox("Seleccionar Grupo:", options=list(opciones.keys()), format_func=lambda x: opciones[x], index=idx)
    grupo_actual = next(g['grupos'] for g in admin_g.data if g['grupo_id'] == g_sel)

    # --- NUEVO: BOX DE INVITACIÓN ---
    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.write("📢 **Invitar nuevos jugadores**")
            codigo = grupo_actual.get('codigo_invitacion', 'S/C')
            st.code(codigo, language="text")
        with c2:
            # Opción C: Link rápido para WhatsApp
            link_inv = f"https://fulbacho.streamlit.app/?unirse={codigo}"
            msg_inv = f"¡Sumate a mi grupo de fulbo *{grupo_actual['nombre']}*! \n\n1️⃣ Entrá acá: https://fulbacho.streamlit.app \n2️⃣ Poné este código: *{codigo}*"
            st.link_button("📲 Pasar Código", f"https://wa.me/?text={urllib.parse.quote(msg_inv)}", use_container_width=True)

    st.divider()

    # --- PESTAÑAS DE GESTIÓN ---
    t1, t2, t3 = st.tabs(["👥 Miembros", "➕ Invitados (Fantasma)", "🎨 Estética"])
    
    with t1:
        miembros_data = supabase.table("grupo_miembros").select("rol, usuarios(nombre)").eq("grupo_id", g_sel).execute().data
        for m in miembros_data: 
            st.write(f"• **{m['usuarios']['nombre']}** ({m['rol']})")
    
    with t2:
        st.subheader("Carga rápida de invitados")
        st.caption("Usá esto para los que no tienen la app.")
        with st.form("inv_fantasma", clear_on_submit=True):
            inv_n = st.text_input("Nombre del Jugador")
            if st.form_submit_button("Agregar al plantel"):
                if inv_n:
                    # Chequeo de duplicados
                    nombres_existentes = [m['usuarios']['nombre'].lower() for m in miembros_data if m['usuarios']]
                    if inv_n.lower() in nombres_existentes:
                        st.warning("Ese nombre ya existe.")
                    else:
                        res = supabase.table("usuarios").insert({"nombre": inv_n}).execute()
                        if res.data:
                            supabase.table("grupo_miembros").insert({"grupo_id": g_sel, "usuario_id": res.data[0]['id'], "rol": "invitado"}).execute()
                            st.success(f"{inv_n} agregado.")
                            st.rerun()
    
    with t3:
        meta = obtener_meta(grupo_actual)
        c1, c2 = st.columns(2)
        new_a = c1.selectbox("Color Equipo A", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta.get('color_a', 'Blanco')), key="edit_a")
        new_b = c2.selectbox("Color Equipo B", list(EMOJIS_COLORES.keys()), index=list(EMOJIS_COLORES.keys()).index(meta.get('color_b', 'Negro')), key="edit_b")
        
        if st.button("Guardar Cambios de Estética"):
            meta['color_a'] = new_a
            meta['color_b'] = new_b
            supabase.table("grupos").update({"tipo_cancha": json.dumps(meta)}).eq("id", g_sel).execute()
            st.success("Configuración guardada.")
            st.rerun()


# =====================================================
# 📅 VISTA PARTIDOS (v2.8 - LÓGICA TÁCTICA AVANZADA)
# =====================================================
def vista_partidos():
    st.header("📅 Armado Táctico de Equipos")
    
    # 1. Obtención de datos básicos
    admin_g = supabase.table("grupo_miembros").select("grupo_id, grupos(*)").eq("usuario_id", user.id).eq("rol", "admin").execute()
    if not admin_g.data:
        st.info("Sección para administradores.")
        return
    
    opciones_g = {g['grupo_id']: g['grupos']['nombre'] for g in admin_g.data if g['grupos']}
    idx = list(opciones_g.keys()).index(st.session_state.grupo_seleccionado) if st.session_state.grupo_seleccionado in opciones_g else 0
    g_sel = st.selectbox("Grupo:", options=list(opciones_g.keys()), format_func=lambda x: opciones_g[x], index=idx, key="psel_v28")
    
    grupo_info = next(g['grupos'] for g in admin_g.data if g['grupo_id'] == g_sel)
    meta = obtener_meta(grupo_info)
    modalidad = meta.get('mod', 'F5') # F5, F6, F8, F11
    
    # 2. Definición de Posiciones según Cancha
    # Mapeo: Posición -> Categoría de Balanceo
    MAPEO_POS = {
        "Arquero": "ARQ",
        "Cierre": "DEF", "Ala": "MED", "Pivot": "DEL", # F5
        "Defensor": "DEF", "Mediocampista": "MED", "Delantero": "DEL", # Gral
        "Lateral": "DEF", "Volante": "MED", "Enganche": "MED" # F8/F11
    }
    
    # Opciones que verá el Admin para elegir "al vuelo"
    OPCIONES_VISTA = ["Arquero", "Defensor", "Mediocampista", "Delantero"]
    if any(mod in modalidad for mod in ["8", "11"]):
        OPCIONES_VISTA = ["Arquero", "Lateral", "Central", "Volante", "Enganche", "Delantero"]

    # 3. Carga de Jugadores
    res_m = supabase.table("grupo_miembros").select("usuarios(id, nombre, usuario_posiciones(posiciones(nombre)))").eq("grupo_id", g_sel).execute()
    j_disp = []
    for item in res_m.data:
        u = item.get('usuarios')
        if u:
            pos_raw = u.get('usuario_posiciones', [])
            nombres = [p['posiciones']['nombre'] for p in pos_raw if p.get('posiciones')]
            u['pos_perfil'] = nombres
            j_disp.append(u)

    col1, col2 = st.columns([1, 1.8])
    
    with col1:
        st.subheader("1. Convocados")
        def toggle():
            for j in j_disp: st.session_state[f"c{j['id']}"] = st.session_state[f"all_v28"]
        st.checkbox("Seleccionar todos", key="all_v28", on_change=toggle)
        
        conv = [j for j in j_disp if st.checkbox(f"{j['nombre']}", key=f"c{j['id']}")]
        st.metric("Total", len(conv))

    with col2:
        st.subheader("2. Ajuste de Posición y Nivel")
        if not conv:
            st.info("Seleccioná jugadores para nivelar.")
        else:
            final_data = {}
            for c in conv:
                with st.container(border=True):
                    # Lógica de posición por defecto
                    pos_defecto = "Mediocampista"
                    if c['pos_perfil']:
                        # Buscamos la primera posición que coincida con nuestras opciones
                        for p in c['pos_perfil']:
                            if p in OPCIONES_VISTA:
                                pos_defecto = p
                                break
                    
                    c1, c2 = st.columns([1, 2])
                    p_elegida = c1.selectbox(f"Pos. {c['nombre']}", OPCIONES_VISTA, 
                                           index=OPCIONES_VISTA.index(pos_defecto) if pos_defecto in OPCIONES_VISTA else 0,
                                           key=f"p_{c['id']}")
                    
                    n_elegido = c2.select_slider(f"Nivel {c['nombre']}", options=range(1,11), value=5, key=f"l_{c['id']}", label_visibility="collapsed")
                    
                    # Categorización para el algoritmo
                    cat = MAPEO_POS.get(p_elegida, "MED")
                    if "Lateral" in p_elegida or "Central" in p_elegida: cat = "DEF"
                    if "Volante" in p_elegida or "Enganche" in p_elegida: cat = "MED"

                    final_data[c['id']] = {
                        "nombre": c['nombre'],
                        "nivel": n_elegido,
                        "pos_label": p_elegida,
                        "categoria": cat, # ARQ, DEF, MED, DEL
                        "orden_peso": {"ARQ": 0, "DEF": 1, "MED": 2, "DEL": 3}.get(cat, 4)
                    }

            if st.button("🪄 Armar Equipos Balanceados", type="primary", use_container_width=True):
                # --- BALANCEO ---
                arqs = [v for v in final_data.values() if v['categoria'] == "ARQ"]
                otros = [v for v in final_data.values() if v['categoria'] != "ARQ"]
                
                # Ordenar por nivel
                arqs = sorted(arqs, key=lambda x: x['nivel'], reverse=True)
                otros = sorted(otros, key=lambda x: x['nivel'], reverse=True)
                
                ea, eb = [], []
                for i, a in enumerate(arqs): (ea if i % 2 == 0 else eb).append(a)
                
                start_a = len(ea) <= len(eb)
                for i, j in enumerate(otros):
                    if (i % 2 == 0) == start_a: ea.append(j)
                    else: eb.append(j)
                
                # --- MOSTRAR (Ordenado por ARQ > DEF > MED > DEL) ---
                ea = sorted(ea, key=lambda x: x['orden_peso'])
                eb = sorted(eb, key=lambda x: x['orden_peso'])
                
                ca, cb = st.columns(2)
                emo_a, emo_b = EMOJIS_COLORES.get(meta.get('color_a'), '⚪'), EMOJIS_COLORES.get(meta.get('color_b'), '⚫')
                
                def f_line(j): return f"• **{j['nombre']}** ({j['pos_label'][:3].upper()})"

                with ca:
                    st.success(f"{emo_a} EQUIPO A")
                    for x in ea: st.write(f_line(x))
                with cb:
                    st.error(f"{emo_b} EQUIPO B")
                    for x in eb: st.write(f_line(x))

                # WhatsApp
                msg = f"⚽ *FULBACHO: {opciones_g[g_sel].upper()}*\n\n"
                msg += f"*{meta.get('color_a', 'A').upper()} {emo_a}:*\n" + "\n".join([f_line(j) for j in ea])
                msg += f"\n\n*{meta.get('color_b', 'B').upper()} {emo_b}:*\n" + "\n".join([f_line(j) for j in eb])
                st.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)

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





