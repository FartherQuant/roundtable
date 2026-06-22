"""CLI entry point for roundtable."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.markdown import Markdown

from .engine import run_deep, run_quick
from .loader import list_personas, load_personas

DEFAULT_PERSONAS = ["kahneman", "munger", "deng-xiaoping"]

console = Console()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="roundtable",
        description="Multi-perspective structured discussion via LLM personas",
    )
    parser.add_argument(
        "topic",
        nargs="?",
        help="The topic/question to discuss",
    )
    parser.add_argument(
        "-p",
        "--personas",
        default=None,
        help=f"Comma-separated persona names (default: {','.join(DEFAULT_PERSONAS)})",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["quick", "deep"],
        default="quick",
        help="Discussion mode: quick=1 LLM call (~30s), deep=5 LLM calls (~2.5min) (default: quick)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM model name (default: gpt-4o, or ROUNDTABLE_MODEL env var)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available personas and exit",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw markdown without rich formatting",
    )

    args = parser.parse_args(argv)

    # --list: show available personas
    if args.list:
        available = list_personas()
        if not available:
            console.print("[yellow]No personas found.[/yellow]")
            return
        console.print("[bold]Available personas:[/bold]\n")
        for name, path in available.items():
            console.print(f"  {name}")
        console.print(
            f"\n[dim]Default: {', '.join(DEFAULT_PERSONAS)}[/dim]"
        )
        return

    # topic is required when not using --list
    if not args.topic:
        parser.error("topic is required (unless using --list)")

    # Parse persona names
    if args.personas:
        persona_names = [n.strip() for n in args.personas.split(",")]
    else:
        persona_names = DEFAULT_PERSONAS

    # Load personas
    try:
        personas = load_personas(persona_names)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    # Show header
    persona_names_str = ", ".join(p.name for p in personas)
    console.print(
        f"\n[bold]Roundtable[/bold] | Mode: {args.mode} | "
        f"Personas: {persona_names_str}\n"
        f"[dim]Topic: {args.topic}[/dim]\n"
    )

    # Run discussion
    try:
        with console.status("[bold green]Discussing..."):
            if args.mode == "quick":
                result = run_quick(args.topic, personas, model=args.model)
            else:
                result = run_deep(args.topic, personas, model=args.model)
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    # Output result
    if args.raw:
        print(result)
    else:
        console.print(Markdown(result))

    console.print("\n[dim]--- Roundtable complete ---[/dim]")


if __name__ == "__main__":
    main()
