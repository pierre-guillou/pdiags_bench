using Eirene

C = eirene("eirene.csv",model="complex",entryformat="ev")
plotbarcode_pjs(C,dim=1)
plotpersistencediagram_pjs(C,dim=1)
