from multiprocessing import Process
from unittest import TestCase

from click.testing import CliRunner
from vpnmd.appd import Server

from vpnm import app
from vpnm.vpnmd_api import Session
from vpnm.web_api import Secret

RUNNER = CliRunner()
CREDS_INPUT = "nikiforova693@gmail.com\nxaswug-syVryc-huvfy9"


class TestClass01(TestCase):
    """auth negative"""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        if Secret.file.exists():
            Secret.file.unlink()

    def test_case01(self):
        """Account"""
        self.assertFalse(Secret.file.exists())
        result = RUNNER.invoke(app.account)
        self.assertIsNone(result.exception)
        self.assertEqual(
            "Are you logged in?\nCheck it with 'vpnm login'\n", result.output
        )

    def test_case02(self):
        """Logout"""
        result = RUNNER.invoke(app.logout)
        self.assertIsNone(result.exception)
        self.assertEqual("Logged out\n", result.output)
        self.assertFalse(Secret.file.exists())

    def test_case03(self):
        """Login"""
        result = RUNNER.invoke(app.login, input=CREDS_INPUT)
        self.assertIsNone(result.exception)
        self.assertEqual("Logged in\n", result.output)
        self.assertTrue(Secret.file.exists())


class TestClass02(TestCase):
    """auth positive"""

    def test_case01(self):
        """Login"""
        self.assertTrue(Secret.file.exists())
        result = RUNNER.invoke(app.login)
        self.assertIsNone(result.exception)
        self.assertEqual("Logged in\n", result.output)

    def test_case02(self):
        """Account"""
        self.assertTrue(Secret.file.exists())
        result = RUNNER.invoke(app.account)
        self.assertIsNone(result.exception)
        self.assertIn("Current balance", result.output)
        self.assertIn("Devices online", result.output)
        self.assertIn("Expire date", result.output)
        self.assertIn("Traffic left", result.output)


class TestClass03(TestCase):
    """vpnmd negative"""

    def test_case01(self):
        """Connect"""
        result = RUNNER.invoke(app.connect, args=("--random"))
        self.assertIsNone(result.exception)
        self.assertEqual(
            "Is vpnm daemon running?\nCheck it with 'systemctl status vpnmd'\n",
            result.output,
        )

    def test_case02(self):
        """Disconnect"""
        result = RUNNER.invoke(app.disconnect)
        self.assertIsNone(result.exception)
        self.assertEqual(
            "Is vpnm daemon running?\nCheck it with 'systemctl status vpnmd'\n",
            result.output,
        )

    def test_case03(self):
        """Status"""
        result = RUNNER.invoke(app.status)
        self.assertIsNone(result.exception)
        self.assertEqual(
            "Is vpnm daemon running?\nCheck it with 'systemctl status vpnmd'\n",
            result.output,
        )


class TestClass04(TestCase):
    """vpnmd positive"""

    server_address = ("localhost", 4000)
    server = Server(server_address)
    server_process = Process(target=server.start)

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.server_process.start()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        cls.server_process.terminate()

    def test_case01(self):
        """vpnmd is running"""
        self.assertTrue(self.server_process.is_alive())

    def test_case02(self):
        """Connect random"""
        result = RUNNER.invoke(app.connect, args=("--random"))
        self.assertIsNone(result.exception)
        self.assertIn("Connected to", result.output)
        self.assertTrue(Session.file.exists())

    def test_case03(self):
        """Status"""
        result = RUNNER.invoke(app.status)
        self.assertIsNone(result.exception)
        self.assertIn("Connected to", result.output)

    def test_case04(self):
        """Disconnect"""
        result = RUNNER.invoke(app.disconnect)
        self.assertIsNone(result.exception)
        self.assertEqual("Disconnected\n", result.output)

    def test_case05(self):
        """Status"""
        result = RUNNER.invoke(app.status)
        self.assertIsNone(result.exception)
        self.assertEqual("Not connected\n", result.output)

    def test_case06(self):
        """Connect manual"""
        result = RUNNER.invoke(app.connect, input="1\n")
        self.assertIsNone(result.exception)
        self.assertIn("Connected to", result.output)
        self.assertTrue(Session.file.exists())

    def test_case07(self):
        """Disconnect"""
        result = RUNNER.invoke(app.disconnect)
        self.assertIsNone(result.exception)
        self.assertEqual("Disconnected\n", result.output)

    def test_case08(self):
        """Connect best"""
        result = RUNNER.invoke(app.connect, args=("--best"))
        self.assertIsNone(result.exception)
        self.assertIn("Connected to", result.output)
        self.assertTrue(Session.file.exists())

    def test_case09(self):
        """Disconnect"""
        result = RUNNER.invoke(app.disconnect)
        self.assertIsNone(result.exception)
        self.assertEqual("Disconnected\n", result.output)

    def test_case10(self):
        result = RUNNER.invoke(app.logout)
        self.assertIsNone(result.exception)
        self.assertEqual("Logged out\n", result.output)
        self.assertFalse(Secret.file.exists())
