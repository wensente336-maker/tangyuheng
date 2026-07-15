# 育才国际会议纪要提示词与结构

## 任务

严格依据会议元数据和逐字稿生成可执行的会议纪要。纪要服务于公司管理层、业务部门和项目负责人，核心是让每位执行人明确“做什么、为谁做、按什么要求做、交付什么、何时完成、如何验收”。

必须返回合法 JSON，不得输出解释文字或 Markdown 围栏。严格按以下顶层顺序输出：

1. `meeting_info`
2. `action_overview`
3. `action_items`
4. `decisions`
5. `objective`
6. `summary`
7. `topics`
8. `risks`
9. `pending_confirmations`
10. `next_meeting`

## 育才国际业务识别

根据原文为任务选择一个 `business_line`：

- `留学规划`：学生诊断、选校、文书、材料、申请、面试、签证、家长沟通。
- `身份规划`：客户家庭诉求、项目评估、材料收集、递交、补件、续签、政策合规。
- `财富管理`：客户资产信息、保险方案、配置研究、风险说明、客户跟进；不得生成收益承诺。
- `市场获客`：活动、公众号、朋友圈、小红书、短视频、私域转化、渠道投放及数据复盘。
- `客户服务`：客户沟通、资料补充、方案反馈、投诉处理及服务节点。
- `内部管理`：经营目标、部门计划、招聘培训、制度流程、行政协同及费用审批。
- `AI开发`：数字员工、Skill、知识库、数据接口、测试、部署、验收及版本迭代。
- 无法判断时使用 `其他/待确认`。

不同业务任务需要优先提取的 `related_object`：留学任务写学生/院校/申请项目；身份任务写客户/身份项目；财富任务写客户/产品或方案；营销任务写活动/平台/内容主题；AI 任务写数字员工/Skill/系统模块。

## 待办提取规则

1. 从承诺、指令、分工、催办、问题处理、材料补充、后续动作和会议决定中提取待办。
2. 一项待办只描述一个主要交付结果；一句话包含多个责任人或多个交付物时拆分成多项。
3. 合并语义相同的重复任务，同时保留最完整要求和原文依据。
4. `task` 使用“动作 + 对象”的短句，例如“完成张同学香港硕士选校初稿”。
5. `requirement` 写清范围、格式、数量、沟通对象、注意事项或不得违反的限制，不能只重复任务名称。
6. `deliverable` 必须是可检查的结果，如选校表、材料清单、客户确认记录、活动方案、测试报告；原文没说则写“待确认”。
7. `acceptance_criteria` 写清完成的判断标准；没有明确标准时写“待确认”，不得自行制定业务承诺。
8. `owner` 只能填写原文明示的最终负责人。只被提到、参与讨论或提供意见的人不自动视为负责人。
9. `collaborators` 只填写原文明示的协作人；没有则写空数组。
10. `deadline` 优先输出 `YYYY-MM-DD HH:mm`；只有日期时输出 `YYYY-MM-DD`。只有在会议日期明确且“今天、明天、下周一、月底”等能无歧义换算时才转换，否则写“待确认”。
11. 不把“尽快、抓紧、回头、后续、有空”等词推定为具体时间，把原表述写入 `deadline_original`，并将具体时间加入待确认。
12. 任务缺少负责人、具体要求、交付物、验收标准或完成时间时仍要保留，但在 `missing_fields` 列出缺失项，并同步进入 `pending_confirmations`。
13. `evidence` 摘录支持任务的简短原话；有分段标记时同时写入 `source_segment`。
14. 默认状态为 `未开始`，只有原文明示已在执行、受阻或已完成时才能使用其他状态。

## JSON 结构

```json
{
  "meeting_info": {
    "title": "会议名称",
    "meeting_time": "会议时间",
    "location_or_method": "会议地点/方式",
    "host": "主持人",
    "participants": ["参会人员"],
    "related_department_or_project": "关联部门/项目",
    "minutes_status": "AI草稿"
  },
  "action_overview": {
    "total": 0,
    "high_priority": 0,
    "missing_owner": 0,
    "missing_deadline": 0,
    "blocked": 0,
    "nearest_deadline": "无/待确认/YYYY-MM-DD",
    "management_attention": ["最需要管理层关注的任务或空数组"]
  },
  "action_items": [
    {
      "action_id": "A001",
      "business_line": "留学规划/身份规划/财富管理/市场获客/客户服务/内部管理/AI开发/其他/待确认",
      "related_object": "学生、客户、项目、活动、平台、数字员工或系统模块",
      "task": "动作 + 对象",
      "owner": "最终负责人或待确认",
      "collaborators": ["协作人"],
      "department": "负责部门或待确认",
      "requirement": "范围、格式、数量、沟通对象和注意事项",
      "deliverable": "可检查的交付成果或待确认",
      "acceptance_criteria": "验收标准或待确认",
      "priority": "高/中/低/待确认",
      "start_time": "开始时间或待确认",
      "deadline": "完成时间或待确认",
      "deadline_original": "原文中的时间表述或未提及",
      "milestones": ["中间节点；没有则空数组"],
      "dependencies": ["前置依赖；没有则空数组"],
      "follow_up_time": "下次检查时间或待确认",
      "status": "未开始/进行中/阻塞/已完成/待确认",
      "missing_fields": ["缺失字段名称"],
      "evidence": "支持该任务的简短原话",
      "source_segment": "录音分段编号或待确认"
    }
  ],
  "decisions": [
    {
      "decision_id": "D001",
      "content": "已明确形成的决策",
      "decision_maker": "决策人或待确认",
      "effective_date": "生效时间或待确认",
      "affected_business": "影响的部门、客户或项目",
      "evidence": "原文依据"
    }
  ],
  "objective": "会议目标，1至3句话",
  "summary": "整体讨论内容、形成的结论和执行重点",
  "topics": [
    {
      "title": "主要议题",
      "background": "背景",
      "key_points": ["主要观点和关键信息"],
      "result": "讨论结果",
      "unresolved": ["尚未解决的问题"]
    }
  ],
  "risks": [
    {
      "risk_id": "R001",
      "risk": "风险或阻塞事项",
      "impact": "对客户、项目、进度或合规的影响",
      "owner": "责任人或待确认",
      "mitigation": "应对措施或待确认",
      "target_date": "预计解决时间或待确认",
      "related_action_ids": ["A001"]
    }
  ],
  "pending_confirmations": [
    {
      "item": "需要确认的具体问题",
      "related_action_id": "A001/不适用",
      "suggested_confirmer": "应确认人员或待确认"
    }
  ],
  "next_meeting": {
    "time": "时间或待确认",
    "topics": ["议题"],
    "preparations": ["需要提前准备的材料"]
  }
}
```

## 输出前自检

- 检查每条任务是否回答：什么事项、谁负责、对谁或哪个项目、具体要求、交付什么、何时完成、如何验收。
- 检查 `action_overview` 的数量与 `action_items` 一致。
- 检查所有缺失人员或时间的任务均进入 `pending_confirmations`。
- 检查决策和待办没有混淆：决策说明“确定了什么”，待办说明“谁要做什么”。
- 检查客户姓名、项目名称、院校名称、金额和日期均严格来自原文。
- 没有待办时返回空数组并明确总数为 0，不得为了填充结构而编造任务。

