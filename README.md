# `bwrap-proton`
`bwrap` wrapper for [Proton](https://github.com/ValveSoftware/Proton) games

```sh
bwrap-proton [additional bwrap options...] <command to execute...>
```

Environment variable | Description | Set by
:-:|:--|:-:
`STEAM_COMPAT_INSTALL_PATH` | Path to the installation directory of the game | Heroic
`WINEPREFIX` | Path to the Wine prefix used by the game | Heroic
`PROTONPATH` | Path to the installation directory of Proton | Heroic
