from multiprocessing import Process
from pathlib import Path
from unittest import TestCase

from click.testing import CliRunner
from vpnmd.appd import Server

from vpnm import app
from vpnm.vpnmd_api import Connection
from vpnm.web_api import Secret

RUNNER = CliRunner()
CREDS_INPUT = "nikiforova693@gmail.com\nxaswug-syVryc-huvfy9"
CONFIG = Path(Connection.config)


class TestClass01(TestCase):
    """auth negative"""

    # @classmethod
    # def setUpClass(cls) -> None:
    #     super().setUpClass()

    #     if Secret.get_file().exists():
    #         Secret.get_file().unlink()

    #     if CONFIG.exists():
    #         CONFIG.unlink()

    # @classmethod
    # def tearDownClass(cls) -> None:
    #     super().tearDownClass()

    #     if Secret.get_file().exists():
    #         Secret.get_file().unlink()

    def test_case01(self):
        """Account while not logged in"""
        result = RUNNER.invoke(app.account)
        self.assertIsNone(result.exception)
        self.assertEqual(
            "Are you logged in?\nCheck it with 'vpnm login'\n", result.output
        )

    def test_case02(self):
        """Logout while not logged in"""
        result = RUNNER.invoke(app.logout)
        self.assertIsNone(result.exception)
        self.assertEqual("Logged out\n", result.output)

    def test_case03(self):
        """Login with wrong creds"""
        result = RUNNER.invoke(app.login, input=CREDS_INPUT.upper())
        self.assertIsNone(result.exception)
        self.assertEqual(
            result.output,
            "Email: NIKIFOROVA693@GMAIL.COM\nPassword: \n402 Incorrect email or password\n",
        )

    def test_case04(self):
        """Login"""
        result = RUNNER.invoke(app.login, input=CREDS_INPUT)
        self.assertIsNone(result.exception)
        self.assertEqual(
            "Email: nikiforova693@gmail.com\nPassword: \nLogged in\n", result.output
        )
        self.assertTrue(Secret.get_file().exists())

    def test_case05(self):
        """Account while logged in"""
        self.assertTrue(Secret.get_file().exists())
        result = RUNNER.invoke(app.account)
        self.assertIsNone(result.exception)
        self.assertIn("Current balance", result.output)
        self.assertIn("Devices online", result.output)
        self.assertIn("Expire date", result.output)
        self.assertIn("Traffic left", result.output)

    def test_case06(self):
        """Connect without vpnmd running"""
        result = RUNNER.invoke(app.connect, args=("--random",))
        self.assertIsNone(result.exception)
        self.assertEqual(
            "Is vpnm daemon running?\nCheck it with 'systemctl status vpnmd'\n",
            result.output,
        )
        # self.assertTrue(CONFIG.exists())

    def test_case07(self):
        """Disconnect without vpnmd running"""
        result = RUNNER.invoke(app.disconnect)
        self.assertIsNone(result.exception)
        self.assertEqual(
            "Is vpnm daemon running?\nCheck it with 'systemctl status vpnmd'\n",
            result.output,
        )

    def test_case08(self):
        """Status without vpnmd running"""
        result = RUNNER.invoke(app.status)
        self.assertIsNone(result.exception)
        self.assertEqual(
            "Is vpnm daemon running?\nCheck it with 'systemctl status vpnmd'\n",
            result.output,
        )

    # def test_case09(self):
    #     """Login while already logged in"""
    #     result = RUNNER.invoke(app.login)
    #     self.assertIsNone(result.exception)
    #     self.assertEqual("Logged in\n", result.output)


class TestClass02(TestCase):
    """vpnmd positive"""

    server: Process

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        server_address = ("localhost", 4000)
        server = Server(server_address)
        cls.server = Process(target=server.start)
        cls.server.start()
        # if CONFIG.exists():
        #     CONFIG.unlink()

        # RUNNER.invoke(app.login, input=CREDS_INPUT)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        cls.server.terminate()

    def test_case01(self):
        """vpnmd is running"""
        self.assertTrue(self.server.is_alive())

    def test_case02(self):
        """Connect random"""
        result = RUNNER.invoke(app.connect, args=("--random",))
        self.assertIsNone(result.exception)
        self.assertTrue(CONFIG.exists())
        self.assertIn("Connected to", result.output)

    def test_case03(self):
        """Connect manually"""
        result = RUNNER.invoke(app.connect, input=1)
        self.assertIsNone(result.exception)
        self.assertIn("Connected to", result.output)

    def test_case04(self):
        """Connect best"""
        result = RUNNER.invoke(app.connect, args=("--best"))
        self.assertIsNone(result.exception)
        self.assertIn("Connected to", result.output)

    def test_case05(self):
        """Status"""
        result = RUNNER.invoke(app.status)
        self.assertIsNone(result.exception)
        self.assertIn("Connected to", result.output)

    def test_case06(self):
        """Disconnect"""
        result = RUNNER.invoke(app.disconnect)
        self.assertIsNone(result.exception)
        self.assertEqual("Disconnected\n", result.output)

    def test_case07(self):
        """Status"""
        result = RUNNER.invoke(app.status)
        self.assertIsNone(result.exception)
        self.assertEqual("Not connected\n", result.output)

    def test_case08(self):
        """Logout"""
        result = RUNNER.invoke(app.logout)
        self.assertIsNone(result.exception)
        self.assertEqual("Logged out\n", result.output)
        self.assertFalse(Secret.get_file().exists())
