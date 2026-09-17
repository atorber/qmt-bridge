using System;
using System.Diagnostics;
using System.IO;
using System.Text;

/// <summary>
/// 控制台 CLI：转发参数到 runtime\python.exe -m qmt_bridge.server.cli
/// </summary>
public static class Program
{
    private static int Main(string[] args)
    {
        try
        {
            string root = AppRoot();
            string python = Path.Combine(root, "runtime", "python.exe");
            if (!File.Exists(python))
            {
                Console.Error.WriteLine("未找到运行时 runtime\\python.exe。请重新安装 QMT Bridge。");
                return 1;
            }

            var psi = new ProcessStartInfo
            {
                FileName = python,
                Arguments = BuildArgs(args),
                WorkingDirectory = root,
                UseShellExecute = false,
                // 继承当前控制台，便于查看日志 / Ctrl+C
            };
            psi.EnvironmentVariables["PYTHONUTF8"] = "1";
            psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";

            using (var proc = Process.Start(psi))
            {
                if (proc == null)
                {
                    Console.Error.WriteLine("无法启动 python 进程。");
                    return 1;
                }
                proc.WaitForExit();
                return proc.ExitCode;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("qmt-server 启动失败: " + ex.Message);
            return 1;
        }
    }

    private static string BuildArgs(string[] args)
    {
        var sb = new StringBuilder();
        sb.Append("-m qmt_bridge.server.cli");
        if (args == null || args.Length == 0)
        {
            return sb.ToString();
        }
        foreach (var arg in args)
        {
            sb.Append(' ');
            sb.Append(QuoteArg(arg));
        }
        return sb.ToString();
    }

    private static string QuoteArg(string arg)
    {
        if (string.IsNullOrEmpty(arg))
        {
            return "\"\"";
        }
        bool needQuote = false;
        for (int i = 0; i < arg.Length; i++)
        {
            char c = arg[i];
            if (c == ' ' || c == '\t' || c == '"' || c == '\n' || c == '\r')
            {
                needQuote = true;
                break;
            }
        }
        if (!needQuote)
        {
            return arg;
        }
        var sb = new StringBuilder();
        sb.Append('"');
        for (int i = 0; i < arg.Length; i++)
        {
            if (arg[i] == '"')
            {
                sb.Append('\\');
            }
            sb.Append(arg[i]);
        }
        sb.Append('"');
        return sb.ToString();
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
