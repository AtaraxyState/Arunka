using System;
using Avalonia.Controls;
using Avalonia.Interactivity;

namespace Arunka;

public partial class MainWindow : Window
{
    ADBTests adbTests = new ADBTests();
    
    public MainWindow()
    {
        InitializeComponent();
    }

    private void OnButtonClick(object? sender, RoutedEventArgs e)
    {
        adbTests.Main(); // Calls your function
    }
    
}