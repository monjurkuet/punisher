import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from punisher.bus.queue import MessageQueue
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
    # Silence all system logs during chat to keep the UI clean
    import logging

    # Disable propagation to root and set levels
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)
        logger.propagate = False
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    logging.root.setLevel(logging.WARNING)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    console.print(
        Panel(
            "[bold green]Punisher Direct Chat[/bold green]\n[dim]System logs disabled. Type 'exit' to quit.[/dim]",
            border_style="green",
        )
    )

    import asyncio
    from punisher.llm.gateway import LLMGateway

    gateway = LLMGateway()
    conversation_history = []

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            if user_input.lower() in ["exit", "quit"]:
                break

            # Add user message to history
            conversation_history.append({"role": "user", "content": user_input})

            # Get response from LLM
            with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
                try:
                    response = asyncio.run(gateway.chat(conversation_history))

                    # Add assistant response to history
                    conversation_history.append(
                        {"role": "assistant", "content": response}
                    )

                    console.print(f"[bold red]Punisher:[/bold red] {response}")
                except Exception as e:
                    console.print(
                        f"[bold red]Punisher:[/bold red] [LLM Error] {str(e)}"
                    )

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
def dashboard():
    """Launch the Rich TUI Dashboard for real-time monitoring."""
    from punisher.dashboard import main as dashboard_main

    dashboard_main()


@main.command()
def run():
    """Run the main CLI interactive loop."""
    console.print(
        Panel("[bold]Punisher AI[/bold]\nType 'exit' to quit.", border_style="green")
    )
    queue = MessageQueue()

    import threading

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
