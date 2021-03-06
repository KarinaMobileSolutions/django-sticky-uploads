from __future__ import unicode_literals

import os
import shutil
import tempfile
import unittest

from django.conf import settings
from django.core import signing
from django.core.files import File
from django.core.files.storage import FileSystemStorage, DefaultStorage
from django.test import SimpleTestCase

from .. import utils
from .base import TempFileMixin


class SerializeTestCase(unittest.TestCase):
    """Serialize a file along with its storage."""

    def test_serialize(self):
        """Serialize mapping of file and storage."""
        storage = FileSystemStorage()
        result = utils.serialize_upload('test.png', storage, '/upload/default/')
        expected = signing.dumps({
            'name': 'test.png',
            'storage': 'django.core.files.storage.FileSystemStorage',
        }, salt='/upload/default/')
        self.assertEqual(result, expected)

    def test_lazy_storge(self):
        """Serialize lazy storage such as DefaultStorage."""
        storage = DefaultStorage()
        result = utils.serialize_upload('test.png', storage, '/upload/default/')
        expected = signing.dumps({
            'name': 'test.png',
            'storage': settings.DEFAULT_FILE_STORAGE,
        }, salt='/upload/default/')
        self.assertEqual(result, expected)


class DeserializeTestCase(SimpleTestCase):
    """Deserialize a file along with its storage class."""

    def test_deserialize(self):
        """Deserialize mapping of file and storage."""
        storage = FileSystemStorage()
        value = utils.serialize_upload('test.png', storage, '/upload/default/')
        result = utils.deserialize_upload(value, '/upload/default/')
        expected = {
            'name': 'test.png',
            'storage': FileSystemStorage,
        }
        self.assertEqual(result, expected)

    def test_bad_signature(self):
        """Attempt to restore when SECRET_KEY has changed."""
        storage = FileSystemStorage()
        value = utils.serialize_upload('test.png', storage, '/upload/default/')
        with self.settings(SECRET_KEY='1234'):
            result = utils.deserialize_upload(value, '/upload/default/')
        expected = {
            'name': None,
            'storage': None,
        }
        self.assertEqual(result, expected)

    def test_unknown_storage(self):
        """Attempt to restore storage class which is no longer importable."""
        value = signing.dumps({
            'name': 'test.png',
            'storage': 'does.not.exist',
        }, salt='/upload/default/')
        result = utils.deserialize_upload(value, '/upload/default/')
        expected = {
            'name': None,
            'storage': None,
        }
        self.assertEqual(result, expected)

    def test_incorrect_url(self):
        """Attempt to restore a serialized value generated by a different url."""
        storage = FileSystemStorage()
        value = utils.serialize_upload('test.png', storage, '/upload/default/')
        result = utils.deserialize_upload(value, '/upload/custom/')
        expected = {
            'name': None,
            'storage': None,
        }
        self.assertEqual(result, expected)


class OpenStoredFileTestCase(TempFileMixin, SimpleTestCase):
    """Deserialize and open file from a storage."""

    def test_open_file(self):
        """Restore and open file from storage."""
        with self.settings(MEDIA_ROOT=self.temp_dir):
            storage = FileSystemStorage()
            value = utils.serialize_upload(self.temp_name, storage, '/upload/default/')
            result = utils.open_stored_file(value, '/upload/default/')
            self.assertTrue(isinstance(result, File))
            self.assertEqual(result.name, os.path.basename(self.temp_name))

    def test_bad_signature(self):
        """Attempt to open file when SECRET_KEY has changed."""
        with self.settings(MEDIA_ROOT=self.temp_dir):
            storage = FileSystemStorage()
            value = utils.serialize_upload(self.temp_name, storage, '/upload/default/')
            with self.settings(SECRET_KEY='1234'):
                result = utils.open_stored_file(value, '/upload/default/')
                self.assertIsNone(result)

    def test_unknown_storage(self):
        """Attempt to open file with storage class which is no longer importable."""
        value = signing.dumps({
            'name': self.temp_name,
            'storage': 'does.not.exist',
        }, salt='/upload/default/')
        result = utils.open_stored_file(value, '/upload/default/')
        self.assertIsNone(result)

    def test_file_does_not_exist(self):
        """Restore file not found in the storage."""
        with self.settings(MEDIA_ROOT=self.temp_dir):
            storage = FileSystemStorage()
            value = utils.serialize_upload('test.png', storage, '/upload/default/')
            result = utils.open_stored_file(value, '/upload/default/')
            self.assertIsNone(result)

    def test_incorrect_url(self):
        """Attempt to open file generated by a different url."""
        with self.settings(MEDIA_ROOT=self.temp_dir):
            storage = FileSystemStorage()
            value = utils.serialize_upload(self.temp_name, storage, '/upload/default/')
            result = utils.open_stored_file(value, '/upload/custom/')
            self.assertIsNone(result)
