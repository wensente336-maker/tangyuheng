# Hermes 部署配置

## 必需环境变量

转写接口采用 OpenAI 兼容的 `/audio/transcriptions`：

```text
HERMES_STT_BASE_URL=https://你的语音服务/v1
HERMES_STT_API_KEY=密钥
HERMES_STT_MODEL=whisper-1
```

总结接口采用 OpenAI 兼容的 `/chat/completions`：

```text
HERMES_LLM_BASE_URL=https://api.deepseek.com/v1
HERMES_LLM_API_KEY=密钥
HERMES_LLM_MODEL=deepseek-chat
```

可选：

```text
MEETING_DATA_DIR=/持久化磁盘/meeting-data
MEETING_MAX_HOURS=8
MEETING_CHUNK_SECONDS=30
```

## Hermes 要求

- 将服务端口 `8765` 暴露为 HTTPS；手机麦克风权限要求安全来源。
- 将 `MEETING_DATA_DIR` 指向容器持久卷，避免重启后丢失。
- 安装 `ffmpeg`。结束录音后服务端用它把片段合并为单个音频再转写。
- 不把密钥写入 `hermes-config.yaml`；使用 Hermes Secret/环境变量注入。
- 反向代理对 `/api/meetings/*/process` 的超时应不低于 30 分钟。

