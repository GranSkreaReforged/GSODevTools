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
| `camera <yaw> <pitch> [distance] [seconds]` | Places the orbit camera without the mouse: `yaw` in degrees round the player from straight behind (180 = facing them, 90 = their right), `pitch` how far it looks down (-55..85, negative looks up; 10-20 is an over-the-shoulder view), `distance` in metres. With `seconds` it glides there (eased, the short way round), for steady pans in recordings. |
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
| `heap` | GSOHDTextures | The managed heap (`GC.GetTotalMemory`). Unity's Mono profiler sizes and Mono's process memory read 0 in the shipped game, so measure process memory from outside (`Get-Process GSO`). |
| `frames [seconds]` | GSOHDTextures | Frame times over that many seconds (default 10): average, percentiles, the worst hitches, the plugin's share, garbage collections and allocation rate. Use it to measure stutter. |
| `lighting` | GSOHDTextures | Time-of-day sky, ambient, sun, shadow, bloom, grading and AO values. |
| `hdtex on\|off` | GSOHDTextures | Shows the original textures or the HD ones in the same session, for comparisons. |
| `hdterrain` | GSOHDTextures | Each terrain layer's colour and normal texture (name, size, format), tiling, metallic and smoothness. |
| `weather` | GSOHDTextures | The game's weather controller (time, speed, cloudiness, temperature, wind, fogginess), rain particles and audio, render fog, the weather pattern and its grading mood. |
| `setweather <clear\|partlycloudy\|overcast\|rain\|fog> [now]` / `setweather auto` | GSOHDTextures | Holds a weather (blended in, or at once with `now`), or goes back to the schedule. |
| `settime <0-2400>` | GSOHDTextures | Sets the time of day (1830 = 18:30). |
| `ambience [radius]` | GSOHDTextures | The lights and particle systems within *radius* (default 150 m), and objects named like light sources (torch, lantern, window, chimney...). |
| `findnames <word>` | GSOHDTextures | Objects, meshes and materials whose names contain the word, with each material's shader and emission support. |
| `inspect <root name>` | GSOHDTextures | That object as a tree with components and positions; also particle shader availability, terrain trees and water surfaces. |
| `mattex <material>` | GSOHDTextures | The textures on every loaded material of that name. |
| `ambstatus` | GSOHDTextures | What the ambience module added in this scene, and live particle counts. |
| `amblamps [n]` / `ambchimneys [n]` | GSOHDTextures | The nearest lit lamps, detected chimneys and leaf trees. |
| `ambwindow` / `ambviewchimney` | GSOHDTextures | Moves the player in front of the nearest lit windows or chimney, along the camera, for a screenshot. |
| `lightning` | GSOHDTextures | A lightning strike now: bolt, flash and thunder. |
| `gfx on\|off` | GSOHDTextures | Switches enhanced lighting (like F10), for before/after screenshots. |
| `checkrecipes` | GSOOffline | Compares the server's crafting recipe ids with the client's `Script_Crafting` list. All 341 should match. |
| `npcbounds [n]` | GSOOffline | The nearest *n* NPCs with rendered size, feet height above the ground and the animation playing. Finds giant, sunken or frozen NPCs. |
| `animclips` | GSOOffline | The client's animation clip table, by id. |
| `door [n]` | GSOOffline | Lists the door table, or goes through door *n* as a click would. Loop over all of them to check every arrival. |
| `building [n]` | GSOOffline | Lists the buildings (Yorkhill's shops and houses), or goes into building *n* as clicking its door would. Click a door inside (`client attemptObjectInteract $me 37`) to come back out. |
| `doorsigns` | GSOOffline | Every shop sign (`Prefab_Object_Sign_*`) in the scene with its three nearest doors and gates. |
| `hover <npc uid>` / `hover obj <typeId>` / `hover off` | GSOOffline | Acts as if the mouse cursor were over that NPC or the nearest object of that type, for the Interact key (F). |
| `interactprompt [press]` | GSOOffline | What F would use now, with the NPCs and objects within 8 m; `press` uses it as F would (with nothing in reach, it does nothing). |
| `animhandlers` | GSOOffline | The client's animation handlers (`EasyAnimationHandler`), which one is current and its animator. Every NPC's animations come from the current one; a destroyed one breaks them. |
| `useobj <typeId>` | GSOOffline | Uses the nearest object of that type as a mouse click does. |
| `updatecheck <version>` / `hdupdatecheck <version>` | GSOOffline / GSOHDTextures | Reruns the GitHub update check as if that version were installed, e.g. `1.0.0` to see the "NEW UPDATE AVAILABLE" overlay. |
| `weight` | GSOOffline | Carried weight against capacity as the server and the client count it, and the player's run speeds (forward, back, sideways). |
| `runtest [seconds]` | GSOOffline | Autoruns forward (default 1 s) and logs the distance and speed against the maximum. Start somewhere open: walls stop it. |
| `die` | GSOOffline | Kills the player as a fatal hit would; they wake at their home wayshrine after the respawn delay (5 s). |
| `canmove` | GSOOffline | Whether the client lets the player move (`dead`, `canControl`) and their position. |
| `workbench` | GSOOffline | The crafting window the client shows (`0` = none) and whether a craft is in progress. |
| `chairs [n]` | GSOOffline | The nearest *n* seats (chair interactables, type 54): the bench or room they belong to, distance, seat point. |
| `sitall [from]` | GSOOffline | Sits on every seat in the scene in turn as a click does and logs `FAIL` for any where the sit doesn't hold; also checks that stepping off stands you up. About 3 s per seat. |
| `bountyreset` / `bountyhere <style 0-4> <level>` / `outlaws` | GSOOffline | A fresh bounty board; an outlaw 8 m away (0 swordsman, 1 two-hander, 2 archer, 3 crossbowman, 4 fire mage); each outlaw's position and whether a player-sized body there overlaps anything. |
| `fakeplayer spawn\|move dx dz\|attack id\|hit n\|die\|anim json\|myanim\|gone` | GSOOffline | A client-side other player driven straight through the client's receivers; `myanim` logs your own animation packet as a template. |
| `houses` | GSOOffline | The house objects the client holds: id (plot), type, size, name, position, door and furniture count. |
| `devbank` | GSOOffline | Opens the bank window as a banker does. |
| `windows` | GSOOffline | The client's open windows by type (2 inventory, 7 shop, 14 bank...). |
| `actionanim <id>` | GSOOffline | Sets the player's animator ActionID (12 = sit, 15 = sit on the ground, 0 = stop). Id 8 (lay dying and die) only ends once the player moves. |
| `clearspot x y z` | GSOOffline | The door arrival search at a point, with the reason each candidate was rejected. |
| `playerstate` | GSOOffline | The client's attack state for the player (`attacking`, `anim.combat`, animation id), action animation, weapon in hand and on the back. |
| `invorder` | GSOOffline | Server vs client inventory and bank, row by row (order, client id, amount). Swaps and drags are index based, so the orders must match. |
| `sortinv` | GSOOffline | Sorts the inventory as the window's "By name" button does. |
| `loot` | GSOOffline | The loot bags the server holds in this scene, and the live bags the client shows. |
| `lootroll <npcType> [n]` | GSOOffline | Rolls that NPC type's drop table *n* times (default 1000) and logs the totals. |
| `lootage <seconds>` | GSOOffline | Ages every loot bag on the ground by that much playing time; bags go at 0 (they last 1200 s). `loot` lists them with the time left. |
| `bountypress <name start>` | GSOOffline | Presses the wanted board's button on that outlaw's line: starts the hunt, or (twice) abandons it. |
| `huntage <seconds>` | GSOOffline | Takes that much playing time off every active bounty's hour (3600 s); at 0 the outlaw gets away. |
| `bufficons [max]` | GSOOffline | Which buff icons exist in the client's resources (`Tex_BuffIcon_<id>`), up to *max* (200). |
| `showbuff <id...>` | GSOOffline | Puts those buffs' icons on the buff bar for a minute, to look at them. |
| `gearfx <grade>` | GSOOffline | Shows that grade's sparkles (4-8) on everything the player wears; `gearfx 0` goes back to the real grades. |
| `gearfxinfo` | GSOOffline | The gear sparkle emitters: how many live, where (from the player), box size, and a few sparkles' size and colour. |
| `gfxprobe` | GSOOffline | Which particle shaders the build has, the particle materials in the scene, and what the worn models are made of. |
| `killnpc <uid>` | GSOOffline | Kills a visible NPC as the player would: XP, loot bag, quest triggers. |
| `devhealth <n>` | GSOOffline | Sets the test character's base health (it's saved, so only on throwaway characters), e.g. to stand in front of bosses. |
| `blowlog on\|off` | GSOOffline | Logs every creature blow aimed at the player: `[blow] <name> (<type>) swings/shoots from <m>` and `... hits you for <n>`. Shows which creatures attack and how hard. |
| `spawnedobjects [from] [to]` | GSOOffline | What each spawned-object prefab (`ab_spawnedObject_N`) contains: objects, renderers and materials, and scripts. Identifies the numbered props without spawning them. |
| `npcparts <uid>` / `npcpart <uid> <child> on\|off` | GSOOffline | A client NPC's model parts (renderers, materials, lights), and showing or hiding one by name (`_` for spaces), e.g. to find an aura that's part of a model. |
| `flyers` | GSOOffline | The client's flying followers (parrot, bats): prefab type, owner, distance from the player and each renderer, to check one is on the shoulder. |
| `combatstats` | GSOOffline | Combat level (server and client), armor alignment and its multipliers, the per-hit damage cap, and base vs effective resistances. |
| `fx <id>` / `sfx <id>` | GSOOffline | Plays an effect (the game's "_GFX IDs" list) 3 m in front of the player, or a sound at the player. |
| `projectiles` | GSOOffline | The client's projectiles in flight (id, position, speed, model). Arrived projectiles linger invisibly for 5 s before the client deletes them. |
| `openurl <url>` | GSOOffline | Calls `Application.OpenURL` as a menu link would. The log shows `Opened <url> through the shell.` when the link was sent through `explorer.exe`, outside the game's process tree. |
| `probe x y z` | GSOOffline | Colliders on a vertical line through a point and within 4 m of it. |
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
