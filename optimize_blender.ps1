# Optimize Blender for Rendering
# Run this script as Administrator

Write-Host "=== Blender Rendering Optimization ===" -ForegroundColor Cyan

# 1. Set high priority for Blender processes
Write-Host "[1/5] Configurando prioridad de procesos Blender..." -ForegroundColor Yellow
$blenderProcesses = Get-Process | Where-Object { $_.ProcessName -match "blender|blender-2|blender-bd" }
if ($blenderProcesses) {
    foreach ($proc in $blenderProcesses) {
        try {
            $proc.PriorityClass = "High"
            Write-Host "  -> Proceso '$($proc.ProcessName)' (PID: $($proc.Id)) prioridad: High" -ForegroundColor Green
        } catch {
            Write-Host "  -> No se pudo cambiar prioridad de '$($proc.ProcessName)'" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  -> No hay procesos Blender en ejecución (ejecuta Blender para aplicar)" -ForegroundColor Yellow
}

# 2. Configure power plan for Blender (use Performance/Turbo)
Write-Host "[2/5] Configurando plan de energ��a para Blender..." -ForegroundColor Yellow
$powerScheme = powercfg -GETACTIVESCHEME
if ($powerScheme -match "GUID") {
    $activeGuid = $matches[1]
    # Use Turbo plan (best for rendering)
    $turboGuid = "6fecc5ae-f350-48a5-b669-b472cb895ccf"
    if (test-path "registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Power\PowerSchemes\$turboGuid") {
        powercfg -SETACTIVESCHEME $turboGuid
        Write-Host "  -> Plan de energ��a: Turbo (mejor para renderizado)" -ForegroundColor Green
    } else {
        Write-Host "  -> Usando plan de energ��a actual (Performance)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  -> No se pudo detectar el esquema actual" -ForegroundColor Red
}

# 3. Configure Windows Visual Effects for rendering
Write-Host "[3/5] Configurando efectos visuales..." -ForegroundColor Yellow
reg add "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v "VisualFX" /t REG_DWORD /d "3" /f
Write-Host "  -> Efectos visuales: Rendimiento" -ForegroundColor Gray

# 4. Configure GPU rendering in Blender (user will do this)
Write-Host "[4/5] Configurando Blender para renderizado..." -ForegroundColor Yellow
Write-Host "  -> Blender > Render Properties > Device: GPU Compute" -ForegroundColor Gray
Write-Host "  -> Blender > Render Properties > Compute Device: CUDA / OptiX / Metal" -ForegroundColor Gray
Write-Host "  -> Blender > Output Properties > Settings: Best (quality)" -ForegroundColor Gray

# 5. Configure file paths for better performance
Write-Host "[5/5] Verificando configuraci��n de archivos Blender..." -ForegroundColor Yellow
Write-Host "  -> Blender > File > Defaults > Save & Load" -ForegroundColor Gray
Write-Host "  -> Usar una SSD para archivos de proyecto y output" -ForegroundColor Gray
Write-Host "  -> Configurar 'Default Save Directory' al disco con mas espacio" -ForegroundColor Gray

Write-Host "" -ForegroundColor Cyan
Write-Host "=== Blender Optimization Complete ===" -ForegroundColor Green
Write-Host "Reinicia Blender y aplica las configuraciones de GPU en el panel" -ForegroundColor Yellow
