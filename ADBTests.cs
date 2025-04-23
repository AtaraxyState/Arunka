using System;
using System.Diagnostics;
using System.IO;
using OpenCvSharp;

class ADBTests
{
    string adbPath = @"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"; // BlueStacks ADB
    string bluestacksDevice = "127.0.0.1:5555";
    string screenshotFile = "screenshot.png";
    string targetImage = @"D:\\Documents\\Git\\ADBTesting\button_image.png"; // Path to the image of the button you want to click

    public void Main()
    {
        try
        {
            EnsureConnected();
            
            // Console.WriteLine("🔍 Checking connected devices...");
            // var devicesOutput = RunAdbCommand("devices");
            // Console.WriteLine(devicesOutput); // Log the connected devices after the screenshot and before the tap command
            
            CaptureScreenshot();
            
            Console.WriteLine($"Screenshot saved to {screenshotFile}");
            
            (int,int)? buttonLocation = FindButtonLocation(screenshotFile, targetImage);
            if (buttonLocation != null)
            {
                // Scale the coordinates based on the screen resolution
                Console.WriteLine($"📍 Tapping at coordinates ({buttonLocation.Value.Item1}, {buttonLocation.Value.Item2})...");
                TapAt(buttonLocation.Value.Item1, buttonLocation.Value.Item2);
            }
            else
            {
                Console.WriteLine("❌ Button not found.");
            }
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
            if (device.Contains(bluestacksDevice)) // Check for BlueStacks device
            {
                isBlueStacksConnected = true;
                break;
            }
        }
        
        if (!isBlueStacksConnected)
        {
            // Try to explicitly connect to BlueStacks
            var output = RunAdbCommand($"connect {bluestacksDevice}");
        
            if (!output.Contains("connected") && !output.Contains("already connected"))
            {
                throw new Exception("Could not connect to BlueStacks ADB.");
            }
        }

        Console.WriteLine("✅ Connected to BlueStacks.");
    }


    
    void CaptureScreenshot()
    {
        Console.WriteLine("📸 Capturing screenshot...");
        var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = adbPath,
                Arguments = $"-s {bluestacksDevice} exec-out screencap -p", // Use the device ID here
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            }
        };

        process.Start();

        using var fs = File.Create(screenshotFile);
        process.StandardOutput.BaseStream.CopyTo(fs);

        process.WaitForExit();

        if (process.ExitCode != 0)
            throw new Exception("Failed to capture screenshot.");
    }

    static (int, int)? FindButtonLocation(string screenshotPath, string buttonImagePath)
    {
        // Load the screenshot and the button image
        var screenMat = Cv2.ImRead(screenshotPath);
        var buttonTemplate = Cv2.ImRead(buttonImagePath);

        // Convert both to grayscale
        Cv2.CvtColor(screenMat, screenMat, ColorConversionCodes.BGR2GRAY);
        Cv2.CvtColor(buttonTemplate, buttonTemplate, ColorConversionCodes.BGR2GRAY);

        // Optional: Add light blur to reduce noise (optional but recommended for stability)
        Cv2.GaussianBlur(screenMat, screenMat, new Size(3, 3), 0);
        Cv2.GaussianBlur(buttonTemplate, buttonTemplate, new Size(3, 3), 0);

        // Perform template matching
        var result = new Mat();
        Cv2.MatchTemplate(screenMat, buttonTemplate, result, TemplateMatchModes.CCoeffNormed);

        // Find the best match location and value
        Cv2.MinMaxLoc(result, out _, out double maxVal, out _, out Point maxLoc);

        Console.WriteLine($"🔍 Match confidence: {maxVal}");

        // Only accept high-confidence matches
        if (maxVal >= 0.9)
        {
            return (maxLoc.X, maxLoc.Y);
        }

        // Not found
        return null;
    }


    (int, int) ScaleCoordinates((int x, int y) coordinates)
    {
        // Get screen resolution via ADB command
        string resolutionOutput = RunAdbCommand($" -s {bluestacksDevice} shell wm size");
        var resolutionParts = resolutionOutput.Split(':')[1].Trim().Split('x');
        int screenWidth = int.Parse(resolutionParts[0]);
        int screenHeight = int.Parse(resolutionParts[1]);

        // Scale the coordinates based on screen resolution
        int scaledX = (int)(coordinates.x * (screenWidth / 1080.0));  // Assuming 1080p base resolution
        int scaledY = (int)(coordinates.y * (screenHeight / 1920.0)); // Assuming 1920p base resolution

        return (scaledX, scaledY);
    }

    void TapAt(int x, int y)
    {
        // Explicitly specify the device with -s
        var command = $" -s {bluestacksDevice} shell input tap {x} {y}";
        RunAdbCommand(command);
        Console.WriteLine($"✅ Tap simulated at ({x}, {y})");
    }

    string RunAdbCommand(string args, int timeoutMs = 5000)
    {
        var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = adbPath,
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



}
