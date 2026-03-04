using HarmonyLib;
using RimWorld;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Verse;
using Verse.AI;

namespace FishingSpotsandAnglerKits
{


    public class PlaceWorker_OnlyOnFishingSpot : PlaceWorker
    {
        public override AcceptanceReport AllowsPlacing(BuildableDef checkingDef, IntVec3 loc, Rot4 rot, Map map,
            Thing thingToIgnore = null, Thing thing = null)
        {
            // 判断放置点所在格子是否有钓鱼点建筑
            var thingsAtPos = map.thingGrid.ThingsListAt(loc);
            bool hasFishingSpot = false;
            foreach (var t in thingsAtPos)
            {
                if (t.def.defName == "FishingSpot")
                {
                    hasFishingSpot = true;
                    break;
                }
            }

            if (!hasFishingSpot)
            {
                return new AcceptanceReport("mustonfishingspot".Translate());
            }



            return AcceptanceReport.WasAccepted;
        }
    }
}
