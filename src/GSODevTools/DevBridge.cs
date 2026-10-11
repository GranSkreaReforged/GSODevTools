using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEngine;

namespace GSODevTools
{
    /// <summary>
    /// Developer automation: lines written to &lt;WorkDir&gt;/cmd.txt are executed in-game and results go
    /// to the BepInEx log with a "[dev]" prefix. Lets features be exercised end-to-end through the
    /// real client without driving its UI.
    ///
    ///   client &lt;Scr_RPCSender method&gt; [args...]   call as if the UI had (ints/floats/bools/strings auto-parsed; "$me" = player name)
    ///   creationdone                               press "Done" in the character creator
    ///   inv                                        dump the client's inventory and equipment
    ///   npcs [n]                                   nearest n client-side NPCs (uid, type, name, distance)
    ///   harvestables [n]                           nearest n harvestables
    ///   shot &lt;name&gt;                                 screenshot to &lt;WorkDir&gt;/&lt;name&gt;.png
    ///   goto x y z                                 move the local player (client side only)
    ///   near &lt;uid&gt;                                 step next to a visible NPC or harvestable
    ///   camera &lt;yaw&gt; &lt;pitch&gt; [dist] [seconds]       place the camera round the player (yaw 0 = behind, 180 = in front), or glide there
    ///   anything else                              a mod's DevCommands method (see ModCommands)
    /// </summary>
    internal class DevBridge : MonoBehaviour
    {
        private string path;
        private float poll;

        private void Start()
        {
            path = Path.Combine(Plugin.WorkDir, "cmd.txt");
            Plugin.Log.LogInfo("[dev] watching " + path);
        }

        private void Update()
        {
            poll -= Time.unscaledDeltaTime;
            if (poll > 0f) return;
            poll = 0.5f;
            if (!File.Exists(path)) return;

            string[] lines;
            try
            {
                lines = File.ReadAllLines(path);
                File.Delete(path);
            }
            catch (IOException)
            {
                return;   // writer still has it open; retry next poll
            }
            foreach (string line in lines)
            {
                if (line.Trim().Length == 0) continue;
                Plugin.Log.LogInfo("[dev] > " + line);
                try
                {
                    Run(line.Trim().Split(' '));
                }
                catch (Exception e)
                {
                    Plugin.Log.LogError("[dev] " + e);
                }
            }
        }

        private static Scr_Player Player => Scr_PlayerHandler.instance != null ? Scr_PlayerHandler.instance.player : null;

        private void Run(string[] a)
        {
            switch (a[0])
            {
                case "client": CallSender(a); break;
                case "inv": DumpInventory(); break;
                case "creationdone":
                    // What the creator's "Done" button does, minus the GUI.
                    Scr_CharacterCreation.instance.active = false;
                    Scr_RPCSender.instance.doneWithCharacterCreation();
                    break;
                case "npcs": DumpNpcs(a.Length > 1 ? int.Parse(a[1]) : 10); break;
                case "harvestables": DumpHarvestables(a.Length > 1 ? int.Parse(a[1]) : 10); break;
                case "near": GoNear(int.Parse(a[1])); break;
                case "shot": Screenshot(a.Length > 1 ? a[1] : "shot"); break;
                case "render": DumpRender(); break;
                case "camera": SetCamera(a); break;
                case "goto":
                    Player.transform.position = new Vector3(F(a[1]), F(a[2]), F(a[3]));
                    break;
                default: ModCommands.Run(a); break;
            }
        }

        private static readonly FieldInfo CamYaw = typeof(CameraController).GetField("x", BindingFlags.Instance | BindingFlags.NonPublic);
        private static readonly FieldInfo CamPitch = typeof(CameraController).GetField("y", BindingFlags.Instance | BindingFlags.NonPublic);
        private Coroutine cameraGlide;
        private const float CameraTilt = 45f;   // CameraController.FixedUpdate: localRotation = Euler(45, 180, 0)

