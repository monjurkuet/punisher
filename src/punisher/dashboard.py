import asyncio
from datetime import datetime
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.console import Console
from rich import box
from punisher.bus.queue import MessageQueue

console = Console()
queue = MessageQueue()


class SatoshiDashboard:
    def __init__(self):
        self.layout = Layout()
        self.messages = []
        self.positions = {}
        self.last_whale = "None"
        self.account_value = "0.00"
        self.start_time = datetime.now()

    def make_layout(self):
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )
        self.layout["body"].split_row(
            Layout(name="tape", ratio=2),
            Layout(name="stats", ratio=1),
        )

    def generate_table(self) -> Table:
        table = Table(
            box=box.MINIMAL_DOUBLE_HEAD, expand=True, border_style="bright_blue"
        )
        table.add_column("Time", style="cyan", width=10)
        table.add_column("Type", width=10)
        table.add_column("Message", style="white")

        for msg in self.messages[-15:]:
            table.add_row(msg["time"], msg["type"], msg["content"])
        return table

    def generate_positions_table(self) -> Table:
        table = Table(box=box.SIMPLE_HEAD, expand=True)
        table.add_column("Coin", style="bold yellow")
        table.add_column("Side", width=8)
        table.add_column("PnL", justify="right")

        for coin, data in self.positions.items():
            pnl = float(data.get("pnl", 0))
            pnl_style = "bold green" if pnl >= 0 else "bold red"
            table.add_row(coin, data.get("side", "N/A"), f"[{pnl_style}]${pnl:,.2f}[/]")
        return table

    def update(self):
        # Header
        header_content = f"[bold white]PUNISHER[/] // [bold green]SATOSHI ALPHA STREAM[/] | [dim]{datetime.now().strftime('%H:%M:%S')}[/]"
        self.layout["header"].update(
            Panel(header_content, border_style="bright_blue", box=box.ROUNDED)
        )

        # Main Tape
        self.layout["tape"].update(
            Panel(
                self.generate_table(),
                title="[bold cyan]Live Intel Tape[/]",
                border_style="cyan",
            )
        )

        # Stats Panel
        self.layout["stats"].update(
            Panel(
                self.generate_positions_table(),
                title="[bold yellow]Whale Positions[/]",
                border_style="yellow",
            )
        )

        # Footer
        uptime = str(datetime.now() - self.start_time).split(".")[0]
        footer_content = f"[dim]Uptime: {uptime} | Monitoring {len(self.positions)} pairs | Press CTRL+C to detach[/]"
        self.layout["footer"].update(Panel(footer_content, border_style="dim"))

    async def run(self):
        self.make_layout()
        with Live(self.layout, refresh_per_second=4, screen=True):
            while True:
                msg = queue.pop("punisher:cli:out", timeout=0)
                if msg:
                    timestamp = datetime.now().strftime("%H:%M:%S")

                    if "[WALLET]" in msg:
                        parts = msg.replace("[WALLET]", "").strip().split(" Value: ")
                        if len(parts) >= 2:
                            self.last_whale = parts[0]
                            self.account_value = parts[1].replace("$", "")
                            self.messages.append(
                                {
                                    "time": timestamp,
                                    "type": "[bold blue]WHALE[/]",
                                    "content": f"Target: {self.last_whale}",
                                }
                            )

                    elif "[POS]" in msg:
                        content = msg.replace("[POS]", "").strip()
                        if ":" in content and "PnL: " in content:
                            parts = content.split(":")
                            coin = parts[1].split("|")[0].strip()
                            pnl_part = (
                                content.split("PnL: ")[1]
                                .replace("$", "")
                                .replace(",", "")
                            )
                            side = "LONG" if "🟢" in content else "SHORT"

                            self.positions[coin] = {"side": side, "pnl": pnl_part}
                            self.messages.append(
                                {
                                    "time": timestamp,
                                    "type": "[bold green]POS[/]",
                                    "content": f"{side} {coin} update",
                                }
                            )

                    elif "[💎]" in msg:
                        self.messages.append(
                            {
                                "time": timestamp,
                                "type": "[bold magenta]INTEL[/]",
                                "content": msg.replace("[💎]", "").strip(),
                            }
                        )

                self.update()
                await asyncio.sleep(0.05)


def main():
    try:
        dash = SatoshiDashboard()
        asyncio.run(dash.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
