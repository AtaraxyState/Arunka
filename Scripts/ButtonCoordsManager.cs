using System;
using System.Collections.Generic;
using System.IO;
using Arunka.Scripts.StaticClassEnum;
using Newtonsoft.Json;
using Formatting = System.Xml.Formatting;

namespace Arunka.Scripts;

public class ButtonCoordsManager(ADBConnector adbConnector) : ADBScriptBase(adbConnector)
{
    /// <summary>
    /// Used to serialize button positions to json
    /// </summary>
    public struct ButtonCoords
    {
        public Enums.Buttons.Button ButtonType;
        public string Name;
        public int X;
        public int Y;
    }
    
    private List<ButtonCoords> _buttonCoords = new List<ButtonCoords>();
    
    public List<ButtonCoords> GetButtonCoords => _buttonCoords;
    
    public void UpdatePosition(string imageName)
    {
       (int,int)? imageCenter = GetButtonLocation(Path.Combine(AppContext.BaseDirectory, "..\\..\\..\\") + "/Resources/Buttons/" + imageName);

       // Update corresponding button in the _buttonCoords list
       if (imageCenter.HasValue)
       {
           int newX = imageCenter.Value.Item1;
           int newY = imageCenter.Value.Item2;

           // Find the entry in the list by Name
           var index = -1;

           if (_buttonCoords.Count > 0)
               index = _buttonCoords.FindIndex(b => b.Name == imageName);

           if (index != -1)
           {
               // Update existing entry
               var button = _buttonCoords[index];
               button.X = newX;
               button.Y = newY;
               _buttonCoords[index] = button;

               Console.WriteLine($"🔄 Updated coordinates for '{imageName}' to ({newX}, {newY})");
           }
           else
           {
               // Add a new entry (default ButtonType if unknown)
               _buttonCoords.Add(new ButtonCoords
               {
                   ButtonType = Enums.Buttons.Button.Custom, // We may want to infer/set this properly
                   Name = imageName,
                   X = newX,
                   Y = newY
               });

               Console.WriteLine($"➕ Added new button '{imageName}' at ({newX}, {newY})");
           }
       }
       else
       {
           Console.WriteLine($"⚠️ Could not locate button '{imageName}' on screen.");
       }
    }
    
    public void SaveToFile(string path)
    {
        string json = JsonConvert.SerializeObject(_buttonCoords);
        File.WriteAllText(path, json);
    }
    
    public void LoadFromFile(string path)
    {
        string json = File.ReadAllText(path);

        List<ButtonCoords>? buttonCoordsList = JsonConvert.DeserializeObject<List<ButtonCoords>>(json);
        
        _buttonCoords = buttonCoordsList ?? new List<ButtonCoords>();
    }
}