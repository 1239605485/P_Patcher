# 安装器 1.6.0 的外置引擎与功能格式

实际实现采用 Java/Dex；旧文档中的 native .so 引擎草案未采用。

引擎 ZIP 包含 engine.json、engine.sig、classes.dex、locators.json。清单格式 mdz-engine/1，api=1，入口 mdz.engine.UnityEngine。files 登记每个负载的字节数与 SHA256。安装器使用固定信任证书验证 RSA-SHA256 签名及负载哈希，将 Dex 设为只读后加载。

固定入口：public static void apply(File input, File output, File work, String locatorsJson, String rulesJson)。

引擎核验作者 1.5.5 data.unity3d 的完整 SHA256，按签名定位表找到 SerializedFile 中的六个 TextAsset，再核验每个对象原始字节 SHA256。按规则修改 JSON，把变长对象追加到文件尾部，更新对象表偏移、大小和序列化文件长度。其余对象字节保持原样。逐块解压与重新 LZ4 压缩通过临时文件完成。

这是精确基准引擎，不是任意新版自动适配引擎。新版位置或结构变化时，需要重新生成定位表并验证规则；不能只改版本号。实现支持当前目标使用的 UnityFS 6/7/8、raw/LZ4 块，未实现 LZMA。

## 单功能包

每个数据功能 ZIP 包含 feature.json 与 feature.sig。例如：

    {"format":"mdz-feature/1","id":"loot-guaranteed","name":"地图物品掉落概率调整","version":"1.0.0","engine_id":"unityfs-json-155","depends_on":["isolation-core"],"signer_sha256":"固定信任证书指纹","rules":[{"object":"world","path":["AreaPresetDatabase","5","ItemDropChance"],"before":0.75,"after":1}]}

path 是 JSON 键或数组索引组成的数组；检查 before 后写入 after。添加字典字段省略 before；删除字段使用 remove=true。追加有唯一 ID 的数组记录使用 append、key_field、key_value。同路径重复修改被拒绝。功能包不能包含可执行脚本。

原生补丁和 Android 隔离功能仍共用一个 mdz-patch/1 基础 ZIP，保留二进制增量操作与完整哈希检查。当前原生钩子互相依赖，尚未拆成每个钩子一个独立包，也没有新增游戏运行时崩溃修复。

## 总包与本机选择

总 ZIP 包含 bundle.json 和 features/*.zip。清单格式 mdz-bundle/1，features 数组登记每个 ZIP 的 path、size、sha256。官方总包另带 bundle.sig；用户重组总包可以不签外层，但所有内层仍必须通过签名验证。

安装器导入时按功能 ID 更新，保留其他已导入功能；用户可勾选启用的数据功能。基础包始终启用。每次检查/生成重新验证参与构建的内层签名、依赖与规则冲突。功能状态区区分未启用、待生成及已生成输出；不从这些状态推断游戏运行已通过。

## 只更新一个功能

提取该 ZIP 的 feature.json，修改规则并保持 id，递增 version，只重签该 ZIP：

    python tools/sign_feature.py --manifest feature.json --key /private/signing.pem --output updated-feature.zip

手机直接导入新单功能 ZIP 即可替换对应功能。原版 APK 和引擎不变时无需重发；每次生成仍从已登记的原版 APK 构建。

需要重新汇总分包时，把保留的功能 ZIP 放进目录：

    python tools/pack_features.py --features feature-zips --output custom-bundle.zip

重组总包不需要私钥；修改具体功能需要重签。不要直接改官方 ZIP 内 JSON 或替换子包却不更新清单。

## 重建全部交付

安装构建依赖、requirements-unity.txt、requirements-modules.txt，先构建安装器以准备工具链。然后提供原版 APK、已验证移植目标 data.unity3d、原生增量模块和本地签名密钥：

    python tools/build_delivery.py --key /private/signing.pem --out delivery --base-apk author155.apk --target-bundle data_port_155.unity3d --native-module original-native-module.zip

这是本次六对象适配的生成器，当前对象格式和核心模块 ID 有约束，并非通用游戏修改器。源码和交付 ZIP 不包含游戏原包、目标资源或私钥。build_unity_object_patch.py / apply_unity_object_patch.py 为旧实验格式，不参与本版流程。
