import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


BASH = shutil.which("bash") or ("C:/Program Files/Git/bin/bash.exe" if Path("C:/Program Files/Git/bin/bash.exe").is_file() else None)
ROOT = Path(__file__).parents[1]


@unittest.skipUnless(BASH, "Bash is required")
class InstallerTests(unittest.TestCase):
    def test_install_update_uninstall_reinstall_preserve_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            extras = root / "klipper/klippy/extras"
            extras.mkdir(parents=True)
            config = root / "config"
            config.mkdir()
            env = {**os.environ, "KLIPPER_DIR": (root / "klipper").as_posix(),
                   "PRINTER_CONFIG_DIR": config.as_posix(), "MEDUSAHC_CONFIG_DIR": (config / "MedusaHC").as_posix()}
            def run(action):
                result = subprocess.run([BASH, (ROOT / "install.sh").as_posix(), action], env=env, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            run("install")
            live = config / "MedusaHC/MHC_variables.cfg"
            live.write_text("# My geometry must survive\n", encoding="utf-8")
            run("update")
            self.assertEqual(live.read_text(), "# My geometry must survive\n")
            run("uninstall")
            self.assertFalse((extras / "medusahc.py").exists())
            self.assertTrue(live.exists())
            run("install")
            self.assertTrue((extras / "medusahc.py").is_file())
            self.assertEqual(live.read_text(), "# My geometry must survive\n")
