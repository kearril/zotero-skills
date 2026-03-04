using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Verse;

namespace FishingSpotsandAnglerKits
{
    public class CompGiveHediffOnEquip : ThingComp
    {
        private CompProperties_GiveHediffOnEquip Props => (CompProperties_GiveHediffOnEquip)props;

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
        public List<HediffDef> hediffDefs;

        public CompProperties_GiveHediffOnEquip()
        {
            compClass = typeof(CompGiveHediffOnEquip);
        }
    }
}
