using System;
using System.IO;
using Arunka.Scripts.StaticClassEnum;

namespace Arunka.Scripts;


/// <summary>
/// Temp script for testing purpose, will be moved to <see  cref="ADBScriptBase">ADBScriptBase</see>
/// </summary>
/// <param name="adbConnector"></param>
public class OpenMainMenuADBScript(ADBConnector adbConnector, ButtonCoordsManager buttonCoordsManager) : ADBScriptBase(adbConnector, buttonCoordsManager)
{
    string targetImage = @"D:\\Documents\\Git\\ADBTesting\button_image.png"; // Path to the image of the button you want to click

    /// <summary>
    /// Use Base methods to OpenMainMenu using image recognition
    /// </summary>
    public void OpenMainMenu()
    {
        try
        {
            TapButton(Enums.Buttons.Button.MainMenu);
        }
        catch (Exception e)
        {
            // TODO implement Error window functionality to prompt those errors
            Console.WriteLine(e);
        }
    }

    /// <summary>
    /// Will wait till its finds image and tap on it
    /// Timeout is at default (5s)
    /// </summary>
    /// <param name="imageName"></param>
    public void TapWhenOnScreen(string imageName)
    {
        string targetImagePath =
            Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons/" + imageName;

        ButtonCoordsManager.ButtonCoords buttonCoords = buttonCoordsManager.GetButtonCoordsWithName(imageName);

        (int, int) coords = (buttonCoords.X, buttonCoords.Y);
        
        WaitAndTap(targetImagePath, coords);
    }
}