using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using Arunka.Scripts.StaticClassEnum;
using OpenCvSharp;
using Button = Arunka.Scripts.StaticClassEnum.Enums.Buttons.Button;

namespace Arunka.Scripts;



/// <summary>
/// Contains base implementation for ADBCommands (IE: FindAndTap, GetText, TapAt, ...)
/// </summary>
public class ADBScriptBase
{
    private string _tempScreenshotFilePath = "tempScreenShot.png";
    private string _tempRegionScreenshotFilePath = "tempRegionScreenShot.png";
    ADBConnector adbConnector;
    ButtonCoordsManager buttonCoordsManager;
    
    private (int x, int y) _lastCropOffset = (0, 0); // Class-level field
    
    /// <summary>
    /// Constructor with both ADBConnector and ButtonCoordsManager
    /// </summary>
    public ADBScriptBase(ADBConnector adbConnector, ButtonCoordsManager buttonCoordsManager)
    {
        this.adbConnector = adbConnector;
        this.buttonCoordsManager = buttonCoordsManager;
    }

    /// <summary>
    /// Constructor with only ADBConnector (ButtonCoordsManager will be null)
    /// </summary>
    public ADBScriptBase(ADBConnector adbConnector)
    {
        this.adbConnector = adbConnector;
        this.buttonCoordsManager = null; // ButtonCoordsManager is not required in this constructor
    }

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

    internal void CaptureScreenshot()
    {
        adbConnector.CaptureScreenshot(_tempScreenshotFilePath);
    }
    
    /// <summary>
    /// Will wait till its finds image and tap on it
    /// Timeout is at default (5s)
    /// </summary>
    /// <param name="imageName"></param>
    public void WaitAndTapFromPath(string imageName, bool regional, CancellationTokenSource? cancellationToken)
    {
        string targetImagePath =
            Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons/" + imageName;

        ButtonCoordsManager.ButtonCoords buttonCoords = buttonCoordsManager.GetButtonCoordsWithName(imageName);

        (int, int) coords = (buttonCoords.X, buttonCoords.Y);
        
        WaitAndTap(targetImagePath, coords, regional,cancellationToken);
    }
    
    /// <summary>
    /// Will wait till its finds image and tap on it
    /// Timeout is at default (5s)
    /// </summary>
    /// <param name="imageName"></param>
    public bool WaitAndTapFromCoords(ButtonCoordsManager.ButtonCoords buttonCoords, bool regional, CancellationTokenSource? cancellationToken)
    {
        string targetImagePath =
            Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons/" + buttonCoords.Name;
        
        (int, int) coords = (buttonCoords.X, buttonCoords.Y);
        
       return WaitAndTap(targetImagePath, coords, regional, cancellationToken);
    }
    
    internal bool WaitAndTap(string buttonImagePath, (int, int) expectedCenter, bool regional, CancellationTokenSource? cancellationToken, int timeOut = 5000)
    {
        // Start the timer
        var startTime = DateTime.Now;
        
        while (!cancellationToken?.IsCancellationRequested ?? true)
        {            
            // Find the button location
            (int, int)? buttonLocation;
            if (regional)
            {
                buttonLocation = FindButtonLocationAtRegion(expectedCenter, buttonImagePath);
            }
            else
            {
                buttonLocation = GetButtonLocation(buttonImagePath);
            }

            // If the button is found
            if (buttonLocation.HasValue)
            {
                var (x, y) = buttonLocation.Value;
                Console.WriteLine($"Found button at ({x}, {y}), tapping...");
                Thread.Sleep(GlobalVariables.ClickCooldown); // Wait 200ms before checking again
                TapAt(x, y);  // Tap at the location
                return true;   // Successfully clicked the button
            }

            // Check if we've timed out
            if ((DateTime.Now - startTime).TotalMilliseconds > timeOut)
            {
                Console.WriteLine("Timeout reached, button not found.");
                return false;  // Timeout reached, return false
            }

            // Optional: Add a small delay to avoid overwhelming the system with requests
            Thread.Sleep(GlobalVariables.SearchLoopCooldown / 5); // Wait 200ms before checking again
        }

        return false;
    }
    
    
    internal void CaptureScreenshotAtRegion((int, int) centerCoordinates, string imagePath)
    {
        // Load the button template to get its size
        var buttonTemplate = Cv2.ImRead(imagePath);

        if (buttonTemplate.Empty())
        {
            Console.WriteLine("Error: Failed to load button template image.");
            return;
        }

        // Prevent invalid search area fraction
        // if (searchAreaFraction < 1)
        // {
        //     Console.WriteLine("Error: searchAreaFraction must be >= 1.");
        //     return;
        // }

        int imageWidth = buttonTemplate.Width;
        int imageHeight = buttonTemplate.Height;
        
        // Console.WriteLine($"Image {imagePath} width: {imageWidth}, image height: {imageHeight}");

        CapturePartialScreenshot(centerCoordinates, imageWidth, imageHeight);
    }


    
    internal void CapturePartialScreenshot((int x, int y) center, int width, int height)
    {
        // Capture the full screenshot
        adbConnector.CaptureScreenshot(_tempRegionScreenshotFilePath);

        // Load the screenshot
        var screenMat = Cv2.ImRead(_tempRegionScreenshotFilePath);
        if (screenMat.Empty())
        {
            Console.WriteLine("Error: Failed to load the screenshot.");
            return;
        }

        // Calculate cropping bounds
        int startX = Math.Max(0, center.x - width / 2);
        int startY = Math.Max(0, center.y - height / 2);
        int endX = Math.Min(screenMat.Width, startX + width);
        int endY = Math.Min(screenMat.Height, startY + height);

        width = endX - startX;
        height = endY - startY;

        if (width <= 1 || height <= 1)
        {
            Console.WriteLine("Error: Cropped region too small or invalid.");
            return;
        }

        // Crop and save
        var roi = new Rect(startX, startY, width, height);
        
        // Console.WriteLine($"Captured screenshot area ({roi.ToString()})");
        
        var croppedScreen = new Mat(screenMat, roi);
        Cv2.ImWrite(_tempRegionScreenshotFilePath, croppedScreen);
        
        _lastCropOffset = (startX, startY);
    }
    
