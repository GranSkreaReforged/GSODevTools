using System.IO;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using UnityEngine;

namespace GSODevTools
{
    [BepInPlugin(Guid, Name, Version)]
    public class Plugin : BaseUnityPlugin
    {
        public const string Guid = "gso.devtools";
        public const string Name = "GSO DevTools";
        public const string Version = PluginInfo.Version;

        internal static ManualLogSource Log;
        internal static string WorkDir;

        private void Awake()
        {
            Log = Logger;

            var enabled = Config.Bind("General", "Enabled", false, "Run the DevBridge: execute commands written to <WorkDir>/cmd.txt. tools/devbridge.ps1 -Enable turns this on.");
            var workDir = Config.Bind("General", "WorkDir", "GSODevTools", "Folder (relative to the game folder, or absolute) holding cmd.txt and screenshots.");

            if (!enabled.Value)
            {
                Log.LogInfo($"{Name} {PluginInfo.BuildVersion} loaded (DevBridge off).");
                return;
            }

            WorkDir = Path.IsPathRooted(workDir.Value) ? workDir.Value : Path.Combine(Paths.GameRootPath, workDir.Value);
            Directory.CreateDirectory(WorkDir);

            var host = new GameObject("GSODevTools");
            DontDestroyOnLoad(host);
            host.hideFlags = HideFlags.HideAndDontSave;
            host.AddComponent<DevBridge>();

            Log.LogInfo($"{Name} {PluginInfo.BuildVersion} loaded. DevBridge on: {WorkDir}");
        }
    }
}
