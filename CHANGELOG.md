# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Split out of GSOOffline: `devbridge.ps1`, `decompile.ps1`, the datamining tools, and their docs and skills.
- The DevBridge is now a standalone BepInEx plugin (`gso.devtools`, off by default), so it can test any mod.
- `DEVBRIDGE.md` lists GSO HD Textures' mod commands (`hdplayer`, `hdui`, `setuiscale`, `openwindow`).
- Mod commands: a `DevCommands` class in any loaded assembly adds bridge commands without referencing this plugin.
- `render` command: camera effects and post-processing profile, lighting, fog, quality, terrain grass and particle counts. `DEVBRIDGE.md` lists GSOOffline's new `npcbounds`, `animclips`, `door`, `clearspot`, `probe` and `playerstate`, and GSO HD Textures' `frames`, `lighting`, `gfx`, `hdtex` and `hdterrain`.

### Changed
- The command file and screenshots moved to `<game>\GSODevTools\`.
- `devbridge.ps1 -ResetSaves` now deletes only the named test account and character, instead of every save.
- Builds no longer touch the game. `build.ps1` puts the plugin in `artifacts\build\<Configuration>\`, laid out like the game folder, with an `INSTALL.txt` saying where it goes; `-Deploy` (replacing the old default and `-NoDeploy`) copies it into the game. BepInEx's DLLs for compiling come from the pinned BepInEx zip, so building doesn't need BepInEx installed in the game.