    /// <summary>
    /// Will search if image is center position using image size
    /// </summary>
    /// <param name="center"></param>
    /// <param name="buttonImagePath"></param>
    /// <returns></returns>
    internal (int, int)? FindButtonLocationAtRegion((int, int) center, string buttonImagePath)
    {
        CaptureScreenshotAtRegion(center, buttonImagePath);

        // Load the screenshot and the button image
        var screenMat = Cv2.ImRead(_tempRegionScreenshotFilePath);
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
            // Offset match coordinates to full screen
            int offsetX = _lastCropOffset.x;
            int offsetY = _lastCropOffset.y;

            int fullX = maxLoc.X + buttonTemplate.Width / 2 + offsetX;
            int fullY = maxLoc.Y + buttonTemplate.Height / 2 + offsetY;

            return (fullX, fullY);
        }

        // Not found
        return null;
    }

    /// <summary>
    /// Tap center of image if found, throws NullRefException if no button found
    /// </summary>
    internal void TapButton(Button button, string customPath = "")
    {
        // Console.WriteLine("🔍 Checking connected devices...");
        // var devicesOutput = RunAdbCommand("devices");
        // Console.WriteLine(devicesOutput); // Log the connected devices after the screenshot and before the tap command
        
        adbConnector.CaptureScreenshot(_tempScreenshotFilePath);

        string path = customPath;
        if (button != Button.Custom)
        {
            path = Enums.Buttons.GetButton(button);
        }
        
        (int,int)? buttonLocation = FindButtonLocation(_tempScreenshotFilePath, path);
        if (buttonLocation != null)
        {
            // Scale the coordinates based on the screen resolution
            Console.WriteLine($"📍 Tapping at coordinates ({buttonLocation.Value.Item1}, {buttonLocation.Value.Item2})...");
            TapAt(buttonLocation.Value.Item1, buttonLocation.Value.Item2);
        }
        else
        {
            Console.WriteLine("❌ Button not found.");
            throw new NullReferenceException($"Button {path} not found.");
        }
    }

    internal bool SearchImage(string filePath)
    {
        adbConnector.CaptureScreenshot(_tempScreenshotFilePath);
        
        (int,int)? buttonLocation = FindButtonLocation(_tempScreenshotFilePath, filePath);
        if (buttonLocation != null)
        {
            // Scale the coordinates based on the screen resolution
            Console.WriteLine($"📍 SearchImage | Button found at ({buttonLocation.Value.Item1}, {buttonLocation.Value.Item2})...");
            return true;
        }
        else
        {
            Console.WriteLine("❌ SearchImage | Button not found.");
            return false;
        }
    }
    
    /// <summary>
    /// Capture and return center of the corresponding image on the screen
    /// </summary>
    /// <param name="screenshotPath">Full screen shot</param>
    /// <param name="buttonImagePath">Image to search</param>
    /// <returns></returns>
    internal (int, int)? GetButtonLocation(string buttonImagePath)
    {
        // Capture screen
        adbConnector.CaptureScreenshot(_tempScreenshotFilePath);
        
        // return middle of button
        return FindButtonLocation(_tempScreenshotFilePath, buttonImagePath);
    }
    
    /// <summary>
    /// Will return center of the corresponding image on the screen
    /// </summary>
    /// <param name="screenshotPath">Full screen shot</param>
    /// <param name="buttonImagePath">Image to search</param>
    /// <returns></returns>
    internal (int, int)? FindButtonLocation(string screenshotPath, string buttonImagePath)
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
            return (maxLoc.X + buttonTemplate.Width / 2, maxLoc.Y + buttonTemplate.Height / 2);
        }

        // Not found
        return null;
    }
    
    
    /// <summary>
    /// Dont use test code not working
    /// </summary>
    /// <param name="coordinates"></param>
    /// <returns></returns>
    internal (int, int) ScaleCoordinates((int x, int y) coordinates)
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