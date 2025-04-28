using System;
using System.IO;
using System.Threading;
using Arunka.Scripts.StaticClassEnum;

namespace Arunka.Scripts;

public class RepeatBattlesADBScript(ADBConnector adbConnector) : ADBScriptBase(adbConnector)
{
    private bool _shouldRepeatBattle;
    private Thread _repeatBattleThread;
    
    
    public void StartRepeatBattles(Enums.ContentType contentType)
    {
        _shouldRepeatBattle = true;
        
        // TODO : Goto content type
        
        
        // Start repeatBattle loop
        _repeatBattleThread = new Thread(RepeatBattleLoop);
        _repeatBattleThread.Start();
    }

    public void StopRepeatBattles()
    {
        _shouldRepeatBattle = false;
        _repeatBattleThread.Join();
    }

    private void RepeatBattleLoop()
    {
        while (_shouldRepeatBattle)
        {
            // Check if repeat ended 
            bool searchResult = SearchImage(Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons/RepeatBattle.png");
            
            // Restart repeat
            if (searchResult)
            {
                Thread.Sleep(GlobalVariables.SearchLoopCooldown * 5);
                ClearSideStoryInventory();
                Thread.Sleep(GlobalVariables.ClickCooldown);
                RestartBattles();
            }
            
            // Sleep
            Thread.Sleep(GlobalVariables.SearchLoopCooldown);
        }
    }

    private void ClearSideStoryInventory()
    {
        TapButton(Enums.Buttons.Button.Custom, Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons//Inventory.png");
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapButton(Enums.Buttons.Button.Custom, Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons//ArrangeInventory.png");
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapButton(Enums.Buttons.Button.Custom, Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons//SimpleSelection.png");
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapButton(Enums.Buttons.Button.Custom, Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons//Sell.png");
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapButton(Enums.Buttons.Button.Custom, Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons/ConfirmSell.png");
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapButton(Enums.Buttons.Button.Custom, Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons//QuitInventoryUsingMVP.png");
    }

    private void RestartBattles()
    {
        TapButton(Enums.Buttons.Button.Custom, Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons//RepeatBattle.png");
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapButton(Enums.Buttons.Button.Custom, Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons//TryAgain.png");
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapButton(Enums.Buttons.Button.Custom, Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons//TryAgain.png");
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapButton(Enums.Buttons.Button.Custom, Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons//SelectTeam.png");
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapButton(Enums.Buttons.Button.Custom, Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons//Start.png");
    }
}