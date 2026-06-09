# 股票基金知识学习网站

基于 Markdown 文档生成的静态学习站点，包含完整的股票基金投资知识体系。

## 项目结构

```
web/
├── index.html              # 主页面
├── css/
│   └── styles.css          # 样式（CSS 变量，支持暗色模式）
├── js/
│   ├── main.js             # 应用入口：渲染、导航、主题、事件
│   ├── toc.js              # 动态目录树与滚动高亮
│   ├── search.js           # 实时搜索
│   └── utils.js            # 工具函数
├── data/
│   └── content.js          # 课程内容数据（由 build_content.py 生成）
├── assets/
│   ├── images/             # 课程图片（52 张 PNG）
│   └── exercises/          # Python 练习代码（12 个 .py 文件）
├── build_content.py        # 内容构建脚本
└── README.md               # 本文件
```

## 使用方式

直接在浏览器中打开 `index.html` 即可。所有依赖从 CDN 加载：

- Font Awesome 6.5.1（图标）
- highlight.js 11.9.0（代码高亮）
- marked.js 11.1.1（Markdown 渲染）

## 功能

- 9 个章节、12 个小节、561 个二级/三级标题
- 左侧可折叠目录树，点击跳转
- 实时全文搜索（Ctrl+K 快捷键）
- 暗色/亮色主题切换（localStorage 持久化）
- 字体大小三档调节
- 代码块一键复制 + Python 文件下载
- 图片点击放大（灯箱）
- 阅读进度条 + 回到顶部
- 移动端响应式适配（侧边栏折叠/展开）

## 更新内容

1. 修改或新增 `.md` 文件
2. 将新的 `.png` 放入对应的 `assets/images/`
3. 将新的 `.py` 放入对应的 `assets/exercises/`
4. 运行 `python3 build_content.py` 重新生成 `data/content.js`
5. 刷新浏览器

## 技术栈

- 纯 HTML/CSS/JS（ES6 模块化）
- CSS 变量实现主题切换
- 无构建工具，零依赖安装
