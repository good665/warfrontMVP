from pathlib import Path
p=Path('skill-assets-work/BlenderSkillChecks.cs')
s=p.read_text(encoding='utf-8-sig').replace('Run();File.WriteAllText', 'Run();CombatPoolingChecks.Run();CombatContactChecks.Run();File.WriteAllText')
s=s.replace('''                scene.BeginField(new MmoSnapshot{zone="squad",instance_id="skill-rematch"},Vector2.zero);''', '''                RenderPreviews(scene,root,actor.gameObject);
                scene.BeginField(new MmoSnapshot{zone="squad",instance_id="skill-rematch"},Vector2.zero);''')
s=s.replace('''                RenderPreviews(scene,root,actor.gameObject);
                Debug.Log''', '''                Debug.Log''')
p.write_text(s,encoding='utf-8-sig')
