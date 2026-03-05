using System.Collections.Generic;
using RimWorld;
using Verse;

namespace FishingSpotsandAnglerKits.Comps
{
    public class CompCauseHediff_AoE_RefuelOnly : ThingComp
    {
        private CompRefuelable? _refuelComp;
        private readonly List<Pawn> _cachedAffectedPawns = new List<Pawn>();
        private int _cacheUpdateCounter = 0;
        private const int CacheUpdateInterval = 60; // 每60tick更新一次缓存

        public CompProperties_CauseHediff_AoE_RefuelOnly Props => (CompProperties_CauseHediff_AoE_RefuelOnly)props;

        private CompRefuelable RefuelComp => _refuelComp ??= parent.TryGetComp<CompRefuelable>();

        public override void CompTick()
        {
            if (RefuelComp == null || !RefuelComp.HasFuel) return;

            _cacheUpdateCounter++;
            if (_cacheUpdateCounter >= CacheUpdateInterval)
            {
                _cacheUpdateCounter = 0;
                UpdateCachedAffectedPawns();
            }

            if (_cachedAffectedPawns.Count > 0)
            {
                RefuelComp.Notify_UsedThisTick();

                if (parent.IsHashIntervalTick(Props.checkInterval))
                {
                    Map map = parent.MapHeld;
                    for (int i = _cachedAffectedPawns.Count - 1; i >= 0; i--)
                    {
                        Pawn p = _cachedAffectedPawns[i];

                        if (p.Spawned && !p.Dead && p.MapHeld == map)
                        {
                            GiveOrUpdateHediff(p);
                        }
                        else
                        {
                            _cachedAffectedPawns.RemoveAt(i);
                        }
                    }
                }
            }
        }

        private void UpdateCachedAffectedPawns()
        {
            _cachedAffectedPawns.Clear();
            Map map = parent.MapHeld;
            if (map == null) return;

            float rangeSq = Props.range * Props.range;
            IntVec3 pos = parent.PositionHeld;
            Faction faction = Faction.OfPlayer;


            foreach (Thing thing in GenRadial.RadialDistinctThingsAround(pos, map, Props.range, true))
            {
                if (thing is Pawn p && p.Faction == faction)
                {
                    if (p.Dead || p.health == null) continue;
                    if (!Props.canTargetSelf && p == parent) continue;
                    if (Props.ignoreMechs && p.RaceProps.IsMechanoid) continue;
                    if (Props.onlyTargetMechs && !p.RaceProps.IsMechanoid) continue;


                    if (p.PositionHeld.DistanceToSquared(pos) <= rangeSq)
                    {
                        _cachedAffectedPawns.Add(p);
                    }
                }
            }
        }

        // 给目标Pawn添加或刷新Hediff
        private void GiveOrUpdateHediff(Pawn target)
        {
            if (Props.hediff == null) return;

            Hediff existingHediff = target.health.hediffSet.GetFirstHediffOfDef(Props.hediff);
            if (existingHediff == null)
            {
                existingHediff = target.health.AddHediff(Props.hediff);
                existingHediff.Severity = 1f;

                HediffComp_Link link = existingHediff.TryGetComp<HediffComp_Link>();
                if (link != null)
                {
                    link.drawConnection = false;
                    link.other = parent;
                }
            }


            HediffComp_Disappears disappear = existingHediff.TryGetComp<HediffComp_Disappears>();
            if (disappear != null)
            {
                disappear.ticksToDisappear = Props.checkInterval + 5;
            }
        }

        // 绘制范围圈
        public override void PostDrawExtraSelectionOverlays()
        {
            GenDraw.DrawRadiusRing(parent.Position, Props.range);
        }
    }

    public class CompProperties_CauseHediff_AoE_RefuelOnly : CompProperties
    {
        public float range = 1.5f;
        public bool onlyTargetMechs = false;
        public bool ignoreMechs = false;
        public bool canTargetSelf = false;
        public int checkInterval = 120;
        public HediffDef? hediff;

        public CompProperties_CauseHediff_AoE_RefuelOnly()
        {
            compClass = typeof(CompCauseHediff_AoE_RefuelOnly);
        }
    }
}