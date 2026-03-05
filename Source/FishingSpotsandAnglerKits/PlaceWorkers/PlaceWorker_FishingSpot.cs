using RimWorld;
using Verse;

namespace FishingSpotsandAnglerKits.PlaceWorkers
{
    public class PlaceWorker_FishingSpot : PlaceWorker
    {
        public override AcceptanceReport AllowsPlacing(BuildableDef checkingDef, IntVec3 loc, Rot4 rot, Map map,
            Thing? thingToIgnore = null, Thing? thing = null)
        {
            bool inFishingZone = loc.GetZone(map) is Zone_Fishing;
            bool validLocation = loc.Standable(map) || loc.GetTerrain(map).IsWater;

            if (inFishingZone && validLocation)
                return AcceptanceReport.WasAccepted;

            foreach (var c in GenAdj.CellsAdjacent8Way(new TargetInfo(loc, map)))

            {
                if (c.InBounds(map) && c.GetZone(map) is Zone_Fishing)
                {
                    if (validLocation)
                        return AcceptanceReport.WasAccepted;
                }
            }

            return new AcceptanceReport("FishingSpotMustBeInOrNextToFishingZone".Translate());
        }
    }
}
