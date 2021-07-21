import pathlib
from unittest import TestCase

import install


class TestClass01(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        install.main(testing=True)

    def test_case01(self):
        """Files are downladed and present on the filesystem"""
        for link in install.LINKS:
            filepath = install.get_filepath_from_filename(
                install.get_filename_from_link(link)
            )
            testing_path = pathlib.Path(filepath)
            self.assertTrue(testing_path.exists())
