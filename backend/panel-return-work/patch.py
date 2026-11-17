from pathlib import Path

root=Path(__file__).parent/'unity'/'script'
def replace(name,old,new):
    path=root/name
    source=path.read_text(encoding='utf-8-sig')
    assert source.count(old)==1,(name,source.count(old),old)
    path.write_text(source.replace(old,new),encoding='utf-8-sig')

replace('MmoView.cs','        private void OpenMmoEquipment() => MmoOpenPanel("equipment");',
'''        private void CloseMmoPanel()
        {
            // Finish an in-flight save before leaving, using the existing request queue.
            if(mmoRequest){mmoPendingAction=CloseMmoPanel;return;}
            if(SquadModeActive||mmoWorld!=null){MmoLeave();return;}
            mmoPanel="";mmoPendingAction=null;mmoError="";
            mmoDodge=mmoSkill1=mmoSkill2=false;
            ClearMmoTarget();ReleaseDungeonCursor();screen=Screen.Lobby;
        }
        private void OpenMmoEquipment() => MmoOpenPanel("equipment");''')
replace('MmoView.cs','if(MmoButton(new Rect(980,145,100,35),"닫기"))mmoPanel="";',
        'if(MmoButton(new Rect(980,145,100,35),"닫기")){CloseMmoPanel();return;}')
replace('MmoEquipmentPanel.cs','if(RuneButton(new Rect(1137,31,99,34),"닫기")){mmoPanel="";return;}',
        'if(RuneButton(new Rect(1137,31,99,34),"닫기")){CloseMmoPanel();return;}')
replace('MmoControlSettings.cs','mmoSettingsFromLobby=screen==Screen.Lobby;',
        'mmoSettingsFromLobby=screen==Screen.Lobby||(!SquadModeActive&&mmoWorld==null);')
replace('MmoControlSettings.cs','if(mmoSettingsFromLobby)screen=Screen.Lobby;',
        'if(mmoSettingsFromLobby)CloseMmoPanel();')
