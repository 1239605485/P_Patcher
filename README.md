# P Patcher 1.7.0 · 核心版

Android 本地 APK 插件安装器，最低 Android 8.0。纯 Java 实现，Python 构建，不依赖 Gradle。应用包名保持 `cn.minidayz.patcher`，版本代码为 10700。

## 界面与功能

- **制作 APK**：添加完整游戏 APK，导入插件总包或单功能 ZIP，查看输入版本和包名，管理功能选择，编辑输出名称、版本名称与内部版本代码，检查兼容性，生成、安装和导出。
- **任务窗口**：四阶段状态、当前步骤进度、可滚动的任务记录、安全取消和一键复制。点击后台任务通知可直接返回任务窗口。
- **工具**：导入或清空游戏日志、导出安装器诊断、清理未完成构建缓存。
- 签名和外置数据引擎放在折叠的“构建配置”中。仅含原生补丁的模块不需要外置数据引擎。

AI 页面、联网请求客户端、API 配置和自动修改模块实现已经移除。应用不声明联网权限。

## 使用顺序

1. 添加需要处理的原版完整游戏 APK。不支持 APKS/XAPK 拆分包。
2. 导入与该游戏版本匹配的插件 ZIP。总包首次导入后，可以按需更新单功能包。
3. 确认名称和版本。留空使用默认值；内部版本代码留空时自动递增。手动代码需高于已安装及上次成功生成的代码，并满足插件档案最低要求。
4. 展开“构建配置”，导入原 P 版签名 PEM 或含该签名的交接 ZIP。只有插件带数据规则时才导入配套引擎 ZIP。
5. 点击“检查并生成 APK”，在任务窗口查看过程，成功后返回制作页安装或导出。

修改文件、功能选择、名称或版本后，已有输出会提示重新生成。若确实需要历史结果，可以在明确提示后继续安装或导出。

## 日志

支持 UTF-8 的 TXT、LOG、JSON 和包含这些文本的 ZIP。输入最多 4 MiB；ZIP 最多 200 个条目，单项最多 4 MiB、总解压量最多 8 MiB。所有条目均计入限制。私钥块、常见口令和令牌会在本机脱敏。导入只保存诊断证据，不修改游戏或插件。游戏日志与安装器诊断包按结构区分。

## 本地构建

准备 Python 3.12 与 JDK 17/21，并让 `java`、`javac` 位于 PATH。工具链按 `toolchain.json` 与 `public_resource_pin.json` 的固定哈希下载和校验。

```sh
python -m pip install -r requirements.txt -r requirements-migration.txt
python tools/build.py --debug
```

正式版需要由持有人提供合并 PKCS8 RSA 私钥及证书的 PEM，密钥不包含在源码或 APK 中：

```sh
python tools/build.py --key /path/to/signing.pem
```

默认签名身份为现有 P 版身份。调试构建使用本机持久化测试密钥，不能覆盖正式安装。模块信任证书与安装器调试签名独立。

构建会验证 APK 签名、ZIP CRC、安装清单和资源表，输出 APK、校验 JSON 与 SHA-256 文件。

## 验证

构建之后运行：

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
python tests/diagnostic_engine_tests.py
python tests/core_engine_tests.py
```

可使用自己的授权输入进行临时完整构建测试，测试输出在结束时删除：

```sh
python tests/core_engine_tests.py --apk /path/game.apk --plugin /path/plugin.zip --key /path/signing.pem --log /path/crash.zip
```

本次交付已完成 24 项 Python 测试、24 项诊断测试、22 项核心行为测试；另外验证了用户提供的三个崩溃日志和修复后的 P14 插件完整构建。自定义名称及两个版本字段、构建记录、签名和归档均已核对。尚未进行 Android 真机界面、安装授权流程或游戏运行测试。

## 工程目录

`src/` 是安装器源码，`engine-src/` 是可选数据引擎源码，`tools/` 保留构建、签名、插件打包与版本迁移工具，`tests/` 是自动检查。插件和引擎格式见 `MODULE_FORMAT.md` 与 `ENGINE_FORMAT.md`。源码交付不包含私钥、构建缓存或用户的游戏 APK。
