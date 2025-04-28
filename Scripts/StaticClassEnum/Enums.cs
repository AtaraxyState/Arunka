namespace Arunka.Scripts.StaticClassEnum;


public class Enums
{
    public enum ContentType
    {
        MainMenu,
        Heroes,
        SideStory,
        Custom
    }

    public static class Buttons {
    
        public enum Button
        {
            MainMenu,
            Heroes,
            SideStory,
            Custom
        }
    
        public static string GetButton(Button button)
        {
            switch (button)
            {
                case Button.MainMenu:
                    return "MainMenu.png";
                case Button.Heroes:
                    return "Heroes.png";
                case Button.SideStory:
                    return "SideStory.png";
                default:
                    return "";
            }
        }
    }
}
