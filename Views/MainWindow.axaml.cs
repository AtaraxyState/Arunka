using System;
using Arunka.Scripts;
using Avalonia.Controls;
using Avalonia.Interactivity;

namespace Arunka;

public partial class MainWindow : Window
{
    ADBConnector _adbConnector = new ();
    private OpenMainMenuADBScript _openMainMenuAdbScript;

    // Used to prevent multiple scripts to use ADB when we make them async (to prevent blocking the rest of the app)
    private bool _isCommandRunning = false;
    
    public MainWindow()
    {
        InitializeComponent();
        _adbConnector.StartConnector(); // Calls your function
        _openMainMenuAdbScript = new OpenMainMenuADBScript(_adbConnector);
    }

    private void OnButtonClick(object? sender, RoutedEventArgs e)
    {
        _isCommandRunning = true;
        _openMainMenuAdbScript.OpenMainMenu();
        _isCommandRunning = false;
    }
    
}