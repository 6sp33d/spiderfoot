# test_sf_web_credentials.py
import io
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stdout

from sf import create_web_credentials, load_web_credentials


class TestSpiderFootWebCredentials(unittest.TestCase):
    """
    Test web interface credential handling in sf.py
    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.passwd_file = os.path.join(self.tmpdir.name, 'passwd')

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_load_web_credentials_missing_file_should_return_empty_dict(self):
        self.assertEqual(dict(), load_web_credentials(self.passwd_file))

    def test_load_web_credentials_should_return_credentials(self):
        with open(self.passwd_file, 'w') as f:
            f.write("alice:secret\n\nbob:pass:with:colons\n")

        self.assertEqual({'alice': 'secret', 'bob': 'pass:with:colons'}, load_web_credentials(self.passwd_file))

    def test_load_web_credentials_invalid_format_should_exit(self):
        with open(self.passwd_file, 'w') as f:
            f.write("no-separator\n")

        with self.assertRaises(SystemExit):
            load_web_credentials(self.passwd_file)

    def test_create_web_credentials_should_write_private_passwd_file(self):
        with redirect_stdout(io.StringIO()) as output:
            credentials = create_web_credentials(self.passwd_file)

        self.assertEqual(['admin'], list(credentials.keys()))
        password = credentials['admin']
        self.assertGreaterEqual(len(password), 20)
        self.assertIn(password, output.getvalue())

        self.assertEqual(credentials, load_web_credentials(self.passwd_file))
        self.assertEqual(0o600, stat.S_IMODE(os.stat(self.passwd_file).st_mode))

    def test_create_web_credentials_should_generate_unique_passwords(self):
        with redirect_stdout(io.StringIO()):
            first = create_web_credentials(self.passwd_file)
            second = create_web_credentials(self.passwd_file)

        self.assertNotEqual(first['admin'], second['admin'])

    def test_create_web_credentials_unwritable_location_should_exit(self):
        passwd_file = os.path.join(self.tmpdir.name, 'missing-directory', 'passwd')

        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            create_web_credentials(passwd_file)
