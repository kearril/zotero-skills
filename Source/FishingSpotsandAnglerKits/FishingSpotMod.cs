using HarmonyLib;
using Verse;

namespace FishingSpotsandAnglerKits
{
    [StaticConstructorOnStartup]
    public static class FishingSpotMod
    {
        static FishingSpotMod()
        {
            var harmony = new HarmonyLib.Harmony("FSAK.fishingspot");
            harmony.PatchAll();
        }
    }
}
