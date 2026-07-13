# 会议纪要结构

总结模型必须返回 JSON，不得添加 Markdown 围栏：

```json
{
  "objective": "会议目标，1至3句话",
  "summary": "整体讨论内容及最终结果",
  "topics": [{"title":"议题","background":"背景","viewpoints":["主要观点"],"result":"讨论结果","unresolved":["尚未解决的问题"]}],
  "decisions": [{"content":"决策内容","decision_maker":"决策人或待确认","effective_date":"生效时间或待确认","evidence":"原文依据"}],
  "actions": [{"task":"任务","owner":"负责人或待确认","collaborators":"协作人或待确认","deadline":"截止时间或待确认","deliverable":"交付物或待确认","priority":"高/中/低/待确认","status":"未开始/进行中/阻塞/已完成/待确认","evidence":"原文依据"}],
  "risks": [{"risk":"风险","impact":"影响","owner":"责任人或待确认","mitigation":"应对措施或待确认","target_date":"预计解决时间或待确认"}],
  "pending_confirmations": ["负责人、日期、结论不明确的内容"],
  "next_meeting": {"time":"时间或待确认","topics":["议题"],"preparations":["提前准备的材料"]}
}
```

规则：原文没有的信息写“待确认”；日期只在原文明确或能由会议日期无歧义换算时转成 `YYYY-MM-DD`；每条决策和任务保留简短原文依据。

