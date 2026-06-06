import socket
import json

HOST = '127.0.0.1'
PORT = 5000

def enviar_peticion(comando, payload=None):
    """Función utilitaria para abrir un socket, enviar datos y recibir respuesta."""
    if payload is None:
        payload = {}
        
    peticion = {
        "comando": comando,
        "payload": payload
    }
    
    try:
        # Crear socket TCP
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
        
        # Enviar JSON serializado
        client_socket.sendall(json.dumps(peticion).encode('utf-8'))
        
        # Recibir respuesta del Worker
        respuesta_bytes = client_socket.recv(4096)
        client_socket.close()
        
        return json.loads(respuesta_bytes.decode('utf-8'))
    except ConnectionRefusedError:
        print("\n[ERROR] No se pudo conectar al servidor. ¿Está encendido?")
        return {"status": 500, "error": "Servidor inaccesible"}

def menu():
    print("\n--- SISTEMA DE GESTIÓN DE TAREAS (DISTRIBUIDO) ---")
    print("1. Registrar nuevo usuario")
    print("2. Iniciar sesión")
    print("3. Ver página de bienvenida (Tareas)")
    print("4. Salir")
    return input("Seleccione una opción: ")

def registrar_usuario():
    usuario = input("Ingrese nombre de usuario: ")
    password = input("Ingrese contraseña: ")
    payload = {"usuario": usuario, "password": password}
    
    res = enviar_peticion("registro", payload)
    print(f"\nEstado: {res.get('status')}")
    print(f"Respuesta: {res.get('mensaje', res.get('error'))}")

def login_usuario():
    usuario = input("Ingrese nombre de usuario: ")
    password = input("Ingrese contraseña: ")
    payload = {"usuario": usuario, "password": password}
    
    res = enviar_peticion("login", payload)
    if res.get('status') == 200:
        print(f"\n¡{res.get('mensaje')}!")
        return True
    else:
        print(f"\nError: {res.get('error')}")
        return False

def ver_tareas():
    res = enviar_peticion("ver_tareas")
    if res.get('status') == 200:
        print("\n--- Contenido Recibido desde el Servidor ---")
        print(res.get('contenido'))
    else:
        print(f"\nError al acceder a las tareas: {res.get('error')}")

if __name__ == "__main__":
    while True:
        opcion = menu()
        if opcion == "1":
            registrar_usuario()
        elif opcion == "2":
            login_usuario()
        elif opcion == "3":
            ver_tareas()
        elif opcion == "4":
            print("Saliendo del cliente...")
            break
        else:
            print("Opción no válida.")