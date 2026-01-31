# Punisher AI Agents

This document outlines the specialized AI agents operating within the Punisher ecosystem. Each agent is designed to run locally, ensuring data sovereignty and privacy.

## 1. Market Intelligence Agent (The Whale)
Monitors on-chain data and exchange flows to identify institutional movement.
- **Focus**: BTC exchange net flows, whale wallet tracking, and liquidation heatmaps.
- **Tools**: Local blockchain indexers, Mempool.space API.

## 2. Sentiment & Social Agent (The Oracle)
Analyzes market sentiment without relying on centralized social media APIs.
- **Focus**: Fear & Greed Index, local scraping of Bitcoin forums, and developer activity.
- **Tools**: `nodriver` for undetectable browser automation, local LLM sentiment analysis.

## 3. Research & Synthesis Agent (The Librarian)
Continuously updates the local knowledge base with the latest Bitcoin improvement proposals (BIPs) and macro-economic shifts.
- **Focus**: Automated research papers, technical documentation, and news synthesis.
- **Tools**: Local search engine integration (http://localhost:9345/docs), RAG (Retrieval-Augmented Generation).

## 4. Execution & Automation Agent (The Operator)
Handles the interaction between the user and the local system or web interfaces.
- **Focus**: Telegram bot management, CLI command execution, and browser-based task automation.
- **Tools**: Python-telegram-bot, `nodriver`.

## Agent Communication Protocol
Agents communicate via a local message bus to ensure that insights from the **Oracle** (Sentiment) can be immediately cross-referenced by the **Whale** (On-chain data) before being presented to the user via the **Operator**.
