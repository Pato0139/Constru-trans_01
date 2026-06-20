
"""
Setup y verificación de Ollama para Constru-Trans
"""
import subprocess
import sys
import time
import requests

def verificar_ollama():
    """Verifica si Ollama está instalado y ejecutándose"""
    try:
        # Verificar si el servicio está activo
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama está corriendo correctamente!")
            return True
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Ollama no está corriendo en http://localhost:11434")
        return False
    except Exception as e:
        print(f"❌ Error al verificar Ollama: {str(e)}")
        return False

def verificar_modelo(modelo="llama3.2"):
    """Verifica si el modelo está descargado"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            modelos = [m["name"] for m in data.get("models", [])]
            if modelo in modelos:
                print(f"✅ Modelo {modelo} ya está descargado!")
                return True
            print(f"⚠️ Modelo {modelo} no está descargado.")
            return False
        return False
    except:
        return False

def descargar_modelo(modelo="llama3.2"):
    """Descarga el modelo Ollama"""
    print(f"📥 Descargando modelo {modelo}... (esto puede tardar unos minutos)")
    try:
        result = subprocess.run(
            ["ollama", "pull", modelo],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos máximo
        )
        if result.returncode == 0:
            print(f"✅ Modelo {modelo} descargado exitosamente!")
            return True
        else:
            print(f"❌ Error al descargar modelo: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ El comando 'ollama' no está disponible. Asegúrate de instalar Ollama primero.")
        return False
    except Exception as e:
        print(f"❌ Error al descargar: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("   CONFIGURACIÓN DE OLLAMA PARA CONSTRU-TRANS")
    print("=" * 60)
    
    # Paso 1: Verificar Ollama
    print("\n📋 Paso 1: Verificando Ollama...")
    if not verificar_ollama():
        print("\n⚠️ Por favor:")
        print("1. Instala Ollama desde https://ollama.com")
        print("2. Abre la aplicación Ollama (debe estar corriendo en segundo plano)")
        print("3. Vuelve a ejecutar este script")
        return
    
    # Paso 2: Verificar modelo
    print("\n📋 Paso 2: Verificando modelo...")
    if not verificar_modelo():
        if not descargar_modelo():
            print("\n❌ No se pudo configurar Ollama. Por favor, verifica la instalación.")
            return
    
    # Paso 3: Prueba simple
    print("\n📋 Paso 3: Probando la conexión...")
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": "Hola, responde solo con 'Funciona!'",
                "stream": False
            },
            timeout=30
        )
        if response.status_code == 200:
            print("✅ ¡Prueba exitosa! Ollama está respondiendo perfectamente.")
            print("\n🎉 ¡Todo listo! Ahora puedes usar el asistente virtual en Constru-Trans.")
        else:
            print(f"❌ Error en la prueba: {response.status_code}")
    except Exception as e:
        print(f"❌ Error en la prueba: {str(e)}")

if __name__ == "__main__":
    main()

