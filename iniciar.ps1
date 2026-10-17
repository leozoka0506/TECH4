$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

# Ambiente comum primeiro; runtime do Codex apenas como conveniência nesta máquina.
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Crie o ambiente Python conforme o README antes de iniciar.'
}

$taskOllama = Join-Path $PSScriptRoot '.runtime\ollama\ollama.exe'
if (Test-Path -LiteralPath $taskOllama) {
    $env:OLLAMA_MODELS = Join-Path $PSScriptRoot '.runtime\models'
    $env:OLLAMA_HOST = '127.0.0.1:11434'
    try { Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3 | Out-Null }
    catch {
        Start-Process -FilePath $taskOllama -ArgumentList 'serve' -WindowStyle Hidden
        Start-Sleep -Seconds 3
    }
}
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.runtime\postgres-env')) {
    & $taskPython scripts/local_postgres.py start
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível iniciar o PostgreSQL.' }
}
Write-Host 'Abra http://127.0.0.1:8501. O token está no APP_TOKEN do .env. Ctrl+C encerra a interface.'
& $taskPython -m escuta serve
