using System;
using System.IO;
using System.Threading;
using Arunka.Scripts.StaticClassEnum;

namespace Arunka.Scripts;

public class RepeatBattlesADBScript(ADBConnector adbConnector, ButtonCoordsManager buttonCoordsManager) : ADBScriptBase(adbConnector, buttonCoordsManager)
{
    private bool _shouldRepeatBattle;
    private Thread _repeatBattleThread;
    private ButtonCoordsManager _buttonCoords;
    
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
        _shouldRepeatBattle = true;
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

        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapAt(_inventoryButtonCoords.X, _inventoryButtonCoords.Y);
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapAt(_arrangeInventory.X, _arrangeInventory.Y);
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapAt(_simpleSelection.X, _simpleSelection.Y);
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapAt(_sellButtonCoords.X, _sellButtonCoords.Y);
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapAt(_confirmSellButtonCoords.X, _confirmSellButtonCoords.Y);
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapAt(_quitInventory.X, _quitInventory.Y);
    }

    private void RestartBattles()
    {
        Console.WriteLine("Restarting Battles");
        
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapAt(_confirmButton.X, _confirmButton.Y);
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapAt(_tryAgainButton.X, _tryAgainButton.Y);
        Thread.Sleep(GlobalVariables.ClickCooldown * 2);
        TapAt(_selectTeamButton.X, _selectTeamButton.Y);
        Thread.Sleep(GlobalVariables.ClickCooldown);
        TapAt(_startButton.X, _startButton.Y);
        
        // Check success TODO this part is shit idk I was drunk or smt
        // var confirm = GetButtonLocation(Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons/Start.png");
        // if (confirm == null)
        // {
        //     Thread.Sleep(GlobalVariables.ClickCooldown);
        //     TapAt(_startButton.X, _startButton.Y);
        // }
        
        // If still null probably need to use leif or SkyStones
        var confirm = GetButtonLocation(Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons/Start.png");
        if (confirm == null)
        {
            Thread.Sleep(GlobalVariables.ClickCooldown);
            TapAt(_selectLeifsButton.X, _selectLeifsButton.Y);
            Thread.Sleep(GlobalVariables.ClickCooldown);
            TapAt(_buyStamina.X, _buyStamina.Y);
            
            // Retap
            Thread.Sleep(GlobalVariables.ClickCooldown);
            TapAt(_startButton.X, _startButton.Y);
        }
    }
}