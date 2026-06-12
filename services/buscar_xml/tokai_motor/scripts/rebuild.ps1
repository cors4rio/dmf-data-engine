# -------------------------------------------------------------------
# Auto Tokai - Script de Rebuild Automático
# Este script automatiza o ciclo de vida do container no Windows usando Podman.
# -------------------------------------------------------------------

$ErrorActionPreference = "Stop"
$ContainerName = "auto_tokai_bot"
$ImageName = "auto_tokai_img"

Write-Host "`n[1/3] Verificando containers antigos..." -ForegroundColor Cyan

# Tentar parar e remover o container se ele já existir
$existing = podman ps -a --format "{{.Names}}" | Select-String "^$ContainerName$"
if ($existing) {
    Write-Host "Parando e removendo '$ContainerName'..." -ForegroundColor Yellow
    podman stop $ContainerName 2>$null
    podman rm $ContainerName 2>$null
}

Write-Host "[2/3] Construindo nova imagem com o código atualizado..." -ForegroundColor Cyan
# Build da imagem (pode demorar na primeira vez)
podman build -t $ImageName .

Write-Host "[3/3] Iniciando o novo container..." -ForegroundColor Cyan

# Execução do Container com todos os mapeamentos do docker-compose
podman run -d `
    --name $ContainerName `
    --restart unless-stopped `
    --network host `
    -e TZ=America/Sao_Paulo `
    -e "NETWORK_DRIVE_Z=/mnt/z_drive/#ROTINA AUTOMATICA NF/NFCe" `
    -e HEADLESS_MODE=True `
    -v "Z:/:/mnt/z_drive:Z" `
    -v "${PWD}/config/credentials.json:/app/config/credentials.json:Z" `
    -v "${PWD}/config/token.json:/app/config/token.json:Z" `
    -v "${PWD}/config/playwright_storage.json:/app/config/playwright_storage.json:Z" `
    $ImageName

Write-Host "`n--- TUDO PRONTO! ---" -ForegroundColor Green
Write-Host "O bot está rodando em segundo plano."
Write-Host "Para acompanhar o que ele está fazendo, digite: podman logs -f $ContainerName"
Write-Host "----------------------------------------------------`n"
