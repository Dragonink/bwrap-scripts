import os

from common import *


def steam_fixes(bwrap: Bwrap) -> None:
    match int(os.getenv("SteamAppId", "0")):
        case _:
            pass
