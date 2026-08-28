> 来源: [https://milvus.io/api-reference/pymilvus/v2.6.x/About.md(PyMilvus](https://milvus.io/api-reference/pymilvus/v2.6.x/About.md\(PyMilvus) SDK v 2.6.x 官方文档)

PyMilvus 是 Milvus 向量数据库的 **Python SDK**,源码开源,托管于 [GitHub](https://github.com/milvus-io/pymilvus)。

- 本版本支持两种与 Milvus 交互的方式,可按需选择:
    1. **MilvusClient**(推荐,更简洁的客户端 API)
    2. **原始 ORM 模块**(传统方式)

# 安装

```bash
uv pip pymilvus==v2.6.17
```

安装后检查版本:

```python
from pymilvus import __version__

print(__version__)

# v2.6.17
```

如需使用**嵌入(Embedding)模型库**,安装附带 model 依赖:

```shell
pip install pymilvus[model]
```

# 连接 Milvus

使用 `MilvusClient` 连接 Milvus 服务端,支持三种认证场景:

```python
from pymilvus import MilvusClient

# 场景一:未开启认证
client = MilvusClient("http://localhost:19530")

# 场景二:开启认证,使用 root 用户
client = MilvusClient(
    uri="http://localhost:19530",
    token="root:Milvus",
    db_name="default"
)

# 场景三:开启认证,使用非 root 用户(自定义用户名/密码)
client = MilvusClient(
    uri="http://localhost:19530",
    token="user:password",  # 替换为你自己的 token
    db_name="default"
)
```

要点:
- `uri` 为 Milvus 服务地址(默认端口 19530)
- `token` 格式为 `用户名:密码`
- `db_name` 指定要连接的数据库,默认 `default`

# 索引建立

向量检索依赖索引加速。流程: `prepare_index_params()` 准备参数 → `add_index()` 添加索引定义 → `create_index()` 建索引。

## 索引类型(IndexType 枚举)

| 索引类型 | 适用场景 |
|---|---|
| FLAT | 暴力搜索,精度最高、速度最慢,适合小数据集 |
| IVF_FLAT / IVF_PQ / IVF_SQ 8 / IVF_RABITQ / SCANN | 倒排索引,聚类加速,大数据量 |
| HNSW / HNSW_SQ / HNSW_PQ / HNSW_PRQ | 图索引,高召回率、低延迟 |
| DISKANN | 磁盘索引,超大规模数据 |
| BIN_FLAT / BIN_IVF_FLAT | 二进制向量 |
| SPARSE_INVERTED_INDEX / SPARSE_WAND | 稀疏向量 |
| INVERTED / STL_SORT / TRIE | 标量字段:INVERTED 通用、STL_SORT 数值、TRIE 用于 VarChar |
| AUTOINDEX | 自动选择最优索引 |
| GPU_BRUTE_FORCE / GPU_IVF_FLAT / GPU_IVF_PQ / GPU_CAGRA | GPU 索引 |

## 准备索引参数与建索引

```python
from pymilvus import MilvusClient, DataType

client = MilvusClient(
    uri="http://localhost:19530",
    token="root:Milvus"
)

# 1. 创建 schema 并添加字段
schema = MilvusClient.create_schema(
    auto_id=False,
    enable_dynamic_field=False,
)
schema.add_field(field_name="my_id", datatype=DataType.INT64, is_primary=True)
schema.add_field(field_name="my_vector", datatype=DataType.FLOAT_VECTOR, dim=5)

# 2. 准备索引参数
index_params = client.prepare_index_params()

# 3. 添加索引定义
# - 标量字段
index_params.add_index(
    field_name="my_id",
    index_type="STL_SORT"
)

# - 向量字段(metric_type 与检索时保持一致)
index_params.add_index(
    field_name="my_vector",
    index_type="IVF_FLAT",
    metric_type="L2",
    params={"nlist": 1024}
)

# 4. 创建集合
client.create_collection(
    collection_name="customized_setup",
    schema=schema
)

# 5. 建立索引
client.create_index(
    collection_name="customized_setup",
    index_params=index_params
)
```

## create_index() 参数

- `collection_name` (必填):集合名。
- `index_params` (必填): `IndexParams` 对象(含一个或多个 `IndexParam`)。
- `timeout`:超时时间, `None` 表示等待响应或出错。
- `kwargs` 中 `sync(bool)`:默认 `True` 同步等待索引完全构建;设为 `False` 则立即返回、后台构建,用 `describe_index()` 查询进度。

## 索引管理

```python
# 列出集合的全部索引(可按字段过滤)
client.list_indexes(collection_name="customized_setup")
# ['my_id', 'my_vector']

# 描述指定索引
client.describe_index(
    collection_name="customized_setup",
    index_name="my_vector"
)
# {
#     'nlist': '1024',
#     'index_type': 'IVF_FLAT',
#     'metric_type': 'L2',
#     'field_name': 'my_vector',
#     'index_name': 'my_vector'
# }

# 删除索引
client.drop_index(
    collection_name="customized_setup",
    index_name="my_vector"
)
```

`describe_index()` 返回字段: `index_type` (索引算法)、`metric_type` (相似度度量,IP/L 2/COSINE)、`nlist`、`total_rows` / `indexed_rows` / `pending_index_rows` (索引进度)、`state` (构建状态)、`field_name`、`index_name`。

## 向量相似度检索 search()

在集合中查找与查询向量最相似的实体,可叠加标量过滤。

主要参数:

- `collection_name` (必填):集合名。
- `data` (必填,与 `ids` 互斥):查询向量列表, `List[List[float]]`。
- `ids`:按主键对应的向量检索(与 `data` 互斥)。
- `anns_field`:目标向量字段名。
- `filter`:标量过滤表达式,如 `'color like "red%"'`;空串表示不过滤。
- `limit`:返回数量(默认 10),与 `offset` 配合分页, `limit + offset < 16384`。
- `output_fields`:返回结果中携带的字段,默认仅主键。
- `search_params`: `metric_type` (与建索引时一致,L 2/IP/COSINE)、`radius` / `range_filter` (范围检索)、`group_by_field` / `group_size` / `strict_group_size` (分组检索)。
- `partition_names`:仅检索指定分区(不适用于 Milvus Lite)。
- `ranker` / `highlighter`:排序器与高亮。

## 基本检索

```python
from pymilvus import MilvusClient

client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")

# 创建集合(自动建索引)、插入数据
client.create_collection(collection_name="test_collection", dimension=5)
client.insert(collection_name="test_collection", data=[...])  # {'insert_count': 10}

search_params = {
    "metric_type": "IP",
    "params": {}
}

res = client.search(
    collection_name="test_collection",
    data=[[0.05, 0.23, 0.07, 0.45, 0.13]],
    limit=3,
    search_params=search_params
)
# [[{'id': 7, 'distance': 0.4801957309246063, 'entity': {}},
#   {'id': 2, 'distance': 0.3205878734588623, 'entity': {}},
#   {'id': 1, 'distance': 0.2993225157260895, 'entity': {}}]]
```

##常用变体

```python
# 带标量过滤
res = client.search(
    collection_name="test_collection",
    data=[[0.05, 0.23, 0.07, 0.45, 0.13]],
    limit=3,
    filter='color like "red%"',
    search_params=search_params
)

# 分页(offset)
res = client.search(
    collection_name="test_collection",
    data=[[0.05, 0.23, 0.07, 0.45, 0.13]],
    limit=3,
    offset=3,
    search_params=search_params
)

# 指定输出字段(entity 中携带 color 与 vector)
res = client.search(
    collection_name="test_collection",
    data=[[0.05, 0.23, 0.07, 0.45, 0.13]],
    limit=3,
    output_fields=["vector", "color"],
    search_params=search_params
)

# 范围检索(radius 下界,range_filter 上界;L2 度量时两者关系相反)
search_params = {
    "metric_type": "IP",
    "params": {
        "radius": 0.1,
        "range_filter": 0.8
    }
}
```

返回结构: `list[dict]`,每条含 `id`、`distance` (相似度)与 `entity` (output_fields 指定的字段)。

## 标量查询

按布尔表达式做标量过滤查询,不涉及相似度计算。

参数: `collection_name` (必填)、`filter` (必填,可传空串)、`output_fields`、`timeout`、`partition_names`、`consistency_level` (一致性级别:Strong(0)/Bounded(1)/Session(2)/Eventually(3))。

```python
# 无条件查询前 5 条
res = client.query(
    collection_name="test_collection",
    filter="",
    limit=5,
)

# 按主键过滤
res = client.query(
    collection_name="test_collection",
    filter="id in [6,7,8]",
)

# 指定输出字段
res = client.query(
    collection_name="test_collection",
    filter="id in [6,7,8]",
    output_fields=["id", "vector"],
)

# 输出全部字段
res = client.query(
    collection_name="test_collection",
    filter="id < 5",
    output_fields=["*"]
)

# 统计符合条件的实体数量
res = client.query(
    collection_name="test_collection",
    filter='color like "red_%"',
    output_fields=["count(*)"]
)
# [{'count(*)': 3}]
```

## 混合检索 hybrid_search()

对多个向量字段(如稠密向量 + 稀疏向量)分别执行 ANN 搜索,再用 `ranker` 合并排序。

```python
from pymilvus import AnnSearchRequest, MilvusClient

client = MilvusClient(uri="http://localhost:19530")

request = AnnSearchRequest(
    data=[[0.1, 0.2, 0.3]],
    anns_field="vector",
    param={"metric_type": "COSINE"},
    limit=10,
    filter='category == "paper"',
)

results = client.hybrid_search(
    collection_name="book_chunks",
    reqs=[request],
    ranker=None,
    limit=10,
)
```

参数:

- `collection_name` (必填):集合名。
- `reqs` (必填): `AnnSearchRequest` 列表。构造参数: `data` (查询向量或稀疏矩阵)、`anns_field` (向量字段名)、`param` (检索参数,如 metric_type)、`limit` (该请求返回数)、`expr` / `filter` (过滤表达式,二者取其一, `expr` 与 `filter` 不能同时提供)。
- `ranker` (必填):合并与排序策略(`BaseRanker` 或 `Function`)。
- `limit`:最终返回条数(topk)。
- `output_fields` / `partition_names` / `timeout` / `kwargs` (分页 offset、一致性级别等)。

返回: `SearchResult` 对象,即合并排序后的检索结果。