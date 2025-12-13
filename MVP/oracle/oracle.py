"""Price oracle for Session Contracts.

Supports two modes:
- sim: Generates correlated random walk prices
- replay: Replays prices from CSV file
"""
import argparse
import asyncio
import csv
import random
import time
from datetime import datetime
from typing import Dict, List, Optional
import httpx


class SimOracle:
    """Simulated price oracle with correlated random walk."""

    def __init__(self, legs: List[str], initial_prices: Dict[str, float] = None):
        self.legs = legs
        self.prices = initial_prices or {leg: 100.0 for leg in legs}
        self.volatilities = {leg: 0.02 for leg in legs}  # 2% volatility per tick

    def tick(self) -> Dict[str, float]:
        """Generate next price tick with correlated moves."""
        # Common market factor (correlation)
        market_factor = random.gauss(0, 0.01)

        for leg in self.legs:
            # Individual factor + market factor
            individual_factor = random.gauss(0, self.volatilities[leg])
            total_change = market_factor + individual_factor

            # Update price (geometric brownian motion)
            self.prices[leg] *= (1 + total_change)

            # Keep prices positive
            self.prices[leg] = max(self.prices[leg], 0.01)

        return self.prices.copy()


class ReplayOracle:
    """Replays prices from CSV file."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.data: List[Dict[str, float]] = []
        self.index = 0
        self.legs: List[str] = []
        self._load_csv()

    def _load_csv(self):
        """Load CSV data."""
        with open(self.csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip timestamp column
                prices = {k: float(v) for k, v in row.items() if k != 'ts'}
                self.data.append(prices)

        if self.data:
            self.legs = list(self.data[0].keys())

    def tick(self) -> Optional[Dict[str, float]]:
        """Get next price tick from replay data."""
        if self.index >= len(self.data):
            return None

        prices = self.data[self.index]
        self.index += 1
        return prices


async def stream_prices(
    session_id: str,
    oracle,
    backend_url: str,
    tick_ms: int,
    max_ticks: int = None
):
    """Stream prices to backend API."""
    tick_count = 0

    async with httpx.AsyncClient() as client:
        while True:
            # Get next tick
            prices = oracle.tick()
            if prices is None:
                print("Replay finished")
                break

            # Send to backend
            try:
                response = await client.post(
                    f"{backend_url}/api/v1/sessions/{session_id}/prices",
                    json={"prices": prices},
                    timeout=5.0
                )
                if response.status_code == 200:
                    timestamp = datetime.utcnow().isoformat()
                    print(f"[{timestamp}] Tick {tick_count}: {prices}")
                else:
                    print(f"Error sending prices: {response.status_code} {response.text}")
            except Exception as e:
                print(f"Error sending prices: {e}")

            tick_count += 1
            if max_ticks and tick_count >= max_ticks:
                print(f"Reached max ticks ({max_ticks})")
                break

            # Wait for next tick
            await asyncio.sleep(tick_ms / 1000.0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Session Contracts Price Oracle")
    parser.add_argument(
        "--mode",
        choices=["sim", "replay"],
        default="sim",
        help="Oracle mode: sim (random walk) or replay (from CSV)"
    )
    parser.add_argument(
        "--session-id",
        required=True,
        help="Session ID to publish prices for"
    )
    parser.add_argument(
        "--backend-url",
        default="http://localhost:8000",
        help="Backend API URL"
    )
    parser.add_argument(
        "--tick-ms",
        type=int,
        default=1000,
        help="Milliseconds between ticks"
    )
    parser.add_argument(
        "--csv",
        help="CSV file path (required for replay mode)"
    )
    parser.add_argument(
        "--legs",
        nargs="+",
        default=["AAPL", "NVDA", "META", "ORCL"],
        help="Leg names for sim mode"
    )
    parser.add_argument(
        "--initial-prices",
        type=float,
        nargs="+",
        help="Initial prices for sim mode (must match legs count)"
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        help="Maximum number of ticks (optional)"
    )

    args = parser.parse_args()

    # Create oracle
    if args.mode == "sim":
        initial_prices = None
        if args.initial_prices:
            if len(args.initial_prices) != len(args.legs):
                print("Error: initial-prices count must match legs count")
                return
            initial_prices = {leg: price for leg, price in zip(args.legs, args.initial_prices)}
        else:
            # Default initial prices
            initial_prices = {
                "AAPL": 190.0,
                "NVDA": 480.0,
                "META": 350.0,
                "ORCL": 104.0
            }
            # Filter to requested legs
            initial_prices = {leg: initial_prices.get(leg, 100.0) for leg in args.legs}

        oracle = SimOracle(args.legs, initial_prices)
        print(f"Starting sim oracle for session {args.session_id}")
        print(f"Legs: {args.legs}")
        print(f"Initial prices: {initial_prices}")

    elif args.mode == "replay":
        if not args.csv:
            print("Error: --csv required for replay mode")
            return

        oracle = ReplayOracle(args.csv)
        print(f"Starting replay oracle for session {args.session_id}")
        print(f"CSV: {args.csv}")
        print(f"Legs: {oracle.legs}")
        print(f"Loaded {len(oracle.data)} ticks")

    print(f"Backend: {args.backend_url}")
    print(f"Tick interval: {args.tick_ms}ms")
    if args.max_ticks:
        print(f"Max ticks: {args.max_ticks}")
    print()

    # Run streaming
    try:
        asyncio.run(stream_prices(
            args.session_id,
            oracle,
            args.backend_url,
            args.tick_ms,
            args.max_ticks
        ))
    except KeyboardInterrupt:
        print("\nStopped by user")


if __name__ == "__main__":
    main()
