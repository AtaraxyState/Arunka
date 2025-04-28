using System;
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

    // Used to prevent multiple scripts to use ADB when we make them async (to prevent blocking the rest of the app)
    private bool _repeatBattleState = false;

    private bool _connectorUsed;
    
    public MainWindow()
    {
        InitializeComponent();
        _adbConnector.StartConnector(); // Calls your function
        _openMainMenuAdbScript = new OpenMainMenuADBScript(_adbConnector);
        _repeatBattlesAdbScript = new RepeatBattlesADBScript(_adbConnector);
    }

    private void OnButtonClick(object? sender, RoutedEventArgs e)
    {
        _repeatBattleState= !_repeatBattleState;

        if (_repeatBattleState)
        {
            _connectorUsed = true;
            _repeatBattlesAdbScript.StartRepeatBattles(Enums.ContentType.Custom);
        }
        else
        {
            _repeatBattlesAdbScript.StopRepeatBattles();
            _connectorUsed = false;
        }
    }
    
}