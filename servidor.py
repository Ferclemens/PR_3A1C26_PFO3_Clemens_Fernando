import socket
import threading
import json
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "tareas_distribuidas.db"
PORT = 5000
HOST = '127.0.0.1'

# --- CONFIGURACIÓN DEL POOL DE WORKERS ---
MAX_WORKERS = 5  
workers_pool = threading.Semaphore(MAX_WORKERS)

# --- CONFIGURACIÓN DE COLORES PARA LA TERMINAL (ANSI) ---
RESET = "\033[0m"
VERDE = "\033[32m"
CIAN = "\033[36m"
AMARILLO = "\033[33m"
ROJO = "\033[31m"
MAGENTA = "\033[35m"

def get_timestamp():
    """Retorna la hora actual formateada para el log."""
    return f"[{datetime.now().strftime('%H:%M:%S')}]"

def init_db():
    """Inicializa la base de datos local."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def manejar_cliente(conn_client, addr):
    """Función que ejecuta cada Worker para atender a un cliente."""
    # Métricas del Pool
    workers_disponibles = workers_pool._value 
    workers_activos = MAX_WORKERS - workers_disponibles
    
    print(f"\n{VERDE}{get_timestamp()} [WORKER ASIGNADO]{RESET} Conexion aceptada desde {addr}")
    print(f"      {CIAN}TELEMETRIA POOL:{RESET} {workers_activos}/{MAX_WORKERS} Workers en uso | Libres: {workers_disponibles}")
    
    while True:
        try:
            data = conn_client.recv(1024).decode('utf-8')
            if not data:
                print(f"{AMARILLO}{get_timestamp()} [INFO]{RESET} El cliente {addr} cerro la conexion ordenadamente.")
                break
            
            peticion = json.loads(data)
            comando = peticion.get("comando")
            payload = peticion.get("payload", {})
            
            print(f"{MAGENTA}{get_timestamp()} [COMANDO ENTRANTE]{RESET} '{comando}' de {addr}")
            respuesta = {"status": 400, "mensaje": "Comando no reconocido"}
            
            # Procesamiento de comandos
            if comando == "registro":
                respuesta = registrar_usuario(payload)
            elif comando == "login":
                respuesta = login_usuario(payload)
            elif comando == "ver_tareas":
                respuesta = obtener_tareas()
                
            print(f"      {VERDE}RESPUESTA ENVIADA:{RESET} Status {respuesta.get('status')} enviado a {addr}")
            conn_client.sendall(json.dumps(respuesta).encode('utf-8'))
            
        except ConnectionResetError:
            print(f"{ROJO}{get_timestamp()} [ADVERTENCIA]{RESET} Conexion interrumpida abruptamente por el cliente {addr}.")
            break
        except Exception as e:
            print(f"{ROJO}{get_timestamp()} [ERROR]{RESET} En el hilo de {addr}: {str(e)}")
            respuesta = {"status": 500, "error": str(e)}
            conn_client.sendall(json.dumps(respuesta).encode('utf-8'))
            break

    # Liberación del hilo del pool
    workers_pool.release()
    nuevos_disponibles = workers_pool._value
    nuevos_activos = MAX_WORKERS - nuevos_disponibles
    
    print(f"\n{AMARILLO}{get_timestamp()} [WORKER LIBERADO]{RESET} Conexion finalizada con {addr}")
    print(f"      {CIAN}TELEMETRIA POOL:{RESET} {nuevos_activos}/{MAX_WORKERS} Workers en uso | Libres: {nuevos_disponibles}")
    conn_client.close()

# --- LÓGICA DE NEGOCIO ---
def registrar_usuario(payload):
    usuario = payload.get('usuario')
    password = payload.get('password')
    if not usuario or not password:
        return {"status": 400, "error": "Faltan datos"}
    
    password_hashed = generate_password_hash(password)
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (usuario, password_hash) VALUES (?, ?)", (usuario, password_hashed))
        conn.commit()
        conn.close()
        return {"status": 201, "mensaje": "Usuario registrado exitosamente"}
    except sqlite3.IntegrityError:
        return {"status": 409, "error": "El usuario ya existe"}

def login_usuario(payload):
    usuario = payload.get('usuario')
    password = payload.get('password')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM usuarios WHERE usuario = ?", (usuario,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[0], password):
        return {"status": 200, "mensaje": "Inicio de sesion exitoso", "token_simulado": "acceso-concedido"}
    return {"status": 401, "error": "Credenciales invalidas"}

def obtener_tareas():
    html_simulado = "<h1>Bienvenido al Sistema de Gestion de Tareas</h1><p>Conectado via Sockets.</p>"
    return {"status": 200, "contenido": html_simulado}

# --- SERVIDOR PRINCIPAL ---
def iniciar_servidor():
    init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server.bind((HOST, PORT))
    server.listen()
    print(f"{VERDE}=================================================================={RESET}")
    print(f"{VERDE}[SERVIDOR ACTIVO] Escuchando conexiones TCP en {HOST}:{PORT}...{RESET}")
    print(f"{CIAN}[CONFIG] Pool restringido a un maximo estricto de {MAX_WORKERS} Workers.{RESET}")
    print(f"{VERDE}=================================================================={RESET}")

    try:
        while True:
            conn_client, addr = server.accept()
            workers_pool.acquire()
            
            hilo_worker = threading.Thread(target=manejar_cliente, args=(conn_client, addr))
            hilo_worker.start()
            
    except KeyboardInterrupt:
        print(f"\n{ROJO}{get_timestamp()} [APAGANDO SERVIDOR]{RESET} Cerrando sockets y base de datos de manera segura...")
    finally:
        server.close()

if __name__ == '__main__':
    iniciar_servidor()