using Verse;

namespace FishingSpotsandAnglerKits.Comps
{
    public class CompGiveHediffOnEquip : ThingComp
    {
        private CompProperties_GiveHediffOnEquip Props => (CompProperties_GiveHediffOnEquip)props;

        //装备时给予Hediff
        public override void Notify_Equipped(Pawn pawn)
        {
            if (this.Props == null || this.Props.hediffDefs == null)
            {
                return;
            }

            foreach (var hediffDef in this.Props.hediffDefs)
            {
                if (pawn.health.hediffSet.GetFirstHediffOfDef(hediffDef, false) == null)
                {
                    pawn.health.AddHediff(hediffDef);
                }
            }
        }

        //卸下时移除Hediff
        public override void Notify_Unequipped(Pawn pawn)
        {
            if (this.Props == null || this.Props.hediffDefs == null)
            {
                return;
            }

            foreach (var hediffDef in this.Props.hediffDefs)
            {
                Hediff hediff = pawn.health.hediffSet.GetFirstHediffOfDef(hediffDef, false);
                if (hediff != null)
                {
                    pawn.health.RemoveHediff(hediff);
                }
            }
        }
    }

    public class CompProperties_GiveHediffOnEquip : CompProperties
    {
        public List<HediffDef>? hediffDefs;

        public CompProperties_GiveHediffOnEquip()
        {
            compClass = typeof(CompGiveHediffOnEquip);
        }
    }
}