        /// <summary>
        /// camera &lt;yaw&gt; &lt;pitch&gt; [distance] [seconds]: the orbit camera's angles, set directly instead of by
        /// right-dragging. yaw is degrees round the player from straight behind (180 = facing them, 90 = their
        /// right), pitch how far it looks down in degrees (-55..85, negative looks up: the camera sits flipped and
        /// tilted 45 degrees on its orbit, whose angle the client limits to -40..100), distance in metres. With
        /// seconds, it glides there
        /// (eased, the short way round) for steady pans in recordings.
        /// </summary>
        private void SetCamera(string[] a)
        {
            var cc = CameraController.instance;
            if (cc == null || cc.target == null || CamYaw == null || CamPitch == null)
            {
                Plugin.Log.LogWarning("[dev] camera: no orbit camera (or its x/y fields moved)");
                return;
            }
            float yaw = cc.target.eulerAngles.y + 180f + F(a[1]);
            float orbitY = Mathf.Clamp(a.Length > 2 ? CameraTilt - F(a[2]) : (float)CamPitch.GetValue(cc), -40f, 100f);
            float dist = a.Length > 3 ? F(a[3]) : cc.desiredDistance;
            float seconds = a.Length > 4 ? F(a[4]) : 0f;
            if (cameraGlide != null) StopCoroutine(cameraGlide);
            if (seconds <= 0f)
            {
                CamYaw.SetValue(cc, yaw);
                CamPitch.SetValue(cc, orbitY);
                cc.desiredDistance = cc.currentDistance = dist;
            }
            else
            {
                cameraGlide = StartCoroutine(GlideCamera(cc, yaw, orbitY, dist, seconds));
            }
            Plugin.Log.LogInfo($"[dev] camera yaw {yaw:F0} (player {cc.target.eulerAngles.y:F0}) pitch {CameraTilt - orbitY:F0} distance {dist:F1}{(seconds > 0 ? $" over {seconds:F1}s" : "")}");
        }

        private static IEnumerator GlideCamera(CameraController cc, float yaw, float pitch, float dist, float seconds)
        {
            float x0 = (float)CamYaw.GetValue(cc), y0 = (float)CamPitch.GetValue(cc), d0 = cc.desiredDistance;
            float dx = Mathf.DeltaAngle(x0, yaw);
            for (float t = 0f; t < seconds; t += Time.deltaTime)
            {
                float k = Mathf.SmoothStep(0f, 1f, t / seconds);
                CamYaw.SetValue(cc, x0 + dx * k);
                CamPitch.SetValue(cc, Mathf.Lerp(y0, pitch, k));
                cc.desiredDistance = Mathf.Lerp(d0, dist, k);
                yield return null;
            }
            CamYaw.SetValue(cc, x0 + dx);
            CamPitch.SetValue(cc, pitch);
            cc.desiredDistance = dist;
        }

