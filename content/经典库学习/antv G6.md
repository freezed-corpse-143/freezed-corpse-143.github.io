
> 参考教程： https://g6.antv.antgroup.com/examples

# 使用 GPU 加速布局

目前支持 GPU 加速的布局算法有：`Fruchterman Layout` `GForce Layout`

首先安装 `@antv/layout-gpu`

```bash
npm install @antv/layout-gpu --save
```

引入并注册布局算法：

```javascript
import { register, Graph, ExtensionCategory } from '@antv/g6'; import { FruchtermanLayout } from '@antv/layout-gpu'; register(ExtensionCategory.LAYOUT, 'fruchterman-gpu', FruchtermanLayout);
```

初始化图并传入布局配置：

```javascript
const graph = new Graph({ // ... 其他配置
	layout: { 
		type: 'fruchterman-gpu', // ... 其他配置 
	}, 
});
```