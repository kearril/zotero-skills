using HarmonyLib;
using RimWorld;
using System.Collections.Generic;
using System.Reflection.Emit;
using Verse;

namespace FishingSpotsandAnglerKits
{
    [HarmonyPatch(typeof(FishingUtility), nameof(FishingUtility.GetCatchesFor))]
    public static class Patch_FishingRareMultiplier
    {
        private static readonly StatDef FishingRareMultiplierDef = StatDef.Named("FishingRareMultiplier");
        private static readonly System.Reflection.MethodInfo ChanceMethod = AccessTools.Method(typeof(Rand), nameof(Rand.Chance));

        static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> instructions)
        {
            var codes = new List<CodeInstruction>(instructions);

            for (int i = 0; i < codes.Count; i++)
            {

                if (codes[i].opcode == OpCodes.Ldc_I4 && (int)codes[i].operand == 300000)
                {
                    yield return new CodeInstruction(OpCodes.Ldc_I4_1);

                    continue;
                }


                yield return codes[i];


                if (codes[i].opcode == OpCodes.Ldc_R4 &&
                    (float)codes[i].operand == 0.01f &&
                    (i + 1 < codes.Count && codes[i + 1].Calls(ChanceMethod)))
                {

                    yield return new CodeInstruction(OpCodes.Ldarg_0); 
                    yield return new CodeInstruction(OpCodes.Call, AccessTools.Method(typeof(Patch_FishingRareMultiplier), nameof(GetMultiplier)));
                    yield return new CodeInstruction(OpCodes.Mul);     
                }
            }
        }

        public static float GetMultiplier(Pawn pawn)
        {
            if (pawn == null) return 1f;
            return pawn.GetStatValue(FishingRareMultiplierDef, true);
        }
    }
}