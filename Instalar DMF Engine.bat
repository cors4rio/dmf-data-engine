@echo off & cls & powershell -NoProfile -ExecutionPolicy Bypass -Command "$scriptPath = '%~dp0'; iex (((Get-Content -Encoding UTF8 -LiteralPath '%~f0') | Where-Object {$_ -notlike '@*'}) -join [char]10)" & exit /b %errorlevel%

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$origem = $scriptPath.TrimEnd('\')
$destino = "$env:LOCALAPPDATA\DMF Engine"
$exe = Join-Path $destino "DMF Engine.exe"
$atalho = "$env:USERPROFILE\Desktop\DMF Engine.lnk"

# 1) Cabeçalho do Instalador
Write-Host "====================================================="
Write-Host "            DMF Engine - Instalador Local" -ForegroundColor Cyan
Write-Host "====================================================="
Write-Host ""
Write-Host "Origem  . . : $origem"
Write-Host "Destino . . : $destino"
Write-Host ""

# 2) Verifica se o aplicativo está aberto
$processos = Get-Process -Name "DMF Engine" -ErrorAction SilentlyContinue
if ($processos) {
    Write-Host "[ERRO] O DMF Engine está aberto. Feche o programa antes de atualizar." -ForegroundColor Red
    Write-Host "Pressione qualquer tecla para sair..."
    [void][Console]::ReadKey($true)
    exit 1
}

# 3) Cria pasta de destino se não existir
if (-not (Test-Path $destino)) {
    New-Item -ItemType Directory -Path $destino -Force | Out-Null
}

# 3.1) Limpa resíduos de instalações antigas que copiavam o projeto inteiro.
#      Esses diretórios de código solto (dmf_engine\, engine\, modulos\, ...) ficam
#      no sys.path do exe e SOBREPÕEM o código empacotado em _internal, fazendo o app
#      rodar uma versão antiga do auth.py (login quebrado, usuários sumindo).
#      A versão correta vive SEMPRE dentro de _internal — nunca solta na raiz.
$residuos = @(
    "dmf_engine", "engine", "modulos", "services", "core",
    "build", "dist", "scratch", "skills", "ESTRUTURA", "ENTRADAS_MANUAIS",
    "Specs_Definitivos", ".claude", ".vscode", "__pycache__"
)
$limpos = 0
foreach ($r in $residuos) {
    $alvo = Join-Path $destino $r
    if (Test-Path $alvo) {
        Remove-Item -LiteralPath $alvo -Recurse -Force -ErrorAction SilentlyContinue
        if (-not (Test-Path $alvo)) { $limpos++ }
    }
}
# Remove .py soltos na raiz (código de dev que não deve coexistir com o exe)
Get-ChildItem -Path $destino -Filter "*.py" -File -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
    $limpos++
}
if ($limpos -gt 0) {
    Write-Host "Limpeza: $limpos resíduo(s) de instalação antiga removido(s)." -ForegroundColor Yellow
}

# 4) Coleta de arquivos e cópia com progresso
$excluir = @(
    "config.json", 
    "supervisores.json", 
    "ultimo_ciclo.json", 
    "dmf_engine.log", 
    "dmf_engine_errors.log", 
    "Instalar DMF Engine.bat",
    "estado_compartilhado.json"
)

# Coleta todos os arquivos recursivamente
$files = Get-ChildItem -Path $origem -Recurse -File | Where-Object { $excluir -notcontains $_.Name }
$total = $files.Count
$copiados = 0
$copias_efetivas = 0

Write-Host "Copiando arquivos da aplicação..."
foreach ($file in $files) {
    $relativePath = $file.FullName.Substring($origem.Length).TrimStart('\')
    $destFile = Join-Path $destino $relativePath
    $destDir = Split-Path $destFile -Parent

    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }

    # Verifica se precisa copiar (se não existe ou se a origem é mais recente)
    $copiar = $false
    if (-not (Test-Path $destFile)) {
        $copiar = $true
    } else {
        $srcTime = $file.LastWriteTime
        $dstTime = (Get-Item $destFile).LastWriteTime
        if (($srcTime - $dstTime).TotalSeconds -gt 2) {
            $copiar = $true
        }
    }

    if ($copiar) {
        try {
            Copy-Item -Path $file.FullName -Destination $destFile -Force -ErrorAction Stop
            $copias_efetivas++
        } catch {
            Write-Host "`n[ERRO] Não foi possível copiar: $relativePath" -ForegroundColor Red
            Write-Host "Verifique se você tem permissões de escrita ou se o DMF Engine está em execução." -ForegroundColor Red
            Write-Host "Pressione qualquer tecla para sair..."
            [void][Console]::ReadKey($true)
            exit 1
        }
    }

    $copiados++
    $percent = [math]::Round(($copiados / $total) * 100)
    
    # Barra de progresso visual
    $barLen = 30
    $filledLen = [math]::Round(($barLen * $percent) / 100)
    $bar = ('#' * $filledLen) + ('-' * ($barLen - $filledLen))
    
    $fileName = $file.Name
    if ($fileName.Length -gt 35) { $fileName = $fileName.Substring(0, 32) + "..." }
    
    # Escreve na mesma linha do terminal
    Write-Host ("`r[{0}] {1,3}% | {2,-35}" -f $bar, $percent, $fileName) -NoNewline
}
Write-Host ""
Write-Host "✔ Cópia de arquivos concluída ($copias_efetivas arquivos atualizados)." -ForegroundColor Green

# 5) Cria o atalho (remove primeiro para invalidar o cache de ícone do Windows)
Write-Host "Criando atalho na Área de Trabalho..."
try {
    if (Test-Path $atalho) { Remove-Item -LiteralPath $atalho -Force -ErrorAction SilentlyContinue }
    $wshShell = New-Object -ComObject WScript.Shell
    $shortcut = $wshShell.CreateShortcut($atalho)
    $shortcut.TargetPath = $exe
    $shortcut.WorkingDirectory = $destino
    $shortcut.Description = "DMF Engine - Automação de Horas"
    $shortcut.IconLocation = "$exe,0"
    $shortcut.Save()
    Write-Host "✔ Atalho criado com sucesso." -ForegroundColor Green
} catch {
    Write-Host "⚠ AVISO: Não foi possível criar o atalho automaticamente." -ForegroundColor Yellow
}

# 5.1) Força refresh do cache de ícone do Explorer (sem reiniciar a sessão)
try {
    ie4uinit.exe -show 2>$null
} catch {}

# 6) Finalização
Write-Host ""
Write-Host "====================================================="
Write-Host " Instalação concluída com sucesso!" -ForegroundColor Green
Write-Host "====================================================="
Write-Host ""

# Pergunta se quer abrir agora
Write-Host "Deseja abrir o DMF Engine agora? [S/N]: " -NoNewline
$abrir = [Console]::ReadLine()
if ($abrir -eq 'S' -or $abrir -eq 's' -or $abrir -eq 'sim' -or $abrir -eq 'Sim') {
    Start-Process -FilePath $exe -WorkingDirectory $destino
}
