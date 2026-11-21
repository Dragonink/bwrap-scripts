import os

from common import *


def steam_fixes(bwrap: Bwrap) -> None:
    match int(os.getenv("SteamAppId", "0")):
        case 2198150:  # Tiny Glade
            bwrap.rw(XDG_DATA_HOME / "Tiny Glade")
        case _:
            pass
