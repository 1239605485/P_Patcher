# P Patcher 1.6.0 · GitHub 可编译工程

Android 安装器与外置 UnityFS 引擎源码。首页保留导入文件、功能清单、生成、安装和名称版本修改；诊断页保留进度、日志导入与导出。此版首页没有 AI/API 设置流程，APK 清单不再声明联网权限和 AI 设置 Activity。

安装器、引擎 ZIP、功能 ZIP 分开更新。首次导入作者 1.5.5 原版 APK、插件总包、引擎包和原 P 版签名文件。后续更新某个数据功能只导入对应 ZIP，再重新生成并安装游戏。功能选择窗口可启用/停用数据功能，原生与隔离基础包保持必需。

本次为架构与打包流程测试交付。已通过电脑端完整构建、签名、58,528 个 Unity 对象核对；未连接 Android 设备，真实 Dex 加载、系统安装与游戏运行均未实测。原生移植沿用此前候选，游戏“点击设置闪退”尚未确认修复，不能标成稳定版。数据功能已拆分，原生钩子仍作为耦合基础包；并非所有原生功能都已独立拆分。

插件总包约 1.8 MB，引擎约 10 KB。原版 Unity 数据解压后约 1.78 GB，生成时建议至少预留 5 GB 空间。当前便携 LZ4 编码器的压缩率低于原版，游戏输出约 274 MB；小插件不等于小输出 APK。

包格式、单功能修改、重组总包和引擎 API 见 ENGINE_FORMAT.md。tools/sign_feature.py 仅重签一个数据功能；tools/pack_features.py 无需私钥即可汇总已签名的分包。旧 build_unity_object_patch.py 实验格式不参与此版流程。

## 在 GitHub 上编译

1. 解压源码包，把全部内容上传到仓库根目录。必须包含 `.github/workflows/build-apk.yml`，不要再套一层文件夹。
2. 打开仓库 **Actions → Build APK → Run workflow**，保持 `release` 不勾选并运行。Push 和 Pull Request 也会执行测试编译。
3. 成功后在该次运行页面底部的 **Artifacts** 下载 `P-Patcher-运行编号`，解压得到 APK、SHA256 和验证报告。

默认构建不需要 Secret，会生成测试签名 APK。应用包名仍为 `cn.minidayz.patcher`，无法覆盖不同签名的旧安装器；每次新的云端运行都会生成新的测试签名。需要保持后续覆盖升级身份时，请使用固定签名构建。测试建议使用独立设备或模拟器，避免卸载有重要私有数据的旧安装器。

## 使用固定签名生成 APK

在仓库 **Settings → Secrets and variables → Actions** 添加 Secret `SIGNING_PEM_BASE64`，内容为“未加密 PKCS8 RSA 私钥 + X.509 证书”的组合 PEM 文件的 Base64。不要把 PEM 上传到仓库。

Windows PowerShell 可将编码复制到剪贴板，路径替换为你自己的文件：

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes('C:\keys\signing.pem')) | Set-Clipboard
```

默认要求原安装器证书指纹 `21fa47120af53f71b39e886eaf0d71a159c34a2d332646a1cf0820a59549ad10`。使用自己的固定证书时，另外添加仓库 Variable `SIGNING_CERT_SHA256`，填写该证书 SHA256 指纹。自有签名无法覆盖旧签名应用，但可让以后各次构建保持同一安装身份。

然后手动运行 Actions 并勾选 `release`。只有这一步读取签名 Secret；Push / PR 默认生成测试包。工作流不自动创建 Release、不发布到应用市场，上传产物只包含 `output/`。

安装器 APK 签名与插件验签公钥是两个用途。APK 换签不会改变 `assets/trust.der` 和插件信任身份，原插件仍按原规则验签。生成游戏 APK 仍需要用户在安装器中导入原签名。

## 本地编译

需要 Python 3.12 与 JDK 17 或 21，`java` 在 PATH 中。首次构建下载并核对工具链 SHA256。

```sh
python -m pip install -r requirements.txt
python tools/build.py --debug
```

固定签名：

```sh
python tools/build.py --key /absolute/path/signing.pem
```

自有证书另加 `--expected-cert-sha256 证书指纹`。默认输出在 `output/`。本地测试签名保存在 `build/debug-signing.pem`，保留它可让本地后续测试包保持同一签名；它不进入 Git 或云端下载产物。

## 迁移辅助工具

```sh
python -m pip install -r requirements-migration.txt
python -m unittest discover -s tests -p 'test_*.py' -v
```

一条命令 `python tools/scan_update.py --new-apk "新版.apk" --stable-apk "稳定P14.apk" --out "本次分析"` 可生成电脑端的精简差异报告；这不生成可安装插件。详见 [版本适配工作流.md](版本适配工作流.md)。插件格式见 [MODULE_FORMAT.md](MODULE_FORMAT.md)。

## 验证与边界

使用固定哈希的 ECJ + D8，纯 Java 源码布局。构建后检查 APK v2 签名、归档 CRC、安装身份及资源表。

本地验证摘要见 BUILD_VALIDATION.json。测试桥只在 tests/jvm 中，将同一 Java 引擎字节码通过 JVM URLClassLoader 执行；不会进入 Android APK，也不能代替真实 Android DexClassLoader 测试。GitHub Actions 文件已保留，尚未在托管仓库运行本版。

未知新版会被基准哈希拦截。新版需要更新引擎定位档案、复核数据规则和原生钩子；没有承诺通用自动移植。源码交付归档不包含私钥。

## 增量项目索引与 AI 交接

复杂分析建议在电脑端保存到独立的项目目录，安装器只接收已经签名的模块。先生成哈希绑定的 APK/引擎/插件索引：

```sh
python tools/project_index.py --apk 原版.apk --engine 引擎包.zip \
  --module 插件总包.zip --out project/index.json
```

每次 Bug 或功能任务只导出相关证据，避免再次发送完整 APK：

```sh
python tools/task_context.py --index project/index.json \
  --task "排查点击设置闪退" --evidence report.json \
  --evidence build_manifest.json --out project/task_context.json
```

索引只能复用已确认的文件身份，不能授权未知版本的 native 或 IL2CPP 补丁。当前工具会明确标记尚未提供的符号索引和自动原生迁移能力；这类修改仍需版本绑定证据、人工复核和真机测试。
