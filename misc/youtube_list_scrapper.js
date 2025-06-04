
let allresult = [];
let elements = document.querySelectorAll('ytd-rich-item-renderer');
let promises = Array.from(elements).map(async (card, index) => {
  let ocr = async img_url => {
    let uploadUrl = 'http://127.0.0.1:8000/ocr';
    try {
      // 1. 下载文件
      const response = await fetch(img_url);
      if (!response.ok) {
          throw new Error(`下载失败: ${response.statusText}`);
      }

      // 2. 获取文件名（从 URL 或响应头中提取）
      const contentDisposition = response.headers.get('content-disposition');
      let fileName = 'downloaded_file';
      if (contentDisposition) {
          const match = contentDisposition.match(/filename="(.+)"/);
          if (match) fileName = match[1];
      } else {
          fileName = img_url.split('/').pop().split('?')[0] || fileName;
      }

      // 3. 将响应转换为 Blob
      const blob = await response.blob();

      // 4. 创建 File 对象（模拟临时文件）
      const file = new File([blob], fileName, { type: blob.type });

      // 5. 构造 FormData 用于上传
      const formData = new FormData();
      formData.append('file', file);

      // 6. 调用上传接口
      const uploadResponse = await fetch(uploadUrl, {
        method: 'POST',
        body: formData
      });

      if (!uploadResponse.ok) {
        throw new Error(`上传失败: ${uploadResponse.statusText}`);
      }

      const result = await uploadResponse.json();
      console.log('上传成功:', result);
      return result.text;
    } catch (error) {
      console.error('上传失败:', error);
      return null;
    }
  };

  let title = card.querySelector('a[id="video-title-link"]').innerText;
  let views = card.querySelectorAll('div[id="metadata-line"] span')[0].innerText;
  let created = card.querySelectorAll('div[id="metadata-line"] span')[1].innerText;
  let img_url = card.querySelector('a#thumbnail img').getAttribute('src');
  let cover_text = await ocr(img_url);
  let url = (u => {
    let a = document.createElement('a');
    a.href = u;
    return a.href;
  })(card.querySelector('a[id="video-title-link"]').getAttribute('href'));
  allresult.push({
    title,
    views,
    created,
    cover_text,
    url
  });
  return index;
});

await Promise.all(promises);

let downloadArrayAsJSON = (allresult, fileName = 'data.json') => {
  try {
    // 1. 将数组转换为 JSON 字符串
    const jsonString = JSON.stringify(allresult, null, 2); // null, 2 用于格式化 JSON，增加可读性

    // 2. 创建 Blob 对象，指定类型为 application/json
    const blob = new Blob([jsonString], { type: 'application/json' });

    // 3. 创建临时 URL
    const url = URL.createObjectURL(blob);

    // 4. 创建一个隐藏的 <a> 元素触发下载
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName; // 设置下载文件名
    document.body.appendChild(link); // 将 link 添加到 DOM
    link.click(); // 触发下载

    // 5. 清理
    document.body.removeChild(link); // 移除临时 link
    URL.revokeObjectURL(url); // 释放 Blob URL
  } catch (error) {
    console.error('下载 JSON 文件失败:', error);
  }
};
let authorName = document.querySelector('div[id="page-header"] h1').innerText;
downloadArrayAsJSON(allresult, `${authorName}.json`);
