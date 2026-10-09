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
- Windows, the [.NET SDK](https://dotnet.microsoft.com/download) 9.0.200 or newer, and your own copy of Gran Skrea Online (the build reads its DLLs; testing needs BepInEx in it)
- Python 3.10+ for datamining
- [dnSpyEx](https://github.com/dnSpyEx/dnSpy) for decompiling

```powershell
.\build.ps1 -Deploy                 # build the DevBridge plugin and copy it into the game (off until enabled)
.\tools\devbridge.ps1 -Enable       # turn it on, with auto-login through GSO Offline Server
.\tools\devbridge.ps1 -Launch -Commands 'npcs 5' -Filter 'uid='
.\tools\devbridge.ps1 -Disable -ResetSaves
```

The game folder is found automatically in any Steam library. Override it with `-GameDir`, `GSO_GAME_DIR` or `-p:GameDir=`.

Without `-Deploy`, `build.ps1` only reads the game. The plugin is laid out in `artifacts\build\<Configuration>\BepInEx\plugins\GSODevTools\` with an `INSTALL.txt`; copy that `BepInEx` folder into the game folder by hand if you prefer. BepInEx's own DLLs for compiling come from the pinned BepInEx zip in `.cache\`.

## Game content

`decomp/` and `extracted/` hold proprietary game code and data. They are git-ignored: never commit or redistribute them.

## Branches

| Branch | Role |
|---|---|
| `main` | Stable. Receives `dev` through a reviewed pull request. |
| `dev` | Integration. Every feature merges here. |
| `feature/<area>/<name>`, `fix/<area>/<name>` | One piece of work, branched from `dev`, e.g. `feature/devbridge/inventory-dump`. |

Branch from `dev`, work locally, then merge it back with `git merge --no-ff`, push `dev` and delete the branch. Feature branches stay local unless you want one backed up or shared. Changes that could break testing or the user's saves (`-ResetSaves`, the DevBridge dispatcher, mod command discovery), carry a security risk (downloads, running processes, deleting files, new dependencies), are large (roughly 300+ lines of code or 10+ files) or touch the build scripts go to `dev` through a pull request that the maintainer reviews and merges on GitHub. `dev` reaches `main` the same way. The branch's final commit is the pull request: first line the title, the rest the description. Merge with **Create a merge commit**.

Nothing here is released, so there is no tag or release script: every build is a dev build, versioned like `0.1.0-dev+<branch>.<commit>` and logged at startup.

## History

Split out of GSOOffline at commit 77cc625 (2026-10-08). The earlier history of these files is in that repo.

## License

GPL-3.0-or-later (see `LICENSE`).
