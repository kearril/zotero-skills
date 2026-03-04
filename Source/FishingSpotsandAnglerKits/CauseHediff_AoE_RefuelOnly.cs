using RimWorld;
using System.Collections.Generic;
using UnityEngine;
using Verse;

namespace FishingSpotsandAnglerKits
{
    /// <summary>
    /// 该组件对玩家派系、特定范围内符合条件的Pawn添加Hediff，
    /// 通过燃料控制激活状态，使用缓存+类型快速过滤优化性能。    
    /// </summary>
    public class CompCauseHediff_AoE_RefuelOnly : ThingComp
    {

        private CompRefuelable refuelComp;

        // 缓存影响范围内的玩家派系Pawn
        private List<Pawn> cachedAffectedPawns = new List<Pawn>();

        // 缓存刷新周期（单位：tick）
        private const int CacheUpdateInterval = 300;

        // 计数器：用于判断何时刷新缓存
        private int cacheUpdateCounter = 0;


        public CompProperties_CauseHediff_AoE_RefuelOnly Props => (CompProperties_CauseHediff_AoE_RefuelOnly)props;

        // 延迟加载燃料组件
        private CompRefuelable RefuelComp
        {
            get
            {
                if (refuelComp == null)
                    refuelComp = parent.GetComp<CompRefuelable>();
                return refuelComp;
            }
        }

        /// <summary>
        /// 每tick运行逻辑，负责缓存更新、消耗燃料、hediff刷新
        /// </summary>
        public override void CompTick()
        {
            base.CompTick();

            // 每CacheUpdateInterval tick刷新一次缓存
            cacheUpdateCounter++;
            if (cacheUpdateCounter >= CacheUpdateInterval)
            {
                cacheUpdateCounter = 0;
                UpdateCachedAffectedPawns();
            }

            // 若存在目标pawn且有燃料，则周期性刷新hediff
            if (cachedAffectedPawns.Count > 0 && RefuelComp != null && RefuelComp.HasFuel)
            {
                RefuelComp.Notify_UsedThisTick();

                // 按checkInterval控制hediff刷新频率
                if (parent.IsHashIntervalTick(Props.checkInterval))
                {
                    foreach (Pawn p in cachedAffectedPawns)
                    {
                        GiveOrUpdateHediff(p);
                    }
                }
            }
        }

        /// <summary>
        /// 刷新作用pawn缓存，只遍历玩家派系pawn，并快速过滤不符合条件者
        /// </summary>
        private void UpdateCachedAffectedPawns()
        {
            cachedAffectedPawns.Clear();

            if (parent.MapHeld == null)
                return;

            foreach (Pawn p in parent.MapHeld.mapPawns.SpawnedPawnsInFaction(Faction.OfPlayer))
            {
                // 剔除死亡、无健康pawn
                if (p.Dead || p.health == null)
                    continue;

                // 是否作用于自己
                if (!Props.canTargetSelf && p == parent)
                    continue;

                // 按是否过滤机械体判断
                if (Props.ignoreMechs && p.RaceProps.IsMechanoid)
                    continue;

                if (Props.onlyTargetMechs && !p.RaceProps.IsMechanoid)
                    continue;

                // 距离判定
                if (p.PositionHeld.DistanceTo(parent.PositionHeld) <= Props.range)
                {
                    cachedAffectedPawns.Add(p);
                }
            }
        }

        /// <summary>
        /// 给Pawn添加或刷新hediff，使用HasHediff优化判定
        /// </summary>
        private void GiveOrUpdateHediff(Pawn target)
        {
            // 没有hediff时直接添加
            if (!target.health.hediffSet.HasHediff(Props.hediff))
            {
                var hediff = target.health.AddHediff(Props.hediff, target.health.hediffSet.GetBrain());
                hediff.Severity = 1f;

                // 如果hediff有链接组件，关联建筑物
                var hediffComp_Link = hediff.TryGetComp<HediffComp_Link>();
                if (hediffComp_Link != null)
                {
                    hediffComp_Link.drawConnection = false;
                    hediffComp_Link.other = parent;
                }

                // 刷新自动消失时间
                var disappearComp = hediff.TryGetComp<HediffComp_Disappears>();
                if (disappearComp != null)
                    disappearComp.ticksToDisappear = Props.checkInterval + 5;
                else
                    Log.ErrorOnce("CompCauseHediff_AoE requires HediffComp_Disappears on the hediff.", 123456);

                return;
            }

            // 有hediff时只刷新倒计时
            var existingHediff = target.health.hediffSet.GetFirstHediffOfDef(Props.hediff);
            var disappear = existingHediff?.TryGetComp<HediffComp_Disappears>();
            if (disappear != null)
                disappear.ticksToDisappear = Props.checkInterval + 5;
        }

        /// <summary>
        /// 绘制选中建筑物时的作用范围圈
        /// </summary>
        public override void PostDrawExtraSelectionOverlays()
        {
            GenDraw.DrawRadiusRing(parent.Position, Props.range);
        }
    }

    /// <summary>
    /// 组件属性定义：范围、目标限制、hediff、tick间隔等由XML定义
    /// </summary>
    public class CompProperties_CauseHediff_AoE_RefuelOnly : CompProperties
    {
        public float range = 1.5f;               // 作用范围
        public bool onlyTargetMechs = false;    // 是否只作用于机械体
        public bool ignoreMechs = false;        // 是否忽略机械体
        public bool canTargetSelf = false;      // 是否作用于自己
        public int checkInterval = 120;         // hediff刷新频率
        public HediffDef hediff;                // 应用的hediff类型

        public CompProperties_CauseHediff_AoE_RefuelOnly()
        {
            compClass = typeof(CompCauseHediff_AoE_RefuelOnly);
        }
    }

    /// <summary>
    /// 放置预览：放置时绘制范围圈
    /// </summary>
    public class PlaceWorker_ShowCauseHediffAoE_RefuelOnly : PlaceWorker
    {
        public override void DrawGhost(ThingDef def, IntVec3 center, Rot4 rot, Color ghostCol, Thing thing = null)
        {
            var compProperties = def.GetCompProperties<FishingSpotsandAnglerKits.CompProperties_CauseHediff_AoE_RefuelOnly>();
            if (compProperties != null)
            {
                GenDraw.DrawRadiusRing(center, compProperties.range, Color.green);
            }
        }
    }
}
