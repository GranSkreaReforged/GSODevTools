# DevBridge: testing through the real client

The DevBridge is a small BepInEx plugin built from this repo (`src/GSODevTools`). When it is enabled, it checks `<game>\GSODevTools\cmd.txt` twice a second, runs each line in-game, and then deletes the file. Results go to `BepInEx/LogOutput.log` with a `[dev]` prefix.

It lets you exercise mod features end to end, through the real client code paths, without clicking through the UI. That is how GSO Offline Server and GSO HD Textures are verified.

It is **off by default** (`General.Enabled = false` in `BepInEx/config/gso.devtools.cfg`) and does nothing in normal play.

## Setup

```powershell
.\build.ps1 -Deploy                                                  # deploy GSODevTools.dll (game closed)
.\tools\devbridge.ps1 -Enable -Account Tester -Character Testguy     # bridge on + auto-login

# ...test...

.\tools\devbridge.ps1 -Disable -ResetSaves -Account Tester -Character Testguy
```

Getting into the world needs **GSO Offline Server** (the official servers are gone). `-Enable` changes:

| Setting | Effect |
|---|---|
| `gso.devtools.cfg` `General.Enabled` | Turns the bridge on. |
| `gso.offline.server.cfg` `Convenience.AutoLogin` | Logs in automatically with this account name. |
| `gso.offline.server.cfg` `Convenience.AutoCharacter` | Enters the world with this character, creating it if needed. A new character stops at the character creator (see `creationdone`). |

`-Disable` reverts all three. `-ResetSaves` deletes only `OfflineSaves\accounts\<Account>.json`, `OfflineSaves\characters\<Character>.json` and `<game>\GSODevTools\`. Pass the same `-Account`/`-Character` you enabled with. It never touches other saves, because real players' characters live in the same folders.

## Sending commands

```powershell
# Fresh start: kill the game, delete the old log, launch, wait for the world to load.
.\tools\devbridge.ps1 -Launch -Commands 'npcs 5' -Filter 'uid='

