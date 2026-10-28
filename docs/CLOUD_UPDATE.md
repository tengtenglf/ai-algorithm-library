# 每日课程云端更新合同

2026-10-28更新。正式站点：https://tengtenglf.github.io/ai-algorithm-library/ 。

原任务 `6ac9e53a5cdc8191b955c5a84cdc3c2f`（每日 AI 算法寓言）保持每天北京时间10:00、同一聊天执行，保留原教学规则；生成后直接使用已连接GitHub提交当天完整原文。原聊天为 `6ac9e367-6ea8-83ec-aeee-555083ffcfb7`。此路径不需要本地文件、桌面应用开着或额外API密钥。

## 入站合同

主分支 `content/inbox/YYYY-MM-DD.json`：

```json
{"conversation_id":"6ac9e367-6ea8-83ec-aeee-555083ffcfb7","messages":[{"id":null,"delivery":{"automation_id":"6ac9e53a5cdc8191b955c5a84cdc3c2f","id":"6ac9e53a5cdc8191b955c5a84cdc3c2f:YYYY-MM-DD"},"text":"本次课程完整原始Markdown"}]}
```

日期替换为实际北京时间日期。任务在发布前无法取得最终聊天消息UUID，因此用独立投递编号并保留 `id:null`；历史导入继续保留真实消息ID。`delivery`是来源声明，不能单凭该字段证明执行在云端，执行证据必须另看真实托管任务运行及GitHub提交。原文与交付课程必须逐字一致，不重新生成替代内容。

正文包含期号、中文年月日、今日主题、三篇正文、连续Q1—Q9、统一参考答案章节和九份完整原答案、编号结束标记。校验失败、日期不符、来源不符和同一期正文冲突均拒绝写入；不覆盖原档。当天文件已存在时核对并复用，避免重跑另生一期。GitHub写入失败时仍交付原课程并报告同步失败。

提交后Actions执行导入、Python/Node回归、完整历史门槛（保留前18期并检查新增期号）、构建与站内链接检查、保存新原文及同步记录、部署Pages。10:15/10:45另检查当天文件；GitHub定时执行可能排队，不能保证精确到分钟。缺少当日原文会明确失败并保留旧网站。

## 实际验收与限制

