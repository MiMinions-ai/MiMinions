import asyncio
import signal
import click
from miminions.core.gateway import GatewayOrchestrator, MessageBus, Phase


class SimpleGateway(GatewayOrchestrator):
    """Minimal gateway orchestrator for CLI usage."""

    def __init__(self):
        super().__init__()
        self.bus = MessageBus()

    async def configure(self):
        # Register the message bus
        self.register(Phase.BUS, self.bus)
        # TODO: Add channels, services as needed


@click.group()
def gateway_cli():
    """Gateway management commands."""
    pass


@gateway_cli.command()
@click.option('--host', default='localhost', help='Host to bind to')
@click.option('--port', default=8000, type=int, help='Port to bind to')
def start(host, port):
    """Start the gateway server."""
    click.echo(f"Starting gateway on {host}:{port}")

    gateway = SimpleGateway()

    def signal_handler(signum, frame):
        click.echo("Received signal, shutting down...")
        asyncio.create_task(gateway.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(gateway.start())
        # Keep running until interrupted
        click.echo("Gateway is running. Press Ctrl+C to stop.")
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        click.echo("Shutting down gateway...")
        asyncio.run(gateway.shutdown())
    except Exception as e:
        click.echo(f"Error starting gateway: {e}")
        raise click.Abort()


@gateway_cli.command()
def status():
    """Check gateway status."""
    click.echo("Gateway status: Not running (CLI status check not implemented yet)")