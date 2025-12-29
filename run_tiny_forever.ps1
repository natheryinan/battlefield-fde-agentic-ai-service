
Set-Location $PSScriptRoot
$env:FDE_PUBLIC_MODE="1"

$backoff = 1

while ($true) {
  try {
    Write-Host "$(Get-Date) START tiny..."
    python .\entrypoint.py
    Write-Host "$(Get-Date) STOP (normal exit) -> restart"
  } catch {
    Write-Host "$(Get-Date) CRASH -> restart"
  }

  Start-Sleep -Seconds $backoff
  if ($backoff -lt 30) { $backoff = [Math]::Min($backoff * 2, 30) }
}