从原任务“立即运行”读取第18期并创建云端回执，提交 `89a300620bac0bc92efae27344a6af00235ba324`；[Actions #3](https://github.com/tengtenglf/ai-algorithm-library/actions/runs/40467367128) 的build、deploy均成功，原文重复导入新增0。回执原消息ID及SHA256经独立GitHub回读核对。没有从本机代写该回执。

这是2026-10-27已有原文的托管读写和发布验证，当次没有另生第19期。2026-10-28新课的实际补齐与投递验收见下文；下一次10点自然触发仍需实际观测。新投递格式的全文保留、来源校验、拒绝伪造消息ID和去重已用行为测试覆盖。历史分享只用于恢复历史，不作为未来课程动态来源。

## 故障恢复

在ChatGPT“定时任务”打开原任务查看错误。权限失效时恢复原有GitHub连接，保持相同仓库范围；不要把令牌写进指令或仓库。补发时直接重跑原任务：有完整今日入站则核对去重，没有则补交原课程。GitHub发布失败可在Actions重跑失败工作；不要改写历史内容或跳过检查。若已有完整原文但当前不可读取，保留现状并报告，不生成替代版，不依赖本机或分享快照。若当天尚无完整课程，由原任务按教学规则制作当天正本；空运行记录不等于已生成课程。

### 2026-10-28断点与恢复入口

当天检查时，main没有`content/inbox/2026-10-28.json`，课程仍为18期、162问/162答。[实际手动触发运行](https://github.com/tengtenglf/ai-algorithm-library/actions/runs/40647546964)在导入步骤报当日文件不存在，Pages未部署。工作流已启用，但截至该次排查没有任何schedule事件运行；缺少平台调度内部证据，不能归因于cron语法或权限。将原10:15和10:45拆为两个等价cron重新登记，不代表未来自然触发已验证。

Actions的 **Run workflow** 现在可填写`target_date`，明确指定已经归档的原文日期；留空仍严格检查北京时间今天。补投2026-10-28时先提交该日期的完整原文，再选择`2026-10-28`运行。不得用2026-10-27的成功运行宣称2026-10-28已同步。文件名、正文日期及投递来源必须一致，日期不能指向未来，同一期冲突仍拒绝覆盖。CLI对应`python scripts/update.py --date 2026-10-28 --report sync-report.json`。

失败运行也上传`original-course-sync-evidence`并在Summary显示`status=failed`和失败原因；成功入库账本及旧站保持原样。`audit.json`检查已归档历史完整性，不证明今天已经到件，必须同时核对`sync.json.target_date`、当天inbox和实际运行结果。

若原ChatGPT任务停在GitHub操作的安全审批，必须由用户在该操作上审阅后继续；本仓库和Actions不能绕过平台审批。2026-10-28在原任务编辑器核实：当前长期说明已无2026-10-27单次重投分支，教学及每日归档规则完整。初次排查未改写任务说明；随后同日按用户要求补上空输出判定、原文优先补投、失败仍交付完整课程的规则，保留教学要求与每日10:00时间。原文已生成时只能复用同一份全文，不重新生成替代版。仅当原文及来源可读取时才能创建缺失的inbox；无法读取时停止并保留旧站，不要求令牌。


同日进一步在ChatGPT Scheduled确认原任务`6ac9e53a5cdc8191b955c5a84cdc3c2f`处于已暂停；已恢复为活跃，界面显示下一次为北京时间2026-10-29 10:00。暂停发生的时间和原因不可从当前界面追溯，不能据此断言当天10点的完整调度历史。

修复提交`bb671a5d2359fe78c11037754ceea1b71f4dea3a`的[push验收](https://github.com/tengtenglf/ai-algorithm-library/actions/runs/40648162088)明确拒绝缺失的2026-10-28原文，Summary及诊断附件成功保存；[指定2026-10-27的恢复验收](https://github.com/tengtenglf/ai-algorithm-library/actions/runs/40648332615)的build和deploy均成功，23项Python测试、2项Node测试及完整历史校验通过。线上audit.json、sync.json和data.json均返回HTTP 200，18期正文与162问/162答逐项与修复前原档一致；sync.json.target_date仍为2026-10-27。这是已有原文的发布验证，不是2026-10-28新课发布。该阶段未生成替代课程，当时2026-10-28原文尚未到件。随后当天补齐已通过以下验收；下一次自然定时触发仍待实际观测。

## 2026-10-28今日补齐已发布

用户明确确认未看到今日完整课程，并要求由原任务补齐。补齐请求发回原聊天执行，原任务实际创建当日入站文件，提交 [`63d712d90e16fe7d7fc275ec73a932cfbe1ec3a5`](https://github.com/tengtenglf/ai-algorithm-library/commit/63d712d90e16fe7d7fc275ec73a932cfbe1ec3a5)；并非在维护仓库的会话另造替代内容。第19期主题为“知识越来越多，怎样学会新东西，又不把旧本领弄丢？”，三课为Language Models Need Sleep、MDL与Hamming Code，九问九答齐全。

[实际push运行40652005229](https://github.com/tengtenglf/ai-algorithm-library/actions/runs/40652005229)的build与deploy均成功：新增1期，23项Python回归、2项Node回归、完整历史校验及859个站内链接通过。Actions将新原文和账本保存为提交`4d6392bf3c56c1b57a2eb791bf450cb42a0ba5e3`。

北京时间15:47独立读取在线audit.json、sync.json、data.json、courses/019.html及originals/019.md均为HTTP 200。网站19期、171问、171答；sync.json.target_date为2026-10-28。GitHub入站正文、在线数据正文及原文下载逐字一致，UTF-8 SHA256为`c88c1874d300894f67ea9211080c7bee434154ab94baeaa16bbc6cc260f01a0c`。前18期正文及162份问题/答案逐项与修复前原档一致。

原定时任务保持活跃，每天北京时间10:00，界面下次为2026-10-29 10:00。任务说明已保存并回读核对：同日优先复用原文；任务状态、空输出或需要操作不能冒充完整课程；生成与发布仅使用云端联网及现有GitHub连接，失败仍完整交付课程。未改变安全审批、连接权限或其他任务。本次新课证明原聊天生产→GitHub入站→Actions→Pages路径可执行；未来自然10:00触发及GitHub10:15/10:45触发尚未发生，不能宣称已验证或保证准点。
