# `bwrap-umu`
`bwrap` wrapper for games launched with [UMU](https://github.com/Open-Wine-Components/umu-launcher)

```sh
bwrap-umu [additional bwrap options...] <command to execute...>
```

Environment variable | Description | Set by _Heroic_ | Set by _Faugus_
:-:|:--|:-:|:-:
`STEAM_COMPAT_INSTALL_PATH` | Path to the installation directory of the game | ✅ | ⚠️
`WINEPREFIX` | Path to the Wine prefix used by the game | ✅ | ✅
`PROTONPATH` | Path to the installation directory of Proton | ✅ | ✅

> [!WARNING]
> If you use _Faugus Launcher_
> and the installation directory of your game is outside the `WINEPREFIX`,
> then you need to manually set `STEAM_COMPAT_INSTALL_PATH`.
