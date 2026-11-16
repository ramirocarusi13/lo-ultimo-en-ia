# Programa el bot en el Programador de tareas de Windows: 3 veces por día.
# Corre con tu usuario y solo cuando tu sesión está iniciada (no pide contraseña).
# Para quitarla:  Unregister-ScheduledTask -TaskName 'Lo Ultimo en IA - bot' -Confirm:$false

param([string[]]$Horas = @('09:17', '15:17', '21:17'))

$script = Join-Path $PSScriptRoot 'run_local.ps1'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`"" `
    -WorkingDirectory (Split-Path $PSScriptRoot -Parent)
$triggers = $Horas | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ }
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'Lo Ultimo en IA - bot' -Action $action -Trigger $triggers `
    -Settings $settings -Description 'Publica carruseles de noticias de IA en Instagram' -Force |
    Select-Object TaskName, State
