from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
import os
import ai_agent
import ml_trainer
from game_logic import EstadoJuego, CATALOGO_PERSONAJES

app = FastAPI()

# Montar carpetas estáticas para la Web
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/static", StaticFiles(directory="static"), name="static")

class StartRequest(BaseModel):
    team_ids: List[int]

# Estado global de la partida
estado_actual = None
dificultad_global = 4
modo_global = "Clásico"

class ActionModel(BaseModel):
    accion_tipo: str
    id_objetivo: int

class ConfigModel(BaseModel):
    modo: str
    dificultad: int

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.get("/api/characters")
def get_characters():
    return CATALOGO_PERSONAJES

@app.post("/api/start")
def start_game(req: StartRequest):
    global estado_actual
    if len(req.team_ids) != 3:
        raise HTTPException(status_code=400, detail="Debe seleccionar exactamente 3 personajes")
    estado_actual = EstadoJuego(ids_elegidos_humano=req.team_ids)
    return {"status": "ok"}

@app.post("/api/config")
def set_config(config: ConfigModel):
    global modo_global, dificultad_global
    modo_global = config.modo
    dificultad_global = config.dificultad
    return {"status": "ok"}

@app.get("/api/state")
def get_state():
    personajes = []
    for i in range(6):
        p = estado_actual.personajes[i]
        personajes.append({
            "id": p.id,
            "nombre": p.nombre,
            "equipo": p.equipo,
            "clase": p.clase,
            "hp": p.hp,
            "hp_max": p.hp_max,
            "vivo": p.vivo
        })
    return {
        "personajes": personajes,
        "turno_actual": estado_actual.obtener_personaje_actual().id,
        "ganador": estado_actual.ganador
    }

@app.post("/api/human_action")
def human_action(action: ActionModel):
    global estado_actual
    personaje_actual = estado_actual.obtener_personaje_actual()
    
    if personaje_actual.equipo != "Humano":
        raise HTTPException(status_code=400, detail="No es tu turno")
    
    # Se guarda automáticamente en CSV tal como se requiere, incluyendo el Modo actual
    jugada = (action.accion_tipo, action.id_objetivo)
    ai_agent.guardar_jugada_csv(estado_actual, jugada, modo_global)
    
    estado_actual.aplicar_accion(jugada)
    return {"status": "ok", "msg": f"Usaste {action.accion_tipo} en ID {action.id_objetivo}"}

@app.post("/api/ai_turn")
def ai_turn():
    global estado_actual
    personaje_actual = estado_actual.obtener_personaje_actual()
    if personaje_actual.equipo != "IA":
        return {"status": "skipped", "msg": "No es turno de IA"}
        
    objetivo_predicho = None
    prediccion_msg = ""
    
    if modo_global == "Adaptativo":
        arbol, _ = ml_trainer.cargar_modelos()
        if arbol is not None:
            try:
                import pandas as pd
                hps = [estado_actual.personajes[i].hp for i in range(6)]
                clase_map = {"Guerrero": 0, "Mago": 1, "Sanador": 2}
                clase_id = clase_map[personaje_actual.clase]
                
                X_actual = pd.DataFrame([hps + [clase_id]], columns=['HP_H1', 'HP_H2', 'HP_H3', 'HP_IA1', 'HP_IA2', 'HP_IA3', 'Clase_Atacante'])
                prediccion = arbol.predict(X_actual)[0]
                objetivo_predicho = int(prediccion)
                nom_obj = estado_actual.personajes[objetivo_predicho].nombre
                prediccion_msg = f"🧠 CEREBRO ML: Predigo que el humano intentará atacar a {nom_obj}. Ajustando Min-Max..."
            except:
                pass

    accion_elegida = ai_agent.obtener_mejor_jugada(estado_actual, dificultad_global, objetivo_predicho)
    if accion_elegida:
        estado_actual.aplicar_accion(accion_elegida)
        return {"status": "ok", "action": accion_elegida, "ml_msg": prediccion_msg}
    else:
        estado_actual.avanzar_turno()
        return {"status": "skipped"}

