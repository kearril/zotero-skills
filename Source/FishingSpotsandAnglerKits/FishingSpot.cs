using HarmonyLib;
using RimWorld;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Verse.AI;
using Verse;
using UnityEngine;

namespace FishingSpotsandAnglerKits
{


    [HarmonyPatch(typeof(WorkGiver_Fish), nameof(WorkGiver_Fish.NonScanJob))]
    public static class WorkGiver_Fish_NonScanJob_Patch
    {
        private const int MaxSearchAttempts = 120;
        private const int SwitchThreshold = 60;

        public static bool Prefix(Pawn pawn, ref Job __result)
        {
            // 如果未启用 Odyssey 模块，则不进行任何钓鱼任务
            if (!ModsConfig.OdysseyActive)
            {
                __result = null;
                return false;
            }

            // 意识形态拒绝钓鱼（触发历史事件通知），则返回无任务
            if (pawn.Ideo != null && !new HistoryEvent(HistoryEventDefOf.SlaughteredFish, pawn.Named(HistoryEventArgsNames.Doer)).Notify_PawnAboutToDo_Job())
            {
                __result = null;
                return false;
            }

            Map map = pawn.Map;
            if (map == null)
            {
                __result = null;
                return false;
            }

            // 第一阶段：尝试所有钓鱼点
            foreach (var spot in GetValidFishingSpotsForPawn(map, pawn))
            {
                IntVec3 standSpot = spot.Position;
                IntVec3? waterCell = FindWaterTargetNearStandSpot(standSpot, map, pawn);

                if (waterCell.HasValue && CanReserveBothPositions(pawn, standSpot, waterCell.Value, map))
                {
                    __result = JobMaker.MakeJob(JobDefOf.Fish, waterCell.Value, standSpot);
                    return false;
                }
            }

            // 第二阶段：尝试钓鱼区随机钓鱼 
            Zone_Fishing bestZone = FindClosestValidFishingZone(pawn, map);
            if (bestZone != null)
            {
                bool allowStandingInWater = false;
                int attempts = 0;

                while (attempts < MaxSearchAttempts)
                {
                    IntVec3 fishCell = bestZone.RandomFishableCell;
                    if (fishCell.IsValid && pawn.CanReserveAndReach(fishCell, PathEndMode.Touch, Danger.Some))
                    {
                        IntVec3 standSpot = WorkGiver_Fish_BestStandSpotFor(pawn, fishCell, avoidStandingInWater: !allowStandingInWater);
                        bool standSpotValid = standSpot.IsValid && (allowStandingInWater || !standSpot.GetTerrain(map).IsWater);

                        if (standSpotValid && CanReserveBothPositions(pawn, standSpot, fishCell, map))
                        {
                            __result = JobMaker.MakeJob(JobDefOf.Fish, fishCell, standSpot);
                            return false;
                        }
                    }

                    attempts++;
                    if (attempts >= SwitchThreshold && !allowStandingInWater)
                    {
                        allowStandingInWater = true; // 尝试让Pawn站在水里
                        attempts = 0;
                    }
                }
            }

            __result = null;
            return false;
        }

        /// <summary>
        /// 获取地图中所有对该Pawn有效的钓鱼点
        /// </summary>
        private static IEnumerable<Thing> GetValidFishingSpotsForPawn(Map map, Pawn pawn)
        {
            foreach (var thing in map.listerThings.ThingsOfDef(ThingDef.Named("FishingSpot")))
            {
                if (thing.Spawned && IsFishingSpotValid(pawn, thing.Position, map))
                    yield return thing;
            }
        }

        /// <summary>
        /// 判断一个钓鱼点是否对Pawn可用
        /// </summary>
        private static bool IsFishingSpotValid(Pawn pawn, IntVec3 standSpot, Map map)
        {
            IntVec3? waterCell = FindWaterTargetNearStandSpot(standSpot, map, pawn);
            if (!waterCell.HasValue)
                return false;

            var zone = waterCell.Value.GetZone(map) as Zone_Fishing;
            if (zone == null || !zone.ShouldFishNow || !zone.Allowed)
                return false;

            // 区域限制
            if (pawn.playerSettings?.EffectiveAreaRestrictionInPawnCurrentMap is Area area)
            {
                if (!area[waterCell.Value])
                    return false;
            }

            // 预约与禁用判断
            return pawn.CanReserve(standSpot) && !standSpot.IsForbidden(pawn)
                && pawn.CanReserve(waterCell.Value) && !waterCell.Value.IsForbidden(pawn);
        }

