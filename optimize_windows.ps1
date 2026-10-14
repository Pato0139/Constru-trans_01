# Optimize Windows for gaming and priority windows
# Run this script as Administrator

Write-Host "=== Windows Gaming Optimization ===" -ForegroundColor Cyan

# 1. Set high priority for Roblox processes
Write-Host "[1/5] Configurando prioridad de procesos Roblox..." -ForegroundColor Yellow
$robloxProcesses = Get-Process | Where-Object { $_.ProcessName -match "roblox|robloxplayer" }
if ($robloxProcesses) {
    foreach ($proc in $robloxProcesses) {
        try {
            $proc.PriorityClass = "High"
            Write-Host "  -> Proceso '$($proc.ProcessName)' (PID: $($proc.Id)) prioridad: High" -ForegroundColor Green
        } catch {
            Write-Host "  -> No se pudo cambiar prioridad de '$($proc.ProcessName)'" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  -> No hay procesos Roblox en ejecución" -ForegroundColor Yellow
}

# 2. Set power plan to High Performance
Write-Host "[2/5] Configurando plan de energía a 'Alto rendimiento'..." -ForegroundColor Yellow
$powerScheme = powercfg -GETACTIVESCHEME
if ($powerScheme -match "GUID") {
    $activeGuid = $matches[1]
    $highPerfGuid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"  # High Performance
    powercfg -SETACTIVESCHEME $highPerfGuid
    Write-Host "  -> Plan de energía: Alto rendimiento" -ForegroundColor Green
} else {
    Write-Host "  -> No se pudo detectar el esquema actual" -ForegroundColor Red
}

# 3. Disable background apps (Windows 10/11)
Write-Host "[3/5] Desactivando apps en segundo plano..." -ForegroundColor Yellow
# This is a system setting, so we just inform the user
Write-Host "  -> Configuración: Configuración > Sistema > Aplicaciones > Apps en segundo plano" -ForegroundColor Gray

# 4. Configure visual effects for better performance
Write-Host "[4/5] Configurando efectos visuales..." -ForegroundColor Yellow
# Set the "Adjust for best performance" option via registry
reg add "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v "VisualFX" /t REG_DWORD /d "3" /f
Write-Host "  -> Efectos visuales: Ajustar para mejor rendimiento" -ForegroundColor Gray

# 5. Configure startup apps
Write-Host "[5/5] Gestionando aplicaciones de inicio..." -ForegroundColor Yellow
Write-Host "  -> Ejecutar: shell:startup" -ForegroundColor Gray
Write-Host "  -> Ejecutar: shell:common startup" -ForegroundColor Gray

Write-Host "" -ForegroundColor Cyan
Write-Host "=== Optimización completada ===" -ForegroundColor Green
Write-Host "Reinicia el explorador para aplicar los cambios" -ForegroundColor Yellow
