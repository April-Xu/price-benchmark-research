# 比价主数据 Schema

每条记录代表一个“厂商 × 目标区域 × 产品/规格 × 计费方式”的唯一价格格。建议用 JSONL，一行一条记录，供 `scripts/check_price_matrix.py` 校验。

## 必填字段

| 字段 | 含义 |
| --- | --- |
| `provider` | 厂商名称，全文统一 |
| `target_region` | 用户要求比较的目标区域；没有区域时填 `global` |
| `product` | 产品或服务名称 |
| `target_spec` | 用户要求的规格、套餐或用量，不写厂商SKU名 |
| `billing_dimension` | 计价维度，如 `hour`、`month`、`year`、`GB`、`GiB`、`10k_requests`、`seat_month` |
| `payment_term` | `on_demand`、`monthly`、`annual_commitment`、`package`、`free_tier`、`other` |
| `currency` | ISO三字母币种，如 `USD` |
| `status` | 匹配状态，见下表 |
| `source_price_url` | 已打开核验的价格页、API或计算器URL |
| `source_spec_url` | 规格、套餐或服务条款URL；价格页已含规格时可相同 |
| `queried_at` | 查询日期，格式 `YYYY-MM-DD` |

## 价格字段

- `list_price`：公开刊例原价。取不到但存在近似价时填 `null`，不要填0。
- `promo_price`：促销/折扣价；必须同时写 `promo_conditions`。
- `substitute_price`：替代SKU、套餐或参考区域的价格；必须同时写 `substitute_of`、`substitute_reason`、`difference_note`。
- `standardized_price`：为比较换算后的价格；必须写 `standardized_unit`、`currency` 和 `formula`。
- `monthly_equivalent_hours`：只有用小时价折算连续运行月费时填写，例如730；真实包月价不要用年承诺价折算。
- `include_in_average`：布尔值。默认只有目标区域精确价为 `true`；异区参考、无法在目标区域采购、口径不一致的记录填 `false`。若精确价因配对样本等原因被排除，需填写 `average_exclusion_reason`。

## 状态枚举

| `status` | 使用条件 |
| --- | --- |
| `exact` | 目标区域、目标规格/套餐和计费条件均匹配 |
| `approximate` | 同一目标区域可购买，但配置、套餐、层级、承诺条件或计量单位有差异 |
| `cross_generation` | 价格真实，但厂商不能在公开页面锁定用户要求的具体代际/型号 |
| `regional_reference` | 目标区域缺公开价，借用业务相关区域的同规格价格 |
| `channel_required` | 公开页不能取得价格，需要登录、销售报价、合同或账号库存确认 |
| `unavailable_public` | 已查公开目录和第二入口，未发现目标公开报价；不等同服务一定不可购买 |
| `unavailable_service` | 官方区域/服务目录明确显示该区域不提供该服务 |

## 通用核对维度

- **计算/算力**：CPU架构与代际、vCPU含义（物理核/线程）、内存、处理器是否可锁定、共享/独享、本地盘、云盘、网络性能、操作系统、实例价是否含盘和公网。
- **对象/块存储**：存储层、冗余/AZ、容量单位、最小计费、请求类型、取回、数据传输、生命周期和免费额度。
- **网络**：流量方向、源区域、目的地或大区、线路类型、公网IP/NAT/负载均衡是否另计、阶梯、免费额度和单位。
- **数据库/中间件**：实例规格、存储、备份、HA、版本/许可证、IOPS、连接数和承诺期。
- **SaaS/许可证**：席位类型、套餐层级、功能包、计费周期、合同期、用户数下限、超额单价、税费、折扣资格和包含/不包含服务。

## 记录原则

1. 原价、促销价、替代价、标准化价分字段存储，不互相覆盖。
2. 一条记录只能表达一个计费维度；小时价、月费、年费分别建记录。
3. 同一SKU同时匹配多个目标规格时，要在 `difference_note` 写明复用关系，不能当作多个独立机型证据。
4. 统一地区价只有在官方条款明确覆盖目标区域时才可作为 `exact` 或 `approximate`；否则用 `regional_reference` 或 `channel_required`。
5. 不保存个人登录过程、手机号、cookie、token或账号信息。
