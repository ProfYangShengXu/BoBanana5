# auto-add-cycle-bridge.ps1 — 由 SessionStart hook 调用
# 自动检查项目 reasonix.toml，缺少 cycle-bridge 则追加

$toml = Join-Path (Get-Location) "reasonix.toml"
if (-not (Test-Path $toml)) { exit 0 }

$content = Get-Content $toml -Raw -ErrorAction SilentlyContinue
if (-not $content) { exit 0 }
if ($content -match "cycle-bridge") { exit 0 }

$bridgePath = "$env:USERPROFILE\.reasonix\bin\cycle-bridge.exe"
if (-not (Test-Path $bridgePath)) { exit 0 }

$plugin = @"

[[plugins]]
name = "cycle-bridge"
command = '$bridgePath'
"@

Add-Content -Path $toml -Value $plugin -Encoding Default
Write-Host "[auto-add] cycle-bridge plugin added to reasonix.toml"