        // What decides how the scene looks: camera effects, lights, ambient, fog, quality, grass and particles.
        private static void DumpRender()
        {
            var log = Plugin.Log;
            foreach (var cam in Camera.allCameras)
            {
                log.LogInfo($"[dev] camera '{cam.name}' depth={cam.depth} far={cam.farClipPlane} hdr={cam.allowHDR} path={cam.actualRenderingPath}");
                foreach (var c in cam.GetComponents<Component>())
                    log.LogInfo("[dev]   " + c.GetType().FullName + (c is Behaviour b ? (b.enabled ? " (on)" : " (off)") : ""));
                foreach (var c in cam.GetComponents<MonoBehaviour>())
                {
                    // Post-processing stack v1: profile.<effect>.enabled
                    var pf = c.GetType().GetField("profile");
                    var profile = pf != null ? pf.GetValue(c) as UnityEngine.Object : null;
                    if (profile == null) continue;
                    var parts = new System.Collections.Generic.List<string>();
                    foreach (var f in profile.GetType().GetFields())
                    {
                        var model = f.GetValue(profile);
                        var en = model != null ? model.GetType().GetProperty("enabled") : null;
                        if (en != null) parts.Add(f.Name + "=" + en.GetValue(model, null));
                    }
                    log.LogInfo($"[dev]   profile '{profile.name}': " + string.Join(", ", parts.ToArray()));
                }
            }
            log.LogInfo($"[dev] colorSpace={QualitySettings.activeColorSpace} quality={QualitySettings.names[QualitySettings.GetQualityLevel()]} pixelLights={QualitySettings.pixelLightCount} shadows={QualitySettings.shadows} shadowDist={QualitySettings.shadowDistance} aa={QualitySettings.antiAliasing} softParticles={QualitySettings.softParticles} texLimit={QualitySettings.masterTextureLimit}");
            log.LogInfo($"[dev] ambient mode={RenderSettings.ambientMode} sky={RenderSettings.ambientSkyColor} equator={RenderSettings.ambientEquatorColor} ground={RenderSettings.ambientGroundColor} intensity={RenderSettings.ambientIntensity} reflections={RenderSettings.reflectionIntensity} skybox={(RenderSettings.skybox != null ? RenderSettings.skybox.name + "/" + RenderSettings.skybox.shader.name : "none")} sun={(RenderSettings.sun != null ? RenderSettings.sun.name : "none")}");
            log.LogInfo($"[dev] fog={RenderSettings.fog} mode={RenderSettings.fogMode} color={RenderSettings.fogColor} density={RenderSettings.fogDensity} start={RenderSettings.fogStartDistance} end={RenderSettings.fogEndDistance}");
            foreach (var l in UnityEngine.Object.FindObjectsOfType<Light>())
                if (l.type == LightType.Directional)
                    log.LogInfo($"[dev] light '{l.name}' enabled={l.enabled} intensity={l.intensity} color={l.color} shadows={l.shadows} rot={l.transform.eulerAngles}");
            foreach (var t in Terrain.activeTerrains)
                log.LogInfo($"[dev] terrain '{t.name}' drawDetails={t.drawTreesAndFoliage} detailDist={t.detailObjectDistance} detailDensity={t.detailObjectDensity} treeDist={t.treeDistance} detailPrototypes={t.terrainData.detailPrototypes.Length} material={(t.materialTemplate != null ? t.materialTemplate.shader.name : t.materialType.ToString())}");
            var ps = Type.GetType("UnityEngine.ParticleSystem, UnityEngine.ParticleSystemModule");
            if (ps != null)
            {
                var all = UnityEngine.Object.FindObjectsOfType(ps);
                int playing = 0;
                foreach (var o in all) if ((bool)ps.GetProperty("isPlaying").GetValue(o, null)) playing++;
                log.LogInfo($"[dev] particle systems: {all.Length} active objects, {playing} playing");
            }
            var opt = Scr_Options.instance;
            if (opt != null)
                log.LogInfo($"[dev] options AO={opt.useAmbientOcclusion} AA={opt.useAntiAliasing} VL={opt.useVolumetricLighting} MB={opt.useMotionBlur} texQuality={opt.textureQuality} detailDist={opt.terrainDetailDistance} detailDensity={opt.terrainDetailDensity} lootParticles={!opt.disableLootParticles}");
        }

        private static float F(string s) => float.Parse(s, CultureInfo.InvariantCulture);

        private static object ParseArg(string s, Type t)
        {
            if (s == "$me") s = Player != null ? Player.playerName : string.Empty;
            if (t == typeof(int)) return int.Parse(s, CultureInfo.InvariantCulture);
            if (t == typeof(float)) return F(s);
            if (t == typeof(bool)) return bool.Parse(s);
            if (t == typeof(string)) return s.Replace('_', ' ');
            if (t == typeof(Vector3))
            {
                var p = s.Split(',');
                return new Vector3(F(p[0]), F(p[1]), F(p[2]));
            }
            throw new ArgumentException("Unsupported parameter type " + t);
        }

