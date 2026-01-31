import click
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from punisher.bus.queue import MessageQueue
from punisher.config import settings
import sys

console = Console()


@click.group()
def main():
    """Punisher - Privacy-First Bitcoin AI Assistant CLI"""
    pass


@main.command()
@click.argument("message", required=False)
def send(message):
    """Send a message to the orchestrator queue."""
    queue = MessageQueue()
    if not message:
        message = click.prompt("Message")

    payload = {"source": "cli", "content": message}
    queue.push("punisher:inbox", payload)
    console.print(f"[green]Sent:[/green] {message}")


@main.command()
def chat():
    """Continuous Chat Mode with Punisher Agent"""
    console.print(
        "[bold green]Punisher Continuous Chat[/bold green] (Type 'exit' to quit)"
    )

    from punisher.bus.queue import MessageQueue

    queue = MessageQueue()

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            if user_input.lower() in ["exit", "quit"]:
                break

            # Send to Orchestrator
            msg = {
                "source": "cli_chat",
                "content": user_input,
                "timestamp": datetime.now().isoformat(),
            }
            queue.push("punisher:inbox", json.dumps(msg))

            # Wait for response (simplified sync wait for MVP)
            # In a real event-driven system, we'd listen effectively.
            # Here we just block-wait on a specific return channel.

            with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
                # Poll for response
                tries = 0
                while tries < 30:  # 30s timeout
                    resp = queue.pop("punisher:cli_chat:out")
                    if resp:
                        console.print(f"[bold red]Punisher:[/bold red] {resp}")
                        break
                    import time

                    time.sleep(0.5)
                    tries += 1

        except KeyboardInterrupt:
            break


@main.command()
def listen():
    """Listen for messages from the orchestrator."""
    queue = MessageQueue()
    console.print("[bold yellow]Listening for responses...[/bold yellow]")
    while True:
        try:
            msg = queue.pop("punisher:cli:out", timeout=1)
            if msg:
                console.print(Panel(msg, title="Punisher", border_style="blue"))
        except KeyboardInterrupt:
            console.print("Stopping...")
            sys.exit(0)


@main.command()
def run():
    """Run the main CLI interactive loop."""
    console.print(
        Panel("[bold]Punisher AI[/bold]\nType 'exit' to quit.", border_style="green")
    )
    queue = MessageQueue()

    import threading
    import time

    def listener():
        while True:
            msg = queue.pop("punisher:cli:out", timeout=1)
            if msg:
                console.print(f"\n[bold blue]Punisher:[/bold blue] {msg}")
                console.print("[bold green]You:[/bold green] ", end="")

    t = threading.Thread(target=listener, daemon=True)
    t.start()

    while True:
        try:
            msg = console.input("[bold green]You:[/bold green] ")
            if msg.lower() in ["exit", "quit"]:
                break

            payload = {"source": "cli", "content": msg}
            queue.push("punisher:inbox", payload)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
