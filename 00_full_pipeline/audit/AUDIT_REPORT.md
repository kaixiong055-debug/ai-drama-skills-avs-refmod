# V5.0 全项目审计

修改开始前对原ZIP所有230个文件完整读取：1457081字节，162份唯一内容、68份完全重复副本；JSON遍历所有节点，Python解析全部AST与1090分支，文档检查全部段落并提取953规则段落。审计方法和每文件sha256/行数/节点数/决策见FILE_AUDIT.json；扫描时原包无独立tests/目录，其selftest与validation JSON在scripts/assets中也全部检查。

发现：h3-3d-drama-batch两个同名Skill；V3/V4.2/V4.3/V4.4目录、主README标题、metadata 5.0/6.1并存；Script里镜头语言/位置职责越界；manifest/segments/animation_plan复制冻结字段；三套avs_contract重复分叉；多个LOCK后处理注入器与旧状态字段；六正文栏限制与V5字段冲突；中文头英文正文而非两个完整独立语言；单镜默认与多镜例外描述存在残留矛盾；旧README本地链接有缺失。

处置：统一12层唯一ID；八份JSON按所有者与父hash连接；一个状态与事件重放引擎；两个同源语言renderer；profile取代互相矛盾默认；LOCK直接纳入生产数据而非修改MD作为事实。所有旧文件都有KEEP/REFACTOR/MERGE/DELETE决定，DELETE只移出活动目录，原字节仍在legacy/V4.4_original.zip。

旧6个selftest入口实际全部返回0。新验证另见VALIDATION_REPORT.json，不能由旧报告PASS代替。没有借用shuohao业务内容或外部素材；只采用用户给出的工程组织原则。实机H3/Studio生成未执行。
