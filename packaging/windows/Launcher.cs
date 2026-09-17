using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

public static class Program
{
    [STAThread]
    private static void Main()
    {
        try
        {
            string root = AppRoot();
            string pythonw = Path.Combine(root, "runtime", "pythonw.exe");
            if (!File.Exists(pythonw))
            {
                MessageBox.Show(
                    "未找到运行时 runtime\\pythonw.exe。\n请重新安装 QMT Bridge。",
                    "QMT Bridge",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
                return;
            }

            var psi = new ProcessStartInfo
            {
                FileName = pythonw,
                Arguments = "-m qmt_bridge.desktop",
                WorkingDirectory = root,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            psi.EnvironmentVariables["PYTHONUTF8"] = "1";
            psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
            Process.Start(psi);
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                ex.Message,
                "QMT Bridge 启动失败",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }
    }

    private static string AppRoot()
    {
        try
        {
            string path = Process.GetCurrentProcess().MainModule.FileName;
            if (!string.IsNullOrEmpty(path))
            {
                return Path.GetDirectoryName(path);
            }
        }
        catch
        {
        }
        return AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
    }
}
