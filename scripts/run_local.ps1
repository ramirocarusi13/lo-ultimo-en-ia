# Pasos "mecánicos" del bot en esta PC. La redacción y la revisión las hace Claude en la
# tarea programada de la app (ver prompts/tarea_programada.md).
#
#   scripts\run_local.ps1 -Build <id>   # fotos con ComfyUI + carrusel + sube las imágenes a GitHub
#   scripts\run_local.ps1 -Publish      # publica en Instagram el post pendiente
#
# Las claves NO van en este archivo: se leen de las variables de entorno de tu usuario
# (IG_USER_ID, IG_ACCESS_TOKEN, IG_GRAPH_HOST, IG_HANDLE).

param(
    [string]$Build,
    [switch]$Publish,
    [string]$ComfyUIDir = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'ComfyUI')
)

# 'Continue': en Windows PowerShell 5.1, git escribe avisos en stderr y con 'Stop' cortarían el script.
$ErrorActionPreference = 'Continue'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force $LogDir | Out-Null
$Log = Join-Path $LogDir ("run-{0:yyyyMMdd-HHmm}.log" -f (Get-Date))
function Log($msg) { $line = "{0:HH:mm:ss} {1}" -f (Get-Date), $msg; $line | Tee-Object -FilePath $Log -Append }

foreach ($n in 'IG_USER_ID', 'IG_ACCESS_TOKEN', 'IG_GRAPH_HOST', 'IG_HANDLE') {
    $v = [Environment]::GetEnvironmentVariable($n, 'User')
    if ($v) { Set-Item "env:$n" $v }
}
$env:PYTHONUTF8 = '1'
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
$Py = Join-Path $Root '.venv\Scripts\python.exe'

function Push-Repo($mensaje) {
    git add posts state
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        git commit --quiet -m $mensaje 2>&1 | ForEach-Object { Log $_ }
        git push --quiet 2>&1 | ForEach-Object { Log $_ }
        if ($LASTEXITCODE -ne 0) { Log 'ERROR: falló git push'; exit 1 }
    }
}

if ($Build) {
    function Test-ComfyUI { try { Invoke-RestMethod http://127.0.0.1:8188/system_stats -TimeoutSec 3 | Out-Null; $true } catch { $false } }
    $started = $false
    try {
        if (-not (Test-ComfyUI)) {
            Log "Iniciando ComfyUI en $ComfyUIDir (modo procesador)"
            Start-Process -FilePath (Join-Path $ComfyUIDir '.venv\Scripts\python.exe') `
                -ArgumentList 'main.py', '--listen', '127.0.0.1', '--port', '8188', '--disable-auto-launch', '--cpu' `
                -WorkingDirectory $ComfyUIDir -WindowStyle Hidden `
                -RedirectStandardOutput (Join-Path $LogDir 'comfyui.out.log') -RedirectStandardError (Join-Path $LogDir 'comfyui.err.log')
            $started = $true
            for ($i = 0; $i -lt 60 -and -not (Test-ComfyUI); $i++) { Start-Sleep 3 }
            if (-not (Test-ComfyUI)) { Log 'ComfyUI no arrancó; se usará la foto de la nota' }
        }
        Log "Armando el post $Build (fotos ~5 min cada una)"
        & $Py src/main.py build $Build 2>&1 | ForEach-Object { Log $_ }
        if ($LASTEXITCODE -ne 0) { Log "No se armó el post (código $LASTEXITCODE)"; exit $LASTEXITCODE }
    }
    finally {
        if ($started) {
            # el python del venv lanza un proceso hijo: se apagan todos los de la carpeta de ComfyUI
            Log 'Apagando ComfyUI para liberar memoria'
            Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$ComfyUIDir*" } |
                Stop-Process -Force -Confirm:$false
        }
    }
    git pull --rebase --quiet 2>&1 | ForEach-Object { Log $_ }
    Push-Repo ("Nuevo post $Build")
    Log 'Imágenes subidas a GitHub'
}

if ($Publish) {
    $remote = (git remote get-url origin 2>$null)
    if ($remote -notmatch 'github\.com[:/](.+?)(\.git)?$') { Log 'ERROR: el repo no tiene remoto de GitHub (origin)'; exit 1 }
    $env:PUBLIC_BASE_URL = "https://raw.githubusercontent.com/$($Matches[1])/main"
    if (-not $env:IG_ACCESS_TOKEN -or -not $env:IG_USER_ID) { Log 'ERROR: faltan IG_USER_ID / IG_ACCESS_TOKEN'; exit 1 }
    Log 'Publicando en Instagram'
    & $Py src/main.py publish 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) { Log 'ERROR: falló la publicación'; exit 1 }
    Push-Repo 'Publicado'
    Log 'Listo'
}
