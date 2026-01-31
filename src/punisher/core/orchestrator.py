import asyncio
import json
import logging
from punisher.bus.queue import MessageQueue
from punisher.config import settings
from punisher.llm.gateway import LLMGateway

logger = logging.getLogger("punisher.orchestrator")


class AgentOrchestrator:
    def __init__(self):
        self.queue = MessageQueue()
        self.llm = LLMGateway()

        # Initialize Crypto Monitors
        from punisher.crypto.hyperliquid import HyperliquidMonitor
        from punisher.crypto.hyperliquid_market import HyperliquidMarketMonitor

        self.hl_wallet_monitor = HyperliquidMonitor()
        self.hl_market_monitor = HyperliquidMarketMonitor(coin="BTC")

        self.running = False

    async def start(self):
        self.running = True
        logger.info("Orchestrator started. Listening on punisher:inbox")

        # Start background tasks
        asyncio.create_task(
            self.hl_wallet_monitor.start()
        )  # Wallet monitoring (WebSocket)
        asyncio.create_task(
            self.hl_market_monitor.start()
        )  # Market data (HTTP polling)

        while self.running:
            try:
                # Poll queue
                msg_raw = self.queue.pop("punisher:inbox", timeout=0)
                if msg_raw:
                    await self.process_message(msg_raw)
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in orchestrator loop: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def process_message(self, msg_raw: str):
        try:
            payload = json.loads(msg_raw)
            source = payload.get("source")
            content = payload.get("content", "").strip()

            logger.info(f"Processing message from {source}: {content}")

            response_text = ""

            # 1. SPECIAL COMMANDS
            if content.lower().startswith("search "):
                query = content[7:]
                from punisher.browser.client import BrowserClient

                browser = BrowserClient()
                result = await browser.search(query)
                await browser.stop()
                response_text = f"SEARCH RESULT:\n{result}"

            elif content.lower() in ["price", "btc", "bitcoin"]:
                from punisher.crypto.bitcoin import BitcoinData

                price = await BitcoinData.get_price()
                market = await BitcoinData.get_market_data()
                if "error" in price:
                    response_text = f"Error: {price['error']}"
                else:
                    response_text = f"BTC: ${price['price_usd']:,.2f} (24h: {market.get('change_24h', 0):.2f}%)"

            else:
                # 2. VETERAN AGENT LOGIC (Context-Aware)
                context_str = "--- MARKET INTELLIGENCE ---\n"

                # A. Live Price Data
                try:
                    from punisher.crypto.bitcoin import BitcoinData

                    price = await BitcoinData.get_price()
                    market = await BitcoinData.get_market_data()
                    context_str += (
                        f"BTC Price: ${price.get('price_usd', 0):,.2f} "
                        f"(24h: {market.get('change_24h', 0):.2f}%)\n"
                    )
                except Exception as e:
                    logger.error(f"Context Error (Price): {e}")

                # B. Research Database (Knowledge Base)
                try:
                    import sqlite3

                    conn = sqlite3.connect("research.db")
                    cursor = conn.cursor()
                    # Get latest 3 market metrics
                    cursor.execute(
                        "SELECT source, metric_name, value FROM market_metrics ORDER BY timestamp DESC LIMIT 3"
                    )
                    metrics = cursor.fetchall()
                    if metrics:
                        context_str += "Saved Metrics:\n"
                        for m in metrics:
                            context_str += f"- {m[0]} {m[1]}: {m[2]}\n"
                    conn.close()
                except Exception as e:
                    logger.error(f"Context Error (DB): {e}")

                # C. Live Web Research (Ad-hoc)
                # If query seems research-heavy, perform a quick search
                if any(
                    k in content.lower()
                    for k in [
                        "news",
                        "latest",
                        "check",
                        "find",
                        "search",
                        "what is",
                        "who is",
                    ]
                ):
                    try:
                        from punisher.browser.client import BrowserClient

                        # Spin up a temporary browser to check this specific thing
                        # This might be slow (5-10s), but provides accuracy
                        logger.info(f"Triggering research for: {content}")
                        browser = BrowserClient()
                        search_res = await browser.search(content)
                        await browser.stop()
                        context_str += f"\n--- LIVE WEB SERACH ---\n{search_res}\n"
                    except Exception as e:
                        context_str += f"\n[Web Research Failed: {e}]\n"

                # 2. LLM EXECUTION
                logger.info(f"Sending to LLM with context length: {len(context_str)}")

                response_text = await self.llm.chat(
                    [
                        {
                            "role": "system",
                            "content": (
                                "You are 'The Punisher', a 30-year Wall Street veteran trader who has pivoted to Bitcoin. "
                                "You act as a senior risk manager and strategist. "
                                "Your style is: Logical, brutally honest, risk-averse, and institutional. "
                                "You despise retail FOMO and hype. You focus on: 'Risk/Reward', 'Liquidity', 'Macro', and 'Market Structure'. "
                                "Use the provided MARKET INTELLIGENCE to back up your claims. "
                                "Be concise. Do not give financial advice, give strategic analysis."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"CONTEXT:\n{context_str}\n\nUSER QUERY:\n{content}",
                        },
                    ]
                )

            # Route response back to source
            if source == "cli":
                self.queue.push("punisher:cli:out", response_text)
            elif source == "cli_chat":
                self.queue.push("punisher:cli_chat:out", response_text)

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message: {msg_raw}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            if source == "cli":
                self.queue.push("punisher:cli:out", f"Error: {str(e)}")

    def stop(self):
        self.running = False
