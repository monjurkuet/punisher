import asyncio
import json
from datetime import datetime
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Log, DataTable, Static, Label
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.binding import Binding
from rich.markdown import Markdown
from punisher.bus.queue import MessageQueue

queue = MessageQueue()


class ChatBubble(Static):
    """A standard chat message bubble container."""

    def __init__(self, content: str, sender: str, is_markdown: bool = True):
        super().__init__()
        self.content = content
        self.sender = sender
        self.is_markdown = is_markdown

    def compose(self) -> ComposeResult:
        timestamp = datetime.now().strftime("%H:%M")
        with Vertical(classes=f"bubble-container {self.sender.lower()}"):
            yield Label(f"{self.sender.upper()} • {timestamp}", classes="bubble-sender")
            if self.is_markdown:
                yield Static(Markdown(self.content), classes="bubble-content")
            else:
                yield Static(self.content, classes="bubble-content")


class LogStream(Log):
    """A high-velocity log for raw intel."""

    def on_mount(self):
        self.border_title = "ALPHA STREAM"


class PunisherTUI(App):
    TITLE = "PUNISHER // SUPREME INTELLIGENCE"

    CSS = """
    PunisherTUI {
        background: #000000;
    }
    
    #main_container {
        height: 1fr;
        padding: 1 2;
    }

    #chat_feed {
        height: 1fr;
        overflow-y: scroll;
        padding: 1 4;
        scrollbar-gutter: stable;
    }

    /* Bubble Styles */
    .bubble-container {
        margin: 1 0;
        padding: 1 2;
        width: 90%;
        border-left: solid #333333;
    }

    .orchestrator {
        background: #111111;
        border-left: solid #61afef;
        align-horizontal: right;
    }

    .punisher {
        background: #0a0a0a;
        border-left: solid #e06c75;
        align-horizontal: left;
    }

    .system {
        background: transparent;
        border: none;
        align-horizontal: center;
        opacity: 0.6;
    }

    .bubble-sender {
        color: #5c6370;
        margin-bottom: 1;
        text-style: bold;
    }

    .bubble-content {
        color: #ffffff;
    }

    /* Input Dock */
    #input_area {
        height: auto;
        border-top: solid #1a1a1a;
        padding: 1 4;
        background: #050505;
    }

    #chat_input {
        background: #1a1a1a;
        border: none;
        color: #ffffff;
        padding: 0 1;
        height: 3;
    }

    #prompt_prefix {
        color: #61afef;
        padding: 1 1;
        text-style: bold;
    }

    /* Stream/Matrix Overlay */
    #stream_log, #agent_matrix {
        display: none;
        height: 1fr;
        border: solid #1a1a1a;
        background: #000000;
    }

    Header {
        background: #050505;
        color: #ffffff;
        text-style: bold;
    }

    Footer {
        background: #050505;
    }
    """

    BINDINGS = [
        Binding("ctrl+l", "toggle_view('stream')", "Alpha Stream", show=True),
        Binding("ctrl+a", "toggle_view('matrix')", "Agent Matrix", show=True),
        Binding("ctrl+c", "toggle_view('chat')", "Back to Chat", show=True),
        Binding("q", "quit", "Exit", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main_container"):
            with ScrollableContainer(id="chat_feed"):
                yield ChatBubble(
                    "System Online. Awaiting Strategic Direction.",
                    "system",
                    is_markdown=False,
                )

            yield LogStream(id="stream_log")
            yield DataTable(id="agent_matrix")

        with Horizontal(id="input_area"):
            yield Static("❯", id="prompt_prefix")
            yield Input(placeholder="Type a command...", id="chat_input")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#chat_input").focus()
        self.run_worker(self.poll_queue(), thread=True)

        # Setup Matrix
        matrix = self.query_one("#agent_matrix", DataTable)
        matrix.add_columns("Agent", "Status", "Load")
        matrix.add_row("PUNISHER", "[bold green]ONLINE[/]", "IDLE")
        matrix.add_row("SATOSHI", "[bold blue]STREAMING[/]", "HYPERLIQUID")
        matrix.add_row("JOKER", "[bold yellow]DISGESTING[/]", "YOUTUBE")

    def action_toggle_view(self, view: str) -> None:
        self.query_one("#chat_feed").display = view == "chat"
        self.query_one("#stream_log").display = view == "stream"
        self.query_one("#agent_matrix").display = view == "matrix"

        if view == "chat":
            self.query_one("#chat_input").focus()

    async def poll_queue(self):
        """Standard queue polling logic."""
        while True:
            msg = queue.pop("punisher:cli:out", timeout=0.1)
            if msg:
                # 1. Update Raw Stream Log
                self.call_from_thread(self.query_one("#stream_log", Log).write, msg)

                # 2. Process Chat Bubbles
                if "PUNISHER IS THINKING" in msg:
                    self.call_from_thread(self.add_message, msg, "system")
                elif any(tag in msg for tag in ["[💎]", "[📺]", "[WALLET]", "[POS]"]):
                    pass  # Keep chat clean
                else:
                    self.call_from_thread(self.add_message, msg, "punisher")

            await asyncio.sleep(0.01)

    def add_message(self, content: str, sender: str):
        """Injects a new chat bubble into the feed."""
        feed = self.query_one("#chat_feed")
        bubble = ChatBubble(content, sender)
        feed.mount(bubble)
        bubble.scroll_visible()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd = event.value.strip()
        if cmd:
            self.query_one("#chat_input", Input).value = ""
            self.add_message(cmd, "orchestrator")

            # Push to System
            payload = {"source": "tui", "content": cmd}
            queue.push("punisher:inbox", json.dumps(payload))


def main():
    app = PunisherTUI()
    app.run()


if __name__ == "__main__":
    main()
