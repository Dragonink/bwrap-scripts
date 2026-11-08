import os
import random
import shlex
import string
import sys
from glob import glob
from os import PathLike
from pathlib import Path
from subprocess import Popen
from typing import Never, override

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


class DbusProxy(CmdBuilder):
    _read_fd: int
    _write_fd: int
    session_bus: Path
    system_bus: Path
    _session_args: list[str | PathLike[str]]
    _system_args: list[str | PathLike[str]]
    _popen: Popen | None = None

    def __init__(self) -> None:
        super().__init__("xdg-dbus-proxy")
        self._read_fd, self._write_fd = os.pipe()
        DBUS_PROXY_DIR = XDG_RUNTIME_DIR / ".dbus-proxy"
        os.makedirs(DBUS_PROXY_DIR, exist_ok=True)
        random_name = "".join(random.sample(string.hexdigits, 5))
        self.session_bus = DBUS_PROXY_DIR / f"{random_name}.session.bus"
        self.system_bus = DBUS_PROXY_DIR / f"{random_name}.system.bus"
        self._session_args = []
        self._system_args = []
        # Base options
        self.opt("fd", str(self._write_fd))
        self.session_args(
            os.environ["DBUS_SESSION_BUS_ADDRESS"],
            self.session_bus,
        )
        self.session_opt("log")
        self.session_opt("filter")
        self.system_args(
            "unix:path=/run/dbus/system_bus_socket",
            self.system_bus,
        )
        self.system_opt("log")
        self.system_opt("filter")

    @staticmethod
    def _opt(key: str, value: str | PathLike[str] | None = None) -> str:
        return f"--{key}" + (f"={value}" if value is not None else "")

    @override
    def opt(self, key: str, *values: str | PathLike[str]) -> None:
        assert len(values) <= 1
        self.args(self._opt(key, values[0] if len(values) > 0 else None))

    def session_args(self, *args: str | PathLike[str]) -> None:
        self._session_args += args

    def session_opt(self, key: str, value: str | PathLike[str] | None = None) -> None:
        self.session_args(self._opt(key, value))

    def system_args(self, *args: str | PathLike[str]) -> None:
        self._system_args += args

    def system_opt(self, key: str, value: str | PathLike[str] | None = None) -> None:
        self.system_args(self._opt(key, value))

    @override
    @property
    def cmd(self) -> list[str | PathLike[str]]:
        return super().cmd + self._session_args + self._system_args

    @property
    def read_fd(self) -> int:
        os.set_inheritable(self._read_fd, True)
        return self._read_fd

    def spawn(self) -> Popen:
        assert self._popen is None, "xdg-dbus-proxy has already been spawned"
        print(str(self), flush=True)
        self._popen = Popen(
            self.cmd, pass_fds=[self._write_fd], stdout=sys.stdout, stderr=sys.stderr
        )
        return self._popen

    def wait_start(self) -> None:
        assert self._popen is not None, "xdg-dbus-proxy should be spawned before"
        os.read(self._read_fd, 1)


class Bwrap(CmdBuilder):
    dbus_proxy: DbusProxy

    def __init__(self, dbus_proxy: DbusProxy) -> None:
        super().__init__("bwrap")
        self.dbus_proxy = dbus_proxy
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
        # D-Bus
        # REF: https://wiki.archlinux.org/title/Bubblewrap/Examples#Steam
        self.opt("sync-fd", str(self.dbus_proxy.read_fd))
        DBUS_SESSION_BUS_ADDRESS = XDG_RUNTIME_DIR / "bus"
        self.rw(self.dbus_proxy.session_bus, DBUS_SESSION_BUS_ADDRESS, required=True)
        self.env("DBUS_SESSION_BUS_ADDRESS", DBUS_SESSION_BUS_ADDRESS)
        self.rw(
            self.dbus_proxy.system_bus,
            "/run/dbus/system_bus_socket",
            required=True,
        )

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

    def network(self) -> None:
        self.ro("/etc/resolv.conf")

    def display(self) -> None:
        # X11
        self.rw("/tmp/.X11-unix")
        self.rw("/tmp/.ICE-unix")
        self.env("DISPLAY")
        # Wayland
        WAYLAND_DISPLAY = os.getenv("WAYLAND_DISPLAY")
        for f in glob(f"{WAYLAND_DISPLAY}*", root_dir=XDG_RUNTIME_DIR):
            self.rw(XDG_RUNTIME_DIR / f)
        self.env("WAYLAND_DISPLAY")

    def gpus(self) -> None:
        self.dev("/dev/dri")
        for d in glob("/dev/nvidia*"):
            self.dev(d)
        # Shader caches
        self.rw(XDG_CACHE_HOME / "mesa_shader_cache", create_dir=True)
        self.rw(XDG_CACHE_HOME / "radv_builtin_shaders", create_dir=True)

    def audio(self) -> None:
        # ALSA
        self.dev("/dev/snd")
        # PulseAudio
        self.rw(XDG_RUNTIME_DIR / "pulse")
        # PipeWire
        for f in glob("pipewire-*", root_dir=XDG_RUNTIME_DIR):
            self.rw(XDG_RUNTIME_DIR / f)

    def input(self) -> None:
        self.dev("/dev/input")

    @override
    def exec(self) -> Never:
        self.dbus_proxy.spawn()
        self.dbus_proxy.wait_start()
        super().exec()


def main(bwrap: Bwrap, command: list[str]) -> Never:
    bwrap.args(*command)
    bwrap.exec()
