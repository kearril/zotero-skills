using System.Reflection.Emit;
using HarmonyLib;
using RimWorld;
using UnityEngine;
using Verse;

namespace FishingSpotsandAnglerKits.Harmony
{
    //修补钓鱼稀有物品的掉落概率，使其受角色属性影响
    //修补出稀有物品的冷却时间，将其移除
    [HarmonyPatch(typeof(FishingUtility), nameof(FishingUtility.GetCatchesFor))]
    public static class Patch_FishingRareMultiplier
    {
        private static readonly StatDef FishingRareMultiplierDef =
            DefDatabase<StatDef>.GetNamed("FishingRareMultiplier");

        private static readonly System.Reflection.MethodInfo ChanceMethod =
            AccessTools.Method(typeof(Rand), nameof(Rand.Chance));

        public static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> instructions)
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
                    Mathf.Approximately((float)codes[i].operand, 0.01f) &&
                    (i + 1 < codes.Count && codes[i + 1].Calls(ChanceMethod)))
                {
                    yield return new CodeInstruction(OpCodes.Ldarg_0);
                    yield return new CodeInstruction(OpCodes.Call,
                        AccessTools.Method(typeof(Patch_FishingRareMultiplier), nameof(GetMultiplier)));
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