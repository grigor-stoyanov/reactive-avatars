import argparse
import webbrowser

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="reactive-avatars",
        description="Mic-reactive avatar overlay for OBS / Streamlabs Browser Sources.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8347)
    parser.add_argument("--no-browser", action="store_true", help="don't open the settings page")
    args = parser.parse_args()

    base = f"http://{args.host}:{args.port}"
    print(f"Overlay  (Browser Source URL): {base}/")
    print(f"Settings (upload your avatar): {base}/settings")
    if not args.no_browser:
        try:
            webbrowser.open(f"{base}/settings")
        except Exception:
            pass
    uvicorn.run("reactive_avatars.server:app", host=args.host, port=args.port, log_level="warning")
