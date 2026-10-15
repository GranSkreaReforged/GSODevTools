# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]
### Changed
- `gen_loot.py` no longer writes the global upgrade and grade stone list: GSOOffline uses the original server's level formulas.

### Added
- `tools/datamining/gen_spawns.py`: builds GSOOffline's `Data/spawns.json`, the original server's NPC and harvestable spawns the client's scene markers lack.
- `tools/datamining/gen_droptables.py`: builds GSOOffline's `Data/droptables.json` from the original server's `Loot.xml`, with the NPC ids its `NPCInfo.xml` knew.
- `tools/datamining/gen_shops.py`: builds GSOOffline's `Data/shops.json` from the original server's `Shops.xml` (in `OldServerArchive\`, outside the repos), checking every item id against the game's item data.
- `gen_loot.py` adds the boss drops the official Steam patch notes name and the wiki's tables miss (`PATCH_NOTE_DROPS`, each row citing its update): the Storage Guard's armor set, Zalranaz's cleaver, Lydia's, Roke's and Jotnar's uniques, the Dark Tamer set from Sepitus, Nirish's venomous ring, amulet and materials, the Tomb guardian's amulet, Serpent's Fang, and the boss pets (Bear, Poacher, Infernal Hound, Young Ghit, Lizard warrior, Argus, Ent). Wiki entries win, and bosses that only have these rows keep their level-based silver.
- `DEVBRIDGE.md` lists GSOOffline's `useobj`, `windows`, `hover`, `interactprompt`, `actionanim`, `chairs`, `sitall`, `workbench`, `die`, `canmove`, `weight`, `runtest` and `updatecheck`, and GSO HD Textures' `hdupdatecheck`.
- `gen_doors.py` links the generic doors, gates, hatches and ladders players reported broken: the poacher dungeon, the Yorkhill sewers hatch, the Bir Amez crypts, the Bal Sardan town gate and Yorkhill's city gates (paired with their twin on the far side of the wall). It also gives inn doors their own room (`INNS`: the lighthouse inn, and Yorkhill's harbour inn in both scenes), instead of the first room in the interiors scene. Deepheart stays unlinked, with the reasons in a comment; its doors are missing from `markers.json`.
- `gen_doors.py` writes Yorkhill's buildings into GSOOffline's `doors.json`: which door in Yorkhill City opens which room of the Yorkhill interiors scene (from the shop signs and quest texts; doors without a sign are marked as guesses), the Hall of Heroes (scene 37), and the manor kitchen's way down to the rat cellar. `DEVBRIDGE.md` lists GSOOffline's `building` and `doorsigns`.
- `camera <yaw> <pitch> [distance] [seconds]` bridge command: places the orbit camera round the player (yaw 0 = behind, 180 = in front) or glides it there, without driving the mouse. Used by GSOMedia for repeatable shots.
- `tools/datamining/gen_loot.py`: downloads the community wiki and builds GSOOffline's monster drop tables (`Data/loot.json`) from it, since the server's own tables are lost. `DEVBRIDGE.md` lists GSOOffline's `loot`, `lootroll` and `killnpc`.
- `DEVBRIDGE.md` lists GSOOffline's `fx`, `sfx` and `projectiles`, and GSO HD Textures' `weather`, `setweather`, `settime`, `ambience`, `findnames`, `inspect`, `mattex`, `ambstatus`, `amblamps`, `ambchimneys`, `ambwindow`, `ambviewchimney` and `lightning`.
- Split out of GSOOffline: `devbridge.ps1`, `decompile.ps1`, the datamining tools, and their docs.
- The DevBridge is now a standalone BepInEx plugin (`gso.devtools`, off by default), so it can test any mod.
- `DEVBRIDGE.md` lists GSO HD Textures' mod commands (`hdplayer`, `hdui`, `setuiscale`, `openwindow`).
- Mod commands: a `DevCommands` class in any loaded assembly adds bridge commands without referencing this plugin.
- `render` command: camera effects and post-processing profile, lighting, fog, quality, terrain grass and particle counts. `DEVBRIDGE.md` lists GSOOffline's new `npcbounds`, `animclips`, `door`, `clearspot`, `probe` and `playerstate`, and GSO HD Textures' `frames`, `lighting`, `gfx`, `hdtex` and `hdterrain`.
- `DEVBRIDGE.md` lists GSOOffline's `openurl`.
- `DEVBRIDGE.md` lists GSOOffline's `invorder` and `sortinv`, and what `playerstate` now shows.

### Changed
- The command file and screenshots moved to `<game>\GSODevTools\`.
- `devbridge.ps1 -ResetSaves` now deletes only the named test account and character, instead of every save.
- Branching: work happens on `feature/<area>/<name>` branches merged into `dev`, which is merged into `main` (README, "Branches"). Risky, large or core changes, and `dev` into `main`, go through a reviewed pull request.
- Every build is a dev build, versioned like `0.1.0-dev+<branch>.<commit>` (`.dirty` with uncommitted changes) and logged at startup, so you can tell which build is in the game.
- Builds no longer touch the game. `build.ps1` puts the plugin in `artifacts\build\<Configuration>\`, laid out like the game folder, with an `INSTALL.txt` saying where it goes; `-Deploy` (replacing the old default and `-NoDeploy`) copies it into the game. BepInEx's DLLs for compiling come from the pinned BepInEx zip, so building doesn't need BepInEx installed in the game.
