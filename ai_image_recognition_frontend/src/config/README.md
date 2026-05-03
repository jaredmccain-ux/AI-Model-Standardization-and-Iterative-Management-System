# API配置管理说明

## 概述

这个配置系统允许您轻松地在本地开发环境和生产环境之间切换API地址，只需要修改一个文件中的一个变量。

## 文件结构

```
src/config/
├── api.js          # API配置管理文件
└── README.md        # 使用说明（本文件）
```

## 使用方法

### 1. 自动环境检测（推荐）

默认情况下，系统会自动检测当前运行环境：
- **本地开发**：当访问地址为 `localhost`、`127.0.0.1` 或 `192.168.x.x` 时，自动使用本地API地址
- **生产环境**：其他情况下使用生产环境API地址

### 2. 手动切换环境

如果需要强制指定环境，请修改 `src/config/api.js` 文件中的 `FORCE_ENV` 变量：

```javascript
// 在 api.js 文件中找到这一行：
const FORCE_ENV = 'auto' // 当前设置

// 修改为以下值之一：
const FORCE_ENV = 'development'  // 强制使用本地环境
const FORCE_ENV = 'production'   // 强制使用生产环境
const FORCE_ENV = 'auto'         // 自动检测（推荐）
```

### 3. 修改API地址

如果需要修改API地址，请在 `src/config/api.js` 文件中的 `ENV_CONFIG` 对象中修改：

```javascript
const ENV_CONFIG = {
  development: {
    API_BASE_URL: 'http://localhost:8000',    // 本地后端域名/端口
    TIMEOUT: 30000
  },
  production: {
    API_BASE_URL: window.location.origin,      // 线上同域部署（通过 Nginx 将 `/api` 代理到后端）
    TIMEOUT: 30000
  }
}
```

注意：请求路径统一以 `/api/...` 形式拼接，例如：

```js
// axios with baseURL
api.post('/api/training/regular', payload)

// 直接使用基址
axios.post(`${API_BASE_URL}/api/visiofirm/annotate`, formData)
```

## 在组件中使用

```javascript
// 导入API配置
import { API_BASE_URL, TIMEOUT } from '@/config/api.js'

// 使用配置
const apiUrl = API_BASE_URL
const requestTimeout = TIMEOUT
```

## 调试信息

在开发模式下，控制台会显示当前的API配置信息，帮助您确认配置是否正确。

## 常见问题

### Q: 如何快速切换到本地测试？
A: 将 `FORCE_ENV` 设置为 `'development'`

### Q: 如何快速切换到生产环境？
A: 将 `FORCE_ENV` 设置为 `'production'`

### Q: 如何添加新的环境（如测试环境）？
A: 在 `ENV_CONFIG` 中添加新的环境配置，然后修改 `FORCE_ENV` 为新环境名称

```javascript
const ENV_CONFIG = {
  development: { API_BASE_URL: 'http://localhost:8000', TIMEOUT: 30000 },
  testing: { API_BASE_URL: 'http://test.example.com:8000', TIMEOUT: 30000 },
  production: { API_BASE_URL: window.location.origin, TIMEOUT: 30000 }
}

// 使用测试环境
const FORCE_ENV = 'testing'
```

## 注意事项

1. 修改配置后需要重新构建项目（`npm run build`）
2. 在生产环境部署时，确保 `FORCE_ENV` 设置正确
3. 建议在版本控制中保持 `FORCE_ENV = 'auto'`，避免影响其他开发者
