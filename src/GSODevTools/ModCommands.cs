using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;

namespace GSODevTools
{
    /// <summary>
    /// Lets each mod add bridge commands without referencing this plugin: any loaded class named
    /// <c>DevCommands</c> (any namespace, may be internal) with a static <c>void Name(string[] args)</c>
    /// method handles the command "name" (case-insensitive). <c>args[0]</c> is the command itself.
    /// </summary>
    internal static class ModCommands
    {
        private static Dictionary<string, MethodInfo> commands;

        public static void Run(string[] a)
        {
            if (commands == null) Discover();
            if (commands.TryGetValue(a[0].ToLowerInvariant(), out var method))
                method.Invoke(null, new object[] { a });
            else
                Plugin.Log.LogWarning("[dev] unknown command " + a[0]);
        }

        private static void Discover()
        {
            commands = new Dictionary<string, MethodInfo>();
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type[] types;
                try { types = asm.GetTypes(); }
                catch (ReflectionTypeLoadException e) { types = e.Types.Where(t => t != null).ToArray(); }

                foreach (var type in types.Where(t => t.Name == "DevCommands"))
                {
                    foreach (var m in type.GetMethods(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic))
                    {
                        var ps = m.GetParameters();
                        if (ps.Length != 1 || ps[0].ParameterType != typeof(string[])) continue;
                        commands[m.Name.ToLowerInvariant()] = m;
                        Plugin.Log.LogInfo($"[dev] mod command '{m.Name.ToLowerInvariant()}' from {type.FullName}");
                    }
                }
            }
        }
    }
}
