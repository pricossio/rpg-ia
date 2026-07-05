import streamlit as st
import pandas as pd
from game_logic import EstadoJuego
import ai_agent
import ml_trainer

# Configuración de página para hacerla ancha y premium
st.set_page_config(page_title="Batalla IA Híbrida", layout="wide", page_icon="⚔️")

# CSS personalizado para la interfaz
st.markdown("""
<style>
.stProgress > div > div > div > div {
    background-color: #2ecc71;
}
.dead-text { color: #e74c3c; text-decoration: line-through; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Inicializar el estado del juego si no existe
if 'estado' not in st.session_state:
    st.session_state.estado = EstadoJuego()
    st.session_state.logs = ["¡Partida iniciada!"]
    st.session_state.arbol = None

def log_msg(msg):
    st.session_state.logs.insert(0, msg)

st.title("⚔️ Batalla Táctica RPG - Inteligencia Artificial Híbrida")
st.markdown("Compite contra un algoritmo **Min-Max** que además **Aprende de tus jugadas (Machine Learning)**.")

tab_juego, tab_ml = st.tabs(["🎮 Tablero de Juego", "🧠 Dashboard de Machine Learning"])

with tab_ml:
    st.header("Centro de Entrenamiento de IA")
    st.write("Aquí es donde ocurre la magia interna requerida por la rúbrica.")
    
    col_train, col_data = st.columns(2)
    
    with col_train:
        st.subheader("Generar Archivos (.pkl)")
        if st.button("🚀 Entrenar Árbol de Decisión y K-Means"):
            with st.spinner("Leyendo CSV y entrenando modelos con scikit-learn..."):
                exito, msg = ml_trainer.entrenar_y_guardar_modelos()
                if exito:
                    st.success(msg)
                    st.session_state.arbol, _ = ml_trainer.cargar_modelos()
                else:
                    st.error(msg)
                    
    with col_data:
        st.subheader("Dataset Generado Internamente (.csv)")
        try:
            df = pd.read_csv("dataset_jugadas.csv")
            st.dataframe(df.tail(8)) # Mostrar últimas jugadas
            st.caption(f"Total de jugadas registradas: {len(df)}")
        except:
            st.info("El archivo CSV se generará en secreto cuando empieces a jugar tus turnos.")

with tab_juego:
    col_config, col_game = st.columns([1, 3])
    
    with col_config:
        st.subheader("Configuración")
        dificultad = st.slider("Profundidad de Búsqueda (Nivel)", 1, 4, 2, help="Nivel 1 es Fácil. Nivel 4 es Difícil.")
        modo = st.radio("Modo de Juego", ["Clásico (Matemático)", "Adaptativo (Predice con ML)"])
        
        if st.button("🔄 Reiniciar Partida"):
            st.session_state.estado = EstadoJuego()
            st.session_state.logs = ["Partida reiniciada."]
            st.session_state.last_action = None
            st.rerun()
            
        st.subheader("Registro de Batalla")
        for l in st.session_state.logs[:6]:
            st.markdown(f"- {l}")
            
    with col_game:
        # Mostrar Pop-up de la última acción (Animación)
        if 'last_action' in st.session_state and st.session_state.last_action:
            st.toast(st.session_state.last_action, icon="🔥")
            st.session_state.last_action = None

        estado = st.session_state.estado
        personaje_actual = estado.obtener_personaje_actual()
        
        if estado.ganador is not None:
            st.success(f"🏆 ¡EL GANADOR ES EL EQUIPO {estado.ganador.upper()}! 🏆")
            st.balloons()
        else:
            if personaje_actual.equipo == "IA":
                st.warning(f"🤖 La IA está calculando el turno de **{personaje_actual.nombre}**...")
                
                # Hacemos que la IA juegue de forma automática sin presionar botón
                import time
                time.sleep(1.2) # Pausa dramática para que el usuario lea
                
                objetivo_predicho = None
                if modo == "Adaptativo (Predice con ML)":
                    if st.session_state.arbol is None:
                        st.session_state.arbol, _ = ml_trainer.cargar_modelos()
                    
                    if st.session_state.arbol is not None:
                        # Hacer la predicción ML
                        hps = [estado.personajes[i].hp for i in range(6)]
                        clase_map = {"Guerrero": 0, "Mago": 1, "Sanador": 2}
                        clase_id = clase_map[personaje_actual.clase]
                        
                        try:
                            X_actual = pd.DataFrame([hps + [clase_id]], columns=['HP_H1', 'HP_H2', 'HP_H3', 'HP_IA1', 'HP_IA2', 'HP_IA3', 'Clase_Atacante'])
                            prediccion = st.session_state.arbol.predict(X_actual)[0]
                            nom_obj = estado.personajes[prediccion].nombre
                            st.toast(f"🧠 ML Predice que atacarás a {nom_obj}", icon="🧠")
                            log_msg(f"🧠 [ML PREDICT] Predigo que el humano intentará atacar a {nom_obj}. Ajustando defensa Min-Max...")
                            objetivo_predicho = prediccion
                        except:
                            pass
                
                # Búsqueda MinMax
                accion_elegida = ai_agent.obtener_mejor_jugada(estado, dificultad, objetivo_predicho)
                if accion_elegida:
                    tipo, id_obj = accion_elegida
                    nom_obj = estado.personajes[id_obj].nombre
                    
                    # Nombres épicos para la IA
                    habilidad = "⚔️ Espadazo Brutal"
                    if personaje_actual.clase == "Mago": habilidad = "🔥 Bola de Fuego"
                    elif personaje_actual.clase == "Sanador" and tipo == "Atacar": habilidad = "⚡ Rayo Sagrado"
                    elif personaje_actual.clase == "Sanador" and tipo == "Curar": habilidad = "💚 Curación Divina"
                    
                    st.session_state.last_action = f"🤖 IA {personaje_actual.nombre} usó {habilidad} en {nom_obj}!"
                    log_msg(st.session_state.last_action)
                    estado.aplicar_accion(accion_elegida)
                else:
                    estado.avanzar_turno()
                st.rerun()
            else:
                st.info(f"🧑 Es tu turno: **{personaje_actual.nombre}**. ¡Elige tu movimiento mágico abajo!")

        st.divider()
        
        # Renderizar el Campo de Batalla Visual
        col_humano, col_vs, col_ia = st.columns([4, 1, 4])
        
        with col_humano:
            st.markdown("### 🛡️ Equipo Humano")
            img_map = {"Guerrero": "assets/warrior.png", "Mago": "assets/mage.png", "Sanador": "assets/healer.png"}
            for i in range(3):
                p = estado.personajes[i]
                col_img, col_info = st.columns([1, 2])
                with col_img:
                    st.image(img_map[p.clase], use_container_width=True)
                with col_info:
                    if p.vivo:
                        st.write(f"**{p.nombre}** ({p.hp}/{p.hp_max} HP)")
                        st.progress(p.hp / p.hp_max)
                        
                        # Si es Sanador y es su turno, puede curar aliados
                        if personaje_actual.equipo == "Humano" and personaje_actual.clase == "Sanador" and p.hp < p.hp_max:
                            if st.button(f"💚 Lanzar Curación a {p.nombre}", key=f"curar_{i}"):
                                ai_agent.guardar_jugada_csv(estado, ("Curar", p.id))
                                st.session_state.last_action = f"🧑 ¡Sanador usó 💚 Curación Divina en {p.nombre}!"
                                log_msg(st.session_state.last_action)
                                estado.aplicar_accion(("Curar", p.id))
                                st.rerun()
                    else:
                        st.markdown(f"<p class='dead-text'>☠️ {p.nombre} (Muerto)</p>", unsafe_allow_html=True)
                st.write("") # Espaciador

        with col_vs:
            st.markdown("<h1 style='text-align: center; margin-top: 50px; color: gray;'>VS</h1>", unsafe_allow_html=True)
            
        with col_ia:
            st.markdown("### 👾 Equipo IA")
            for i in range(3, 6):
                p = estado.personajes[i]
                col_img, col_info = st.columns([1, 2])
                with col_img:
                    st.image(img_map[p.clase], use_container_width=True)
                with col_info:
                    if p.vivo:
                        st.write(f"**{p.nombre}** ({p.hp}/{p.hp_max} HP)")
                        st.progress(p.hp / p.hp_max)
                        
                        # Botón para atacar enemigo
                        if personaje_actual.equipo == "Humano":
                            habilidad = "⚔️ Espadazo"
                            if personaje_actual.clase == "Mago": habilidad = "🔥 Bola de Fuego"
                            elif personaje_actual.clase == "Sanador": habilidad = "⚡ Rayo Sagrado"
                            
                            if st.button(f"{habilidad} a {p.nombre}", key=f"atacar_{i}"):
                                ai_agent.guardar_jugada_csv(estado, ("Atacar", p.id))
                                st.session_state.last_action = f"🧑 ¡Tu {personaje_actual.nombre} usó {habilidad} contra {p.nombre}!"
                                log_msg(st.session_state.last_action)
                                estado.aplicar_accion(("Atacar", p.id))
                                st.rerun()
                    else:
                        st.markdown(f"<p class='dead-text'>☠️ {p.nombre} (Muerto)</p>", unsafe_allow_html=True)
                st.write("")
