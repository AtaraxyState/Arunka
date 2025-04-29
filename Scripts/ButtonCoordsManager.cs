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
        try
        {
            if (_buttonCoords == null || _buttonCoords.Count == 0)
            {
                Console.WriteLine("⚠️ No button coordinates to save.");
                return;
            }

            string json = JsonConvert.SerializeObject(_buttonCoords);
            File.WriteAllText(path, json);
            Console.WriteLine($"✅ Saved {_buttonCoords.Count} button(s) to '{path}'.");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Error saving to file '{path}': {ex.Message}");
        }
    }

    public void LoadFromFile(string path)
    {
        try
        {
            if (!File.Exists(path))
            {
                Console.WriteLine($"⚠️ File not found: {path}");
                return;
            }

            string json = File.ReadAllText(path);

            if (string.IsNullOrWhiteSpace(json))
            {
                Console.WriteLine($"⚠️ File '{path}' is empty.");
                return;
            }

            List<ButtonCoords>? buttonCoordsList = JsonConvert.DeserializeObject<List<ButtonCoords>>(json);

            if (buttonCoordsList != null)
            {
                _buttonCoords = buttonCoordsList;
                Console.WriteLine($"✅ Loaded {_buttonCoords.Count} button(s) from '{path}'.");
            }
            else
            {
                Console.WriteLine($"⚠️ Failed to deserialize JSON from '{path}'.");
                _buttonCoords = new List<ButtonCoords>();
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Error loading from file '{path}': {ex.Message}");
        }
    }

}