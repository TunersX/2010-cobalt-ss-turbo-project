from pathlib import Path
from tunersx.transports.demo import generate_demo_frames

def run_demo_capture(seconds: int, out_file: Path) -> dict:
    return generate_demo_frames(seconds=seconds, out_file=out_file)
