# Corre el bot completo en esta PC: noticia -> texto (Claude) -> fotos (ComfyUI) ->
# carrusel -> sube las imágenes a GitHub (URL pública) -> publica en Instagram.
#
# Lo lanza el Programador de tareas de Windows (ver scripts/programar_tarea.ps1).
# Las claves NO van en este archivo: se leen de las variables de entorno de tu usuario
# (ANTHROPIC_API_KEY, IG_USER_ID, IG_ACCESS_TOKEN, IG_GRAPH_HOST, IG_HANDLE, AUTO_PUBLISH).
#
# Opciones:
#   -ComfyUIDir  carpeta de ComfyUI (por defecto Documentos\ComfyUI)
#   -NoPublish   solo genera y sube las imágenes, no publica

param(
    [string]$ComfyUIDir = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'ComfyUI'),
    [switch]$NoPublish
)

# 'Continue': en Windows PowerShell 5.1, git escribe avisos en stderr y con 'Stop' cortarían el script.
$ErrorActionPreference = 'Continue'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force $LogDir | Out-Null
$Log = Join-Path $LogDir ("run-{0:yyyyMMdd-HHmm}.log" -f (Get-Date))
function Log($msg) { $line = "{0:HH:mm:ss} {1}" -f (Get-Date), $msg; $line | Tee-Object -FilePath $Log -Append }

# Variables de usuario: el Programador de tareas no siempre las trae actualizadas.
foreach ($n in 'ANTHROPIC_API_KEY', 'IG_USER_ID', 'IG_ACCESS_TOKEN', 'IG_GRAPH_HOST', 'IG_HANDLE', 'AUTO_PUBLISH') {
    $v = [Environment]::GetEnvironmentVariable($n, 'User')
    if ($v) { Set-Item "env:$n" $v }
}
$env:PYTHONUTF8 = '1'
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
$Py = Join-Path $Root '.venv\Scripts\python.exe'

if (-not $env:ANTHROPIC_API_KEY) { Log 'Falta ANTHROPIC_API_KEY en las variables de usuario.'; exit 1 }

# URL pública de las imágenes: archivos crudos del repo de GitHub (tiene que ser público).
$remote = (git remote get-url origin 2>$null)
if ($remote -match 'github\.com[:/](.+?)(\.git)?$') {
    $env:PUBLIC_BASE_URL = "https://raw.githubusercontent.com/$($Matches[1])/main"
} elseif (-not $NoPublish) {
    Log 'El repo no tiene un remoto de GitHub (origin); no se puede publicar.'; exit 1
}

function Test-ComfyUI { try { Invoke-RestMethod http://127.0.0.1:8188/system_stats -TimeoutSec 3 | Out-Null; $true } catch { $false } }

$comfy = $null
try {
    Log 'Actualizando el repo'
    git pull --rebase --quiet 2>&1 | ForEach-Object { Log $_ }

    if (-not (Test-ComfyUI)) {
        Log "Iniciando ComfyUI en $ComfyUIDir (modo procesador)"
        $comfy = Start-Process -FilePath (Join-Path $ComfyUIDir '.venv\Scripts\python.exe') `
            -ArgumentList 'main.py', '--listen', '127.0.0.1', '--port', '8188', '--disable-auto-launch', '--cpu' `
            -WorkingDirectory $ComfyUIDir -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $LogDir 'comfyui.out.log') -RedirectStandardError (Join-Path $LogDir 'comfyui.err.log')
        for ($i = 0; $i -lt 60 -and -not (Test-ComfyUI); $i++) { Start-Sleep 3 }
        if (-not (Test-ComfyUI)) { Log 'ComfyUI no arrancó; el bot usará la foto de la nota' }
    }

    Log 'Generando el carrusel'
    & $Py src/main.py generate 2>&1 | ForEach-Object { Log $_ }
    if (-not (Test-Path posts/pending.json)) { Log 'No hay post nuevo (sin noticia en tendencia o descartada).'; exit 0 }

    Log 'Subiendo imágenes a GitHub'
    git add posts state
    git commit --quiet -m ("Nuevo post {0:yyyy-MM-dd HH:mm}" -f (Get-Date)) 2>&1 | ForEach-Object { Log $_ }
    git push --quiet 2>&1 | ForEach-Object { Log $_ }

    if ($NoPublish -or $env:AUTO_PUBLISH -ne 'true') { Log 'AUTO_PUBLISH no está en true: queda para revisar en posts/.'; exit 0 }

    Start-Sleep 30  # que GitHub sirva los archivos recién subidos
    Log 'Publicando en Instagram'
    & $Py src/main.py publish 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) { Log 'Falló la publicación'; exit 1 }
    git add posts
    git commit --quiet -m 'Publicado' 2>&1 | ForEach-Object { Log $_ }
    git push --quiet 2>&1 | ForEach-Object { Log $_ }
    Log 'Listo'
}
finally {
    if ($comfy) {
        # el python del venv lanza un proceso hijo: se apagan todos los de la carpeta de ComfyUI
        Log 'Apagando ComfyUI para liberar memoria'
        Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$ComfyUIDir*" } |
            Stop-Process -Force -Confirm:$false
    }
}
