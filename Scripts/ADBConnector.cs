using System;
using System.Diagnostics;
using System.IO;
using OpenCvSharp;

public class ADBConnector
{
    private string _adbPath = @"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"; // BlueStacks ADB
    private string _bluestacksDevice = "127.0.0.1:5555";
    
    public string AdbPath => _adbPath;
    public string BluestacksDevice => _bluestacksDevice;
    
    

    public void StartConnector()
    {
        try
        {
            EnsureConnected();
            
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Error: {ex.Message}");
        }
    }

    void EnsureConnected()
    {
        Console.WriteLine("🔌 Connecting to BlueStacks ADB...");

        // List all connected devices/emulators
        var devicesOutput = RunAdbCommand("devices");

        // Parse the output and look for the BlueStacks device
        var devices = devicesOutput.Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);
        
        bool isBlueStacksConnected = false;
        
        foreach (var device in devices)
        {
            if (device.Contains(_bluestacksDevice)) // Check for BlueStacks device
            {
                isBlueStacksConnected = true;
                break;
            }
        }
        
        if (!isBlueStacksConnected)
        {
            // Try to explicitly connect to BlueStacks
            var output = RunAdbCommand($"connect {_bluestacksDevice}");
        
            if (!output.Contains("connected") && !output.Contains("already connected"))
            {
                throw new Exception("Could not connect to BlueStacks ADB.");
            }
        }

        Console.WriteLine("✅ Connected to BlueStacks.");
    }
   
    public string RunAdbCommand(string args, int timeoutMs = 5000)
    {
        var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = _adbPath,
                Arguments = args,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            }
        };

        process.Start();

        if (!process.WaitForExit(timeoutMs))
        {
            process.Kill();
            throw new Exception($"ADB command timed out: adb {args}");
        }

        string output = process.StandardOutput.ReadToEnd();
        string error = process.StandardError.ReadToEnd();

        if (process.ExitCode != 0)
            throw new Exception($"ADB command failed: {error}");

        return output;
    }
    
    
    /// <summary>
    /// Take screen and save at path filePath (includes file name)
    /// </summary>
    /// <param name="filePath"></param>
    /// <exception cref="Exception"></exception>
    internal void CaptureScreenshot(string filePath)
    {
        Console.WriteLine("📸 Capturing screenshot...");
        var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = _adbPath,
                Arguments = $"-s {_bluestacksDevice} exec-out screencap -p", // Use the device ID here
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            }
        };

        process.Start();

        using var fs = File.Create(filePath);
        process.StandardOutput.BaseStream.CopyTo(fs);

        process.WaitForExit();

        if (process.ExitCode != 0)
            throw new Exception("Failed to capture screenshot.");
    }
    
}
