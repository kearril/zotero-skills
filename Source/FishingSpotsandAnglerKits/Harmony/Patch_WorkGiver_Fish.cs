using HarmonyLib;
using RimWorld;
using Verse;
using Verse.AI;

namespace FishingSpotsandAnglerKits.Harmony
{
    [HarmonyPatch(typeof(WorkGiver_Fish), nameof(WorkGiver_Fish.NonScanJob))]
    public static class WorkGiver_Fish_NonScanJob_Patch
    {
        private static ThingDef? fishingSpotDef;

        private static ThingDef FishingSpotDef
        {
            get
            {
                if (fishingSpotDef == null)
                    fishingSpotDef = DefDatabase<ThingDef>.GetNamed("FishingSpot");
                return fishingSpotDef;
            }
        }

        public static bool Prefix(Pawn pawn, ref Job __result)
        {
            if (!ModsConfig.OdysseyActive) return true;

            Map map = pawn.Map;
            if (map == null) return true;

            // 获取地图上所有的钓鱼点建筑
            List<Thing> allSpots = map.listerThings.ThingsOfDef(FishingSpotDef);
            if (allSpots.NullOrEmpty()) return true;

            // 意识形态检查：复用原版的事件通知逻辑
            if (pawn.Ideo != null &&
                !new HistoryEvent(HistoryEventDefOf.SlaughteredFish, pawn.Named(HistoryEventArgsNames.Doer))
                    .Notify_PawnAboutToDo_Job())
            {
                return true;
            }

            // 寻找最近且可用的钓鱼点
            // 按距离排序以优化体验，同时过滤掉被禁止或不可达的点
            var sortedSpots = allSpots
                .Where(s => s.Spawned && !s.IsForbidden(pawn))
                .OrderBy(s => s.Position.DistanceToSquared(pawn.Position));

            foreach (var spot in sortedSpots)
            {
                IntVec3 standSpot = spot.Position;

                
                if (!pawn.CanReserveAndReach(standSpot, PathEndMode.OnCell, Danger.Some, layer: ReservationLayerDefOf.Floor)) continue;

                // 寻找周围可用的水域
                IntVec3? waterCell = FindWaterTargetNearStandSpot(standSpot, map, pawn);
                if (waterCell.HasValue)
                {
                    // 找到了可用的建筑点，生成任务
                    __result = JobMaker.MakeJob(JobDefOf.Fish, waterCell.Value, standSpot);
                    return false;
                }
            }

            return true;
        }

        /// <summary>
        /// 在钓鱼点周围寻找属于钓鱼区的水格子
        /// </summary>
        private static IntVec3? FindWaterTargetNearStandSpot(IntVec3 standSpot, Map map, Pawn pawn)
        {
            foreach (var dir in GenAdj.CardinalDirections)
            {
                IntVec3 target = standSpot + dir;
                if (!target.InBounds(map) || target.IsForbidden(pawn)) continue;

                TerrainDef terrain = target.GetTerrain(map);
                if (!terrain.IsWater) continue;

                // 检查该水格是否在钓鱼区内
                if (target.GetZone(map) is Zone_Fishing zone && zone.ShouldFishNow && zone.IsFishable(target))
                {
                    // 检查水面是否能预约（防止两个人在一个格子上钓鱼）
                    if (pawn.CanReserve(target, layer: ReservationLayerDefOf.Floor))
                    {
                        return target;
                    }
                }
            }
            return null;
        }
    }
}