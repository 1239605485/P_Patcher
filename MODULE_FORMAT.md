# mdz-patch/1 模块格式

ZIP 必须有 `module.json`、`module.sig`、所需的 `payload/*`。`module.sig` 是清单原始 UTF-8 字节的 SHA256withRSA 签名；软件内置的是现有 P 版证书公钥。ZIP 时间等元数据不参与信任判断；每个实际负载的 SHA-256 由已签名清单约束。

清单根字段：`format`、`engine_min`、`id`、`name`、`version`、`signer_sha256`、`profiles`、`payloads`。

每个 profile 绑定一个完整输入 APK 的 `input_sha256`。输出身份由 `output_package`、`output_version`、`output_version_code` 指定。当前只接受现有共存版安装身份。

`modules` 按依赖顺序排列。模块有 `id`、`name`、`mandatory:true`、`depends_on` 和 `operations`。首版只支持必需模块，必须存在 `isolation-core`；条件匹配不代表功能已实机验证。

## 单功能分包

可把总包拆成 `isolation-core + 一个功能模块` 的独立 ZIP，后续只修改一个功能时无需重新发送整个包：

```text
P_Patcher_GitHub/.venv/Scripts/python.exe tools/split_module.py \
  --module 总插件包.zip --key 签名.pem \
  --module-id p14-features --out feature_packages
```

输出包保留原 APK 适配档案、payload 和依赖顺序，只重新签名清单。安装器按原有兼容性检查处理；缺少 `isolation-core` 的包会被拒绝。

每个 operation 定义：

```json
{
  "entry": "lib/arm64-v8a/libil2cpp.so",
  "before_sha256": "原条目SHA256",
  "before_size": 123,
  "after_sha256": "目标条目SHA256",
  "after_size": 125,
  "commands": [{"copy": [0, 120]}, {"data": "payload/负载SHA256"}]
}
```

`copy` 只从该操作的原条目复制指定范围；`data` 从模块负载复制。负载记录为 `payloads[path]={"size":整数,"sha256":"..."}`。新增 ZIP 条目声明 `create:true`，前像必须是空内容 SHA 和长度零，且输入不存在该条目。

不允许重复 ZIP 项、路径穿越、未满足依赖、未声明的交叉模块覆盖或签名元数据修改。不支持删除原条目、不执行任意脚本。新增操作类型需要提高引擎/格式版本，不能默默忽略。

APK 重打包会去除旧 APK 签名并按本地导入身份签名；构建日志、清单和模块包不得包含私钥。对未知作者新版的首次适配仍需人工分析，不能把版本号相近当成二进制兼容。

## 引擎2：签名完整指纹

`engine_min:2` 的档案可以增加 `input_inventory`，其中每个非签名、非目录 ZIP 条目包含 `size` 和 `sha256`；AndroidManifest.xml 另包含 `identity`。`input_manifest_payload` 指向 `payload/*` 中该输入原始清单，同时受 payloads 和 inventory 的 SHA/长度约束。

仅在整包 SHA 没匹配时尝试完整指纹。所有条目集合及内容必须相同；唯一例外是 manifest 的结构化 identity 相同，允许 label 和 versionName/versionCode 的值变化。结构化算法解析字符串池并按命名空间、标签、属性、类型和值生成摘要；保留资源映射、组件、包名、权限和其他节点。未知 XML 块、样式池或歧义将拒绝归一化。资源表、DEX、本地库和 Unity 数据没有通配符。

匹配后从签名负载恢复 manifest 前像，原有 operation 的前后像校验继续逐项执行。原始输入不会被修改。成功历史不参与兼容性授权。任意其他变化会生成最接近档案的差异诊断，不应用旧目标。
