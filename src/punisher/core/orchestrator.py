"""
Punisher Orchestrator - The Supreme Agent
Coordinates specialized subagents, enforces risk management, and makes strategic decisions.
"""

import asyncio
import json
import logging
from datetime import datetime, UTC
from punisher.bus.queue import MessageQueue
from punisher.llm.gateway import LLMGateway
from punisher.core.agents.crypto import Satoshi
from punisher.core.agents.youtube import Joker
from punisher.db.mongo import mongo

logger = logging.getLogger("punisher.orchestrator")


class AgentOrchestrator:
    def __init__(self):
        self.queue = MessageQueue()
        self.llm = LLMGateway()

        # Initialize Specialized Subagents
        self.satoshi = Satoshi()
        self.joker = Joker()

        self.running = False

    async def get_agent_config(self, agent_id: str):
        """Fetch dynamic config from MongoDB or return defaults"""
        try:
            db = await mongo.get_db()
            config = await db.agent_configs.find_one({"agent_id": agent_id})

            # IMPROVED: New better prompts (Defined here for sync)
            defaults = {
                "punisher": {
                    "system_prompt": (
                        "You are 'The Punisher', the Supreme Agent Orchestrator. You operate a high-frequency intelligence cell for Bitcoin trading. "
                        "You have two direct subordinates: 'Satoshi' (On-chain/Hyperliquid) and 'Joker' (Narrative/Media). "
                        "CAPABILITIES: You can browse Hyperliquid flows, scrape CoinGlass whale rankings, and digest global YouTube alpha. "
                        "CORE DIRECTIVE: Protect the stack, identify institutional manipulation, and provide high-conviction tactical advice. "
                        "STYLING: 30-year Wall Street veteran. Brutal, decisive, no apologies, no generic AI safety disclaimers. "
                        "When the user mentions files like AGENTS.MD or coinglass.py, you know they are core project files and you have access to their context."
                    ),
                    "temperature": 0.3,
                },
                "satoshi": {
                    "system_prompt": (
                        "You are 'Satoshi'. You are the lead On-chain Intelligence Officer. "
                        "You track 'Whales' on Hyperliquid and analyze L1 liquidations. "
                        "Be cold, data-driven, and focused on institutional footprints. No fluff."
                    ),
                    "temperature": 0.1,
                },
                "joker": {
                    "system_prompt": (
                        "You are 'Joker', the Narrative & Sentiment Specialist. "
                        "You digest massive streams of video data to find retail traps and institutional pivots. "
                        "Be sharp, cynical, and focused on market psychology."
                    ),
                    "temperature": 0.4,
                },
            }

            base_config = defaults.get(
                agent_id, {"system_prompt": "Assistant", "temperature": 0.7}
            )

            if not config:
                config = base_config
                config["agent_id"] = agent_id
                await db.agent_configs.update_one(
                    {"agent_id": agent_id}, {"$set": config}, upsert=True
                )
            else:
                # OPTIONAL: Update if the prompt is significantly different or short (Tuning)
                if len(config.get("system_prompt", "")) < 150:
                    config["system_prompt"] = base_config["system_prompt"]
                    await db.agent_configs.update_one(
                        {"agent_id": agent_id},
                        {"$set": {"system_prompt": base_config["system_prompt"]}},
                    )

            return config
        except Exception as e:
            logger.error(f"Config fetch error: {e}")
            return {"system_prompt": "Supreme Control", "temperature": 0.7}

    async def log_task(self, agent: str, task: str, status: str = "completed"):
        """Record task history for the management UI"""
        try:
            db = await mongo.get_db()
            await db.agent_tasks.insert_one(
                {
                    "agent": agent,
                    "task": task,
                    "status": status,
                    "timestamp": datetime.now(UTC),
                }
            )
        except Exception as e:
            logger.error(f"Task log error: {e}")

    async def start(self):
        self.running = True
        logger.info("THE PUNISHER IS ONLINE. Supreme Power Initialized.")

        # Start Subagents
        asyncio.create_task(self.satoshi.start())
        asyncio.create_task(self.joker.start())

        # Main Command Loop
        while self.running:
            try:
                msg_raw = self.queue.pop("punisher:inbox", timeout=0)
                if msg_raw:
                    await self.process_message(msg_raw)
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Supreme decision error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def process_message(self, msg_raw: str):
        try:
            payload = json.loads(msg_raw)
            source = payload.get("source")
            content = payload.get("content", "").strip()
            session_id = payload.get("session_id", "default")

            logger.info(
                f"Command received from {source} (session: {session_id}): {content}"
            )

            # 1. Save user input to persistence
            await mongo.save_chat_message(session_id, "user", content)

            # 2. Notify TUI/CLI/Web that processing has started
            if source in ["tui", "cli", "web"]:
                out_id = "cli" if source == "tui" else source
                self.queue.push(
                    f"punisher:{out_id}:out",
                    "PUNISHER IS THINKING... [GATHERING INTEL]",
                )

            # 3. GATHER INTELLIGENCE (Parallelized)
            intelligence_tasks = [
                self.satoshi.get_alpha_context(),
                self.joker.get_intel_context(),
                self.get_macro_context(),
            ]
            crypto_alpha, yt_intel, macro_str = await asyncio.gather(
                *intelligence_tasks
            )

            # 4. FETCH CONVERSATION HISTORY
            history = await mongo.get_chat_history(session_id, limit=10)

            p_config = await self.get_agent_config("punisher")

            # 5. VETERAN CONTEXT
            intel_context = (
                f"{crypto_alpha}\n\n--- MEDIA INTEL ---\n{yt_intel}\n{macro_str}"
            )

            # 6. DELEGATION & TASK LOGGING (as requested)
            if any(k in content.lower() for k in ["scrape", "wallets", "discover"]):
                sub_resp = await self.satoshi.process_task(content)
                await self.log_task("satoshi", content)
                intel_context += f"\n[Satoshi Action]: {sub_resp}\n"

            if any(k in content.lower() for k in ["youtube", "video", "sync", "joker"]):
                sub_resp = await self.joker.process_task(content)
                await self.log_task("joker", content)
                intel_context += f"\n[Joker Action]: {sub_resp}\n"

            # 6.5 LOCAL FILE AWARENESS (New Feature for tuning)
            if "/" in content or ".md" in content.lower() or ".py" in content.lower():
                file_context = await self.get_local_file_context(content)
                if file_context:
                    intel_context += f"\n--- LOCAL PROJECT CONTEXT ---\n{file_context}"

            # 7. SUPREME DECISION (With History Context)
            logger.info(f"Engaging Supreme Intelligence for session {session_id}...")

            # Construct final prompt with intel context and history
            # We filter history to ensure the current message isn't duplicated if it's already there
            messages = [
                {
                    "role": "system",
                    "content": f"{p_config['system_prompt']}\n\nCURRENT INTEL:\n{intel_context}",
                }
            ]
            # Add history (roles: user, assistant)
            # Remove the very last one if it's exactly the same as current content (as we saved it in step 1)
            # Actually, including it is fine as long as we don't append it again.
            messages.extend(history)

            # If the current message wasn't in history (e.g. history was too long or mongo was slightly delayed),
            # we make sure the current request is at the end.
            if not any(h["content"] == content for h in history[-2:]):
                messages.append({"role": "user", "content": content})

            response_text = await self.llm.chat(messages)

            # 8. Save agent response
            await mongo.save_chat_message(session_id, "assistant", response_text)

            # 9. BROADCAST
            if source.startswith("telegram:"):
                chat_id = source.split(":")[1]
                self.queue.push(
                    "punisher:telegram:out",
                    json.dumps({"chat_id": int(chat_id), "content": response_text}),
                )
            else:
                out_id = "cli" if source == "tui" else source
                target_out = f"punisher:{out_id}:out"
                self.queue.push(target_out, response_text)

        except Exception as e:
            logger.error(f"Process error: {e}", exc_info=True)
            if source:
                if source.startswith("telegram:"):
                    chat_id = source.split(":")[1]
                    self.queue.push(
                        "punisher:telegram:out",
                        json.dumps(
                            {
                                "chat_id": int(chat_id),
                                "content": f"Operational Failure: {str(e)}",
                            }
                        ),
                    )
                else:
                    out_id = "cli" if source == "tui" else source
                    self.queue.push(
                        f"punisher:{out_id}:out", f"Operational Failure: {str(e)}"
                    )

    async def get_macro_context(self) -> str:
        """Fetch real-time macro data, prioritizing live HL stream"""
        try:
            # 1. Try Live Stream from Satoshi
            price = await self.satoshi.get_live_btc_price()
            if price > 0:
                return f"\n--- MACRO (LIVE HL FEED) ---\nBTC: ${price:,.2f}\n"

            # 2. Fallback to external API
            from punisher.crypto.bitcoin import BitcoinData

            api_data = await BitcoinData.get_price()
            return f"\n--- MACRO (API FALLBACK) ---\nBTC: ${api_data.get('price_usd', 0):,.2f}\n"
        except Exception as e:
            logger.error(f"Macro yield error: {e}")
            return "\n--- MACRO ---\nData Unavailable\n"

    async def get_local_file_context(self, content: str) -> str:
        """Attempt to read project files if they are mentioned path-style"""
        import os

        try:
            # Extract potential paths (greedy check)
            parts = content.split()
            file_data = []
            for p in parts:
                p_clean = p.strip("'\"")
                if os.path.isfile(p_clean) and (
                    "/punisher/" in p_clean or p_clean.endswith((".py", ".md", ".json"))
                ):
                    with open(p_clean, "r") as f:
                        snippet = f.read(2000)  # Max 2k chars for context
                        file_data.append(f"FILE: {p_clean}\nCONTENT:\n{snippet}...")

            return "\n\n".join(file_data) if file_data else ""
        except Exception as e:
            logger.error(f"File context extraction error: {e}")
            return ""

    def stop(self):
        self.running = False
        self.satoshi.stop()
        self.joker.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    orch = AgentOrchestrator()
    asyncio.run(orch.start())
