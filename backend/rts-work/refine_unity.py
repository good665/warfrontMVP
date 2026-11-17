from pathlib import Path
p=Path('rts-work/unity/SquadStrategyView.cs')
s=p.read_text(encoding='utf-8-sig')
s=s.replace('))strategySquad="";', '))SelectStrategySquad("");').replace('))strategySquad="all";', '))SelectStrategySquad("all");').replace('))strategySquad=s.id;', '))SelectStrategySquad(s.id);')
s=s.replace('string queue="생산: ";if(st.queue!=null)foreach(var q in st.queue)queue+=StrategyKind(q.kind)+$" {q.remaining:0}s  ";', 'string queue=$"생산 {st.queue?.Length??0}/3 (차례대로): ";if(st.queue!=null)for(int i=0;i<st.queue.Length;i++){var q=st.queue[i];queue+=StrategyKind(q.kind)+(i==0?$" {q.remaining:0}s  ":$" 대기 {q.duration:0}s  ");}')
s=s.replace('"명령 거절: "+st.action_error', '"명령 거절: "+StrategyErrorLabel(st.action_error)')
s=s.replace('if(Keyboard.current!=null&&Keyboard.current.escapeKey.wasPressedThisFrame)strategyPlacement="";', '''Fill(new Rect(245,246,715,76),new Color(.025f,.04f,.075f,.92f));
            BaseText(new Rect(255,248,695,22),"선택: "+StrategySelectionLabel(st)+(StrategySelectionLocked?" · 명령 전송 대기":""),12,baseCyan);
            BaseText(new Rect(255,270,695,22),"병영: 생산 가속 · 전초기지: 시야 · 방어탑: 주변 받는 피해 감소 (자동 공격 없음)",12,baseMuted);
            BaseText(new Rect(255,292,695,22),"정찰 연구: 시야 +120 · 수호병: 궁수 피해 감소 · 궁수: 치유사에 추가 피해 · 정찰병: 낮은 체력",11,baseMuted);
            DrawStrategyBuildingLabels();
            if(Keyboard.current!=null&&Keyboard.current.escapeKey.wasPressedThisFrame)strategyPlacement="";''')
p.write_text(s,encoding='utf-8-sig')
p=Path('rts-work/unity/DungeonFirstPersonView.cs')
s=Path('C:/Users/good6/WarfrontMVP/Assets/script/DungeonFirstPersonView.cs').read_text(encoding='utf-8-sig')
s=s.replace('enemy.kind=="base"?3.2f:enemy.kind=="boss"?2.1f:1.35f', 'enemy.kind=="base"?3.2f:SquadModeActive&&StrategyBuildingKind(enemy.kind)?2.5f:enemy.kind=="boss"?2.1f:1.35f')
s=s.replace('enemy.name,12,Color.white', 'SquadModeActive&&StrategyBuildingKind(enemy.kind)?StrategyKind(enemy.kind):enemy.name,12,Color.white')
p.write_text(s,encoding='utf-8-sig')
