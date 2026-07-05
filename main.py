import os
import time
from game_logic import EstadoJuego
import ai_agent
import ml_trainer

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def imprimir_estado(estado):
    print("="*50)
    print("       ⚔️ BATALLA TÁCTICA RPG ⚔️")
    print("="*50)
    
    print("\n[ EQUIPO HUMANO ]")
    for i in range(3):
        p = estado.personajes[i]
        estado_str = f"HP: {p.hp:3d}/{p.hp_max}" if p.vivo else "☠️ MUERTO"
        print(f"  {p.id}. {p.nombre:15s} | {estado_str}")
        
    print("\n[ EQUIPO IA ]")
    for i in range(3, 6):
        p = estado.personajes[i]
        estado_str = f"HP: {p.hp:3d}/{p.hp_max}" if p.vivo else "☠️ MUERTO"
        print(f"  {p.id}. {p.nombre:15s} | {estado_str}")
    print("\n" + "="*50)

def extraer_caracteristicas_actuales(estado):
    # Esto transforma el tablero en una fila como la del CSV para que el modelo la entienda
    hps = [estado.personajes[i].hp for i in range(6)]
    atacante = estado.obtener_personaje_actual()
    clase_map = {"Guerrero": 0, "Mago": 1, "Sanador": 2}
    clase_id = clase_map[atacante.clase]
    return hps + [clase_id]

def jugar_partida(dificultad, modo_adaptativo=False, modelo_arbol=None):
    estado = EstadoJuego()
    
    while estado.ganador is None:
        limpiar_pantalla()
        imprimir_estado(estado)
        
        personaje_actual = estado.obtener_personaje_actual()
        print(f"\nEs el turno de: >> {personaje_actual.nombre} <<")
        
        acciones = estado.obtener_acciones_validas()
        if not acciones:
            estado.avanzar_turno()
            continue
            
        if personaje_actual.equipo == "Humano":
            print("Elige tu acción:")
            for i, accion in enumerate(acciones):
                tipo, id_obj = accion
                nom_obj = estado.personajes[id_obj].nombre
                print(f" [{i}] {tipo} a {nom_obj}")
                
            eleccion = -1
            while eleccion < 0 or eleccion >= len(acciones):
                try:
                    eleccion = int(input("\nIngresa el número de tu acción: "))
                except ValueError:
                    pass
            accion_elegida = acciones[eleccion]
            
            ai_agent.guardar_jugada_csv(estado, accion_elegida)
            estado.aplicar_accion(accion_elegida)
            
        else:
            objetivo_predicho = None
            if modo_adaptativo and modelo_arbol is not None:
                # Predecir qué hará el humano usando scikit-learn
                try:
                    import pandas as pd
                    X_actual = pd.DataFrame([extraer_caracteristicas_actuales(estado)], 
                                            columns=['HP_H1', 'HP_H2', 'HP_H3', 'HP_IA1', 'HP_IA2', 'HP_IA3', 'Clase_Atacante'])
                    prediccion = modelo_arbol.predict(X_actual)
                    objetivo_predicho = prediccion[0]
                    nom_obj = estado.personajes[objetivo_predicho].nombre
                    print(f"\n🧠 [CEREBRO ML] Predicción: El humano intentará atacar a >> {nom_obj} <<")
                    print("🧠 [CEREBRO ML] Ajustando heurística Min-Max para defender...")
                except Exception as e:
                    pass

            print(f"La IA está pensando (Min-Max Profundidad {dificultad})...")
            accion_elegida = ai_agent.obtener_mejor_jugada(estado, dificultad, objetivo_predicho)
            
            if accion_elegida:
                tipo, id_obj = accion_elegida
                nom_obj = estado.personajes[id_obj].nombre
                print(f"¡La IA decidió {tipo} a {nom_obj}!")
                time.sleep(3) # Pausa para que el jugador alcance a leer la predicción
                estado.aplicar_accion(accion_elegida)
            else:
                estado.avanzar_turno()
            
    limpiar_pantalla()
    imprimir_estado(estado)
    print(f"\n🏆 ¡EL GANADOR ES: {estado.ganador.upper()}! 🏆")
    input("\nPresiona Enter para volver al menú principal...")

def menu_principal():
    while True:
        limpiar_pantalla()
        print("========================================")
        print("      PROYECTO FINAL IA - JUEGO RPG     ")
        print("========================================")
        print("[1] Jugar Modo Clásico (Búsqueda Min-Max)")
        print("[2] Entrenar Cerebro IA (Generar archivos .pkl)")
        print("[3] Jugar Modo Adaptativo (Machine Learning)")
        print("[4] Salir")
        print("========================================")
        
        opcion = input("Elige una opción: ")
        
        if opcion == "1":
            print("\nElige Dificultad para la máquina:")
            print("[1] Fácil (Profundidad 1)")
            print("[2] Intermedio (Profundidad 2)")
            print("[3] Difícil (Profundidad 4)")
            dif = input("Dificultad: ")
            nivel = 1
            if dif == "2": nivel = 2
            elif dif == "3": nivel = 4
            jugar_partida(dificultad=nivel, modo_adaptativo=False)
            
        elif opcion == "2":
            print("\nIniciando entrenamiento del modelo con el archivo dataset_jugadas.csv...")
            exito, mensaje = ml_trainer.entrenar_y_guardar_modelos()
            print(mensaje)
            input("\nPresiona Enter para continuar...")
            
        elif opcion == "3":
            arbol, kmeans = ml_trainer.cargar_modelos()
            if arbol is None:
                print("\nERROR: No se encontraron los modelos .pkl.")
                print("Por favor usa la opción [2] primero para entrenar la IA.")
                input("Presiona Enter para continuar...")
            else:
                print("\nIniciando MODO ADAPTATIVO (Nivel Difícil por defecto)")
                jugar_partida(dificultad=4, modo_adaptativo=True, modelo_arbol=arbol)
            
        elif opcion == "4":
            break

if __name__ == "__main__":
    menu_principal()
