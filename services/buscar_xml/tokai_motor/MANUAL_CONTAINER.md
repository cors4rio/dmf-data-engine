# Guia de Operacao - Auto Tokai (Podman)

Este guia contem os comandos essenciais para gerenciar a automacao no ambiente de container (Podman).

---

## Comandos de Ciclo de Vida

Como o ambiente utiliza Podman, o comando docker-compose pode nao estar disponível. Use os comandos abaixo:

### 1. Reconstruir e Subir o Robo (Recomendado)
Sempre que fizer uma alteracao no codigo ou no .env, use o script automatizado que ja trata as permissoes e volumes:
```powershell
.\scripts\rebuild.ps1
```

### 2. Derrubar o Container Manualmente
Se precisar parar o robo imediatamente:
```powershell
podman stop auto_tokai_bot
podman rm auto_tokai_bot
```

### 3. Acompanhar a Execucao (Logs)
Para ver o que o robo esta fazendo em tempo real (muito util para debugar):
```powershell
podman logs -f auto_tokai_bot
```

---

## Gestao de Mapas e Clientes

O robo depende do mapa do SharePoint para saber o que baixar.

### 1. Adicionar/Remover Clientes
1. Edite o arquivo config/config_clientes.json.
2. Apos salvar, voce precisa regenerar o mapa do ano atual:
```powershell
python scripts/generate_map.py --ano 2026
```

---

## Testes e Debug

### 1. Rodar Teste Manual (Fora do Container)
Para testar a extracao de um mes especifico sem esperar pelo agendamento:
```powershell
python teste_manual.py
```

### 2. Entrar no Container
Se precisar navegar nos arquivos internos do container para verificar algo:
```powershell
podman exec -it auto_tokai_bot bash
```

---

## Observacoes Importantes
- Drives de Rede: O container espera que a unidade Z: esteja devidamente mapeada no Windows Host.
- Timezone: O container esta configurado para America/Sao_Paulo. Se o horario das notificacoes estiver errado, verifique o relagio do Host.
- Headless: No container, o robo sempre roda em modo HEADLESS=True (sem janela visível).
