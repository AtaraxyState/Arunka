using System;
using System.IO;
using System.Linq;
using Arunka.Scripts;
using Arunka.Scripts.StaticClassEnum;
using Avalonia.Controls;
using Avalonia.Interactivity;

namespace Arunka;

public partial class MainWindow : Window
{
    ADBConnector _adbConnector = new ();
    private OpenMainMenuADBScript _openMainMenuAdbScript;
    private RepeatBattlesADBScript _repeatBattlesAdbScript;
    private ButtonCoordsManager _buttonCoordsManager;

    // Used to prevent multiple scripts to use ADB when we make them async (to prevent blocking the rest of the app)
    private bool _repeatBattleState = false;

    private bool _connectorUsed;
    
    string _coordsJSONPath = "coords.json";
    
    public MainWindow()
    {
        InitializeComponent();
        _adbConnector.StartConnector(); // Calls your function
        _buttonCoordsManager = new ButtonCoordsManager(_adbConnector);

        _openMainMenuAdbScript = new OpenMainMenuADBScript(_adbConnector, _buttonCoordsManager);
        _repeatBattlesAdbScript = new RepeatBattlesADBScript(_adbConnector, _buttonCoordsManager);
        
        OnLoadClick(null, null);
        
        LoadImageNames();
    }
    
    private void LoadImageNames()
    {
        string folderPath = Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons/"; // change this to your folder path

        if (Directory.Exists(folderPath))
        {
            var files = Directory.GetFiles(folderPath)
                .Select(Path.GetFileName)
                .ToList();

            ImageNameDropdown.ItemsSource = files;
            if (files.Any())
                ImageNameDropdown.SelectedIndex = 0;
        }
    }

    private void RepeatButtonOnClick(object? sender, RoutedEventArgs e)
    {
        _repeatBattleState= !_repeatBattleState;

        if (_repeatBattleState)
        {
            _connectorUsed = true;
            _repeatBattlesAdbScript.StartRepeatBattles(Enums.ContentType.Custom, _buttonCoordsManager);
        }
        else
        {
            _repeatBattlesAdbScript.StopRepeatBattles();
            _connectorUsed = false;
        }
    }
    
    private void OnScreenshotClick(object? sender, RoutedEventArgs e)
    {
        _openMainMenuAdbScript.CaptureScreenshot();
    }
    
    private void WaitAndTap(object? sender, RoutedEventArgs e)
    {
        string imageName = ImageNameDropdown.SelectedItem?.ToString() ?? string.Empty;
        if (!string.IsNullOrWhiteSpace(imageName))
        {
            _openMainMenuAdbScript.TapWhenOnScreen(imageName);
        }
    }
    
    private void OnUpdateClick(object? sender, RoutedEventArgs e)
    {
        string imageName = ImageNameDropdown.SelectedItem?.ToString() ?? string.Empty;
        if (!string.IsNullOrWhiteSpace(imageName))
        {
            _buttonCoordsManager.UpdatePosition(imageName);
        }
    }

    private void OnLoadClick(object? sender, RoutedEventArgs? e)
    {
        if (File.Exists(_coordsJSONPath))
        {
            if (_connectorUsed)
            {
                // TODO error window here
                return;
            }

            _connectorUsed = true;
            _buttonCoordsManager.LoadFromFile(_coordsJSONPath);
            _connectorUsed = false;
        }
    }

    private void OnSaveClick(object? sender, RoutedEventArgs e)
    {
        if (_connectorUsed)
        {
            // TODO error window here
            return;
        }

        _connectorUsed = true;
        _buttonCoordsManager.SaveToFile(_coordsJSONPath);
        _connectorUsed = false;
    }
}