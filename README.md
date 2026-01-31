# Punisher - Stealth Bitcoin Market Intelligence AI

The **Punisher** is a sophisticated, privacy-first AI intelligence cell designed for institutional-grade Bitcoin market analysis. It operates entirely locally on Ubuntu bare metal, leveraging advanced stealth techniques to monitor markets, whales, and media narratives without detection.

---

## 🚀 Key Features

### 🐳 Global Market Intelligence
- **Stealth Hyperliquid Monitoring**: Undetectable WebSocket connection mimicking legitimate Chrome fingerprints to monitor whales and L1 flows.
- **CoinGlass Discovery**: `nodriver`-powered DOM scraper that discovers top traders from exchange leaderboards.
- **Web Intelligence Link**: Fully integrated with a local SearXNG engine (`http://localhost:9345`) for real-time news and technical lookup.
- **Stealth Browsing**: Agents use `nodriver` to browse and digest the live web without being flagged as bots.

### 🧠 Triple-Agent Architecture
- **The Punisher**: Supreme Orchestrator (Wall Street Veteran Persona).
- **Satoshi**: On-chain & Flow specialist (Cold, Data-driven).
- **Joker**: Narrative & Media specialist (Cynical, Sentiment-focused).
- *See [AGENTS.MD](./AGENTS.MD) for full specs.*

### 🖥️ Unified Mission Control
- **Web Dashboard**: A premium, React-based UI with a dedicated "Live Intel Feed" and ChatGPT-style chat interface.
- **Direct CLI Chat**: High-speed, responsive chat via `uv run punisher chat` with aggressive log suppression for a pure tactical experience.
- **Real-time Telemetry**: Monitor mission status with `uv run punisher listen`.

---

## 🛠️ Stack & Installation

- **Backend**: Python 3.12, FastAPI, `uv`, Playwright/nodriver.
- **Frontend**: Vite, React, Tailwind, AlpineJS.
- **Databases**: MongoDB (Time-series data), SQLite (Message Queue & Knowledge Base).
- **Intelligence**: Local SearXNG engine.

### Setup
1. **Clone & Sync**:
   ```bash
   git clone git@github.com:monjurkuet/punisher.git
   cd punisher
   uv sync
   ```
2. **Environment**:
   ```bash
   cp .env.template .env # Fill in keys
   ```

---

## ⚡ Usage

### 1. Launch the Mission Control
Starts the Orchestrator, Telegram bot, and Research Scheduler.
```bash
uv run python src/punisher/server.py
```

### 2. Enter Direct Chat (Terminal)
Pure chat mode with system logs hidden.
```bash
uv run punisher chat
```

### 3. Monitor Live Telemetry
View raw hyperliquid feeds and agent logs in real-time.
```bash
uv run punisher listen
```

### 4. Launch Rich TUI Dashboard
Full-screen dashboard with live intel tape and positions.
```bash
uv run punisher dashboard
```

### 5. Open Web Dashboard
Accessible at `http://localhost:3000/`.

---

### 🔧 Tool-Calling
The agents can now execute local tools:
- `read_file(path)`: Read project files.
- `list_directory(path)`: List directory contents.
- `web_search(query)`: Search the web.

Ask: *"Read AGENTS.MD and tell me about the agents"* to trigger file access.

---

## 📂 Project Structure
- `src/punisher/core`: The Orchestrator, Agent Tools, and Subagents.
- `src/punisher/crypto`: Hyperliquid WebSocket/HTTP stealth monitors.
- `src/punisher/scrapers`: CoinGlass and high-level web extraction.
- `src/punisher/research`: YouTube pipeline and local knowledge base.
- `punisher-web`: React-based dashboard source.

## 🤝 Contributing
Commits follow [Conventional Commits](https://www.conventionalcommits.org/).

## 📜 License
MIT
