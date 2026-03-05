using FishingSpotsandAnglerKits.Comps;
using UnityEngine;
using Verse;

namespace FishingSpotsandAnglerKits.PlaceWorkers
{
    /// <summary>
    /// 放置预览：放置时绘制范围圈
    /// </summary>
    public class PlaceWorker_ShowCauseHediffAoE_RefuelOnly : PlaceWorker
    {
        public override void DrawGhost(ThingDef def, IntVec3 center, Rot4 rot, Color ghostCol, Thing? thing = null)
        {
            var compProperties = def.GetCompProperties<CompProperties_CauseHediff_AoE_RefuelOnly>();
            if (compProperties != null)
            {
                GenDraw.DrawRadiusRing(center, compProperties.range, Color.green);
            }
        }
    }
}
