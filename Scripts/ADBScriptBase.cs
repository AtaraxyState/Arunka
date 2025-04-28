using System;
using System.Diagnostics;
using System.IO;
using OpenCvSharp;

namespace Arunka.Scripts;

/// <summary>
/// Contains base implementation for ADBCommands (IE: FindAndTap, GetText, TapAt, ...)
/// </summary>
public class ADBScriptBase(ADBConnector adbConnector)
{
    private string _tempScreenshotFilePath = "tempScreenShot.png";

    /// <summary>
    /// Tap at screen coords
    /// </summary>
    internal void TapAt(int x, int y)
    {
        // Explicitly specify the device with -s
        var command = $" -s {adbConnector.BluestacksDevice} shell input tap {x} {y}";
        adbConnector.RunAdbCommand(command);
        Console.WriteLine($"✅ Tap simulated at ({x}, {y})");
    }

    
    /// <summary>
    /// Tap center of image if found, throws NullRefException if no button found
    /// </summary>
    internal void TapButton(string inputFilePath)
    {
        // Console.WriteLine("🔍 Checking connected devices...");
        // var devicesOutput = RunAdbCommand("devices");
        // Console.WriteLine(devicesOutput); // Log the connected devices after the screenshot and before the tap command
        
        adbConnector.CaptureScreenshot(_tempScreenshotFilePath);
        
        (int,int)? buttonLocation = FindButtonLocation(_tempScreenshotFilePath, inputFilePath);
        if (buttonLocation != null)
        {
            // Scale the coordinates based on the screen resolution
            Console.WriteLine($"📍 Tapping at coordinates ({buttonLocation.Value.Item1}, {buttonLocation.Value.Item2})...");
            TapAt(buttonLocation.Value.Item1, buttonLocation.Value.Item2);
        }
        else
        {
            Console.WriteLine("❌ Button not found.");
            throw new NullReferenceException($"Button {inputFilePath} not found.");
        }
    }
    
    private (int, int)? FindButtonLocation(string screenshotPath, string buttonImagePath)
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
    
    
    /// <summary>
    /// Dont use test code not working
    /// </summary>
    /// <param name="coordinates"></param>
    /// <returns></returns>
    (int, int) ScaleCoordinates((int x, int y) coordinates)
    {
        // Get screen resolution via ADB command
        string resolutionOutput = adbConnector.RunAdbCommand($" -s {adbConnector.BluestacksDevice} shell wm size");
        var resolutionParts = resolutionOutput.Split(':')[1].Trim().Split('x');
        int screenWidth = int.Parse(resolutionParts[0]);
        int screenHeight = int.Parse(resolutionParts[1]);

        // Scale the coordinates based on screen resolution
        int scaledX = (int)(coordinates.x * (screenWidth / 1080.0));  // Assuming 1080p base resolution
        int scaledY = (int)(coordinates.y * (screenHeight / 1920.0)); // Assuming 1920p base resolution

        return (scaledX, scaledY);
    }
}