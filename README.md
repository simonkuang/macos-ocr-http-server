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

如果你希望我同时生成配套的 `requirements.txt` 和 HTML 模板，可以继续告诉我。

