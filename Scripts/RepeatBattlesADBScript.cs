﻿using System;
using System.IO;
using System.Threading;
using Arunka.Scripts.StaticClassEnum;

namespace Arunka.Scripts;

public class RepeatBattlesADBScript(ADBConnector adbConnector, ButtonCoordsManager buttonCoordsManager) : ADBScriptBase(adbConnector, buttonCoordsManager)
{
    private bool _shouldRepeatBattle;    
    private ButtonCoordsManager _buttonCoords;

    private CancellationTokenSource? _cts;
    private Thread _repeatBattleThread;

    private ButtonCoordsManager.ButtonCoords _inventoryButtonCoords;
    private ButtonCoordsManager.ButtonCoords _arrangeInventory;
    private ButtonCoordsManager.ButtonCoords _simpleSelection;
    private ButtonCoordsManager.ButtonCoords _sellButtonCoords;
    private ButtonCoordsManager.ButtonCoords _confirmSellButtonCoords;
    private ButtonCoordsManager.ButtonCoords _quitInventory;
    private ButtonCoordsManager.ButtonCoords _confirmButton;
    private ButtonCoordsManager.ButtonCoords _tryAgainButton;
    private ButtonCoordsManager.ButtonCoords _selectTeamButton;
    private ButtonCoordsManager.ButtonCoords _startButton;
    private ButtonCoordsManager.ButtonCoords _selectLeifsButton;
    private ButtonCoordsManager.ButtonCoords _selectSkystonesButton;
    private ButtonCoordsManager.ButtonCoords _buyStamina;
    
    public void StartRepeatBattles(Enums.ContentType contentType, ButtonCoordsManager buttonCoords)
    {
        _buttonCoords = buttonCoords;

        _inventoryButtonCoords = _buttonCoords.GetButtonCoords.Find(x => x.Name == "Inventory.png");
        _arrangeInventory = _buttonCoords.GetButtonCoords.Find(x => x.Name == "ArrangeInventory.png");
        _simpleSelection = _buttonCoords.GetButtonCoords.Find(x => x.Name == "SimpleSelection.png");
        _sellButtonCoords = _buttonCoords.GetButtonCoords.Find(x => x.Name == "Sell.png");
        _confirmSellButtonCoords = _buttonCoords.GetButtonCoords.Find(x => x.Name == "ConfirmSell.png");
        _quitInventory = _buttonCoords.GetButtonCoords.Find(x => x.Name == "QuitInventoryUsingMVP.png");
        _confirmButton = _buttonCoords.GetButtonCoords.Find(x => x.Name == "ConfirmButton.png");
        _tryAgainButton = _buttonCoords.GetButtonCoords.Find(x => x.Name == "TryAgain.png");
        _selectTeamButton = _buttonCoords.GetButtonCoords.Find(x => x.Name == "SelectTeam.png");
        _startButton = _buttonCoords.GetButtonCoords.Find(x => x.Name == "Start.png");
        _selectLeifsButton = _buttonCoords.GetButtonCoords.Find(x => x.Name == "SelectLeifs.png");
        _selectSkystonesButton = _buttonCoords.GetButtonCoords.Find(x => x.Name == "SelectSkystones.png");
        _buyStamina = _buttonCoords.GetButtonCoords.Find(x => x.Name == "BuyStamina.png");
        
        // TODO : Goto content type
        
        // Start repeatBattle loop
        _repeatBattleThread = new Thread(RepeatBattleLoop);
        _cts = new CancellationTokenSource();
        _repeatBattleThread.Start();
    }

    public void StopRepeatBattles()
    {
        _cts.Cancel();            // Request cancellation
        _repeatBattleThread.Join(1000);
    }

    private void RepeatBattleLoop()
    {
        while (!_cts.IsCancellationRequested)
        {
            // Check if repeat ended 
            bool searchResult = SearchImage(Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons/RepeatBattle.png");
            
            // Restart repeat
            if (searchResult)
            {
                Thread.Sleep(GlobalVariables.SearchLoopCooldown * 2);
                ClearSideStoryInventory();
                Thread.Sleep(GlobalVariables.ClickCooldown);
                RestartBattles();
            }
            
            // Sleep
            Thread.Sleep(GlobalVariables.SearchLoopCooldown * 5);
        }
    }

    private void ClearSideStoryInventory()
    {
        Console.WriteLine("Clearing Side Story Inventory");

        WaitAndTapFromCoords(_inventoryButtonCoords,true,_cts);
        WaitAndTapFromCoords(_arrangeInventory,true, _cts);
        WaitAndTapFromCoords(_simpleSelection,true, _cts);
        WaitAndTapFromCoords(_sellButtonCoords,true, _cts);
        WaitAndTapFromCoords(_confirmSellButtonCoords,true, _cts);
        WaitAndTapFromCoords(_quitInventory,true, _cts);
    }

    private void RestartBattles()
    {
        Console.WriteLine("Restarting Battles");
        
        WaitAndTapFromCoords(_confirmButton,true, _cts);
        WaitAndTapFromCoords(_tryAgainButton,true, _cts);
        Thread.Sleep(GlobalVariables.ClickCooldown * 5);

        WaitAndTapFromCoords(_selectTeamButton, false, _cts);
        WaitAndTapFromCoords(_startButton,false, _cts);
        
        Thread.Sleep(GlobalVariables.ClickCooldown);
        
        // Check if need to buy stamina
        var confirm = GetButtonLocation(Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons/SelectLeifs.png");
        if (confirm == null)
        {
            Thread.Sleep(GlobalVariables.ClickCooldown);
            WaitAndTapFromCoords(_selectLeifsButton,true, _cts);
            Thread.Sleep(GlobalVariables.ClickCooldown);
            WaitAndTapFromCoords(_buyStamina,true, _cts);
            
            // Retap confirm
            Thread.Sleep(GlobalVariables.ClickCooldown);
            WaitAndTapFromCoords(_startButton,false, _cts);
        }
    }
}