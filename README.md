# Sony Reader App for Calibre's Annotations plugin
This script extends the ["Annotations" plugin](https://www.mobileread.com/forums/showthread.php?p=2853161) of the [Calibre](https://calibre-ebook.com/) ebook manager. It enables the plugin to fetch annotations and notes made on a Sony Reader and add them to Calibre.


## Setup
1. Install the ["Annotations" plugin](https://www.mobileread.com/forums/showthread.php?p=2853161) in your Calibre software.
2. Download the python scripts from this repository to your computer.
3. Edit the "Annotations" plugin's config file (in Ubuntu it is located at `~/.config/calibre/plugins/annotations.json`) and add the file location of this script to `"additional_readers": [ ... ]`.

## Compatibility and tests
The reader uses direct dictionary iteration, compatible with both Python 2 and
Python 3. Regression tests run on Python 3 and use in-memory SQLite databases
with stand-ins for the Annotations plugin API; no connected reader is needed.

Run from the repository directory:

```sh
python3 -B -m unittest discover -s tests -v
```

To test with calibre's bundled Python on macOS:

```sh
PYTHONDONTWRITEBYTECODE=1 /Applications/calibre.app/Contents/MacOS/calibre-debug -e tests/test_sony_reader.py
```

These tests cover book metadata, Unicode annotations, timestamp ordering, page
locations, duplicate note suppression, and an empty annotation database. A full
import through calibre with a connected Sony Reader still requires manual testing.
