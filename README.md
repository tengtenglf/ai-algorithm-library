# AI 算法寓言 · 学习书架

收录课程原始全文、原题与原答案，提供全文检索、折叠答案、D+1/D+7/D+30复习与进度备份。当前恢复第15—18期，前14期仍待取回；没有使用摘要或重新生成的内容冒充原文。

## 网站

[打开学习书架](https://tengtenglf.github.io/ai-algorithm-library/)

进度保存在当前浏览器，可导出和导入。不同域名和设备的进度相互独立。

## 自动更新

授权本机跟进读取原ChatGPT聊天，将当天原始消息保存至 `content/inbox/YYYY-MM-DD.json`，通过已连接GitHub账号提交。GitHub Actions消费入站原文，校验9道原题与9份原答案、保存版本历史、执行测试、构建并发布GitHub Pages。工作流也会在北京时间10:15与10:45检查当天入站文件；缺少当天原文会明确失败并保留已发布版本。

这是“本机读取→GitHub入站→Actions导入与发布”路径；ChatGPT定时任务直接向外推送的通道尚未验证。将云端导入发布与未来本机定时运行分别验收。

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

`python3 scripts/library.py audit --require-complete` 必须在补齐前14期后才会通过。普通构建成功不代表18期完整。补齐后可设置仓库变量 `REQUIRE_COMPLETE_HISTORY=true`，将其设为发布门槛。

原聊天内部引用不能还原外部网址时会显示“未解析”；完整原文下载保留原始引用。课程研究事实未重新审校。KaTeX资源随站点托管，并保留原许可证。
