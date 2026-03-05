using HarmonyLib;
using RimWorld;
using Verse;
using Verse.AI;

namespace FishingSpotsandAnglerKits.Harmony
{
    //绘制额外的钓鱼特效，如果角色有SeasFavor这个Hediff
    [HarmonyPatch(typeof(JobDriver_Fish), "MakeNewToils")]
    public static class Patch_FishingEffect_Postfix
    {
        private static HediffDef? _seasFavor;

        private static HediffDef SeasFavor =>
            _seasFavor ??= DefDatabase<HediffDef>.GetNamed("SeasFavor");

        private static EffecterDef? _goldenFishing;

        private static EffecterDef GoldenFishing =>
            _goldenFishing ??= DefDatabase<EffecterDef>.GetNamed("GoldenFishing");

        public static IEnumerable<Toil> Postfix(IEnumerable<Toil> __result, JobDriver_Fish __instance)
        {
            foreach (Toil toil in __result)
            {
                if (toil.tickAction != null && __instance.pawn.health.hediffSet.HasHediff(SeasFavor))
                {
                    yield return toil.WithEffect(
                        GoldenFishing,
                        TargetIndex.A
                    );
                }
                else
                {
                    yield return toil;
                }
            }
        }
    }
}