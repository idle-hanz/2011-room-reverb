$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
Get-Content (Get-ChildItem part*.b64 | Sort-Object Name) | Set-Content -Encoding ascii pack.b64
certutil -decode pack.b64 2011-room-reverb.zip | Out-Null
Write-Host "Wrote $(Resolve-Path .\2011-room-reverb.zip)"
