"""İmza stil geçişleri (firca, murekkep): ffmpeg ifadeyi kabul eder, geçişin ortasında iki sahne de görünür."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kurgu  # noqa: E402


def orta_kare(tur: str) -> np.ndarray:
    with tempfile.TemporaryDirectory() as d:
        yol = Path(d) / "k.rgb"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "lavfi", "-i", "color=c=black:s=320x568:r=30:d=1.5",
                        "-f", "lavfi", "-i", "color=c=white:s=320x568:r=30:d=1.5",
                        "-filter_complex", "[0:v]format=yuv420p,settb=AVTB[a];[1:v]format=yuv420p,settb=AVTB[b];"
                        f"[a][b]xfade=transition={kurgu.GECISLER[tur]}:duration=0.8:offset=0.3,"
                        "select='eq(n\\,21)',format=gray",
                        "-frames:v", "1", "-f", "rawvideo", str(yol)], check=True)
        return np.frombuffer(yol.read_bytes(), np.uint8).reshape(568, 320)


class StilGecisi(unittest.TestCase):
    def test_iki_sahne_de_gorunur(self):
        for tur in ("firca", "murekkep"):
            k = orta_kare(tur)
            self.assertGreater((k > 200).mean(), 0.15, tur)  # yeni sahne
            self.assertGreater((k < 40).mean(), 0.15, tur)  # eski sahne (+ mürekkep çizgisi)

    def test_kurgu_denetimi_kabul_eder(self):
        self.assertIn("firca", kurgu.GECISLER)
        self.assertIn("murekkep", kurgu.GECISLER)


if __name__ == "__main__":
    unittest.main()
