"""
惠和资产项目 - 高德地图地理编码 & 片区划分脚本
"""
import requests
import json
import time
import re
from pathlib import Path

KEY = 'a8459f2dbcf06e8ba5d0fbd7be7a4163'
CITY = '龙岩市'
OUTPUT_DIR = Path(__file__).parent.parent / 'output' / 'office'

# 82个项目名称
PROJECTS = [
    "东宝路（矿产）", "东肖食品站", "东肖食品老站", "中山东路（商总）",
    "中山路3期（糖酒）", "中山路（五交化）", "中山路（食品）", "九一北路（面粉加工厂）",
    "九一南路3号", "九一南路3号二层", "九一南路3号地下室", "兴晖社区",
    "凤凰北路（棉纺）", "凤凰北路（粮油）", "凤凰路（二被）", "凤凰路（矿产）",
    "凯丰商厦", "凯丰商厦（国资、惠和）", "凯丰商厦（国资）", "北环西路23号",
    "北环西路66号", "北环西路67号", "南环中路（食品）", "原交通大楼",
    "原交通大楼外墙", "原龙港公司", "双泉路（酒厂）", "和平路49号",
    "塔泉商厦（翔丰）", "塔泉大厦（翔丰）", "塔泉大厦（翔丰）龙津", "大池食品站",
    "小池食品站", "工业中路（糖酒）", "工业大厦", "工业西路(氨厂）",
    "工业西路（食品）", "工农路D14#店", "挺秀花园2#楼", "挺秀路（惠发）",
    "曹溪中路（液压）", "曹溪管理站", "沁芳轩", "溪畔路（燃料）",
    "登高东美食广场", "登高东路（惠发）", "登高中路108-1号", "登高中路108-2号",
    "登高中路（食品）", "登高西路（五交化）", "登高西路（燃料）", "矿管大楼一层（惠发）",
    "祥和家苑（化肥）", "罗龙东路220号", "罗龙东路222号", "罗龙东路（糖酒）",
    "罗龙西路（食品）", "老百货食堂大楼", "老百货食堂宿舍", "莲新南路4-2号",
    "莲新南路4-3号", "莲新南路4-4号", "莲新南路4-5号", "莲新南路（惠发）",
    "莲花大厦七层", "西安南路26-17号（国资）", "西安南路（食品）", "解放北路（农机）",
    "解放南路（商总）", "谢氨路（氨厂）", "银河商业城A幢（糖酒）", "银河商业城B幢（糖酒）",
    "闽西交易城（五交化）", "龙岩图书馆（新华书吧）", "龙川中路（五交化）", "龙川中路（商总）",
    "龙川中路（惠发）", "龙川中路（糖酒）", "龙川中路（食品）", "龙铁名苑（燃料）",
    "龙门镇（丝钉厂）", "龙门食品站",
]


def clean_project_name(name: str) -> str:
    """清理项目名: 去掉括号内的业主标注, 提取地址部分"""
    # 去掉全角/半角括号及内容
    cleaned = re.sub(r'[（(][^）)]*[）)]', '', name).strip()
    return cleaned


def extract_address_part(name: str) -> str:
    """
    从项目名中提取可用于地理编码的部分。
    策略:
    1. 如果有明确路名+门牌号, 直接用
    2. 如果只有路名, 加上'龙岩市'
    3. 如果是地标名, 直接搜索
    """
    cleaned = clean_project_name(name)

    # 如果已清理成空或无意义文本, 回退用原名
    if len(cleaned) < 2:
        return name

    # 优先级1: 看起来像地址的 (含路/街/巷/号/村/镇)
    if re.search(r'[路街巷号村镇园苑厦楼城]', cleaned):
        return f"龙岩市新罗区{cleaned}"

    # 优先级2: 地标名, 直接加龙岩市前缀
    return f"龙岩市{cleaned}"


