import os
import shlex
from os import PathLike
from pathlib import Path
from typing import Never

XDG_CACHE_HOME = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
XDG_CONFIG_HOME = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
XDG_DATA_HOME = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
XDG_RUNTIME_DIR = Path(
    os.getenv("XDG_RUNTIME_DIR", Path("/run/user") / str(os.getuid()))
)


class CmdBuilder:
    _program: str | PathLike[str]
    _args: list[str | PathLike[str]]

    def __init__(self, program: str | PathLike[str]) -> None:
        self._program = program
        self._args = []

    def __repr__(self) -> str:
        return shlex.join(map(str, self.cmd))

    def args(self, *args: str | PathLike[str]) -> None:
        self._args += args

    def opt(self, key: str, *values: str | PathLike[str]) -> None:
        self.args(f"--{key}", *values)

    @property
    def cmd(self) -> list[str | PathLike[str]]:
        return [self._program, *self._args]

    def exec(self) -> Never:
        print(str(self), flush=True)
        os.execvp(self._program, self._args)


class Bwrap(CmdBuilder):
    def __init__(self) -> None:
        super().__init__("bwrap")
        # Base options
        self.opt("die-with-parent")
        self.opt("new-session")
        self.opt("clearenv")
        # Base filesystem
        self.opt("proc", "/proc")
        self.opt("tmpfs", "/tmp")
        self.opt("dev", "/dev")
        self.ro("/usr", required=True)
        self.ro("/bin", required=True)
        self.ro("/lib", required=True)
        self.ro("/lib64", required=True)
        self.dir(XDG_RUNTIME_DIR, mode=0o0700)
        # Basic environment
        self.env("PATH", "/usr/bin")
        self.env("HOME")
        self.env("XDG_CACHE_HOME")
        self.env("XDG_CONFIG_HOME")
        self.env("XDG_DATA_HOME")
        self.env("XDG_RUNTIME_DIR", XDG_RUNTIME_DIR)

    def _perms(self, mode: int) -> None:
        self.opt("perms", f"{mode:04o}")

    def dir(self, dest: str | PathLike[str] | None, mode: int | None = None) -> None:
        if dest:
            if mode is not None:
                self._perms(mode)
            self.opt("dir", dest)

    def _bind(
        self,
        opt: str,
        src: str | PathLike[str] | None,
        dest: str | PathLike[str] | None = None,
        create_dir: bool = False,
        required: bool = False,
    ) -> None:
        if dest is None:
            dest = src
        if src and dest:
            if create_dir:
                if not os.path.exists(src):
                    os.makedirs(src)
                required = True
            self.opt(opt if required else f"{opt}-try", src, dest)

    def dev(
        self,
        src: str | PathLike[str] | None,
        dest: str | PathLike[str] | None = None,
        required: bool = False,
    ) -> None:
        self._bind("dev-bind", src, dest, required=required)

    def rw(
        self,
        src: str | PathLike[str] | None,
        dest: str | PathLike[str] | None = None,
        create_dir: bool = False,
        required: bool = False,
    ) -> None:
        self._bind("bind", src, dest, create_dir, required)

    def ro(
        self,
        src: str | PathLike[str] | None,
        dest: str | PathLike[str] | None = None,
        create_dir: bool = False,
        required: bool = False,
    ) -> None:
        self._bind("ro-bind", src, dest, create_dir, required)

    def env(self, key: str, value: str | PathLike[str] | None = None) -> None:
        if value is None:
            value = os.getenv(key)
        if value:
            self.opt("setenv", key, value)


def main(bwrap: Bwrap, command: list[str]) -> Never:
    bwrap.args(*command)
    bwrap.exec()
