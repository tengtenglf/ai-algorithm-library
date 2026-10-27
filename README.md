# AI 算法寓言 · 学习书架

收录课程原始全文、原题与原答案，提供全文检索、折叠答案、D+1/D+7/D+30复习与进度备份。已从原聊天分享恢复第1—18期，共162道原题与162份原答案；没有使用摘要或重新生成的内容冒充原文。分段推送的课程按原消息顺序无改写拼接，保留片段ID与校验哈希。

## 网站

[打开学习书架](https://tengtenglf.github.io/ai-algorithm-library/)

进度保存在当前浏览器，可导出和导入。不同域名和设备的进度相互独立。

## 自动更新

原ChatGPT任务每天北京时间10:00在原聊天中生成课程，随后通过已连接GitHub直接创建 `content/inbox/YYYY-MM-DD.json`。GitHub Actions校验九问九答、保存版本历史、构建并发布；另在10:15与10:45检查当天入站。主路径全在云端，不依赖电脑开机。缺少当天完整原文会停止发布并保留现有网站。

2026-10-27已从原任务的“立即运行”完成云端原文读取、GitHub写入和Pages发布：[真实运行记录](https://github.com/tengtenglf/ai-algorithm-library/actions/runs/40467367128)。本次复用已归档的第18期，没有另生第19期；下一次10点自然定时触发尚未观测。[完整合同与恢复方法](docs/CLOUD_UPDATE.md)。

同一期相同内容自动去重，不改写原文；同一期不同内容会停止导入，需要人工审校。来源ID、原文SHA256和每次新增内容的同步证据均保存在Git历史。网页状态页提供最近一次入库记录；每次Actions运行同时保留同步证据附件。

## 本地验证

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
node --test tests/review.test.cjs
python3 scripts/library.py build
python3 scripts/library.py links
python3 -m http.server 8765 --directory dist
```

`python3 scripts/library.py audit --require-complete` 已通过18期完整性检查。工作流始终执行这一历史完整性门槛，避免历史课程悄悄丢失。原始片段及拼接证据见 `content/sources/shared-course-fragments.json`。

原聊天内部引用不能还原外部网址时会显示“未解析”；完整原文下载保留原始引用。课程研究事实未重新审校。KaTeX资源随站点托管，并保留原许可证。
