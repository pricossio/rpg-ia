import os
import pickle

def entrenar_y_guardar_modelos(archivo_csv="dataset_jugadas.csv"):
    try:
        import pandas as pd
        from sklearn.tree import DecisionTreeClassifier
        from sklearn.cluster import KMeans
    except ImportError:
        return False, "Faltan librerías. Abre una consola y escribe: pip install pandas scikit-learn"
        
    if not os.path.exists(archivo_csv):
        return False, f"No se encontró el archivo {archivo_csv}. Juega el Modo Clásico primero."
        
    try:
        df = pd.read_csv(archivo_csv)
        if len(df) < 5:
            return False, "Muy pocos datos en el CSV. ¡Juega al menos 5 o 6 turnos para que la IA tenga algo que aprender!"
            
        # Extraemos las características (Features): Las vidas de todos y quién está atacando
        X = df[['HP_H1', 'HP_H2', 'HP_H3', 'HP_IA1', 'HP_IA2', 'HP_IA3', 'Clase_Atacante']]
        
        # Objetivo (Target): A quién decidió atacar el humano
        y_objetivo = df['ID_Objetivo']
        
        # MODELO 1: Aprendizaje Supervisado (Árbol de Decisión)
        # Predecirá a quién va a atacar el humano basándose en las barras de vida
        modelo_arbol = DecisionTreeClassifier(max_depth=5, random_state=42)
        modelo_arbol.fit(X, y_objetivo)
        
        # MODELO 2: Aprendizaje No Supervisado (K-Means)
        # Agrupará los estilos de los tableros en 3 clústeres (ej: "Peligroso", "Seguro", "Equilibrado")
        modelo_kmeans = KMeans(n_clusters=3, random_state=42, n_init='auto')
        modelo_kmeans.fit(X)
        
        # Guardamos los archivos .pkl internamente
        with open("modelo_arbol.pkl", "wb") as f:
            pickle.dump(modelo_arbol, f)
            
        with open("modelo_kmeans.pkl", "wb") as f:
            pickle.dump(modelo_kmeans, f)
            
        return True, "¡Entrenamiento exitoso! Se han generado los archivos 'modelo_arbol.pkl' y 'modelo_kmeans.pkl'."
    except Exception as e:
        return False, f"Error durante el entrenamiento: {e}"

def cargar_modelos():
    try:
        with open("modelo_arbol.pkl", "rb") as f:
            arbol = pickle.load(f)
        with open("modelo_kmeans.pkl", "rb") as f:
            kmeans = pickle.load(f)
        return arbol, kmeans
    except FileNotFoundError:
        return None, None
