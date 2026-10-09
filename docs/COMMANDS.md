# Command reference

Every script in GSODevTools. Run them from the repo root, in PowerShell. Each one finds the game automatically (Steam libraries); `-GameDir` overrides that.

## build.ps1

Builds the DevBridge plugin into `artifacts\build\<Configuration>\` (laid out like the game folder, with an `INSTALL.txt`). It only reads the game; copying into it is opt-in.

| Parameter | Default | Meaning |
|---|---|---|
| `-Configuration Debug\|Release` | Debug | Build configuration |
| `-GameDir <path>` | auto | Game folder to compile against (remembered in `GameDir.user.props`) |
| `-Deploy` | off | Copy the built files into `<game>\BepInEx\plugins\GSODevTools`. Close the game first. |
| `-InstallBepInEx` | off | Put the pinned BepInEx 5.4.23.5 (hash-checked) and `steam_appid.txt` into the game |
| `-Clean` | off | `dotnet clean` and empty `artifacts\build\<Configuration>` first |

## tools/devbridge.ps1

Drives the real client for testing. See [DEVBRIDGE.md](DEVBRIDGE.md).

| Parameter | Default | Meaning |
|---|---|---|
| `-Enable` | | Turn the bridge on and set GSOOffline's AutoLogin/AutoCharacter |
| `-Account <name>` / `-Character <name>` | Tester / Testguy | The test account (used by `-Enable` and `-ResetSaves`) |
| `-Disable` | | Kill the game and revert those settings |
| `-ResetSaves` | | Kill the game and delete only that account's and character's saves, plus `<game>\GSODevTools\` |
| `-Launch` | | Kill the game, delete the old log, start the game, and wait (up to 120 s) for the world to load |
| `-Commands <lines>` | | Bridge commands to send, one at a time |
| `-Wait <seconds>` | 2 | Pause after each command |
| `-Filter <regex>` | | Only print matching log lines |

## tools/decompile.ps1

| Parameter | Meaning |
|---|---|
| `-DnSpyConsole <path>` | dnSpyEx console. Defaults to `<game>\GSO_Data\Managed\dnSpy.Console.exe` or one on PATH. |

Writes `decomp\` (git-ignored; never commit it).

## tools/datamining

| Command | Meaning |
|---|---|
| `.\tools\datamining\extract.ps1 [-GameDir]` | Creates the venv (UnityPy) and writes `extracted\textassets\*.txt`, `extracted\markers.json` and `extracted\scenes.txt` |
| `tools\datamining\.venv\Scripts\python.exe -I tools\datamining\gen_doors.py extracted\markers.json ..\GSOOffline\src\GSOOffline\Data\doors.json` | Regenerate GSOOffline's door table |
| `python -I tools\datamining\gen_loot.py fetch extracted\wiki\pages.json` | Download every page of the Gran Skrea Online community wiki (wikitext, through its MediaWiki API) into `extracted\wiki\` |
| `python -I tools\datamining\gen_loot.py build extracted\wiki\pages.json extracted\textassets ..\GSOOffline\src\GSOOffline\Data\loot.json` | Regenerate GSOOffline's monster drop tables from the wiki's "Drops" and "Drop sources" tables, matched to the game's item and NPC names. Prints names it couldn't match (fix them in `ALIASES`/`SKIP`). |
| `dump_text.py`, `dump_markers.py`, `scenes.py`, `count_dummies.py` | Building blocks used by extract.ps1, runnable on their own (see each file's docstring/argv) |

## DevBridge commands (written to `<game>\GSODevTools\cmd.txt`)

| Command | Meaning |
|---|---|
| `client <Scr_RPCSender method> [args]` | Call a client send method as the UI would. `$me` = player name; `_` in strings becomes a space. |
| `creationdone` | Press Done in the character creator |
| `inv` | Dump inventory, equipment, silver and HP |
| `npcs [n]` / `harvestables [n]` | List the nearest NPCs or nodes, with uids |
| `near <uid>` | Step next to an NPC or node |
| `goto x y z` | Move the player (client side) |
| `shot <name>` | Screenshot to `<game>\GSODevTools\<name>.png` |
| `checkrecipes` | (GSOOffline mod command) Verify server recipe ids against the client's |

## Plugin settings (`<game>\BepInEx\config\gso.devtools.cfg`)

| Section.Key | Default | Meaning |
|---|---|---|
| General.Enabled | false | Run the DevBridge |
| General.WorkDir | `GSODevTools` | Folder for `cmd.txt` and screenshots (relative to the game folder, or absolute) |