# Send to an already-running game. -Wait is the pause after each command, in seconds.
.\tools\devbridge.ps1 -Commands 'client interactNpc 10018 $me', 'client sendDialogueOptionChoise $me 1' -Wait 1.5 -Filter 'dialogue'
```

The script prints the log lines produced since it started; `-Filter` is a regex applied to them. Use single quotes so PowerShell leaves `$me` alone.

You can also write lines to `<game>\GSODevTools\cmd.txt` by hand. Several lines per file are fine.

## Command reference

| Command | What it does |
|---|---|
| `client <method> [args...]` | Calls the public `Scr_RPCSender.<method>` with that many arguments, exactly as the game UI would. Arguments are parsed to the parameter types (int, float, bool, string, `Vector3` as `x,y,z`). `$me` is replaced with the player's name, and `_` in strings becomes a space (`/give_193` → `/give 193`). |
| `creationdone` | Presses "Done" in the character creator. Pick the class first with `client updateFightingStyleAndProfession <style> <profession>`. |
| `inv` | Dumps the client's inventory (id, type, name, amount, slot, equipped), equipment slots, silver and HP. |
| `npcs [n]` | Lists the nearest *n* client-side NPCs: uid, type, name, distance, HP, whether they can be interacted with. |
| `harvestables [n]` | Lists the nearest *n* harvestable nodes. |
| `near <uid>` | Moves the player next to a visible NPC or harvestable. |
| `goto x y z` | Moves the player on the client side only. The server learns the new position from the next sync. For server-side moves use `client sendChatMessage $me /tele_x_y_z` or `/scene_id_x_y_z`. |
| `shot <name>` | Saves a screenshot to `<game>\GSODevTools\<name>.png`. Read it back to check what the player would see. |
| `render` | How the scene is drawn: camera components and the post-processing profile's effects, quality settings, ambient light, fog, directional lights, terrain grass settings, particle counts and the game's graphics options. |
| *anything else* | A mod command (below). |

### Mod commands

Any loaded assembly can add commands, without referencing this plugin. Declare a class named `DevCommands` (any namespace, internal is fine) with static methods taking `string[]`:

```csharp
internal static class DevCommands
{
    private static void CheckRecipes(string[] args) { ... }   // command "checkrecipes"; args[0] is the command
}
```

They are discovered on first use, the name is matched case-insensitively, and each discovery is logged (`[dev] mod command 'x' from Y`). Current mod commands:

| Command | Mod | What it does |
|---|---|---|
| `checkrecipes` | GSOOffline | Compares the server's crafting recipe ids with the client's `Script_Crafting` list. All 341 should match. |
| `npcbounds [n]` | GSOOffline | The nearest *n* NPCs with rendered size, feet height above the ground and the animation playing. Finds giant, sunken or frozen NPCs. |
| `animclips` | GSOOffline | The client's animation clip table, by id. |
| `hdplayer` | GSOHDTextures | Each local-player material's texture properties: `HD WxH for <key>` or `<key> (original)`. |
| `hdui` | GSOHDTextures | Screen size, the game's UI options (`useLUI`, `scaleGUI`, ...) and every root canvas with how it scales. |
| `setuiscale <x>` | GSOHDTextures | Sets `UI.Scale` (saved to the user's cfg, so reset it afterwards) and logs the resulting factor. |
| `openwindow <type> [tab] [scrollY]` | GSOHDTextures | Opens a classic window via `Script_WindowController.OpenWindowType` (2 = inventory, 3 = skills, 18 = main menu). For the main menu, `tab` picks the page (1 = Video options) and `scrollY` scrolls it (`openwindow 18 1 330` shows Interface scale). |

## Useful `client` calls

These are the message layouts most often needed. GSOOffline's `docs/PROTOCOL.md` has the full list.

| Goal | Command |
|---|---|
| Talk to an NPC | `client interactNpc <uid> $me` |
| Pick a dialogue option | `client sendDialogueOptionChoise $me <optionId>` (the log line `[dialogue] node N options [..]` shows which ids are visible) |
| Interact with an object/door | `client attemptObjectInteract $me <interactable typeId>` (the nearest one of that type is used) |
| Harvest a node | `client startAction $me 1 <harvestable uid>` |
| Craft a recipe | `client startAction $me 2 <recipe id>` |
| Target and attack | `client selectNpcTarget $me <uid>`, then `client useAbility $me 0` |
| Put an ability on the bar | `client setAbilityToSlot $me <slot> <abilityId>`, then `client useAbility $me <slot>` |
| Shop | `client buyItemFromNPCShop <typeId> <amount> $me`, `client sellItemToNPCShop <typeId> <itemId> <amount> $me` |
| Bank | `client addBankItem <itemId> <typeId> <amount>`, `client removeBankItem ...`, `client addBankSilver <±amount>` |
| Chat / server commands | `client sendChatMessage $me /help`; also `/pos`, `/give_<id>_<n>`, `/quest_<id>_<phase>`, `/scene_<id>`, `/wayshrine_<id>`, `/silver_<n>`, `/save` |

## Log lines worth filtering on

| Prefix | Source |
|---|---|
| `[dev]` | Bridge command echoes and dumps |
| `[dialogue] node N options [...]` | GSOOffline: each dialogue node shown |
| `Quest Q -> phase P` | GSOOffline: quest progress |
| `[skill] ...` | GSOOffline: harvest and craft starts, refusals and cancellations |
| `[notice] ...` | GSOOffline: every message the server shows the player (errors included) |
| `Unhandled client event X/Y` | GSOOffline: client messages the server does not implement yet; this is the to-do list |
| `Client failed handling event` | GSOOffline: the server sent something the client choked on |
| `Replaced <key> -> WxH` | GSOHDTextures (with `Debug.LogReplacements`) |

## Pitfalls

- **Stale logs.** BepInEx only truncates `LogOutput.log` once the new game is running. `-Launch` deletes the log first; a hand-rolled wait loop must do the same, or it will match the previous run.
- **DLLs are locked while the game runs.** Close the game before any `build.ps1 -Deploy` (`-Launch` and `-Disable` kill it).
- **A plain `build.ps1` doesn't change the game.** Every repo's build writes only to its own `artifacts\build\`; a mod you changed needs `build.ps1 -Deploy` in its repo before you test it.
- **New characters need `creationdone`**, otherwise they can't move.
- **Uids are per scene.** NPC uid = scene × 10000 + index; harvestable uid = 5,000,000 + scene × 10000 + index. They are stable between runs of the same scene, so a uid seen in `npcs` can be reused.
- **`npcs` right after spawning can be empty.** NPCs stream in by distance; wait or move first.
- **`near` can wedge you into scenery.** The server's range checks are deliberately loose (20 m for harvesting) because node transforms sit a few metres off their markers.
- **Clean up afterwards.** Run `-Disable -ResetSaves` with the same names, so the next normal launch doesn't auto-login as the test account.
