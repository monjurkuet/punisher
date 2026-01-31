# Punisher - Stealth Bitcoin Market Intelligence AI

The **Punisher** is a sophisticated, privacy-first AI trading assistant designed for institutional-grade Bitcoin market analysis. It operates entirely locally on Ubuntu bare metal, leveraging advanced stealth techniques to monitor markets and wallets without detection.

## 🚀 Key Features

### 🐳 Stealth Hyperliquid Monitoring
- **Undetectable WebSocket Connection**: Mimics legitimate Chrome TLS fingerprints and headers to bypass bot detection.
- **Wallet Stalking**: Tracks specific whale wallets using `webData2` subscriptions.
- **Market Sentinel**: Polls L2 order books and recent trades via HTTP/2 for global market sentiment.
- **Data Persistence**: Stores wallet snapshots, positions, and whale trades in MongoDB.
- **CoinGlass Scraper**: Automated scraper to discover top trader wallets from leaderboards.

### 🧠 Institutional Persona
- **Wall Street Veteran**: The AI acts as a 30-year risk manager—cynical, logical, and anti-FOMO.
- **Context-Aware**: Injects live BTC price, saved research metrics, and real-time news into every response.

### 🔒 Privacy & Architecture
- **100% Local**: No external cloud dependnecies; runs on your hardware.
- **Modern Stack**: Built with `Python 3.12+`, `uv`, `FastAPI`, `Playwright`, and `MongoDB`.
- **Hybrid Storage**: SQLite for quick lookups, MongoDB for high-volume time-series data.

## 🛠️ Installation

1. **Prerequisites**
   - Ubuntu 22.04+ / Linux
   - Python 3.12+
   - `uv` package manager
   - MongoDB Cluster (Atlas or Local)

2. **Setup**
   ```bash
   git clone git@github.com:monjurkuet/punisher.git
   cd punisher
   uv sync
   ```

3. **Configuration**
   Copy `.env.template` to `.env` and fill in your credentials:
   ```bash
   cp .env.template .env
   ```
   Required keys:
   - `OPENAI_API_KEY` (for LLM Gateway)
   - `MONGODB_URI` (for wallet/market data)
   - `TELEGRAM_BOT_TOKEN` (optional)

## ⚡ Usage

### Start the Core Server
This launches the Orchestrator, WebSocket monitors, and API.
```bash
uv run punisher-server
```

### Access the CLI
Chat with the AI and view real-time alerts.
```bash
uv run punisher
```

### Scrape Wallets
Update the tracked wallet list from CoinGlass.
```bash
uv run python src/punisher/scrapers/coinglass.py
```

## 📂 Project Structure
- `src/punisher/core`: Orchestrator and main event loop.
- `src/punisher/crypto`: Hyperliquid WebSocket/HTTP monitors & Stealth logic.
- `src/punisher/scrapers`: CoinGlass and other web scrapers.
- `src/punisher/db`: MongoDB and SQLite interfaces.
- `src/punisher/llm`: Gateway to LLM providers.

## 🤝 Contributing
Commits should use [Conventional Commits](https://www.conventionalcommits.org/).
- `feat`: New capabilities
- `fix`: Bug fixes
- `refactor`: Code restructuring

## 📜 License
MIT
