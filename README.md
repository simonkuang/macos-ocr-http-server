借用 MacOS 中的 Vision 库，完成 OCR 的 python HTTP server。

---

### ✅ 核心变更

* 删除了异步 `process_image_async` 背景任务。
* `/upload` 路径已改为同步的 `/ocr`，并同步执行 OCR。
* 统一的同步式数据库写入。
* 更清晰的错误处理和返回格式。

---

### ✅ 更新后的 API 文档

#### `POST /ocr`

上传图片并执行 OCR。

* **请求参数**：

  * `file`: `UploadFile`（图片）
* **返回**：

```json
{
  "file_id": "xxx",
  "text": "识别的文本",
  "status": "done"
}
```

失败时：

```json
{
  "file_id": "xxx",
  "text": null,
  "status": "error",
  "error": "错误描述"
}
```

---

#### `GET /result/{file_id}`

根据文件 ID 查询 OCR 结果。

* **返回**：

```json
{
  "file_id": "xxx",
  "text": "识别的文本或null",
  "status": "done|error|not_found"
}
```

---

#### `GET /admin`

* 返回简易后台管理页面。

---

#### `POST /admin/delete`

* 表单参数：多个 `file_ids`。
* 删除文件和数据库记录。

---

## 🕷 爬虫脚本

### 1. Youtube 列表信息爬虫

**代码：** `/misc/youtube_list_scrapper.js`
**使用方法：**

0. 开启 MacOS OCR HTTP Server
1. 打开 youtube 的作者页面
2. 往下刷瀑布流，确保要采集的内容都加载完
3. 将 js 代码复制到浏览器的控制台里面，执行
4. 自动开启下载，保存采集到的数据
