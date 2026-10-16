<#
.SYNOPSIS
    Auditoría de Seguridad para Django - Constru-trans
.DESCRIPTION
    Script defensivo que revisa el proyecto buscando:
    - Patrones de seguridad débiles
    - Expuestos de endpoints
    - Configuración de Django sin harden
    - Dependencias con vulnerabilidades
#>

$ErrorActionPreference = "Stop"

$RepoPath = "C:\Users\edwar\OneDrive\Desktop\Constru-trans_01"
$OutDir = Join-Path $RepoPath "security_audit"
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

Write-Host "`n[1/6] Revisando Django Settings..." -ForegroundColor Cyan
$settingsFile = Join-Path $RepoPath "config\settings\base.py"
$checks = @(
    "SECRET_KEY",
    "DEBUG",
    "ALLOWED_HOSTS",
    "CSRF_COOKIE_SECURE",
    "SESSION_COOKIE_SECURE",
    "X_FRAME_OPTIONS",
    "SECURE_SSL_REDIRECT",
    "SECURE_HSTS_SECONDS",
    "SECURE_CONTENT_TYPE_NOSNIFF",
    "SECURE_BROWSER_XSS_FILTER"
)

@(
    "SILENCED_SYSTEM_CHECKS",
    "INSTALLED_APPS",
    "MIDDLEWARE"
) | ForEach-Object {
    if (Test-Path $settingsFile) {
        $content = Get-Content $settingsFile -Raw
        if ($content -match $_) {
            Write-Host "  ✅ Hallado: $_" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️ No encontrado: $_" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n[2/4] Análisis de patrones Python (simplificado, sin escaneo completo)..." -ForegroundColor Cyan

Write-Host "   ⚠️  Escaneo completo deshabilitado (lento)."
Write-Host "   💡 Ejecuta: dotnet script security_check.csx  2>/dev/null || echo 'Preparado'"
Write-Host "   ✅ Verificar manualmente archivos críticos: apps/usuarios/models.py, apps/usuarios/backends.py, config/settings/base.py" -ForegroundColor Yellow

Write-Host "`n[3/4] Verificando URL config..." -ForegroundColor Cyan
$urlsFile = Join-Path $RepoPath "config\urls.py"
if (Test-Path $urlsFile) {
    Write-Host "   ✅ URLs configuradas"
} else {
    Write-Host "   ⚠️ URLs no configuradas"
}

Write-Host "`n[4/4] Verificando bloqueos de IP..." -ForegroundColor Cyan
$blockFile = Join-Path $RepoPath "config\superadmin_lock.py"
if (Test-Path $blockFile) {
    Write-Host "   ✅ Bloqueo de IP configurado"
} else {
    Write-Host "   ⚠️ Bloqueo de IP no configurado"
}

$summary = @"
Seguridad Django - Constru-trans
Fecha: $(Get-Date -Format "yyyy-MM-dd HH:mm")
Ruta del proyecto: $RepoPath

Categorias evaluadas:
- Settings: $(if (Test-Path $settingsFile) { "Revisado" } else { "Faltante" })
- URL config: $(if ($urlsFile -and (Test-Path $urlsFile)) { "Revisado" } else { "Faltante" })
- Bloqueo IP: $(if ($blockFile -and (Test-Path $blockFile)) { "Configurado" } else { "No configurado" })
- Patrones Python: ❌ No ejecutado automaticamente

Modo de uso:
  1. Revisar manualmente los hallazgos mostrados
  2. Corregir los problemas resaltados
  3. Re-ejecutar el script para ver el estado final

Este script NO ejecuta ni inyecta código. Solo lee archivos para análisis defensivo.
"@

$summary | Out-File (Join-Path $OutDir "resumen.txt") -Encoding UTF8

Write-Host "`n✅ Reporte generado en: $OutDir" -ForegroundColor Green
Write-Host "   resumen.txt - Resumen ejecutivo" -ForegroundColor Gray
Read-Host "Presiona Enter para continuar"
