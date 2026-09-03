#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_pbf_v13.py — PitchforkBent_SpeedBoost v1.3.0 构建
=================================================================
在 v1.2.0（MI_Sword 纹理 + 握持修正）基础上，v1.3.0 主人三项新指示：
A. 剑缩小 20%：ItemMesh0.RelativeScale3D 1.2 → 0.96（现显示为草叉原版 1.2x）
B. 柄再下移半个剑柄：ItemMesh0.RelativeLocation.Z -25 → -15（掌心落柄中部）
C. 碰撞/声音/伤害/攻速全面剑化（对齐 2H_Katana 双手剑基准）：
   - 攻击碰撞胶囊尺寸/旋转 → 2H_Katana（两个 MeleeAttackCollisionCapsule）
   - RowName 2H_Pitchfork_Bent → 2H_Katana（查剑行伤害/冲击/音效表）
   - DamageOnUse 0.8 → 0.2；CombatAnimationPlayRateModifier 0.93 → 1.06（攻速）
   - 投掷 WeaponDesc：Damage 30→80、SharpnessSlash 0.2→1.0、注入 ImpactSoundCategory=Sharp_Metal
   - 动画预设 Weapons_2H_Spear → Weapons_2H_Swords（挥砍动作+攻速）
   - FP 动画 DA_Generic_2H1_Melee_rework_2 → DA_Generic_2H1_Melee_rework
   - 取放音 Inventory_Handling_Axe → Inventory_Handling_Knife（剑类）
   - 武器标签钝器 Blunt* → 刃器 Sharp*（损伤类型/修理判刃器）
   - 投掷 Bounciness 0 → 0.03
