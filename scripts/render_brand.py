"""Reproducibly render Home Assistant native local brand images from SVG."""
from pathlib import Path
import cairosvg

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "assets" / "branding" / "itc-icon.svg"
dest = ROOT / "custom_components" / "homefitnesscode" / "brand"
dest.mkdir(parents=True, exist_ok=True)
for filename, px in (("icon.png", 256), ("icon@2x.png", 512)):
    target = dest / filename
    cairosvg.svg2png(
        url=str(source), write_to=str(target),
        output_width=px, output_height=px,
    )
    if target.stat().st_size < 1024:
        raise RuntimeError(f"Unexpectedly small brand asset: {target}")
    print(f"{target.relative_to(ROOT)}: {target.stat().st_size:,} bytes")
