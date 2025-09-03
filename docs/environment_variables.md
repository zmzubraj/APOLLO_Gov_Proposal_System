# Environment Variables

APOLLO uses a `.env` file at the project root to configure data sources, model behavior, and optional chain integrations. The table below lists each variable and its role.

| Variable | Required | Role |
|----------|----------|------|
| `SUBSCAN_API_KEY` | Yes | API key for the Subscan service that supplies Polkadot chain data. |
| `NEWS_API_KEY` | Optional | Key for News API to pull external news articles. |
| `REDDIT_CLIENT_ID` | Optional | Reddit application identifier for scraping subreddit posts. |
| `REDDIT_CLIENT_SECRET` | Optional | Secret paired with the client ID for Reddit access. |
| `SUBSTRATE_NODE_URL` | Yes | WebSocket endpoint of the target Substrate node. |
| `SUBSTRATE_PRIVATE_KEY` | Optional | sr25519 key used for signing on-chain transactions. |
| `DISCORD_WEBHOOK_URL` | Optional | Webhook URL for broadcasting updates to Discord. |
| `TELEGRAM_BOT_TOKEN` | Optional | Token for a Telegram bot used to send messages. |
| `TELEGRAM_CHAT_ID` | Optional | Chat or channel ID that receives Telegram updates. |
| `TWITTER_BEARER` | Optional | Bearer token for posting summary messages to X/Twitter. |
| `DATA_WEIGHT_CHAT` | Optional | Weight of real-time chat sentiment in draft ranking. |
| `DATA_WEIGHT_FORUM` | Optional | Weight of long-form forum discussions. |
| `DATA_WEIGHT_NEWS` | Optional | Weight of news articles. |
| `DATA_WEIGHT_CHAIN` | Optional | Weight of on-chain activity metrics. |
| `DATA_WEIGHT_GOVERNANCE` | Optional | Weight of historical governance data. |
| `NEWS_LOOKBACK_DAYS` | Optional | Number of days of news to collect for analysis. |
| `HISTORICAL_SAMPLE_SEED` | Optional | Seed for deterministic sampling of past referenda. |
| `MIN_PASS_CONFIDENCE` | Optional | Confidence threshold to classify drafts as likely to pass. |
| `ENABLE_EVM_FETCH` | Optional | When `true`, fetches blocks from an EVM-compatible chain. |
| `EVM_RPC_URL` | Conditionally | RPC endpoint for the EVM chain (required if EVM fetch is enabled). |
| `EVM_START_BLOCK` | Optional | Starting block number for EVM data collection. |
| `EVM_END_BLOCK` | Optional | Final block number for EVM data collection. |