"""
import json, os, shutil, subprocess, sys

MOD_NAME = "PitchforkBent_SpeedBoost"
MOD_ROOT = r"W:\hermes\SCUM_MOD\PitchforkBent_SpeedBoost"
PAK = os.path.join(MOD_ROOT, MOD_NAME + ".pak")
FM = r"R:\Program Files\SCUMMod\Output\Exports\SCUM\Content\ConZ_Files"
UACLI = r"W:/hermes/UAssetCLI/UAssetCLI/UAssetCLI.dll"
DOTNET = r"C:\Program Files\dotnet\dotnet"
REPAK = r"C:/Users/Administrator/.cargo/bin/repak"
ENGINE = "VER_UE4_27"
TMP = r"C:\tmp"
BASE = os.path.join(TMP, "thornblade", "extract_v18")
STAGING = os.path.join(TMP, "pf_v13_staging")
JWORK = os.path.join(TMP, "pf_v13_json")

SRC_PATHS = {
    "cdp": r"SCUM/Content/ConZ_Files/Items/Weapons/New_Melee/2H_Pitchfork_Bent.uasset",
    "es": r"SCUM/Content/ConZ_Files/Items/Weapons/New_Melee/2H_Pitchfork_Bent_ES.uasset",
    "mesh": r"SCUM/Content/ConZ_Files/Models/Objects/Items/Pitchfork_bent/SM_Pitchfork_bent.uasset",
    "mat": r"SCUM/Content/LunaPort/Thornblade/Sword.uasset",
    "tex_base": r"SCUM/Content/LunaPort/Thornblade/Sword_low_Sword_BaseColor.uasset",
    "tex_nrm": r"SCUM/Content/LunaPort/Thornblade/Sword_low_Sword_Normal.uasset",
    "tex_rgh": r"SCUM/Content/LunaPort/Thornblade/Sword_low_Sword_Roughness.uasset",
}


def dotnet(*args):
    r = subprocess.run([DOTNET, UACLI] + list(args), capture_output=True, text=True, timeout=240)
    return r.returncode, r.stdout, r.stderr


def tojson(u, j):
    rc, _, err = dotnet("tojson", u, j, ENGINE)
    if rc != 0:
        print(f"✗ tojson {u}: {err[:300]}"); sys.exit(1)


def fromjson(j, u):
    os.makedirs(os.path.dirname(u), exist_ok=True)
    rc, _, err = dotnet("fromjson", j, u, u.replace(".uasset", ".uexp"), ENGINE)
    if rc != 0:
        print(f"✗ fromjson {j}: {err[:300]}")
        sys.exit(1)


def load(j):
    with open(j, encoding="utf-8") as f:
        return json.load(f)


def dump(j, d):
    with open(j, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def need(base_file):
    src = os.path.join(BASE, base_file)
    if not os.path.exists(src):
        print(f"✗ 缺失 v1.1.0 解包文件 {src}"); sys.exit(1)
    return src


def deep_swap(node, pairs):
    """把 dict 值 / 列表元素中的 str（含纯字符串列表如 NameMap）按 pairs(旧->新) 替换。"""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and v in pairs:
                node[k] = pairs[v]
            else:
                deep_swap(v, pairs)
    elif isinstance(node, list):
        for i, it in enumerate(node):
            if isinstance(it, str) and it in pairs:
                node[i] = pairs[it]
            else:
                deep_swap(it, pairs)


def ensure_names(d, names):
    added = 0
    for n in names:
        if n not in d["NameMap"]:
            d["NameMap"].append(n)
            added += 1
    if added:
        d["Generations"][0]["NameCount"] = len(d["NameMap"])


def main():
    for dd in (STAGING, JWORK):
        if os.path.exists(dd):
            shutil.rmtree(dd)
        os.makedirs(dd)

    # ---------- 1) mesh：同 v1.2（Grip Z 5 + 槽→MI_Sword） ----------
    mesh_src = need(SRC_PATHS["mesh"])
    mesh_j = os.path.join(JWORK, "mesh.json")
    tojson(mesh_src, mesh_j)
    mesh = load(mesh_j)
    done = False
    for e in mesh["Exports"]:
        if str(e.get("ObjectName", "")).startswith("StaticMeshSocket"):
            grip = any(p.get("Name") == "SocketName" and p.get("Value") == "Grip" for p in e.get("Data", []))
            if grip and not done:
                done = True
                for q in e["Data"]:
                    if q.get("Name") == "RelativeLocation":
                        q["Value"][0]["Value"]["Z"] = 5.0
    if not done:
        print("✗ mesh: Grip 未找"); sys.exit(1)
    if "MaterialInstanceConstant" not in mesh["NameMap"]:
        mesh["NameMap"].append("MaterialInstanceConstant")
        mesh["Generations"][0]["NameCount"] = len(mesh["NameMap"])
    imps = mesh["Imports"]
    if imps[4]["ObjectName"] != "Sword":
        print("✗ mesh import[4] 意外"); sys.exit(1)
    imps[4]["ObjectName"] = "MI_Sword"
    imps[4]["ClassName"] = "MaterialInstanceConstant"
    imps[6]["ObjectName"] = "/Game/LunaPort/Thornblade/MI_Sword"
    deep_swap(mesh["NameMap"], {"/Game/LunaPort/Thornblade/Sword": "/Game/LunaPort/Thornblade/MI_Sword", "Sword": "MI_Sword"})
    for e in mesh["Exports"]:
        deep_swap(e.get("Data", []), {"Sword": "MI_Sword",
                                      "/Game/LunaPort/Thornblade/Sword": "/Game/LunaPort/Thornblade/MI_Sword"})
    dump(os.path.join(JWORK, "mesh_mod.json"), mesh)
    fromjson(os.path.join(JWORK, "mesh_mod.json"), os.path.join(STAGING, SRC_PATHS["mesh"]))

    # ---------- 2) CDO：v1.3 剑化 ----------
    cdp_src = need(SRC_PATHS["cdp"])
    cdp_j = os.path.join(JWORK, "cdp.json")
    tojson(cdp_src, cdp_j)
    cdp = load(cdp_j)

    # 2a. ItemMesh0：缩放 0.96 + RelLoc.Z -15
    for e in cdp["Exports"]:
        if e.get("ObjectName") != "ItemMesh0":
            continue
        for p in e["Data"]:
            if p.get("Name") == "RelativeScale3D":
                v = p["Value"][0]["Value"] if isinstance(p["Value"], list) and "Value" in p["Value"][0] else p["Value"]
                if isinstance(v, dict) and "X" in v:
                    v["X"] = v["Y"] = v["Z"] = 0.96
                print("  [cdp] ItemMesh0.RelativeScale3D = 0.96")
            if p.get("Name") == "RelativeLocation":
                p["Value"][0]["Value"]["Z"] = -15.0
                print("  [cdp] ItemMesh0.RelativeLocation.Z = -15（已存在，改值）")
        # 注入 RelativeLocation（若缺失：柄再下移）
        has_rel = any(p.get("Name") == "RelativeLocation" for p in e["Data"])
        if not has_rel:
            e["Data"].append({
                "$type": "UAssetAPI.PropertyTypes.Structs.StructPropertyData, UAssetAPI",
                "StructType": "Vector",
                "SerializeNone": True,
                "StructGUID": "{00000000-0000-0000-0000-000000000000}",
                "SerializationControl": "NoExtension",
                "Operation": "None",
                "Name": "RelativeLocation",
                "ArrayIndex": 0, "IsZero": False,
                "PropertyTagFlags": "None",
                "PropertyTypeName": None,
                "PropertyTagExtensions": "NoExtension",
                "Value": [{
                    "$type": "UAssetAPI.PropertyTypes.Structs.VectorPropertyData, UAssetAPI",
                    "Name": "RelativeLocation",
                    "ArrayIndex": 0, "IsZero": False,
                    "PropertyTagFlags": "None",
                    "PropertyTypeName": None,
                    "PropertyTagExtensions": "NoExtension",
                    "Value": {"$type": "UAssetAPI.UnrealTypes.FVector, UAssetAPI",
                              "X": 0.0, "Y": 0.0, "Z": -15.0}
                }]
            })
            print("  [cdp] ItemMesh0: 注入 RelativeLocation = (0, 0, -15)（柄再下移）")
    # 2b. DamageOnUse 0.8 -> 0.2
    for e in cdp["Exports"]:
        if e.get("ObjectName") == "DamageOnUseTag_0":
            for p in e.get("Data", []):
                if p.get("Name") == "DamageOnUse":
                    p["Value"] = 0.2
                    print("  [cdp] DamageOnUse 0.8 → 0.2")
    # 2c/2d. 攻击碰撞胶囊尺寸 + RowName
    cap = {
        "MeleeAttackCollisionCapsule1_GEN_VARIABLE": (17.95406150817871, 2.603053092956543),
        "MeleeAttackCollisionCapsule_GEN_VARIABLE": (42.04141616821289, 2.7007009983062744),
    }
    for e in cdp["Exports"]:
        nm = e.get("ObjectName")
        if nm in cap:
            hh, rr = cap[nm]
            for p in e.get("Data", []):
                if p.get("Name") == "CapsuleHalfHeight":
                    p["Value"] = hh
                if p.get("Name") == "CapsuleRadius":
                    p["Value"] = rr
                if p.get("Name") == "RowName":
                    p["Value"] = "2H_Katana"
            # 递归：_weaponDescRef.DataTable.RowName（攻击伤害行）
            def _fix_row(node):
                if isinstance(node, dict):
                    if node.get("Name") == "RowName":
                        node["Value"] = "2H_Katana"
                    for v in node.values():
                        _fix_row(v)
                elif isinstance(node, list):
                    for v in node:
                        _fix_row(v)
            _fix_row(e.get("Data", []))
            print(f"  [cdp] {nm}: 胶囊 {hh:.2f}/{rr:.2f}, RowName→2H_Katana（_weaponDescRef 伤害行）")
    # 2e. 攻速倍率
    for e in cdp["Exports"]:
        if e.get("ObjectName") == "MeleeWeaponItemTag_0":
            for p in e.get("Data", []):
                if p.get("Name") == "CombatAnimationPlayRateModifier":
                    p["Value"] = 1.06
                    print("  [cdp] CombatAnimationPlayRateModifier 0.93 → 1.06（攻速 ↑）")
    # 2f. 投掷 WeaponDesc 结构：Damage/SharpnessSlash/注入 ImpactSoundCategory
    for e in cdp["Exports"]:
        if e.get("ObjectName") == "ThrowableItemTag_0":
            def mutate(node):
                if isinstance(node, dict):
                    if node.get("Name") == "Damage" and node.get("Value") == 30.0:
                        node["Value"] = 80.0
                        print("  [cdp] 投掷 Damage 30 → 80")
                    if node.get("Name") == "SharpnessSlash":
                        node["Value"] = 1.0
                        print("  [cdp] SharpnessSlash 0.2 → 1.0")
                    for v in node.values():
                        mutate(v)
                elif isinstance(node, list):
                    for v in node:
                        mutate(v)
            mutate(e.get("Data", []))
            # 找 WeaponDesc 结构顶层 Struct 并追加 ImpactSoundCategory
            for p in e.get("Data", []):
                if p.get("Name") == "WeaponDesc":
                    val = p.get("Value")
                    has = False

                    def hasc(node):
                        nonlocal has
                        if isinstance(node, dict):
                            if node.get("Name") == "ImpactSoundCategory":
                                has = True
                            for v in node.values():
                                hasc(v)
                        elif isinstance(node, list):
                            for v in node:
                                hasc(v)
                    hasc(val)
                    if not has:
                        val.append({
                            "$type": "UAssetAPI.PropertyTypes.Objects.EnumPropertyData, UAssetAPI",
                            "EnumType": "ECharacterImpactSourceSoundCategory",
                            "InnerType": None,
                            "Name": "ImpactSoundCategory",
                            "ArrayIndex": 0, "IsZero": False,
                            "PropertyTagFlags": "None",
                            "PropertyTypeName": None,
                            "PropertyTagExtensions": "NoExtension",
                            "Value": "ECharacterImpactSourceSoundCategory::Sharp_Metal",
                        })
                        print("  [cdp] 注入 ImpactSoundCategory = Sharp_Metal（命中金属声）")
    # 2g. 投掷 Bounciness
    for e in cdp["Exports"]:
        if e.get("ObjectName") == "ThrowingComponent":
            for p in e.get("Data", []):
                if p.get("Name") == "Bounciness":
                    p["Value"] = 0.03
                    print("  [cdp] Bounciness 0 → 0.03")
    # 2h. import 替换（剑化引用）
    imp_swaps = {  # 对象名： (旧, 新) —— 也换包路径 + class
        "Inventory_Handling_Axe": "Inventory_Handling_Knife",
        "Weapons_2H_Spear": "Weapons_2H_Swords",
        "DA_Generic_2H1_Melee_rework_2": "DA_Generic_2H1_Melee_rework",
        "BluntMeleeWeaponRepairable": "SharpMeleeWeaponRepairable",
        "BluntMeleeWeapon": "SharpMeleeWeapon",
    }
    pkg_swaps = {
        "/Game/WwiseAudio/Event/DefaultWorkUnit/Player/Inventory_Handling_Axe": "/Game/WwiseAudio/Event/DefaultWorkUnit/Player/Inventory_Handling_Knife",
        "/Game/ConZ_Files/Skills/MeleeAnimationPresets/Weapons_2H_Spear": "/Game/ConZ_Files/Skills/MeleeAnimationPresets/Weapons_2H_Swords",
        "/Game/ConZ_Files/Data/ItemFirstPersonAnimations/DA_Generic_2H1_Melee_rework_2": "/Game/ConZ_Files/Data/ItemFirstPersonAnimations/DA_Generic_2H1_Melee_rework",
        "/Game/ConZ_Files/Items/Tags/Repair/BluntMeleeWeaponRepairable": "/Game/ConZ_Files/Items/Tags/Repair/SharpMeleeWeaponRepairable",
        "/Game/ConZ_Files/Items/Tags/Melee/Blunt": "/Game/ConZ_Files/Items/Tags/Melee/Blade",
        "/Game/ConZ_Files/Items/Tags/Weapons/BluntMeleeWeapon": "/Game/ConZ_Files/Items/Tags/Weapons/SharpMeleeWeapon",
    }
    for i, im in enumerate(cdp["Imports"]):
        on = im["ObjectName"]
        if on in imp_swaps:
            im["ObjectName"] = imp_swaps[on]
        if on in pkg_swaps:
            im["ObjectName"] = pkg_swaps[on]
        if on == "BluntMeleeWeapon" and im["ClassName"] == "BluntMeleeWeaponItemTag":
            im["ClassName"] = "SharpMeleeWeaponItemTag"
    # NameMap：旧串换新 + 新名补齐
    deep_swap(cdp["NameMap"], dict(imp_swaps))
    deep_swap(cdp["NameMap"], dict(pkg_swaps))
    ensure_names(cdp, list(imp_swaps.values()) + list(pkg_swaps.values()) +
                 ["SharpMeleeWeaponItemTag", "2H_Katana", "ImpactSoundCategory",
                  "ECharacterImpactSourceSoundCategory",
                  "ECharacterImpactSourceSoundCategory::Sharp_Metal"])
    ensure_names(cdp, ["RelativeLocation", "Vector", "FVector"])
    for e in cdp["Exports"]:
        deep_swap(e.get("Data", []), dict(imp_swaps))
        deep_swap(e.get("Data", []), dict(pkg_swaps))
    dump(os.path.join(JWORK, "cdp_mod.json"), cdp)
    fromjson(os.path.join(JWORK, "cdp_mod.json"), os.path.join(STAGING, SRC_PATHS["cdp"]))

    # ---------- 3) 其余原样拷贝 ----------
    for base_p in [SRC_PATHS[k][:-7] for k in ("es", "tex_base", "tex_nrm", "tex_rgh")]:
        for ext in (".uasset", ".uexp", ".ubulk"):
            srcf = os.path.join(BASE, base_p + ext)
            if not os.path.exists(srcf):
                continue
            dstf = os.path.join(STAGING, base_p + ext)
            os.makedirs(os.path.dirname(dstf), exist_ok=True)
            shutil.copy2(srcf, dstf)
    mat_base = SRC_PATHS["mat"][:-7]
    for ext in (".uasset", ".uexp"):
        srcf = os.path.join(BASE, mat_base + ext)
        if os.path.exists(srcf):
            shutil.copy2(srcf, os.path.join(STAGING, mat_base + ext))

    # ---------- 4) MI_Sword（同 v1.2，从原版 MI 深拷贝） ----------
    mi_src = os.path.join(FM, "Models/Objects/Items/Pitchfork_bent/Materials/MI_Pitchfork_bent.uasset")
    if not os.path.exists(mi_src):
        print("✗ 缺 MI_Pitchfork_bent"); sys.exit(1)
    mi_j = os.path.join(JWORK, "mi.json")
    tojson(mi_src, mi_j)
    mi = load(mi_j)
    for e in mi["Exports"]:
        if e.get("ObjectName") == "MI_Pitchfork_bent":
            e["ObjectName"] = "MI_Sword"
    deep_swap(mi["NameMap"], {"MI_Pitchfork_bent": "MI_Sword",
                              "/Game/ConZ_Files/Models/Objects/Items/Pitchfork_bent/Materials": "/Game/LunaPort/Thornblade"})
    src_tex = {
        "T_Pitchfork_Bent_D": "/Game/ConZ_Files/Models/Objects/Items/Pitchfork_bent/Textures/T_Pitchfork_Bent_D",
        "T_Pitchfork_Bent_M": "/Game/ConZ_Files/Models/Objects/Items/Pitchfork_bent/Textures/T_Pitchfork_Bent_M",
        "T_Pitchfork_Bent_N": "/Game/ConZ_Files/Models/Objects/Items/Pitchfork_bent/Textures/T_Pitchfork_Bent_N",
    }
    dst_tex = {
        "T_Pitchfork_Bent_D": ("Sword_low_Sword_BaseColor", "/Game/LunaPort/Thornblade/Sword_low_Sword_BaseColor"),
        "T_Pitchfork_Bent_M": ("Sword_low_Sword_Roughness", "/Game/LunaPort/Thornblade/Sword_low_Sword_Roughness"),
        "T_Pitchfork_Bent_N": ("Sword_low_Sword_Normal", "/Game/LunaPort/Thornblade/Sword_low_Sword_Normal"),
    }
    tex_index = {n: None for n in src_tex}
    old_pkg_to_name = {p: n for n, p in src_tex.items()}
    for i, im in enumerate(mi["Imports"]):
        nm = im["ObjectName"]
        if nm in tex_index and im["ClassName"] == "Texture2D":
            im["ObjectName"] = dst_tex[nm][0]
            tex_index[nm] = i
        elif isinstance(nm, str) and nm in old_pkg_to_name and im["ClassName"] == "Package":
            im["ObjectName"] = dst_tex[old_pkg_to_name[nm]][1]
    deep_swap(mi["NameMap"], {v: dst_tex[k][1] for k, v in src_tex.items()})
    deep_swap(mi["NameMap"], {k: v[0] for k, v in dst_tex.items()})
    deep_swap(mi["NameMap"], {k: v[1] for k, v in dst_tex.items()})
    deep_swap(mi["NameMap"], {"/Game/ConZ_Files/Models/Objects/Items/Pitchfork_bent/Textures": "/Game/LunaPort/Thornblade"})
    deep_swap(mi["Exports"][0].get("Data", []), {k: v[0] for k, v in dst_tex.items()})
    deep_swap(mi["Exports"][0].get("Data", []), {k: v[1] for k, v in dst_tex.items()})
    # 参数引用置换
    for e in mi["Exports"]:
        if e.get("ObjectName") != "MI_Sword":
            continue
        for p in e.get("Data", []):
            if p.get("Name") not in ("TextureParameterValues", "ScalarParameterValues"):
                continue
            for item in p.get("Value", []):
                h = {"nm": None, "vv": None}

                def sc(node):
                    if isinstance(node, dict):
                        if node.get("Name") == "Name" and isinstance(node.get("Value"), str):
                            h["nm"] = node["Value"]
                        if node.get("Name") == "ParameterValue" and isinstance(node.get("Value"), int) and node["Value"] < 0:
                            h["vv"] = node["Value"]
                        for v in node.values():
                            sc(v)
                    elif isinstance(node, list):
                        for v in node:
                            sc(v)
                sc(item)
                map_pname = {"Color": "T_Pitchfork_Bent_D", "Normal": "T_Pitchfork_Bent_N", "AOMEC": "T_Pitchfork_Bent_M"}
                if h["nm"] in map_pname and h["vv"] is not None:
                    old_obj = map_pname[h["nm"]]
                    new_neg = -(tex_index[old_obj] + 1)

                    def setval(node):
                        if isinstance(node, dict):
                            if node.get("Name") == "ParameterValue" and isinstance(node.get("Value"), int) and node["Value"] == h["vv"]:
                                node["Value"] = new_neg
                                return True
                            for v in node.values():
                                if setval(v):
                                    return True
                        elif isinstance(node, list):
                            for v in node:
                                if setval(v):
                                    return True
                        return False
                    if setval(item):
                        print(f"  [mi] 参数 {h['nm']} → 纹理 {dst_tex[old_obj][0]}")
                if p.get("Name") == "ScalarParameterValues" and h["nm"] in ("Roughness Max", "Roughness Min"):
                    for v in item.values() if isinstance(item, dict) else []:
                        pass
                    # 简单：递归改
                    def setsc(node):
                        if isinstance(node, dict):
                            if node.get("Name") == "ParameterValue" and h["nm"] == "Roughness Max":
                                node["Value"] = 0.55
                            if node.get("Name") == "ParameterValue" and h["nm"] == "Roughness Min":
                                node["Value"] = 0.15
                            for v in node.values():
                                setsc(v)
                        elif isinstance(node, list):
                            for v in node:
                                setsc(v)
                    setsc(item)
    # 全文档深换旧贴图名/包路径（覆盖头部软引用等）
    deep_swap(mi, {k: dst_tex[k][0] for k in src_tex})
    deep_swap(mi, {k: dst_tex[k][1] for k in src_tex})
    deep_swap(mi, {"/Game/ConZ_Files/Models/Objects/Items/Pitchfork_bent/Textures": "/Game/LunaPort/Thornblade"})
    deep_swap(mi, {"MI_Pitchfork_bent": "MI_Sword"})
    deep_swap(mi, {"/Game/ConZ_Files/Models/Objects/Items/Pitchfork_bent/Materials": "/Game/LunaPort/Thornblade"})
    dump(os.path.join(JWORK, "mi_mod.json"), mi)
    fromjson(os.path.join(JWORK, "mi_mod.json"), os.path.join(STAGING, "SCUM/Content/LunaPort/Thornblade/MI_Sword.uasset"))


    # ---------- 4b) ORM 金属/遮蔽图：从 Roughness 模板改名 + 接入 AOMEC ----------
    # 4b1. 模板拷贝：Roughness uasset/uexp
    ORM = "Sword_low_Sword_OcclusionRoughnessMetallic"
    rough_u = os.path.join(BASE, r"SCUM/Content/LunaPort/Thornblade/Sword_low_Sword_Roughness.uasset")
    orm_u = os.path.join(STAGING, "SCUM/Content/LunaPort/Thornblade/" + ORM + ".uasset")
    orm_uexp = orm_u.replace(".uasset", ".uexp")
    orm_ubulk = orm_u.replace(".uasset", ".ubulk")
    os.makedirs(os.path.dirname(orm_u), exist_ok=True)
    shutil.copy2(rough_u, orm_u)
    shutil.copy2(rough_u.replace(".uasset", ".uexp"), orm_uexp)
    # 4b2. 改名（export 对象名 + NameMap 包根/对象名）
    orm_j = os.path.join(JWORK, "orm.json")
    tojson(orm_u, orm_j)
    od = load(orm_j)
    for e in od["Exports"]:
        if e.get("ObjectName") == "Sword_low_Sword_Roughness":
            e["ObjectName"] = ORM
    for k in range(len(od["NameMap"])):
        if od["NameMap"][k] == "Sword_low_Sword_Roughness":
            od["NameMap"][k] = ORM
        if od["NameMap"][k] == "/Game/LunaPort/Thornblade/Sword_low_Sword_Roughness":
            od["NameMap"][k] = "/Game/LunaPort/Thornblade/" + ORM
    for e in od["Exports"]:
        deep_swap(e.get("Data", []), {"Sword_low_Sword_Roughness": ORM})
    dump(os.path.join(JWORK, "orm_mod.json"), od)
    fromjson(os.path.join(JWORK, "orm_mod.json"), orm_u)
    # 4b3. 写 ORM 像素数据（先由 enc_orm.py 生成，此处拷贝入）
    src_orm = r"C:\tmp\pf_orm\Sword_low_Sword_OcclusionRoughnessMetallic.ubulk"
    shutil.copy2(src_orm, orm_ubulk)
    print("  [orm] 模板改名 + ubulk 写入:", ORM)

    # 4b4. MI：加 ORM import + 把 AOMEC 参数引用改指向 ORM
    mi_s2 = load(os.path.join(JWORK, "mi_mod.json"))
    # 追加 Package import + 对象 import
    orm_pkg = "/Game/LunaPort/Thornblade/" + ORM
    n = len(mi_s2["Imports"])
    mi_s2["Imports"].append({
        "$type": "UAssetAPI.Import, UAssetAPI",
        "ObjectName": orm_pkg, "OuterIndex": 0,
        "ClassPackage": "/Script/CoreUObject", "ClassName": "Package",
        "PackageName": None, "bImportOptional": False})
    pkg_idx = n
    mi_s2["Imports"].append({
        "$type": "UAssetAPI.Import, UAssetAPI",
        "ObjectName": ORM, "OuterIndex": -(pkg_idx + 1),
        "ClassPackage": "/Script/Engine", "ClassName": "Texture2D",
        "PackageName": None, "bImportOptional": False})
    obj_idx = n + 1
    ensure_names(mi_s2, [ORM, orm_pkg])
    # AOMEC 参数引用 -> -(obj_idx+1)
    def repoint(node):
        if isinstance(node, dict):
            if node.get("Name") == "Name" and node.get("Value") == "AOMEC":
                # 找同层 ParameterValue 并已标记
                pass
            for v in node.values():
                repoint(v)
        elif isinstance(node, list):
            for v in node:
                repoint(v)
    for e in mi_s2["Exports"]:
        if e.get("ObjectName") != "MI_Sword":
            continue
        for p in e.get("Data", []):
            if p.get("Name") != "TextureParameterValues":
                continue
            for item in p.get("Value", []):
                h = {"nm": None, "vv": None}
                def sc(node):
                    if isinstance(node, dict):
                        if node.get("Name") == "Name" and isinstance(node.get("Value"), str):
                            h["nm"] = node["Value"]
                        if node.get("Name") == "ParameterValue" and isinstance(node.get("Value"), int):
                            h["vv"] = node["Value"]
                        for v in node.values():
                            sc(v)
                    elif isinstance(node, list):
                        for v in node:
                            sc(v)
                sc(item)
                if h["nm"] == "AOMEC" and h["vv"] is not None:
                    def setv(node):
                        if isinstance(node, dict):
                            if node.get("Name") == "ParameterValue" and isinstance(node.get("Value"), int) and node["Value"] == h["vv"]:
                                node["Value"] = -(obj_idx + 1)
                                return True
                            for v in node.values():
                                if setv(v):
                                    return True
                        elif isinstance(node, list):
                            for v in node:
                                if setv(v):
                                    return True
                        return False
                    if setv(item):
                        print(f"  [mi] AOMEC → {ORM} (ref -{obj_idx+1})")
    dump(os.path.join(JWORK, "mi_orm.json"), mi_s2)
    fromjson(os.path.join(JWORK, "mi_orm.json"),
             os.path.join(STAGING, "SCUM/Content/LunaPort/Thornblade/MI_Sword.uasset"))

    # ---------- 5) repak ----------
    out_pak = os.path.join(TMP, MOD_NAME + ".pak")
    if os.path.exists(out_pak):
        os.remove(out_pak)
    r = subprocess.run([REPAK, "pack", "--version", "V11", "--compression", "Zlib",
                        "--mount-point", "../../../", STAGING, out_pak],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        print("repak pack 失败:", r.stdout, r.stderr); sys.exit(1)
    r = subprocess.run([REPAK, "list", out_pak], capture_output=True, text=True, timeout=120)
    lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
    bad = [l for l in lines if not l.startswith("SCUM/Content/")]
    print(f"repak list: {len(lines)} 条，前缀异常 {len(bad)} 条")
    for l in lines:
        print("  ", l)
    if bad:
        sys.exit(1)
    shutil.copy2(out_pak, PAK)
    print(f"[OK] → {PAK} ({os.path.getsize(PAK)} B, {os.path.getsize(PAK)/1048576:.2f} MB)")


if __name__ == "__main__":
    main()