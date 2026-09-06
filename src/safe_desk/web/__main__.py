from __future__ import annotations

import argparse
from pathlib import Path

from safe_desk.web.app import create_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe Desk local trader UI (dry-run, no secrets)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--log-dir", type=Path, default=Path("logs"))
    args = parser.parse_args(argv)
    try:
        import uvicorn
    except ImportError:
        print('Install the UI extras: pip install -e ".[dev]"')
        return 2
    application = create_app(log_dir=args.log_dir)
    print(f"Safe Desk UI  |  DRY-RUN  |  http://{args.host}:{args.port}")
    print("PAPER / SIMULATED journal — not live PnL. No secrets stored.")
    uvicorn.run(application, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
