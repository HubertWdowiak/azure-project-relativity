from unittest import TestCase
from unittest.mock import patch, Mock

from setup import create_app, get_db_connection


class Test(TestCase):

    @patch("setup.Flask")
    def test_create_app(self, flask_mock: Mock):
        create_app()
        flask_mock.assert_called_once()

    @patch("setup.create_engine")
    def test_get_db_connection(self, create_engine_mock: Mock):
        get_db_connection()
        create_engine_mock.assert_called_once()
