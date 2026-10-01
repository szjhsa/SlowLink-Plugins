<div align="center">

# SlowLink Plugins

**SlowLink 的独立规则插件仓库**

[![Release](https://img.shields.io/github/v/release/szjhsa/SlowLink-Plugins?display_name=tag&sort=semver&style=flat-square)](https://github.com/szjhsa/SlowLink-Plugins/releases/latest)
[![Release Build](https://img.shields.io/github/actions/workflow/status/szjhsa/SlowLink-Plugins/release.yml?style=flat-square&label=release)](https://github.com/szjhsa/SlowLink-Plugins/actions/workflows/release.yml)
[![License](https://img.shields.io/github/license/szjhsa/SlowLink-Plugins?style=flat-square)](LICENSE)

</div>

这个仓库只保存 SlowLink 的规则插件包，不包含 SlowLink 主程序代码。

核心 SlowLink 是通用引擎；规则插件决定它“识别什么、怎么分类、如何去重”。上传一个插件包，就能让纯净版变成对应规则版本。

## 插件包格式

每个插件是一个 zip，至少包含：

```text
plugins/<plugin_id>/
├── plugin.json
└── rules.json
```

`plugin.json` 字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 插件 ID，只允许字母、数字、下划线和短横线 |
| `name` | 插件名称 |
| `version` | 插件版本 |
| `min_core_version` | 要求的最低 SlowLink 核心版本 |
| `author` | 作者 |

`rules.json` 是 SlowLink 引擎读取的规则数据：

| 分区 | 内容 |
| --- | --- |
| `matcher` | 已使用、关闭注册、注册成功等安全过滤 |
| `code_rules` | 内置强格式开关、默认码识别规则、正向/负向上下文 |
| `dedup` | 活动关键词、抽奖 ID/模板、来源行提示、TTL 默认值 |
| `code_identity` | 掩码/明文注册码的统一身份匹配、固定锚点和 TTL |
| `flow` | 优先队列关键词 |
| `defaults` | Redis 默认配置 |

## 内置插件

`plugins/builtin/` 是 SlowLink 1.0 的默认规则插件包。

## 使用方式

1. 安装 SlowLink 1.0。
2. 打开网页后台 → 工具与备份 → 规则插件。
3. 上传 `slowlink-plugin-builtin-v1.0.0.zip` 或你的专属插件包。
4. 上传成功后会立即启用，无需重启容器。

## 发布

推送 `v*` 标签后，GitHub Actions 会自动：

1. 校验 `plugin.json` 和 `rules.json`。
2. 生成 `dist/slowlink-plugin-<id>-v<version>.zip`。
3. 生成 `SHA256SUMS.txt`。
4. 创建 GitHub Release 并上传 zip 与校验文件。

## 许可证

MIT License
