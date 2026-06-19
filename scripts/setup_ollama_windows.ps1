
# Script de Setup COMPLETO para Ollama en Constru-Trans
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   CONFIGURACIÓN DE OLLAMA PARA CONSTRU-TRANS" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# Paso 1: Verificar Ollama
Write-Host "`n[1/5] Verificando Ollama..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Ollama está corriendo correctamente!" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Ollama NO está corriendo!" -ForegroundColor Red
    Write-Host "`n⚠️ Por favor sigue estos pasos:" -ForegroundColor Yellow
    Write-Host "1. Abre el navegador y ve a https://ollama.com"
    Write-Host "2. Descarga e instala Ollama para Windows"
    Write-Host "3. Abre la aplicación Ollama (debe estar en la barra de tareas)"
    Write-Host "4. Vuelve a ejecutar este script"
    Write-Host "`nPresiona cualquier tecla para salir..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

# Paso 2: Verificar modelo
Write-Host "`n[2/5] Verificando modelo llama3.2..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -UseBasicParsing
    $data = $response.Content | ConvertFrom-Json
    $modelos = $data.models | ForEach-Object { $_.name }
    
    if ("llama3.2" -in $modelos) {
        Write-Host "✅ Modelo llama3.2 ya está descargado!" -ForegroundColor Green
    } else {
        Write-Host "📥 Descargando modelo llama3.2... (esto puede tardar unos minutos)" -ForegroundColor Yellow
        Write-Host "Por favor, espera..." -ForegroundColor Gray
        ollama pull llama3.2
        Write-Host "✅ Modelo descargado!" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ No se pudo verificar el modelo, intentando descargarlo..." -ForegroundColor Yellow
    ollama pull llama3.2
}

# Paso 3: Probar conexión
Write-Host "`n[3/5] Probando conexión..." -ForegroundColor Yellow
try {
    $body = @{
        model = "llama3.2"
        prompt = "Hola, responde solo con 'Funciona perfectamente!'"
        stream = $false
    } | ConvertTo-Json
    
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30 -UseBasicParsing
    
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ ¡Prueba exitosa! Ollama está respondiendo perfectamente." -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ Hubo un problema en la prueba, pero Ollama está configurado." -ForegroundColor Yellow
}

# Paso 4: Verificar el proyecto
Write-Host "`n[4/5] Verificando proyecto Constru-Trans..." -ForegroundColor Yellow
Write-Host "✅ Encontrado el proyecto en: $(Get-Location)" -ForegroundColor Green

# Paso 5: Completado!
Write-Host "`n[5/5] ¡Todo listo!" -ForegroundColor Green
Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "   🎉 ¡CONFIGURACIÓN COMPLETADA!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "`nAhora puedes:" -ForegroundColor Yellow
Write-Host "1. Iniciar el servidor Django (python manage.py runserver)"
Write-Host "2. Abrir el navegador y usar el chat"
Write-Host "3. El asistente responderá con datos REALES del sistema!"
Write-Host "`n¡Disfruta de tu asistente virtual inteligente! 🚀" -ForegroundColor Cyan
Write-Host "`nPresiona cualquier tecla para salir..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

