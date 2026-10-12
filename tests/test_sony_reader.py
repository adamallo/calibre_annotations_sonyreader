"""Regression tests using SQLite fixtures without a connected reader or calibre UI."""

import contextlib
import datetime
import importlib.util
import io
from pathlib import Path
import sqlite3
import sys
import time
import types
import unittest
from unittest.mock import Mock, patch


def load_reader():
    support = types.ModuleType('calibre_plugins.annotations.reader_app_support')
    support.USBReader = object
    common = types.ModuleType('calibre_plugins.annotations.common_utils')
    common.AnnotationStruct = types.SimpleNamespace
    common.BookStruct = types.SimpleNamespace
    modules = {support.__name__: support, common.__name__: common}
    path = Path(__file__).resolve().parents[1] / 'AnnotationsFeching_SonyReader.py'
    spec = importlib.util.spec_from_file_location('sony_reader_under_test', path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module.SonyReaderApp


class SonyReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader_class = load_reader()

    def setUp(self):
        self.reader = self.reader_class()
        self.reader.app_name_ = 'SONY'
        self.reader.opts = types.SimpleNamespace(pb=Mock(), device_name='Test reader')
        for name in ('_log', 'create_books_table', 'create_annotations_table',
                     'add_to_books_db', 'add_to_annotations_db',
                     'update_book_last_annotation', 'update_timestamp', 'commit'):
            setattr(self.reader, name, Mock())
        self.reader.generate_books_db_name = Mock(return_value='books')
        self.reader.generate_annotations_db_name = Mock(return_value='annotations')
        self.conn = sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.execute('CREATE TABLE books (_id INTEGER, author TEXT, title TEXT)')
        self.conn.execute('CREATE TABLE annotation '
                          '(_id INTEGER, content_id INTEGER, added_date INTEGER, '
                          'marked_text TEXT, name TEXT, page INTEGER)')
        self.reader._get_db = Mock(return_value=self.conn)

    def fetch(self, method):
        with contextlib.redirect_stdout(io.StringIO()):
            getattr(self.reader, method)()

    def test_books_preserve_unicode_metadata_and_ids(self):
        self.conn.executemany('INSERT INTO books VALUES (?, ?, ?)', [
            (7, 'José Saramago', 'Ensaio sobre a cegueira'),
            (2, '夏目漱石', 'こころ'),
        ])
        self.fetch('get_installed_books')
        books = {call.args[1].book_id: call.args[1]
                 for call in self.reader.add_to_books_db.call_args_list}
        self.assertEqual(set(self.reader.installed_books), {2, 7})
        self.assertEqual(books[7].author, 'José Saramago')
        self.assertEqual(books[2].title, 'こころ')
        self.assertEqual(books[2].title_sort, 'こころ')
        self.assertTrue(books[7].active)
        self.reader.opts.pb.set_maximum.assert_called_once_with(2)
        self.reader.commit.assert_called_once_with()

    def test_annotations_are_sorted_and_preserve_text_and_locations(self):
        # Insert out of chronological order; include a fractional second.
        self.conn.executemany('INSERT INTO annotation VALUES (?, ?, ?, ?, ?, ?)', [
            (10, 7, 1600000010250, 'Café — 日本語', 'A separate note', 12),
            (11, 2, 1600000000500, 'Same text', 'Same text', 3),
        ])
        self.fetch('get_active_annotations')
        annotations = [call.args[1]
                       for call in self.reader.add_to_annotations_db.call_args_list]
        self.assertEqual([ann.book_id for ann in annotations], [2, 7])
        self.assertEqual([ann.location for ann in annotations], ['p. 3', 'p. 12'])
        self.assertEqual(annotations[0].note_text, '')
        self.assertEqual(annotations[1].highlight_text, 'Café — 日本語')
        self.assertEqual(annotations[1].note_text, 'A separate note')
        expected = time.mktime(datetime.datetime.fromtimestamp(1600000000.5).timetuple())
        self.assertEqual(annotations[0].last_modification, expected)
        self.assertLess(annotations[0].last_modification, annotations[1].last_modification)
        self.assertEqual(self.reader.update_book_last_annotation.call_count, 2)
        self.assertEqual(self.reader.opts.pb.increment.call_count, 2)
        self.reader.update_timestamp.assert_called_once_with('annotations')
        self.reader.commit.assert_called_once_with()

    def test_empty_annotation_database(self):
        self.fetch('get_active_annotations')
        self.reader.add_to_annotations_db.assert_not_called()
        self.reader.opts.pb.set_maximum.assert_called_once_with(0)
        self.reader.commit.assert_called_once_with()


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SonyReaderTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