        private static void CallSender(string[] a)
        {
            int argc = a.Length - 2;
            var method = typeof(Scr_RPCSender).GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .FirstOrDefault(m => m.Name == a[1] && m.GetParameters().Length == argc);
            if (method == null)
            {
                Plugin.Log.LogWarning($"[dev] no Scr_RPCSender.{a[1]} with {argc} args");
                return;
            }
            var ps = method.GetParameters();
            var args = new object[argc];
            for (int i = 0; i < argc; i++) args[i] = ParseArg(a[i + 2], ps[i].ParameterType);
            method.Invoke(Scr_RPCSender.instance, args);
        }

        private static void DumpInventory()
        {
            var sb = new StringBuilder("[dev] inventory:");
            foreach (var s in Inventory.instance.items)
                sb.Append($"\n  id={s.item.itemID} type={s.item.itemTypeID} '{s.item.itemName}' x{s.amount} slot={s.item.itemSlot} equipped={s.item.currentlyEquipped} hp+{s.item.itemStatHealth}");
            foreach (var e in Inventory.instance.equipSlots)
                if (e.item != null) sb.Append($"\n  [{e.slot}] {e.item.itemName}");
            var p = Player;
            if (p != null) sb.Append($"\n  silver={p.silver} hp={p.currentHealth}/{p.maximumHealth}");
            Plugin.Log.LogInfo(sb.ToString());
        }

        private static void DumpNpcs(int n)
        {
            var p = Player;
            if (p == null) return;
            var sb = new StringBuilder("[dev] npcs:");
            foreach (var npc in Scr_NpcHandler.instance.npcList.Where(x => x != null)
                         .OrderBy(x => Vector3.Distance(x.transform.position, p.transform.position)).Take(n))
                sb.Append($"\n  uid={npc.npcUniqueId} type={npc.npcTypeId} '{npc.npcName}' d={Vector3.Distance(npc.transform.position, p.transform.position):F1} hp={npc.currentHealth}/{npc.maxHealth} interact={npc.canInteract}");
            Plugin.Log.LogInfo(sb.ToString());
        }

        private static void DumpHarvestables(int n)
        {
            var p = Player;
            if (p == null) return;
            var sb = new StringBuilder("[dev] harvestables:");
            foreach (var h in Scr_HarvestableHandler.instance.harvestablesList.Where(x => x != null)
                         .OrderBy(x => Vector3.Distance(x.transform.position, p.transform.position)).Take(n))
                sb.Append($"\n  uid={h.uniqueId} type={h.typeId} '{h.harvestableName}' d={Vector3.Distance(h.transform.position, p.transform.position):F1} hp={h.currentHealth}");
            Plugin.Log.LogInfo(sb.ToString());
        }

        private static void GoNear(int uid)
        {
            Transform t = null;
            var h = Scr_HarvestableHandler.instance.harvestablesList.FirstOrDefault(x => x != null && x.uniqueId == uid);
            if (h != null) t = h.transform;
            var n = Scr_NpcHandler.instance.npcList.FirstOrDefault(x => x != null && x.npcUniqueId == uid);
            if (n != null) t = n.transform;
            if (t == null)
            {
                Plugin.Log.LogWarning("[dev] nothing visible with uid " + uid);
                return;
            }
            var dir = (Player.transform.position - t.position);
            dir.y = 0f;
            Player.transform.position = t.position + (dir.sqrMagnitude > 0.01f ? dir.normalized : Vector3.forward) * 1.5f + Vector3.up * 0.5f;
        }

        private static void Screenshot(string name)
        {
            string file = Path.Combine(Plugin.WorkDir, name + ".png");
            ScreenCapture.CaptureScreenshot(file);
            Plugin.Log.LogInfo("[dev] screenshot -> " + file);
        }
    }
}
