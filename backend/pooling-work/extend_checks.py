from pathlib import Path
p=Path('pooling-work/CombatPoolingChecks.cs')
s=p.read_text(encoding='utf-8-sig')
s=s.replace('Debug.Log("COMBAT_POOLING_CHECKS PASS:', '''var burst=new MmoProjectile[80];for(int i=0;i<burst.Length;i++)burst[i]=new MmoProjectile{id=100+i,end_x=400,flight=1};
                scene.SquadProjectiles(burst,0);scene.SquadProjectiles(null,0);
                var storage=root.transform.Find("Combat visual pool");Check(storage!=null&&storage.childCount<=192,"Idle pool retained unbounded burst objects");
                int arrows=0;foreach(Transform child in storage)if(child.name.StartsWith("Authoritative arrow"))arrows++;
                Check(arrows==64,"Arrow idle retention did not respect cap");
                Debug.Log("COMBAT_POOLING_CHECKS PASS:''')
p.write_text(s,encoding='utf-8-sig')
