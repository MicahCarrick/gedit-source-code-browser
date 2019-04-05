import sys, os

path = os.path.dirname(__file__)

if not path in sys.path:
    sys.path.insert(0, path)

import plugin
from plugin import SourceCodeBrowserPlugin


