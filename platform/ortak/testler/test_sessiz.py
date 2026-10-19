import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import sessiz  # noqa: E402


class Sessiz(unittest.TestCase):
    def test_ozet_hata_ve_son_satirlar(self):
        satirlar = [f"kare {i}" for i in range(100)]
        satirlar[10] = "Error: dosya yok"
        out = sessiz.ozet(satirlar, son=3)
        self.assertEqual(out, ["Error: dosya yok", "…", "kare 97", "kare 98", "kare 99"])

    def test_cikis_kodu_ve_log(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "a.log"
            kod_py = "import sys; [print(i) for i in range(500)]; sys.exit(3)"
            buf = io.StringIO()
            with redirect_stdout(buf):
                kod = sessiz.main(["--satir", "2", "--log", str(log), "--", sys.executable, "-c", kod_py])
            self.assertEqual(kod, 3)
            self.assertEqual(len(log.read_text().splitlines()), 500)
            ekran = buf.getvalue().splitlines()
            self.assertIn("çıkış 3", ekran[0])
            self.assertEqual(ekran[1:], ["498", "499"])


if __name__ == "__main__":
    unittest.main()
