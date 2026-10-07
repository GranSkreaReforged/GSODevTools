# GSO DevTools

Developer tooling shared by the Gran Skrea Online mods (GSO Offline Server, GSO HD Textures):

| Tool | What it's for |
|---|---|
| **DevBridge** (`src/GSODevTools`, a BepInEx plugin) + `tools/devbridge.ps1` | Drive the real game client by script: send client messages, list NPCs, teleport, take screenshots. Mods add their own commands through a `DevCommands` class. See [docs/DEVBRIDGE.md](docs/DEVBRIDGE.md). |
| `tools/decompile.ps1` | Decompile the game's scripts with dnSpyEx into `decomp/` |
| `tools/datamining/` | Extract the game's data (XML TextAssets, scene markers, scene list) with UnityPy into `extracted/`, and generate GSOOffline's door table |

Every script is listed in [docs/COMMANDS.md](docs/COMMANDS.md).

This is not for players. Nothing here is released; it lives next to the mods in the same workspace folder.

## Setup

Requirements:
- Windows, the [.NET SDK](https://dotnet.microsoft.com/download) 9.0.200 or newer, and Gran Skrea Online with BepInEx installed
- Python 3.10+ for datamining
- [dnSpyEx](https://github.com/dnSpyEx/dnSpy) for decompiling

```powershell
.\build.ps1                         # build + deploy the DevBridge plugin (off until enabled)
.\tools\devbridge.ps1 -Enable       # turn it on, with auto-login through GSO Offline Server
.\tools\devbridge.ps1 -Launch -Commands 'npcs 5' -Filter 'uid='
.\tools\devbridge.ps1 -Disable -ResetSaves
```

The game folder is found automatically in any Steam library. Override it with `-GameDir`, `GSO_GAME_DIR` or `-p:GameDir=`.

## Game content

`decomp/` and `extracted/` hold proprietary game code and data. They are git-ignored: never commit or redistribute them.

## History

Split out of GSOOffline at commit 77cc625 (2026-10-08). The earlier history of these files is in that repo.

## License

GPL-3.0-or-later (see `LICENSE`).