def geocode(address: str) -> dict | None:
    """调用高德地理编码API"""
    url = 'https://restapi.amap.com/v3/geocode/geo'
    params = {
        'key': KEY,
        'address': address,
        'city': CITY,
        'batch': 'false',
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if data['status'] == '1' and int(data['count']) > 0:
            geo = data['geocodes'][0]
            return {
                'location': geo['location'],        # "lng,lat"
                'formatted_address': geo.get('formatted_address', ''),
                'province': geo.get('province', ''),
                'city': geo.get('city', ''),
                'district': geo.get('district', ''),
                'township': geo.get('township', []),
                'adcode': geo.get('adcode', ''),
                'level': geo.get('level', ''),
            }
    except Exception as e:
        print(f"  请求异常: {e}")
    return None


def reverse_geocode(lng: float, lat: float) -> dict | None:
    """逆地理编码, 获取详细行政区划"""
    url = 'https://restapi.amap.com/v3/geocode/regeo'
    params = {
        'key': KEY,
        'location': f'{lng},{lat}',
        'extensions': 'all',
        'radius': 1000,
        'roadlevel': 1,
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if data['status'] == '1':
            regeocode = data['regeocode']
            addr_comp = regeocode.get('addressComponent', {})
            return {
                'formatted_address': regeocode.get('formatted_address', ''),
                'province': addr_comp.get('province', ''),
                'city': addr_comp.get('city', ''),
                'district': addr_comp.get('district', ''),
                'township': addr_comp.get('township', ''),
                'street': addr_comp.get('streetNumber', {}).get('street', ''),
                'neighborhood': addr_comp.get('neighborhood', {}).get('name', ''),
                'adcode': addr_comp.get('adcode', ''),
                'towncode': addr_comp.get('towncode', ''),
            }
    except Exception as e:
        print(f"  逆地理异常: {e}")
    return None


def poi_search(keyword: str) -> dict | None:
    """POI关键字搜索, 作为地理编码的补充"""
    url = 'https://restapi.amap.com/v3/place/text'
    params = {
        'key': KEY,
        'keywords': keyword,
        'city': '350802',  # 新罗区adcode
        'citylimit': 'true',
        'offset': 1,
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if data['status'] == '1' and int(data['count']) > 0:
            poi = data['pois'][0]
            lng, lat = poi['location'].split(',')
            return {
                'location': poi['location'],
                'formatted_address': poi.get('address', ''),
                'name': poi.get('name', ''),
                'adcode': poi.get('adcode', ''),
                'type': poi.get('type', ''),
            }
    except Exception as e:
        print(f"  POI异常: {e}")
    return None


def geocode_with_fallback(name: str) -> dict:
    """
    三级联查策略:
    1. 清理后的地址直接地理编码
    2. 原始名称地理编码
    3. POI关键字搜索
    """
    result = {
        'project_name': name,
        'success': False,
        'source': None,
        'location': None,
        'lng': None,
        'lat': None,
        'formatted_address': '',
        'province': '',
        'city': '',
        'district': '',
        'township': '',
        'adcode': '',
        'level': '',
    }

    # 策略1: 清理后地址
    address = extract_address_part(name)
    geo = geocode(address)

    if not geo:
        # 策略2: 原始名称 + 龙岩市
        geo = geocode(f"龙岩市新罗区{clean_project_name(name)}")

    if not geo:
        # 策略3: 原始名称直接搜
        geo = geocode(f"龙岩市{name}")

    if not geo:
        # 策略4: POI关键字搜索
        poi = poi_search(clean_project_name(name))
        if poi:
            result['success'] = True
            result['source'] = 'poi'
            result['location'] = poi['location']
            lng, lat = poi['location'].split(',')
            result['lng'] = float(lng)
            result['lat'] = float(lat)
            result['formatted_address'] = poi['formatted_address']
            result['adcode'] = poi.get('adcode', '')
            return result

    if geo:
        result['success'] = True
        result['source'] = 'geocode'
        result['location'] = geo['location']
        lng, lat = geo['location'].split(',')
        result['lng'] = float(lng)
        result['lat'] = float(lat)
        result['formatted_address'] = geo['formatted_address']
        result['province'] = geo['province']
        result['city'] = geo['city']
        result['district'] = geo['district']
        if isinstance(geo.get('township'), list) and len(geo.get('township', [])) > 0:
            result['township'] = geo['township'][0]
        else:
            result['township'] = str(geo.get('township', ''))
        result['adcode'] = geo['adcode']
        result['level'] = geo['level']

    return result


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("HuiHe Asset Projects - Amap Geocoding Batch")
    print(f"Total: {len(PROJECTS)} projects")
    print("=" * 80)

    results = []
    success_count = 0
    fail_count = 0

    for i, proj in enumerate(PROJECTS, 1):
        print(f"\n[{i:2d}/82] {proj}")
        result = geocode_with_fallback(proj)

        if result['success']:
            success_count += 1
            addr_short = result['formatted_address'][:40] if result['formatted_address'] else ''
            print(f"  [OK] {result['source']}: {result['location']} | {addr_short}")
            # 逆地理获取详细行政区划
            if result['lng'] and result['lat']:
                regeo = reverse_geocode(result['lng'], result['lat'])
                if regeo:
                    result['regeo'] = regeo
                    result['township'] = regeo.get('township', result.get('township', ''))
                    result['district'] = regeo.get('district', result.get('district', ''))
                    result['adcode'] = regeo.get('adcode', result.get('adcode', ''))
                    print(f"     [区域] {regeo.get('district','')}/{regeo.get('township','')}")
        else:
            fail_count += 1
            print(f"  [FAIL] 未定位")

        results.append(result)

        # 控制API频率 (每秒不超过30次)
        if i % 10 == 0:
            time.sleep(0.1)

    # 保存原始结果
    raw_path = OUTPUT_DIR / 'geocode_raw.json'
    with open(raw_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 80}")
    print(f"Done! Success: {success_count}, Failed: {fail_count}")
    print(f"Raw data saved: {raw_path}")

    # 打印失败列表
    if fail_count > 0:
        print(f"\n[FAILED] ({fail_count} projects):")
        for r in results:
            if not r['success']:
                print(f"  - {r['project_name']}")

    return results


if __name__ == '__main__':
    main()
