"""Match-only zodiac characters. Values are owned by the authoritative simulation."""

ZODIAC = {
    'rat': dict(name='쥐', q='재빠른 돌진', e='무리의 습격', q_kind='dash', e_kind='burst', q_power=24, e_power=58),
    'ox': dict(name='소', q='뿔 들이받기', e='대지의 울림', q_kind='dash', e_kind='stun', q_power=34, e_power=52),
    'tiger': dict(name='호랑이', q='맹호의 발톱', e='호랑이 포효', q_kind='cone', e_kind='fear', q_power=42, e_power=48),
    'rabbit': dict(name='토끼', q='달빛 회복', e='보름달 보호', q_kind='heal', e_kind='shield', q_power=30, e_power=80),
    'dragon': dict(name='용', q='화염 숨결', e='천룡의 분노', q_kind='cone', e_kind='meteor', q_power=38, e_power=76),
    'snake': dict(name='뱀', q='독니', e='맹독 안개', q_kind='poison', e_kind='venom', q_power=20, e_power=30),
    'horse': dict(name='말', q='질주', e='기병의 돌격', q_kind='speed', e_kind='charge', q_power=0, e_power=64),
    'goat': dict(name='양', q='바위 방패', e='초원의 축복', q_kind='shield', e_kind='heal', q_power=38, e_power=65),
    'monkey': dict(name='원숭이', q='여의봉', e='회전 봉술', q_kind='line', e_kind='spin', q_power=36, e_power=60),
    'rooster': dict(name='닭', q='깃털 사격', e='여명의 울음', q_kind='line', e_kind='rally', q_power=36, e_power=35),
    'dog': dict(name='개', q='추적의 이빨', e='수호자의 결의', q_kind='slow', e_kind='guard', q_power=32, e_power=45),
    'pig': dict(name='돼지', q='몸통 박치기', e='튼튼한 배짱', q_kind='dash', e_kind='fortify', q_power=32, e_power=65),
}
