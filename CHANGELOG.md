# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Split out of GSOOffline: `devbridge.ps1`, `decompile.ps1`, the datamining tools, and their docs and skills.
- The DevBridge is now a standalone BepInEx plugin (`gso.devtools`, off by default), so it can test any mod.
- Mod commands: a `DevCommands` class in any loaded assembly adds bridge commands without referencing this plugin.

### Changed
- The command file and screenshots moved to `<game>\GSODevTools\`.
- `devbridge.ps1 -ResetSaves` now deletes only the named test account and character, instead of every save.
