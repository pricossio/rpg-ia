import copy
import random

# Catálogo global de 9 personajes únicos
CATALOGO_PERSONAJES = [
    # Guerreros
    {"id": 1, "nombre": "Caballero", "clase": "Guerrero", "hp": 100, "ataque": 25},
    {"id": 2, "nombre": "Paladín", "clase": "Guerrero", "hp": 130, "ataque": 15},
    {"id": 3, "nombre": "Asesino", "clase": "Guerrero", "hp": 70, "ataque": 40},
    # Magos
    {"id": 4, "nombre": "Piromante", "clase": "Mago", "hp": 60, "ataque": 45},
    {"id": 5, "nombre": "Nigromante", "clase": "Mago", "hp": 70, "ataque": 35},
    {"id": 6, "nombre": "Ilusionista", "clase": "Mago", "hp": 50, "ataque": 50},
    # Sanadores
    {"id": 7, "nombre": "Clérigo", "clase": "Sanador", "hp": 80, "ataque": 10, "cura": 35},
    {"id": 8, "nombre": "Druida", "clase": "Sanador", "hp": 90, "ataque": 10, "cura": 30},
    {"id": 9, "nombre": "Bardo", "clase": "Sanador", "hp": 70, "ataque": 10, "cura": 40}
]

class Personaje:
    def __init__(self, id_char, nombre, equipo, clase, hp_max, ataque, cura=0):
        self.id = id_char
        self.nombre = nombre
        self.equipo = equipo # 'Humano' o 'IA'
        self.clase = clase # 'Guerrero', 'Mago', 'Sanador'
        self.hp_max = hp_max
        self.hp = hp_max
        self.ataque = ataque
        self.cura_pot = cura
        self.vivo = True

    def recibir_dano(self, cantidad):
        self.hp -= cantidad
        if self.hp <= 0:
            self.hp = 0
            self.vivo = False

    def curar(self, cantidad):
        if self.vivo:
            self.hp += cantidad
            if self.hp > self.hp_max:
                self.hp = self.hp_max

class EstadoJuego:
    def __init__(self, ids_elegidos_humano=None):
        self.personajes = {}
        
        # Si no se enviaron personajes, poner por defecto para evitar errores
        if not ids_elegidos_humano or len(ids_elegidos_humano) != 3:
            ids_elegidos_humano = [1, 4, 7] # Caballero, Piromante, Clérigo
            
        todos_ids = [c["id"] for c in CATALOGO_PERSONAJES]
        ids_disponibles_ia = [x for x in todos_ids if x not in ids_elegidos_humano]
        ids_elegidos_ia = random.sample(ids_disponibles_ia, 3)

        idx = 0
        # Crear 3 Humanos
        for pid in ids_elegidos_humano:
            t = next(c for c in CATALOGO_PERSONAJES if c["id"] == pid)
            self.personajes[idx] = Personaje(idx, t["nombre"], "Humano", t["clase"], t["hp"], t["ataque"], t.get("cura", 0))
            idx += 1
            
        # Crear 3 IAs
        for pid in ids_elegidos_ia:
            t = next(c for c in CATALOGO_PERSONAJES if c["id"] == pid)
            self.personajes[idx] = Personaje(idx, f"{t['nombre']} Oscuro", "IA", t["clase"], t["hp"], t["ataque"], t.get("cura", 0))
            idx += 1

        # Intercalamos los turnos (H1, IA1, H2, IA2, H3, IA3)
        self.orden_turnos = [0, 3, 1, 4, 2, 5]
        self.indice_turno = 0
        self.ganador = None # 'Humano', 'IA', o None

    def clonar(self):
        return copy.deepcopy(self)

    def obtener_personaje_actual(self):
        return self.personajes[self.orden_turnos[self.indice_turno]]

    def obtener_acciones_validas(self):
        atacante = self.obtener_personaje_actual()
        if not atacante.vivo:
            return [] 

        acciones = []
        equipo_contrario = "IA" if atacante.equipo == "Humano" else "Humano"
        
        # Carta 1: Atacar y Carta 2: Especial (Objetivo = Enemigo)
        for p_id, p in self.personajes.items():
            if p.vivo and p.equipo == equipo_contrario:
                acciones.append(("Atacar", p.id))
                acciones.append(("Especial", p.id))
        
        # Carta 3: Curar (Objetivo = Aliado, incluso a sí mismo)
        for p_id, p in self.personajes.items():
            if p.vivo and p.equipo == atacante.equipo:
                acciones.append(("Curar", p.id))
                    
        return acciones

    def aplicar_accion(self, accion):
        tipo_accion, id_objetivo = accion
        atacante = self.obtener_personaje_actual()
        objetivo = self.personajes[id_objetivo]

        if tipo_accion == "Atacar":
            objetivo.recibir_dano(atacante.ataque)
            
        elif tipo_accion == "Especial":
            if atacante.clase == "Guerrero":
                # Golpe Temerario (1.5x daño, pierde 10 HP)
                objetivo.recibir_dano(int(atacante.ataque * 1.5))
                atacante.recibir_dano(10)
            elif atacante.clase == "Mago":
                # Robo de Vida (Daño base, se cura 30%)
                dmg = atacante.ataque
                objetivo.recibir_dano(dmg)
                atacante.curar(int(dmg * 0.3))
            elif atacante.clase == "Sanador":
                # Castigo Sagrado (1.2x daño)
                objetivo.recibir_dano(int(atacante.ataque * 1.2))
                
        elif tipo_accion == "Curar":
            if atacante.clase == "Sanador":
                objetivo.curar(35) # Curación Mayor
            else:
                objetivo.curar(20) # Poción Básica
            
        self.verificar_victoria()
        self.avanzar_turno()

    def avanzar_turno(self):
        self.indice_turno = (self.indice_turno + 1) % len(self.orden_turnos)
        if self.ganador is None:
            intentos = 0
            while not self.obtener_personaje_actual().vivo and intentos < 6:
                self.indice_turno = (self.indice_turno + 1) % len(self.orden_turnos)
                intentos += 1

    def verificar_victoria(self):
        vivos_humano = sum(1 for p in self.personajes.values() if p.equipo == "Humano" and p.vivo)
        vivos_ia = sum(1 for p in self.personajes.values() if p.equipo == "IA" and p.vivo)
        
        if vivos_humano == 0:
            self.ganador = "IA"
        elif vivos_ia == 0:
            self.ganador = "Humano"
