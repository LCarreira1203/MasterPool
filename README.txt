MASTERPOOL V1.0 FINAL

COMO RODAR:
1. Instale as dependências:
   pip install -r requirements.txt

2. Mantenha seu arquivo .env na raiz do projeto:
   TELEGRAM_BOT_TOKEN=seu_token
   TELEGRAM_CHAT_ID=seu_chat_id

3. Rode:
   python main.py

COMANDOS:
 /start
 /help
 /id
 /search sol
 /addpool
 /delpool
 /listpools
 /status
 /bomdia

FUNÇÕES AUTOMÁTICAS:
- Relatório diário às 09:00.
- Monitoramento das pools a cada 5 minutos.
- Alerta 1x quando a distância cruzar para 5% ou menos de um range.
- Alerta 1x quando sair do range.
- Cotações em US$ e R$ para todos os tokens cadastrados nas pools.

IMPORTANTE:
- O preço usado para monitorar o range é sempre o primeiro token do par.
  Exemplo: SOL/USDC monitora SOL.
- Para cotações, o relatório mostra os dois tokens do par.
