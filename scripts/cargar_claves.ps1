# Guarda claves como variables de entorno de tu usuario de Windows (nunca en archivos del proyecto).
# Lo que escribís no se ve en pantalla. Dejá vacío para no cambiar una clave.
#   powershell -ExecutionPolicy Bypass -File scripts\cargar_claves.ps1 ANTHROPIC_API_KEY
#   powershell -ExecutionPolicy Bypass -File scripts\cargar_claves.ps1 IG_USER_ID IG_ACCESS_TOKEN

param([Parameter(Mandatory)][string[]]$Nombres)

foreach ($n in $Nombres) {
    $s = Read-Host "Pegá el valor de $n (Enter para no cambiarlo)" -AsSecureString
    $v = [Net.NetworkCredential]::new('', $s).Password.Trim()
    if ($v) {
        [Environment]::SetEnvironmentVariable($n, $v, 'User')
        Write-Host "  $n guardada ($($v.Length) caracteres)." -ForegroundColor Green
    } else {
        Write-Host "  $n sin cambios." -ForegroundColor Yellow
    }
}