        /// <summary>
        /// 在钓鱼点周围寻找水格子作为目标格
        /// 优先顺序：东、北、西、南
        /// </summary>
        private static IntVec3? FindWaterTargetNearStandSpot(IntVec3 standSpot, Map map, Pawn pawn)
        {
            foreach (var dir in GenAdj.CardinalDirections)
            {
                IntVec3 target = standSpot + dir;
                if (!target.InBounds(map)) continue;

                TerrainDef terrain = target.GetTerrain(map);
                if (!terrain.IsWater) continue;

                var zone = target.GetZone(map) as Zone_Fishing;
                if (zone == null || !zone.ShouldFishNow || !zone.Allowed) continue;

                if (IsReservedByOtherFishingJob(map, target, pawn)) continue;
                if (!pawn.CanReserve(target)) continue;

                return target;
            }
            return null;
        }

        /// <summary>
        /// 查找距离Pawn最近的有效钓鱼区
        /// </summary>
        private static Zone_Fishing FindClosestValidFishingZone(Pawn pawn, Map map)
        {
            Zone_Fishing best = null;
            float minDistSquared = float.MaxValue;

            foreach (Zone zone in map.zoneManager.AllZones)
            {
                if (zone is Zone_Fishing zf && zf.ShouldFishNow && zf.Cells.Count > 0)
                {
                    float dist = pawn.Position.DistanceToSquared(zf.Cells[0]);
                    if (best == null || dist < minDistSquared)
                    {
                        best = zf;
                        minDistSquared = dist;
                    }
                }
            }
            return best;
        }

        /// <summary>
        /// 判断Pawn是否能同时预约站立点与目标点，并且这两个点未被其他钓鱼任务预约
        /// </summary>
        private static bool CanReserveBothPositions(Pawn pawn, IntVec3 standSpot, IntVec3 targetSpot, Map map)
        {
            return pawn.CanReserve(standSpot)
                && !IsReservedByOtherFishingJob(map, standSpot, pawn)
                && pawn.CanReserve(targetSpot)
                && !IsReservedByOtherFishingJob(map, targetSpot, pawn);
        }

        /// <summary>
        /// 判断指定cell是否已经被其他Pawn钓鱼任务预约
        /// </summary>
        private static bool IsReservedByOtherFishingJob(Map map, IntVec3 cell, Pawn checkingPawn)
        {
            return map.reservationManager.ReservationsReadOnly.Any(res =>
                res.Target.Cell == cell && res.Claimant != checkingPawn && res.Job?.def == JobDefOf.Fish);
        }

        /// <summary>
        /// 选择靠近鱼点的最佳站立格子（避免站在水中）
        /// </summary>
        private static IntVec3 WorkGiver_Fish_BestStandSpotFor(Pawn pawn, IntVec3 fishSpot, bool avoidStandingInWater = true)
        {
            IntVec3 best = IntVec3.Invalid;
            float bestScore = float.MinValue;

            foreach (var dir in GenAdj.CardinalDirections)
            {
                IntVec3 candidate = fishSpot + dir;
                if (!candidate.InBounds(pawn.Map) || !candidate.Standable(pawn.Map) || candidate.IsForbidden(pawn))
                    continue;

                if (!pawn.CanReserveAndReach(candidate, PathEndMode.Touch, Danger.Some))
                    continue;

                if (!avoidStandingInWater)
                    return candidate;

                // 水面地形的分数较低（尽量避免）
                float score = candidate.GetTerrain(pawn.Map).IsWater ? 0.5f : 1f;
                if (score > bestScore || (Mathf.Approximately(score, bestScore) && Rand.Bool))
                {
                    best = candidate;
                    bestScore = score;
                }
            }

            return best;
        }
    }





    [StaticConstructorOnStartup]
    public static class FishingSpotMod
    {
        static FishingSpotMod()
        {
            var harmony = new Harmony("FSAK.fishingspot");
            harmony.PatchAll();
        }
    }

    public class PlaceWorker_FishingSpot : PlaceWorker
    {
        public override AcceptanceReport AllowsPlacing(BuildableDef checkingDef, IntVec3 loc, Rot4 rot, Map map,
            Thing thingToIgnore = null, Thing thing = null)
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
