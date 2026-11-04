"""Optional branding: a display name, window icon and logo for one gym.

A brand is a folder holding brand.json ({"name": ..., "exe": ...}) and
optionally icon.ico and logo.png. It is looked up in this order:

1. a "brand" folder bundled into the exe by `build.bat <brand>`
2. a "brand" folder next to the app
3. brands/<MMA_BRAND> when the MMA_BRAND environment variable is set
"""

import io
import json
import os
import sys

from .db import app_dir


class Brand(object):
    def __init__(self, name=None, icon=None, logo=None):
        self.name = name
        self.icon = icon
        self.logo = logo


def _folders():
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        yield os.path.join(bundle, "brand")
    yield os.path.join(app_dir(), "brand")
    env = os.environ.get("MMA_BRAND")
    if env:
        yield os.path.join(app_dir(), "brands", env)


def _file(folder, name):
    path = os.path.join(folder, name)
    return path if os.path.isfile(path) else None


def load():
    for folder in _folders():
        config = _file(folder, "brand.json")
        if config:
            with io.open(config, encoding="utf-8") as f:
                data = json.load(f)
            return Brand(data.get("name"), _file(folder, "icon.ico"),
                         _file(folder, "logo.png"))
    return Brand()
