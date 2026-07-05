import pygame
import sys
import time
from game_logic import EstadoJuego
import ai_agent
import ml_trainer

# Pygame Setup
pygame.init()
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Batalla Táctica RPG - IA Híbrida")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (50, 50, 50)
BLUE = (50, 150, 255)
RED = (255, 50, 50)
GREEN = (50, 255, 50)

font_small = pygame.font.SysFont("consolas", 14)
font_med = pygame.font.SysFont("consolas", 20)
font_large = pygame.font.SysFont("consolas", 30)

def draw_text(surface, text, font, color, x, y, center=False):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    surface.blit(text_surface, text_rect)

def draw_health_bar(surface, x, y, hp, hp_max):
    pygame.draw.rect(surface, RED, (x, y, 100, 10))
    if hp > 0:
        ratio = hp / hp_max
        pygame.draw.rect(surface, GREEN, (x, y, 100 * ratio, 10))

class Boton:
    def __init__(self, x, y, w, h, text):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
    def draw(self, surface):
        pygame.draw.rect(surface, GRAY, self.rect)
        pygame.draw.rect(surface, WHITE, self.rect, 2)
        draw_text(surface, self.text, font_med, WHITE, self.rect.centerx, self.rect.centery, center=True)
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

def menu_principal():
    btn_clasico = Boton(WIDTH//2 - 200, 200, 400, 50, "1. Jugar Clásico (Generar CSV)")
    btn_entrenar = Boton(WIDTH//2 - 200, 280, 400, 50, "2. Entrenar IA (Generar .pkl)")
    btn_adaptativo = Boton(WIDTH//2 - 200, 360, 400, 50, "3. Jugar Adaptativo (Usa .pkl)")
    btn_salir = Boton(WIDTH//2 - 200, 440, 400, 50, "4. Salir")
    
    mensaje_info = "Selecciona una opción"

    while True:
        screen.fill(BLACK)
        draw_text(screen, "PROYECTO FINAL IA - RPG HÍBRIDO", font_large, WHITE, WIDTH//2, 100, center=True)
        
        btn_clasico.draw(screen)
        btn_entrenar.draw(screen)
        btn_adaptativo.draw(screen)
        btn_salir.draw(screen)
        
        draw_text(screen, mensaje_info, font_med, GREEN, WIDTH//2, 520, center=True)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn_clasico.is_clicked(event.pos):
                    # Dificultad 4 por defecto para demostración
                    jugar_partida(dificultad=4, modo_adaptativo=False) 
                elif btn_entrenar.is_clicked(event.pos):
                    mensaje_info = "Entrenando modelo scikit-learn. Por favor espera..."
                    screen.fill(BLACK)
                    draw_text(screen, mensaje_info, font_med, GREEN, WIDTH//2, HEIGHT//2, center=True)
                    pygame.display.flip()
                    exito, msj = ml_trainer.entrenar_y_guardar_modelos()
                    mensaje_info = msj
                elif btn_adaptativo.is_clicked(event.pos):
                    arbol, _ = ml_trainer.cargar_modelos()
                    if arbol is None:
                        mensaje_info = "ERROR: Entrena la IA primero (Opción 2)"
                    else:
                        jugar_partida(dificultad=4, modo_adaptativo=True, modelo_arbol=arbol)
                elif btn_salir.is_clicked(event.pos):
                    pygame.quit(); sys.exit()

def jugar_partida(dificultad, modo_adaptativo=False, modelo_arbol=None):
    estado = EstadoJuego()
    mensaje_accion = "Partida iniciada."
    mensaje_ml = "Búsqueda Min-Max Clásica Activada." if not modo_adaptativo else "Modo Adaptativo Activado."
    
    while estado.ganador is None:
        screen.fill(BLACK)
        
        # Textos de la cabecera
        draw_text(screen, "EQUIPO HUMANO", font_med, BLUE, 150, 50, center=True)
        draw_text(screen, "EQUIPO IA", font_med, RED, WIDTH - 150, 50, center=True)
        draw_text(screen, mensaje_accion, font_med, WHITE, WIDTH//2, 30, center=True)
        
        # Panel Analytics
        pygame.draw.rect(screen, (20, 20, 20), (0, HEIGHT - 100, WIDTH, 100))
        draw_text(screen, "PANEL ANALYTICS (CEREBRO IA):", font_small, GREEN, 20, HEIGHT - 90)
        draw_text(screen, mensaje_ml, font_med, GREEN, 20, HEIGHT - 60)
        
        # Dibujar a los personajes como cajitas
        rects_personajes = {}
        for p in estado.personajes.values():
            if p.equipo == "Humano":
                x = 100
                y = 100 + p.id * 100
            else:
                x = WIDTH - 200
                y = 100 + (p.id - 3) * 100
                
            color = BLUE if p.equipo == "Humano" else RED
            if not p.vivo: color = GRAY
            
            rect = pygame.Rect(x, y, 100, 50)
            rects_personajes[p.id] = rect
            
            # Resaltar de quién es el turno
            if p.id == estado.obtener_personaje_actual().id and p.vivo:
                pygame.draw.rect(screen, WHITE, (x-5, y-5, 110, 60), 3)
                
            pygame.draw.rect(screen, color, rect)
            draw_text(screen, p.nombre, font_small, WHITE, x + 50, y + 25, center=True)
            draw_health_bar(screen, x, y + 60, p.hp, p.hp_max)

        pygame.display.flip()
        
        personaje_actual = estado.obtener_personaje_actual()
        acciones = estado.obtener_acciones_validas()
        
        if not acciones:
            estado.avanzar_turno()
            continue

        if personaje_actual.equipo == "Humano":
            mensaje_accion = f"Tu turno ({personaje_actual.nombre}): Haz clic en un enemigo."
            if personaje_actual.clase == "Sanador":
                mensaje_accion = "Tu turno (Sanador): Clic en enemigo (Atacar) o aliado herido (Curar)."
                
            esperando_clic = True
            accion_elegida = None
            
            while esperando_clic:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit(); sys.exit()
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        pos = event.pos
                        for pid, rect in rects_personajes.items():
                            if rect.collidepoint(pos):
                                for acc in acciones:
                                    if acc[1] == pid:
                                        accion_elegida = acc
                                        esperando_clic = False
                                        break
                
            if accion_elegida:
                ai_agent.guardar_jugada_csv(estado, accion_elegida)
                estado.aplicar_accion(accion_elegida)
                
        else:
            mensaje_accion = f"Turno de la IA ({personaje_actual.nombre}). Pensando..."
            objetivo_predicho = None
            
            if modo_adaptativo and modelo_arbol is not None:
                try:
                    import pandas as pd
                    def extraer(est):
                        hps = [est.personajes[i].hp for i in range(6)]
                        clase_map = {"Guerrero": 0, "Mago": 1, "Sanador": 2}
                        return hps + [clase_map[est.obtener_personaje_actual().clase]]
                        
                    X_actual = pd.DataFrame([extraer(estado)], columns=['HP_H1', 'HP_H2', 'HP_H3', 'HP_IA1', 'HP_IA2', 'HP_IA3', 'Clase_Atacante'])
                    prediccion = modelo_arbol.predict(X_actual)[0]
                    objetivo_predicho = prediccion
                    nom_obj = estado.personajes[objetivo_predicho].nombre
                    mensaje_ml = f"Predicción ML: Humano atacará a {nom_obj}. Ajustando táctica..."
                except:
                    mensaje_ml = "Error al ejecutar modelo. ¿Instalaste pandas?"
            else:
                mensaje_ml = f"Calculando el futuro con Búsqueda Min-Max (Profundidad: {dificultad})"
                
            # Renderizamos una vez más rápido para mostrar el texto "Pensando..."
            pygame.display.flip()
            pygame.event.pump() # Evitar que la ventana se congele

            # La IA elige la jugada
            accion_elegida = ai_agent.obtener_mejor_jugada(estado, dificultad, objetivo_predicho)
            if accion_elegida:
                estado.aplicar_accion(accion_elegida)
            else:
                estado.avanzar_turno()
            time.sleep(1.5) # Pausa dramática

    # Pantalla de Fin de Juego
    screen.fill(BLACK)
    draw_text(screen, f"¡EL GANADOR ES: {estado.ganador.upper()}!", font_large, GREEN, WIDTH//2, HEIGHT//2, center=True)
    draw_text(screen, "Haz clic en cualquier parte para volver al menú...", font_med, WHITE, WIDTH//2, HEIGHT//2 + 50, center=True)
    pygame.display.flip()
    
    esperando = True
    while esperando:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or event.type == pygame.MOUSEBUTTONDOWN:
                esperando = False

if __name__ == "__main__":
    menu_principal()
