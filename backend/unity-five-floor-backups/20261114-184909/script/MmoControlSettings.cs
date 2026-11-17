using System;
using UnityEngine;
using UnityEngine.InputSystem;
namespace Warfront
{
    [Serializable] public sealed class MmoTouchPreference
    {
        public float x,y,scale=1;
    }
    [Serializable] public sealed class MmoPlaySettings
    {
        public float mouse=1,touch=1,distance=5.6f,volume=.65f,strategicZoom=11;
        public bool invertY,sound=true;
        public MmoTouchPreference[] controls;
    }
    public sealed partial class GameBootstrap
    {
        private const string MmoSettingsKey="warfront.playSettings.v2";
        private MmoPlaySettings mmoSettings,mmoSettingsDraft;
        private int mmoSettingsTab,mmoSelectedControl;
        private bool mmoSettingsFromLobby;
        private bool mmoImpactAudio=true;
        private float mmoImpactVolume=.65f;
        private string mmoSettingsError="";
        private static readonly string[] MmoControlNames={"이동 패드","","공격","회피","폭발 룬","회복"};
        private static Rect MmoDefaultControl(int index)
        {
            switch(index)
            {
                case 0:return new Rect(35,604,150,96);
                case 1:return new Rect(550,604,120,80);
                case 2:return new Rect(374,608,126,80);
                case 3:return new Rect(506,608,126,80);
                case 4:return new Rect(638,608,126,80);
                default:return new Rect(770,608,126,80);
            }
        }
        private static MmoPlaySettings MmoDefaultSettings()
        {
            var value=new MmoPlaySettings{controls=new MmoTouchPreference[6]};
            for(int i=0;i<6;i++){var rect=MmoDefaultControl(i);value.controls[i]=new MmoTouchPreference{x=rect.center.x,y=rect.center.y};}
            return value;
        }
        private static float MmoSettingValue(float value,float min,float max,float fallback)=>float.IsNaN(value)||float.IsInfinity(value)?fallback:Mathf.Clamp(value,min,max);
        private static Rect MmoSettingsControl(MmoPlaySettings value,int index)
        {
            var pref=value.controls[index];var original=MmoDefaultControl(index);
            return new Rect(pref.x-original.width*pref.scale*.5f,pref.y-original.height*pref.scale*.5f,original.width*pref.scale,original.height*pref.scale);
        }
        private static bool MmoLayoutValid(MmoPlaySettings value)
        {
            for(int i=0;i<6;i++)
            {
                if(i==1)continue; // Reserved legacy preference slot; target lock was removed.
                var rect=MmoSettingsControl(value,i);
                if(rect.xMin<20||rect.xMax>924||rect.yMin<594||rect.yMax>704)return false;
                if(rect.Overlaps(new Rect(198,600,166,96)))return false;
                for(int j=0;j<i;j++)
                {
                    if(j==1)continue;
                    var other=MmoSettingsControl(value,j);other.xMin-=3;other.yMin-=3;other.xMax+=3;other.yMax+=3;
                    if(rect.Overlaps(other))return false;
                }
            }
            return true;
        }
        private static MmoPlaySettings MmoNormalizeSettings(MmoPlaySettings value,bool repairLayout)
        {
            if(value==null)value=MmoDefaultSettings();
            value.mouse=MmoSettingValue(value.mouse,.25f,3,1);value.touch=MmoSettingValue(value.touch,.25f,3,1);
            value.distance=MmoSettingValue(value.distance,3.5f,8,5.6f);value.volume=MmoSettingValue(value.volume,0,1,.65f);
            value.strategicZoom=MmoSettingValue(value.strategicZoom<=0?11:value.strategicZoom,7.5f,14,11);
            var defaults=MmoDefaultSettings();
            if(value.controls==null||value.controls.Length!=6)value.controls=defaults.controls;
            for(int i=0;i<6;i++)
            {
                if(value.controls[i]==null)value.controls[i]=defaults.controls[i];
                var p=value.controls[i];var rect=MmoDefaultControl(i);
                p.scale=MmoSettingValue(p.scale,.75f,Mathf.Min(1.35f,110/rect.height),1);
                p.x=MmoSettingValue(p.x,20+rect.width*p.scale*.5f,924-rect.width*p.scale*.5f,defaults.controls[i].x);
                p.y=MmoSettingValue(p.y,594+rect.height*p.scale*.5f,704-rect.height*p.scale*.5f,defaults.controls[i].y);
            }
            if(repairLayout&&!MmoLayoutValid(value))value.controls=defaults.controls;
            return value;
        }
        private void EnsureMmoSettings()
        {
            if(mmoSettings!=null)return;
            try{mmoSettings=MmoNormalizeSettings(JsonUtility.FromJson<MmoPlaySettings>(PlayerPrefs.GetString(MmoSettingsKey,"")),true);}
            catch(ArgumentException){mmoSettings=MmoDefaultSettings();}
            ApplyMmoSettings();
        }
        private void ApplyMmoSettings()
        {
            dungeonDistance=mmoSettings.distance;strategicZoom=mmoSettings.strategicZoom;mmoImpactAudio=mmoSettings.sound;mmoImpactVolume=mmoSettings.volume;
        }
        private Rect MmoControlRect(int index)
        {
            EnsureMmoSettings();return MmoSettingsControl(mmoPanel=="controls"&&mmoSettingsDraft!=null?mmoSettingsDraft:mmoSettings,index);
        }
        private bool MmoNavigationPointer(Vector2 point)=>SquadModeActive?SquadOverlayPointer(point):mmoWorld!=null&&new Rect(mmoField.x+10,mmoField.y+10,192,223).Contains(point);
        private void ApplyMmoLookDelta(Vector2 delta,bool touch)
        {
            EnsureMmoSettings();
            float sensitivity=(touch?.15f:.12f)*(touch?mmoSettings.touch:mmoSettings.mouse);
            dungeonYaw=Mathf.Repeat(dungeonYaw+delta.x*sensitivity,360);
            dungeonPitch=Mathf.Clamp(dungeonPitch-delta.y*sensitivity*(mmoSettings.invertY?-1:1),-35,48);
        }
        private void UpdateMmoTouchLook()
        {
            if(Touchscreen.current==null){mmoLookTouchId=-1;return;}
            foreach(var touch in Touchscreen.current.touches)
            {
                var point=MmoUiPoint(touch.position.ReadValue());
                if(!touch.press.isPressed||!mmoField.Contains(point)||point.x<=mmoField.center.x||DungeonPointerBlocked(point))continue;
                int id=touch.touchId.ReadValue();
                if(mmoLookTouchId<0)mmoLookTouchId=id;
                if(mmoLookTouchId==id){ApplyMmoLookDelta(touch.delta.ReadValue(),true);return;}
            }
            mmoLookTouchId=-1;
        }
        private void OpenMmoControlSettings()
        {
            EnsureMmoSettings();ClearMmoTarget();ReleaseDungeonCursor();
            mmoSettingsFromLobby=screen==Screen.Lobby||(!SquadModeActive&&mmoWorld==null);
            mmoSettingsDraft=JsonUtility.FromJson<MmoPlaySettings>(JsonUtility.ToJson(mmoSettings));
            mmoSettingsError="";mmoSettingsTab=0;mmoPanel="controls";screen=Screen.Mmo;
            mmoDodge=mmoSkill1=mmoSkill2=false;
        }
        private void CloseMmoControlSettings()
        {
            mmoSettingsDraft=null;mmoSettingsError="";mmoPanel="";
            if(mmoSettingsFromLobby)CloseMmoPanel();
        }
        private void SaveMmoControlSettings()
        {
            MmoNormalizeSettings(mmoSettingsDraft,false);
            if(!MmoLayoutValid(mmoSettingsDraft)){mmoSettingsError="버튼이 겹칩니다. 미리보기에서 간격을 벌려 주세요.";return;}
            mmoSettings=JsonUtility.FromJson<MmoPlaySettings>(JsonUtility.ToJson(mmoSettingsDraft));
            PlayerPrefs.SetString(MmoSettingsKey,JsonUtility.ToJson(mmoSettings));PlayerPrefs.Save();ApplyMmoSettings();CloseMmoControlSettings();
        }
        private float MmoSettingsSlider(Rect rect,string title,float value,float min,float max,string suffix="")
        {
            BaseText(new Rect(rect.x,rect.y,rect.width,23),title+" · "+value.ToString("0.00")+suffix,15,baseText);
            return GUI.HorizontalSlider(new Rect(rect.x,rect.y+30,rect.width,24),value,min,max);
        }
        private void DrawMmoControlSettings()
        {
            if(mmoSettingsDraft==null){CloseMmoControlSettings();return;}
            Fill(new Rect(0,120,1280,470),new Color(0,0,0,.84f));Panel(new Rect(170,130,940,455));
            BaseText(new Rect(200,144,600,36),"시점 · 소리 · 터치 조작 설정",25,baseGold);
            if(GUI.Button(new Rect(200,187,420,33),"시점 · 소리"))mmoSettingsTab=0;
            if(GUI.Button(new Rect(635,187,420,33),"터치 버튼 배치"))mmoSettingsTab=1;
            var draft=mmoSettingsDraft;
            if(mmoSettingsTab==0)
            {
                if(SquadModeActive)
                {
                    draft.strategicZoom=MmoSettingsSlider(new Rect(210,238,390,60),"고정 사선 시점 · 확대/축소",draft.strategicZoom,7.5f,14);
                    BaseText(new Rect(650,238,390,60),"시점 방향은 고정됩니다.\n전장에서 휠로 확대·축소할 수 있습니다.",14,baseMuted);
                    BaseText(new Rect(210,322,390,60),"마우스는 조준에 사용합니다.\nWASD 이동 · 좌클릭 공격 · Q/E 스킬",14,baseText);
                }
                else
                {
                    draft.mouse=MmoSettingsSlider(new Rect(210,238,390,60),"마우스 시점 감도",draft.mouse,.25f,3,"배");
                    draft.touch=MmoSettingsSlider(new Rect(650,238,390,60),"터치 시점 감도",draft.touch,.25f,3,"배");
                    draft.distance=MmoSettingsSlider(new Rect(210,322,390,60),"기본 카메라 거리",draft.distance,3.5f,8);
                    draft.invertY=GUI.Toggle(new Rect(210,410,390,32),draft.invertY,"상하 시점 반전 (마우스 · 터치)");
                }
                draft.volume=MmoSettingsSlider(new Rect(650,322,390,60),"타격음 음량",draft.volume,0,1);
                draft.sound=GUI.Toggle(new Rect(650,410,390,32),draft.sound,"타격음 사용");
                BaseText(new Rect(210,455,830,28),"저장 후 적용 · 취소 시 기존 설정 유지 · 설정 중에도 전투는 계속됩니다.",14,baseMuted);
            }
            else
            {
                int[] visibleControls={0,2,3,4,5};
                if(mmoSelectedControl==1)mmoSelectedControl=0;
                for(int n=0;n<visibleControls.Length;n++){int i=visibleControls[n];string title=SquadModeActive&&i>=4?(i==4?"Q 스킬":"E 필살기"):MmoControlNames[i];if(GUI.Button(new Rect(204+n*172,233,165,35),(i==mmoSelectedControl?"● ":"")+title))mmoSelectedControl=i;}
                var pref=draft.controls[mmoSelectedControl];var original=MmoDefaultControl(mmoSelectedControl);
                pref.scale=MmoSettingsSlider(new Rect(210,287,390,60),"버튼 크기",pref.scale,.75f,Mathf.Min(1.35f,110/original.height),"배");
                pref.x=MmoSettingsSlider(new Rect(650,287,390,60),"가로 위치",pref.x,20+original.width*pref.scale*.5f,1260-original.width*pref.scale*.5f);
                pref.y=MmoSettingsSlider(new Rect(210,371,390,60),"세로 위치",pref.y,594+original.height*pref.scale*.5f,704-original.height*pref.scale*.5f);
                MmoNormalizeSettings(draft,false);
                BaseText(new Rect(650,379,390,66),"아래 조작 영역에서 배치를 미리 봅니다.\n각 버튼을 골라 크기와 위치를 조절하세요.",14,baseMuted);
                bool valid=MmoLayoutValid(draft);
                BaseText(new Rect(210,455,830,28),valid?"배치 가능 · 버튼은 화면 밖으로 나가지 않습니다.":"버튼이 겹칩니다. 가로 위치를 바꿔 간격을 벌려 주세요.",14,valid?baseCyan:baseGold);
                var selected=MmoSettingsControl(draft,mmoSelectedControl);
                Fill(new Rect(selected.x,selected.y,selected.width,3),baseGold);Fill(new Rect(selected.x,selected.yMax-3,selected.width,3),baseGold);
            }
            BaseText(new Rect(210,487,830,24),mmoSettingsError,13,baseGold);
            if(GUI.Button(new Rect(210,530,250,37),"기본값으로 복원")){mmoSettingsDraft=MmoDefaultSettings();mmoSettingsError="";}
            if(GUI.Button(new Rect(510,530,250,37),"취소"))CloseMmoControlSettings();
            bool enabled=GUI.enabled;GUI.enabled=enabled&&MmoLayoutValid(mmoSettingsDraft??draft);
            if(GUI.Button(new Rect(810,530,250,37),"저장하고 적용"))SaveMmoControlSettings();
            GUI.enabled=enabled;
        }
    }
}