@app.post("/api/train")
def train_models():
    exito, msg = ml_trainer.entrenar_y_guardar_modelos()
    return {"success": exito, "msg": msg}

@app.post("/api/clear_memory")
def clear_memory():
    for f in ["dataset_jugadas.csv", "modelo_arbol.pkl", "modelo_kmeans.pkl"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass
    return {"status": "ok", "msg": "Memoria de IA borrada con éxito."}

# ESTAS SON LAS 3 RUTAS CLAVE PARA QUE LA PROFESORA DESCARGUE LOS ARCHIVOS
@app.get("/api/download/{filename}")
def download_file(filename: str):
    valid_files = ["dataset_jugadas.csv", "modelo_arbol.pkl", "modelo_kmeans.pkl"]
    if filename not in valid_files:
        raise HTTPException(status_code=404, detail="Archivo no permitido")
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="El archivo aún no ha sido generado. ¡Juega/Entrena primero!")
    
    return FileResponse(filename, filename=filename, media_type="application/octet-stream")

@app.get("/api/graph")
def get_graph():
    csv_path = "dataset_jugadas.csv"
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=400, detail="Juega primero para generar datos.")
    
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.cluster import KMeans
    
    df = pd.read_csv(csv_path)
    if len(df) < 5:
        raise HTTPException(status_code=400, detail="Faltan datos. Juega al menos 5 turnos.")
        
    df['Salud_Humano'] = df['HP_H1'] + df['HP_H2'] + df['HP_H3']
    df['Salud_IA'] = df['HP_IA1'] + df['HP_IA2'] + df['HP_IA3']
    
    X_kmeans = df[['Salud_Humano', 'Salud_IA']]
    kmeans = KMeans(n_clusters=2, random_state=42, n_init='auto')
    df['Cluster'] = kmeans.fit_predict(X_kmeans)
    
    plt.figure(figsize=(10, 6))
    
    df_clasico = df[df['Modo_IA'] == 0]
    df_adaptativo = df[df['Modo_IA'] == 1]
    
    if not df_clasico.empty:
        sns.scatterplot(data=df_clasico[df_clasico['Cluster']==0], x='Salud_Humano', y='Salud_IA', marker='o', color='#e74c3c', s=150, edgecolor='black', label='Clásico (Agresivo)')
        sns.scatterplot(data=df_clasico[df_clasico['Cluster']==1], x='Salud_Humano', y='Salud_IA', marker='o', color='#3498db', s=150, edgecolor='black', label='Clásico (Conservador)')
        
    if not df_adaptativo.empty:
        sns.scatterplot(data=df_adaptativo[df_adaptativo['Cluster']==0], x='Salud_Humano', y='Salud_IA', marker='^', color='#e74c3c', s=200, edgecolor='black', label='Adaptativo (Agresivo)')
        sns.scatterplot(data=df_adaptativo[df_adaptativo['Cluster']==1], x='Salud_Humano', y='Salud_IA', marker='^', color='#3498db', s=200, edgecolor='black', label='Adaptativo (Conservador)')
        
    # Extraer y graficar Centroides
    centros = kmeans.cluster_centers_
    plt.scatter(centros[:, 0], centros[:, 1], marker='X', color='black', s=400, edgecolor='white', linewidths=2, label='Centroides Matemáticos', zorder=5)
        
    max_val = max(df['Salud_Humano'].max(), df['Salud_IA'].max()) + 20
    plt.plot([0, max_val], [0, max_val], 'k:', label='Línea de Equidistancia (Y = X)')
    
    plt.title("Gráfico Comparativo: K-Means (Clásico vs Adaptativo)")
    plt.xlabel("Salud Total del Humano")
    plt.ylabel("Salud Total de la IA")
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    
    out_path = "static/kmeans_graph.png"
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return {"url": "/static/kmeans_graph.png"}
