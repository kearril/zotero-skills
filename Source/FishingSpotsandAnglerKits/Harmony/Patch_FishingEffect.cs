using HarmonyLib;
using RimWorld;
using System.Collections.Generic;
using Verse;
using Verse.AI;

namespace FishingSpotsandAnglerKits
{
    [HarmonyPatch(typeof(JobDriver_Fish), "MakeNewToils")]
    public static class Patch_FishingEffect_Postfix
    {
        private static readonly HediffDef SeasFavor = HediffDef.Named("SeasFavor");
        private static readonly EffecterDef GoldenFishing = DefDatabase<EffecterDef>.GetNamed("GoldenFishing");

        public static void Postfix(JobDriver_Fish __instance, ref IEnumerable<Toil> __result)
        {
            var toils = new List<Toil>(__result);

            foreach (var toil in toils)
            {
                // WaitWith toil 的特征：tickAction 不为空
                if (toil.tickAction != null)
                {
                    if (__instance.pawn.health.hediffSet.HasHediff(SeasFavor))
                    {
                        // 模拟多杆钓鱼的效果（其实只是叠加个特效）
                        toil.WithEffect(
                            GoldenFishing,
                            () => __instance.job.GetTarget(TargetIndex.A),
                            null
                        );
                    }

             
                    break;
                }
            }

            __result = toils;
        }
    }
}
