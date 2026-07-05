import math
import os
import copy

def evaluar_estado(estado, objetivo_predicho=None):
    if estado.ganador == "IA": return 99999
    elif estado.ganador == "Humano": return -99999
        
    hp_ia = sum(p.hp for p in estado.personajes.values() if p.equipo == "IA" and p.vivo)
    hp_humano = sum(p.hp for p in estado.personajes.values() if p.equipo == "Humano" and p.vivo)
    vivos_ia = sum(1 for p in estado.personajes.values() if p.equipo == "IA" and p.vivo)
    vivos_humano = sum(1 for p in estado.personajes.values() if p.equipo == "Humano" and p.vivo)
    
    score = (hp_ia - hp_humano) + (vivos_ia * 500) - (vivos_humano * 500)
    
    # LA MAGIA DEL MODO ADAPTATIVO
    if objetivo_predicho is not None and objetivo_predicho in estado.personajes:
        p_obj = estado.personajes[objetivo_predicho]
        if p_obj.equipo == "IA":
            # Si el ML predice que el humano atacará a este personaje IA, 
            # le damos un bono enorme a los tableros donde este personaje se mantiene con alta vida.
            # Esto hará que el Min-Max decida defenderlo, curarlo o atacar agresivamente para protegerlo.
            score += (p_obj.hp * 10) 
            
    return score

def minimax_alfa_beta(estado, profundidad, alfa, beta, maximizando, objetivo_predicho=None):
    if profundidad == 0 or estado.ganador is not None:
        return evaluar_estado(estado, objetivo_predicho), None

    acciones = estado.obtener_acciones_validas()
    if not acciones:
        return evaluar_estado(estado, objetivo_predicho), None

    mejor_accion = acciones[0]

    if maximizando:
        max_eval = -math.inf
        for accion in acciones:
            estado_clonado = estado.clonar()
            estado_clonado.aplicar_accion(accion)
            proximo_es_ia = estado_clonado.obtener_personaje_actual().equipo == "IA"
            evaluacion, _ = minimax_alfa_beta(estado_clonado, profundidad - 1, alfa, beta, proximo_es_ia, objetivo_predicho)
            if evaluacion > max_eval:
                max_eval = evaluacion
                mejor_accion = accion
            alfa = max(alfa, evaluacion)
            if beta <= alfa:
                break
        return max_eval, mejor_accion
    else:
        min_eval = math.inf
        for accion in acciones:
            estado_clonado = estado.clonar()
            estado_clonado.aplicar_accion(accion)
            proximo_es_ia = estado_clonado.obtener_personaje_actual().equipo == "IA"
            evaluacion, _ = minimax_alfa_beta(estado_clonado, profundidad - 1, alfa, beta, proximo_es_ia, objetivo_predicho)
            if evaluacion < min_eval:
                min_eval = evaluacion
                mejor_accion = accion
            beta = min(beta, evaluacion)
            if beta <= alfa:
                break
        return min_eval, mejor_accion

def obtener_mejor_jugada(estado, nivel_dificultad, objetivo_predicho=None):
    _, mejor_accion = minimax_alfa_beta(estado, nivel_dificultad, -math.inf, math.inf, True, objetivo_predicho)
    return mejor_accion

def guardar_jugada_csv(estado_previo, accion, modo_global, archivo="dataset_jugadas.csv"):
    cabeceras = not os.path.exists(archivo)
    with open(archivo, "a", encoding="utf-8") as f:
        if cabeceras:
            f.write("HP_H1,HP_H2,HP_H3,HP_IA1,HP_IA2,HP_IA3,Clase_Atacante,Tipo_Accion,Modo_IA,ID_Objetivo\n")
            
        hps = [estado_previo.personajes[i].hp for i in range(6)]
        atacante = estado_previo.obtener_personaje_actual()
        clase_map = {"Guerrero": 0, "Mago": 1, "Sanador": 2}
        clase_id = clase_map[atacante.clase]
        tipo_accion, id_objetivo = accion
        accion_id = 0 if tipo_accion == "Atacar" else 1
        
        # 0 = Clásico, 1 = Adaptativo
        modo_id = 0 if modo_global == "Clásico" else 1
        
        fila = hps + [clase_id, accion_id, modo_id, id_objetivo]
        f.write(",".join(map(str, fila)) + "\n")
