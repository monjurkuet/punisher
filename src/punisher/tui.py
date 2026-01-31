import json
import httpx
from datetime import datetime

from rich.markdown import Markdown
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.message import Message
from textual.widgets import Header, Footer, Input, Log, DataTable, Static, Label, Select

from punisher.bus.queue import MessageQueue

# Initialize Infrastructure
queue = MessageQueue()


class NewMessage(Message):
    """Signal for new data received from the mission queue."""

    def __init__(self, content: str):
        self.payload = content
        super().__init__()


class ChatBubble(Static):
    """A high-fidelity message container with semantic highlighting."""

    def __init__(self, content: str, sender: str, is_markdown: bool = True):
        super().__init__()
        self.message_content = content
        self.sender = sender
        self.is_markdown = is_markdown

    def compose(self) -> ComposeResult:
        ts = datetime.now().strftime("%H:%M:%S")
        with Vertical(classes=f"bubble-container {self.sender.lower()}"):
            yield Label(f"[{self.sender.upper()}] // {ts}", classes="bubble-meta")
            if self.is_markdown:
                yield Static(Markdown(self.message_content), classes="bubble-body")
            else:
                yield Static(self.message_content, classes="bubble-body")


class PunisherTUI(App):
    """
    MISSION CONTROL CENTER
    High-performance TUI for Autonomous Trading Intelligence.
    """

    TITLE = "PUNISHER // MISSION CONTROL"
    SUB_TITLE = "SYSTEM READY"

    CSS = """
    PunisherTUI {
        background: #000000;
        color: #e0e0e0;
    }

    #app_grid {
        layout: grid;
        grid-size: 3;
        grid-columns: 25% 1fr 25%;
        height: 1fr;
        margin: 0;
        padding: 0;
    }

    /* Sidebars */
    .sidebar {
        background: #050505;
        border-right: solid #333;
        padding: 0;
        margin: 0;
    }

    .right-sidebar {
        background: #050505;
        border-left: solid #333;
        padding: 0;
        margin: 0;
    }

    .panel-header {
        color: #00ff41;
        text-style: bold;
        background: #111;
        height: 1;
        width: 100%;
        content-align: center middle;
        margin: 0;
        border-bottom: solid #333;
    }

    /* Center Mission Feed */
    #center_pane {
        height: 1fr;
        background: #000;
        margin: 0;
        padding: 0;
    }

    #chat_history {
        height: 1fr;
        padding: 0 1;
        overflow-y: scroll;
        scrollbar-gutter: stable;
    }

    /* Message Aesthetics - Dense */
    .bubble-container {
        margin-top: 1;
        padding: 0 1;
        background: #0a0a0a;
        border-left: solid #333;
    }

    .bubble-meta { 
        color: #888; 
        margin: 0;
        text-style: bold;
    }
    
    .bubble-body { 
        color: #eee; 
        padding-bottom: 0;
    }

    .orchestrator { border-left: solid #3a86ff; background: #080c14; }
    .punisher { border-left: solid #ff006e; background: #140810; }
    .system { border-left: solid #555; background: #000; opacity: 0.8; }

    /* Command Input - High Contrast */
    #input_bar {
        height: 3;
        border-top: solid #333;
        background: #111;
        padding: 0;
        margin: 0;
        align-vertical: middle;
    }

    #chat_input {
        border: none;
        background: #222;
        color: #ffffff;
        height: 1;
        width: 1fr;
        padding: 0 1;
    }
    
    #chat_input:focus {
        border: none;
    }

    #prompt {
        color: #00ff41;
        padding-left: 1;
        padding-right: 1;
        text-style: bold;
        content-align: center middle; 
        height: 1;
    }
    
    /* Model Selection */
    #model_select {
        margin: 0;
        border: none;
        height: 3;
        background: #111;
    }

    SelectCurrent {
        border: none;
        background: #111;
        color: #00ff41;
    }

    /* Data Visualization */
    DataTable {
        background: transparent;
        border: none;
        height: 1fr;
        margin: 0;
    }

    Log {
        background: transparent;
        color: #00ff41;
        height: 1fr;
        border: none;
        margin: 0;
    }

    Header { background: #111; color: #00ff41; text-style: bold; height: 1; margin: 0; }
    Footer { background: #111; height: 1; margin: 0; }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Shutdown", show=True),
        Binding("ctrl+k", "clear_stream", "Clear Stream", show=True),
        Binding("ctrl+r", "refresh_matrix", "Refresh Matrix", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="app_grid"):
            # L-Pane: Intelligence Matrix & Config
            with Vertical(classes="sidebar"):
                yield Label("SYSTEM STATUS", classes="panel-header")
                yield Select([], prompt="Loading Models...", id="model_select")
                yield DataTable(id="agent_matrix")

            # C-Pane: Mission Objectives
            with Vertical(id="center_pane"):
                with ScrollableContainer(id="chat_history"):
                    yield ChatBubble(
                        "SECURE LINK ESTABLISHED. READY FOR PROTOCOL.", "system", False
                    )

                with Horizontal(id="input_bar"):
                    yield Static("❯", id="prompt")
                    yield Input(
                        placeholder="ENTER COMMAND PROTOCOL...", id="chat_input"
                    )

            # R-Pane: Alpha Stream (Live Intel)
            with Vertical(classes="right-sidebar"):
                yield Label("INTEL STREAM", classes="panel-header")
                yield Log(id="stream_log")

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#chat_input").focus()
        self._init_matrix()
        self.fetch_models()
        self.poll_queue_worker()

    def _init_matrix(self):
        matrix = self.query_one("#agent_matrix", DataTable)
        matrix.clear(columns=True)
        matrix.add_columns("SYSTEM", "LOAD", "CORE")
        matrix.add_row("ORCHESTRA", "[green]HEALTHY[/]", "AUTO")
        matrix.add_row("PUNISHER", "[bold cyan]IDLE[/]", "LLM")
        matrix.add_row("RESEARCH", "[yellow]ACTIVE[/]", "YTB")

    @work(thread=True)
    def fetch_models(self):
        """Fetches available LLM models from the local gateway."""
        try:
            response = httpx.get("http://localhost:8087/v1/models", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                models = [(m["id"], m["id"]) for m in data.get("data", [])]

                # Update UI on main thread
                def update_select():
                    select = self.query_one("#model_select", Select)
                    select.set_options(models)
                    select.value = "vision-model_QWEN"  # Default preference

                self.call_from_thread(update_select)
        except Exception as e:
            error_msg = str(e)

            def show_error():
                self.query_one("#stream_log", Log).write(
                    f"[ERROR] Failed to fetch models: {error_msg}"
                )

            self.call_from_thread(show_error)

    @work(thread=True)
    def poll_queue_worker(self) -> None:
        """Isolated sync thread for blocking queue polling."""
        while True:
            msg = queue.pop("punisher:cli:out", timeout=1)
            if msg:
                self.post_message(NewMessage(msg))

    @on(NewMessage)
    async def handle_incoming(self, message: NewMessage) -> None:
        raw = message.payload

        # 1. Direct to Intel Stream
        self.query_one("#stream_log", Log).write(raw)

        # 2. Filter for Mission Objectives (Chat)
        if not any(tag in raw for tag in ["[💎]", "[📺]", "[WALLET]", "[POS]"]):
            sender = "punisher"
            if "[SYSTEM]" in raw.upper() or "INITIALIZING" in raw.upper():
                sender = "system"
            await self.post_chat_bubble(raw, sender)

    async def post_chat_bubble(self, content: str, sender: str):
        history = self.query_one("#chat_history")
        bubble = ChatBubble(content, sender)
        await history.mount(bubble)
        bubble.scroll_visible()

    @on(Input.Submitted)
    async def handle_command(self, event: Input.Submitted) -> None:
        cmd = event.value.strip()
        if not cmd:
            return

        self.query_one("#chat_input", Input).value = ""
        await self.post_chat_bubble(cmd, "orchestrator")

        # Dispatch via Message Bus
        envelope = {
            "source": "mission_control",
            "content": cmd,
            "timestamp": datetime.now().isoformat(),
        }
        queue.push("punisher:inbox", json.dumps(envelope))

    @on(Select.Changed)
    def on_model_select(self, event: Select.Changed) -> None:
        """Handle model change events."""
        if event.value:
            self.query_one("#stream_log", Log).write(
                f"[SYSTEM] Model switched to: {event.value}"
            )
            # Here we could push a config update to the queue if needed
            # queue.push("punisher:config", json.dumps({"model": event.value}))

    def action_clear_stream(self):
        self.query_one("#stream_log", Log).clear()

    def action_refresh_matrix(self):
        self._init_matrix()


def main():
    """CLI Entrypoint for punisher-tui."""
    app = PunisherTUI()
    app.run()


if __name__ == "__main__":
    main()
