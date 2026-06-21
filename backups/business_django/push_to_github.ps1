# Script para subir cambios a GitHub
$ErrorActionPreference = "Continue"

# Ruta a Git
$gitPath = "C:\Users\$env:USERNAME\AppData\Local\GitHubDesktop\app-3.5.8\resources\app\git\cmd\git.exe"

# Asegurarse de estar en el directorio correcto
Set-Location "c:\Users\edwar\Downloads\Constru-trans_01"

Write-Host "=== Estado del repositorio ===" -ForegroundColor Cyan
& $gitPath status

Write-Host "`n=== Pulling cambios remotos ===" -ForegroundColor Yellow
& $gitPath pull origin main --no-rebase

Write-Host "`n=== Pushing cambios ===" -ForegroundColor Green
& $gitPath push -u origin main

Write-Host "`n=== HECHO! ===" -ForegroundColor Green
