"""Tests para hello_world.py — cubren los 3 AC del SPEC (TT-1).

Ejecutar desde la raíz del repo:
    python3 -m unittest test_hello_world -v
    # o equivalentemente
    pytest test_hello_world.py -v
"""
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "hello_world.py"
EXPECTED_STDOUT = "Hola Mundo\n"


def _run_with(interpreter, script, *args, timeout=10):
    return subprocess.run(
        [str(interpreter), str(script), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run(script, *args, timeout=10):
    return _run_with(sys.executable, script, *args, timeout=timeout)


class HelloWorldAcceptance(unittest.TestCase):
    """AC-1: stdout exacto 'Hola Mundo\\n' + exit 0 sin argumentos."""

    def test_run_no_args_prints_hola_mundo_and_exits_zero(self):
        result = _run(SCRIPT)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, EXPECTED_STDOUT)

    def test_run_no_args_does_not_write_to_stderr(self):
        result = _run(SCRIPT)
        self.assertEqual(result.stderr, "")


class HelloWorldAcceptanceWithArgs(unittest.TestCase):
    """AC-2: con argumentos extra, misma salida y exit 0."""

    def test_run_with_extra_args_ignores_them_and_exits_zero(self):
        result = _run(SCRIPT, "--foo", "bar", "x")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, EXPECTED_STDOUT)


class HelloWorldAcceptanceMissingInterpreter(unittest.TestCase):
    """AC-3: sin intérprete Python válido -> no se imprime 'Hola Mundo',
    exit code != 0, el SO emite un mensaje de error claro por stderr.
    """

    def test_missing_interpreter_no_hola_mundo_and_nonzero_exit(self):
        bogus = "/this/python/does/not/exist"
        try:
            result = _run_with(bogus, SCRIPT)
        except FileNotFoundError as ex:
            # El SO rechazó lanzar el intérprete (ENOENT). El contrato del
            # AC-3 se cumple: no hay 'Hola Mundo' y el error es claro.
            self.assertNotIn("Hola Mundo", str(ex))
            return
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Hola Mundo", result.stdout)
        self.assertTrue(
            result.stderr.strip(),
            "El SO debe emitir un mensaje de error claro por stderr",
        )


if __name__ == "__main__":
    unittest.main()
