# `bwrap-umu`
`bwrap` wrapper for games launched with [UMU](https://github.com/Open-Wine-Components/umu-launcher)

```sh
bwrap-umu [additional bwrap options...] <command to execute...>
```

Environment variable | Description | Set by _Heroic_
:-:|:--|:-:
`STEAM_COMPAT_INSTALL_PATH` | Path to the installation directory of the game | ✅
`WINEPREFIX` | Path to the Wine prefix used by the game | ✅
`PROTONPATH` | Path to the installation directory of Proton | ✅
