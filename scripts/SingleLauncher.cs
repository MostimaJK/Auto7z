// Verified, versioned extraction. Never edits user configuration or output.
using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading;
using System.Windows.Forms;
[assembly: AssemblyTitle("Auto7z Single")]
[assembly: AssemblyVersion("__VERSION__.0")]
internal static class SingleLauncher {
    const string PayloadHash = "__PAYLOAD_SHA__";
    static readonly Dictionary<string, string> Files = new Dictionary<string, string> { __FILES__ };
    static string Digest(Stream stream) { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant(); }
    static bool Valid(string folder) {
        foreach (var file in Files) {
            string path = Path.Combine(folder, file.Key.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(path)) return false;
            using (var stream = File.OpenRead(path)) if (Digest(stream) != file.Value) return false;
        }
        return true;
    }
    [STAThread] static int Main(string[] args) {
        string stage = null;
        try {
            string parent = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Auto7z", "Runtime");
            Directory.CreateDirectory(parent);
            string cache = Path.Combine(parent, "__VERSION__-" + PayloadHash.Substring(0, 16));
            using (var mutex = new Mutex(false, @"Local\Auto7z-" + PayloadHash)) {
                bool locked = false;
                try {
                    try { locked = mutex.WaitOne(TimeSpan.FromSeconds(60)); } catch (AbandonedMutexException) { locked = true; }
                    if (!locked) throw new IOException("另一個 Auto7z 正在準備執行檔，請稍後再試。");
                    if (!Valid(cache) && Directory.Exists(cache)) {
                        // Reuse a verified repair on later launches; preserve the invalid original.
                        string repair = cache + "-repair";
                        cache = Valid(repair) || !Directory.Exists(repair) ? repair : repair + "-" + Guid.NewGuid().ToString("N");
                    }
                    if (!Valid(cache)) {
                        stage = cache + ".staging-" + Guid.NewGuid().ToString("N");
                        Directory.CreateDirectory(stage);
                        using (var payload = Assembly.GetExecutingAssembly().GetManifestResourceStream("Payload.zip")) {
                            if (Digest(payload) != PayloadHash) throw new IOException("內嵌檔案校驗失敗，請重新下載。");
                            payload.Position = 0;
                            using (var zip = new ZipArchive(payload, ZipArchiveMode.Read)) {
                                foreach (var entry in zip.Entries) {
                                    string target = Path.GetFullPath(Path.Combine(stage, entry.FullName));
                                    if (!target.StartsWith(Path.GetFullPath(stage) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new IOException("拒絕不安全的壓縮路徑。");
                                    if (entry.Name.Length == 0) { Directory.CreateDirectory(target); continue; }
                                    Directory.CreateDirectory(Path.GetDirectoryName(target)); entry.ExtractToFile(target, false);
                                }
                            }
                        }
                        if (!Valid(stage)) throw new IOException("執行檔校驗失敗，請重新下載。");
                        Directory.Move(stage, cache); stage = null;
                    }
                    if (args.Length == 1 && args[0] == "--verify") return 0;
                    string application = Path.Combine(cache, "Auto7z", "Auto7z.exe");
                    Process.Start(new ProcessStartInfo(application) { WorkingDirectory = Path.GetDirectoryName(application), UseShellExecute = false });
                } finally { if (locked) mutex.ReleaseMutex(); }
            }
            return 0;
        } catch (Exception error) {
            if (!(args.Length == 1 && args[0] == "--verify")) MessageBox.Show(error.Message, "Auto7z 啟動失敗", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        } finally {
            if (stage != null && Directory.Exists(stage)) {
                string parent = Path.GetFullPath(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Auto7z", "Runtime")) + Path.DirectorySeparatorChar;
                if (Path.GetFullPath(stage).StartsWith(parent, StringComparison.OrdinalIgnoreCase) && Path.GetFileName(stage).Contains(".staging-")) {
                    try { Directory.Delete(stage, true); } catch { }
                }
            }
        }
    }
}
