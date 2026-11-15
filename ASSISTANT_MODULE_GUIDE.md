# 可选的签名插件功能说明

模块格式仍是 mdz-patch/1。可在 module.json 根节点加入 assistant.features，重新签名后才会被当作插件说明读取。安装器只从验签通过的对象读取这些字段；它们不代替原有哈希、依赖和兼容检查。

```json
{
  "assistant": {
    "features": [
      {
        "module_id": "实际存在的模块ID",
        "description": "这个功能改变什么、目的是什么、哪些行为必须保持",
        "locators": [
          {"entry": "assets/config.json", "kind": "text", "contains": "唯一定位片段"}
        ],
        "manual_tests": ["启动并进入受影响地图", "复现原问题并检查结果"]
      }
    ]
  }
}
```

1.4仅把locators与manual_tests作为分析证据提供给AI，尚不执行定位表达式、不自动修改native代码。实际修改位置还会从模块operations中提取entry、前后哈希和长度。旧插件没有说明时展示实际操作，不编造功能含义。每个模块的定位列表展示前12项，完整操作仍由补丁引擎验证。
