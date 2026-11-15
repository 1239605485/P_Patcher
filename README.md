# P Patcher · GitHub 编译工程

Android 安装器完整源码，保留 1.4.0 功能与新增迁移证据分析。支持 GitHub Actions 自动生成 APK，或在 Windows / Linux / macOS 本地编译，无需完整 Android SDK。

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

`tools/prepare_version.py` 是电脑端 P14 → 新版迁移证据入口，不会直接生成已适配游戏。它还需要完整游戏输入和旧迁移工作目录，未包含在本仓库。插件格式见 [MODULE_FORMAT.md](MODULE_FORMAT.md)。

## 工程改动

- 使用固定哈希的 ECJ + D8，保留纯 Java 源码布局。
- 修复 Windows classpath 分隔符和 JAR 路径，移除 Linux 字体及本机私钥路径依赖。
- 使用现有图标，构建不依赖 Pillow 或系统字体。
- 构建后检查 APK v2 签名、归档 CRC、安装身份及资源表，输出验证报告。
- 忽略构建缓存、产物、私钥及游戏 APK。
- 工程整理不代表 1.5.5 游戏功能移植完成；Android 真机运行仍需验证。

本地已完成实际 APK 编译、签名/清单/资源检查，并用临时证书验证固定签名入口。尚未在 GitHub 托管环境运行工作流，详细记录见 [BUILD_VALIDATION.json](BUILD_VALIDATION.json)。

参考：[GitHub Python 工作流](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)、[构建产物上传](https://github.com/actions/upload-artifact)。
