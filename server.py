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
    
    # Se guarda automáticamente en CSV tal como se requiere
    jugada = (action.accion_tipo, action.id_objetivo)
    ai_agent.guardar_jugada_csv(estado_actual, jugada)
    
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

#descargar archivos
@app.get("/api/download/{filename}")
def download_file(filename: str):
    valid_files = ["dataset_jugadas.csv", "modelo_arbol.pkl", "modelo_kmeans.pkl"]
    if filename not in valid_files:
        raise HTTPException(status_code=404, detail="Archivo no permitido")
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="El archivo aún no ha sido generado. ¡Juega/Entrena primero!")
    
    return FileResponse(filename, filename=filename, media_type="application/octet-stream")
